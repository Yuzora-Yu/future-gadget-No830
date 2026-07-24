from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from datetime import date
from typing import Any

from .config import CONTROL_COUNT, PROTOCOL_VERSION, SAMPLES_PER_BIT
from .models import Loto7Result
from .protocol import FRAME_BITS, FrameError, bits_to_bytes, chip_descriptor, decode_frame

CONTROL_SEED = b"FG830|public-placebo-controls|v1"


@dataclass(frozen=True)
class DecodeAttempt:
    frame: bytes
    bit_scores: tuple[int, ...]
    strength: float
    decoded: Loto7Result | None
    error: str


def decode_noise(
    packet: bytes,
    key: bytes,
    day: date,
    samples_per_bit: int = SAMPLES_PER_BIT,
) -> DecodeAttempt:
    if not packet:
        raise ValueError("empty noise packet")

    bits: list[int] = []
    scores: list[int] = []
    for bit_index in range(FRAME_BITS):
        score = 0
        for sample_index in range(samples_per_bit):
            position, pn, _ = chip_descriptor(
                key, day, bit_index, sample_index, len(packet)
            )
            estimated = (packet[position] & 1) ^ pn
            score += 1 if estimated else -1
        scores.append(score)
        bits.append(1 if score > 0 else 0)

    frame = bits_to_bytes(bits)
    denominator = math.sqrt(samples_per_bit)
    strength = sum(abs(score) / denominator for score in scores) / FRAME_BITS
    decoded: Loto7Result | None = None
    error = ""
    try:
        decoded = decode_frame(frame, key)
        if decoded.draw_date != day:
            error = "authenticated frame date does not match reception date"
            decoded = None
    except FrameError as exc:
        error = str(exc)

    return DecodeAttempt(
        frame=frame,
        bit_scores=tuple(scores),
        strength=round(strength, 6),
        decoded=decoded,
        error=error,
    )


def control_keys(count: int = CONTROL_COUNT) -> list[bytes]:
    return [
        hashlib.sha256(CONTROL_SEED + index.to_bytes(4, "big")).digest()
        for index in range(count)
    ]


def evaluate_reception(packet: bytes, key: bytes, day: date) -> dict[str, Any]:
    target = decode_noise(packet, key, day)
    controls = [decode_noise(packet, control, day) for control in control_keys()]
    target_rank = 1 + sum(control.strength > target.strength for control in controls)
    valid_controls = sum(control.decoded is not None for control in controls)

    decoded = None
    if target.decoded:
        decoded = {
            "draw": target.decoded.draw,
            "date": target.decoded.draw_date.isoformat(),
            "main": list(target.decoded.main),
            "bonus": list(target.decoded.bonus),
        }

    return {
        "protocol_version": PROTOCOL_VERSION,
        "date": day.isoformat(),
        "authenticated": target.decoded is not None,
        "decoded": decoded,
        "frame_hex": target.frame.hex(),
        "frame_sha256": hashlib.sha256(target.frame).hexdigest(),
        "bit_scores": list(target.bit_scores),
        "strength": target.strength,
        "rank": target_rank,
        "population": 1 + len(controls),
        "control_authenticated_frames": valid_controls,
        "decode_error": target.error,
    }
