from __future__ import annotations

import hashlib
import os
import platform
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .actuator import run_actuator
from .config import (
    ACTUATOR_SECONDS,
    CONTROL_COUNT,
    DATA_DIR,
    JST,
    KEY_ID,
    MIZUHO_LOTO7_URL,
    NOISE_BYTES,
    NOISE_DIR,
    PROTOCOL_FILE,
    PROTOCOL_VERSION,
    RECEPTION_CUTOFF,
    RECEPTIONS_DIR,
    SAMPLES_PER_BIT,
    SOFTWARE_VERSION,
    STATUS_FILE,
    TRANSMISSION_GRACE_END,
    TRANSMISSION_TIME,
    TRANSMISSIONS_DIR,
    now_jst,
)
from .keys import key_fingerprint, load_secret
from .noise import collect_noise, load_compressed, save_compressed
from .protocol import decode_frame, encode_frame
from .receiver import evaluate_reception
from .result_fetcher import ResultNotPublished, fetch_official_result, parse_mizuho_text
from .storage import read_json, write_json


def _date_path(directory: Path, day: date, suffix: str = ".json") -> Path:
    return directory / f"{day.isoformat()}{suffix}"


def write_protocol(key: bytes) -> None:
    write_json(
        PROTOCOL_FILE,
        {
            "protocol_version": PROTOCOL_VERSION,
            "software_version": SOFTWARE_VERSION,
            "key_id": KEY_ID,
            "key_fingerprint": key_fingerprint(key),
            "frame": {
                "bytes": 16,
                "sync": "0x829A",
                "authenticated_tag_bits": 32,
                "crc": "CRC-16/CCITT-FALSE",
            },
            "receiver": {
                "noise_bytes": NOISE_BYTES,
                "samples_per_bit": SAMPLES_PER_BIT,
                "control_count": CONTROL_COUNT,
                "scheduled_jst": "Friday 09:00",
                "eligibility_cutoff_jst": "Friday 18:00",
            },
            "transmitter": {
                "result_check_starts_jst": "Friday 20:00",
                "retry_window_jst": "Friday 20:00 to Saturday 03:00",
                "official_source": MIZUHO_LOTO7_URL,
                "actuator_mode": "keyed equal-work local computation",
            },
            "rule": "Reception data is never modified after the official result is known.",
        },
    )


def receive(day: date | None = None) -> dict[str, Any]:
    key = load_secret()
    current = now_jst()
    target_day = day or current.date()

    if target_day != current.date():
        raise RuntimeError("historical or future reception dates are not allowed")
    if current.weekday() != 4 or target_day.weekday() != 4:
        raise RuntimeError("reception is defined only for the current Friday JST")
    if current.time() >= RECEPTION_CUTOFF:
        raise RuntimeError("reception cutoff has passed; do not create after-result reception data")

    record_path = _date_path(RECEPTIONS_DIR, target_day)
    if record_path.exists():
        return read_json(record_path, {})

    packet, metadata = collect_noise(NOISE_BYTES)
    noise_path = _date_path(NOISE_DIR, target_day, ".bin.zlib")
    save_compressed(packet, noise_path)
    evaluation = evaluate_reception(packet, key, target_day)
    record = {
        **evaluation,
        "collected_at_jst": current.isoformat(timespec="seconds"),
        "eligible_for_temporal_claim": True,
        "noise": {
            **metadata,
            "file": str(noise_path.relative_to(DATA_DIR)),
            "compressed_bytes": noise_path.stat().st_size,
        },
        "key_id": KEY_ID,
        "key_fingerprint": key_fingerprint(key),
        "fixed_before_result": True,
    }
    write_json(record_path, record)
    write_protocol(key)
    update_status()
    return record


def transmission_target(now: datetime | None = None) -> date | None:
    current = now or now_jst()
    if current.tzinfo is None:
        current = current.replace(tzinfo=JST)
    current = current.astimezone(JST)
    if current.weekday() == 4 and current.time() >= TRANSMISSION_TIME:
        return current.date()
    if current.weekday() == 5 and current.time() < TRANSMISSION_GRACE_END:
        return current.date() - timedelta(days=1)
    return None


def transmission_due(now: datetime | None = None) -> bool:
    day = transmission_target(now)
    return bool(day and not _date_path(TRANSMISSIONS_DIR, day).exists())


def _hamming_distance(left: bytes, right: bytes) -> int:
    if len(left) != len(right):
        raise ValueError("frames must have equal length")
    return sum((a ^ b).bit_count() for a, b in zip(left, right))


def transmit(
    day: date | None = None,
    fixture_text: str | None = None,
    force: bool = False,
    actuator_seconds: float | None = None,
    dry_run: bool = False,
) -> dict[str, Any] | None:
    key = load_secret()
    current = now_jst()
    target_day = day or transmission_target(current)
    if target_day is None:
        if not force:
            raise RuntimeError("outside the Friday 20:00–Saturday 03:00 JST transmission window")
        raise RuntimeError("--force requires --date")
    if target_day.weekday() != 4:
        raise RuntimeError("target draw date must be Friday JST")
    if fixture_text is not None and not dry_run:
        raise RuntimeError("fixture input is permitted only with --dry-run")

    transmission_path = _date_path(TRANSMISSIONS_DIR, target_day)
    if transmission_path.exists() and not dry_run:
        return read_json(transmission_path, {})

    try:
        result = (
            parse_mizuho_text(fixture_text, target_day)
            if fixture_text is not None
            else fetch_official_result(target_day)
        )
    except ResultNotPublished:
        return None

    result.validate()
    frame = encode_frame(result, key)
    decoded_check = decode_frame(frame, key)
    if (
        decoded_check.draw != result.draw
        or decoded_check.draw_date != result.draw_date
        or decoded_check.main != result.main
        or decoded_check.bonus != result.bonus
    ):
        raise AssertionError("encoded frame did not round-trip")

    duration = (
        float(os.getenv("ACTUATOR_SECONDS", ACTUATOR_SECONDS))
        if actuator_seconds is None
        else actuator_seconds
    )
    actuation = run_actuator(
        frame=frame,
        key=key,
        day=target_day,
        noise_size=NOISE_BYTES,
        samples_per_bit=SAMPLES_PER_BIT,
        duration_seconds=max(0.0, duration),
    )

    reception_path = _date_path(RECEPTIONS_DIR, target_day)
    reception = read_json(reception_path, {})
    received_frame_hex = reception.get("frame_hex", "")
    distance = None
    if isinstance(received_frame_hex, str) and len(received_frame_hex) == 32:
        try:
            distance = _hamming_distance(bytes.fromhex(received_frame_hex), frame)
        except ValueError:
            distance = None

    payload = result.canonical_payload()
    record = {
        "protocol_version": PROTOCOL_VERSION,
        "software_version": SOFTWARE_VERSION,
        "key_id": KEY_ID,
        "key_fingerprint": key_fingerprint(key),
        "draw": result.draw,
        "date": result.draw_date.isoformat(),
        "main": list(result.main),
        "bonus": list(result.bonus),
        "canonical_payload": payload,
        "payload_sha256": hashlib.sha256(payload.encode("ascii")).hexdigest(),
        "frame_hex": frame.hex(),
        "frame_sha256": hashlib.sha256(frame).hexdigest(),
        "official_source": result.source_url,
        "official_page_text_sha256": result.source_sha256,
        "checked_at_jst": current.isoformat(timespec="seconds"),
        "actuation": actuation,
        "reception_record_present": bool(reception),
        "received_target_hamming_distance": distance,
        "completed": True,
        "dry_run": dry_run,
    }
    if not dry_run:
        write_json(transmission_path, record)
        write_protocol(key)
        update_status()
    return record


def verify(day: date) -> dict[str, Any]:
    key = load_secret()
    reception_path = _date_path(RECEPTIONS_DIR, day)
    transmission_path = _date_path(TRANSMISSIONS_DIR, day)
    noise_path = _date_path(NOISE_DIR, day, ".bin.zlib")
    if not reception_path.exists() or not noise_path.exists():
        raise FileNotFoundError(f"no reception data for {day.isoformat()}")
    reception = read_json(reception_path, {})
    transmission = read_json(transmission_path, {})
    packet = load_compressed(noise_path)
    evaluation = evaluate_reception(packet, key, day)
    return {
        "date": day.isoformat(),
        "noise_sha256_matches": hashlib.sha256(packet).hexdigest()
        == reception.get("noise", {}).get("sha256"),
        "reception_reproduced": evaluation.get("frame_hex") == reception.get("frame_hex"),
        "transmission_present": bool(transmission),
    }


def doctor(allow_missing_key: bool = False) -> dict[str, Any]:
    key_ok = False
    fingerprint = None
    key_error = None
    try:
        key = load_secret()
        key_ok = True
        fingerprint = key_fingerprint(key)
    except (RuntimeError, ValueError) as exc:
        key_error = str(exc)
        if not allow_missing_key:
            raise

    return {
        "ok": key_ok or allow_missing_key,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "protocol_version": PROTOCOL_VERSION,
        "software_version": SOFTWARE_VERSION,
        "timezone": "JST (+09:00)",
        "now_jst": now_jst().isoformat(timespec="seconds"),
        "key_configured": key_ok,
        "key_fingerprint": fingerprint,
        "key_error": key_error,
        "data_directory": str(DATA_DIR),
        "official_source": MIZUHO_LOTO7_URL,
    }


def _latest_json(directory: Path) -> dict[str, Any] | None:
    files = sorted(directory.glob("????-??-??.json"))
    return read_json(files[-1], {}) if files else None


def update_status() -> dict[str, Any]:
    protocol = read_json(PROTOCOL_FILE, {})
    status = {
        "protocol_version": PROTOCOL_VERSION,
        "software_version": SOFTWARE_VERSION,
        "key_id": KEY_ID,
        "key_fingerprint": protocol.get("key_fingerprint"),
        "updated_at_jst": now_jst().isoformat(timespec="seconds"),
        "latest_reception": _latest_json(RECEPTIONS_DIR),
        "latest_transmission": _latest_json(TRANSMISSIONS_DIR),
    }
    write_json(STATUS_FILE, status)
    return status
