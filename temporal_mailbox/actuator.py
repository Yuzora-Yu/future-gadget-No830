from __future__ import annotations

import hashlib
import hmac
import time
from datetime import date
from typing import Any

from .protocol import build_chip_plan


def run_actuator(
    frame: bytes,
    key: bytes,
    day: date,
    noise_size: int,
    samples_per_bit: int,
    duration_seconds: float,
) -> dict[str, Any]:
    """Execute fixed-duration, equal-work keyed local computation.

    Both chip values perform the same number and type of operations. The only
    difference is a domain byte inside the hash chain. This function performs
    no network writes, messages, posts, or modifications to third-party systems.
    """

    plan = build_chip_plan(frame, key, day, noise_size, samples_per_bit)
    plan_digest = hashlib.sha256()
    transcript = hashlib.sha256(b"FG830|actuator-transcript|v1")
    start = time.monotonic()
    interval = duration_seconds / len(plan) if duration_seconds > 0 else 0.0

    for index, chip in enumerate(plan):
        descriptor = (
            chip.bit_index.to_bytes(1, "big")
            + chip.sample_index.to_bytes(2, "big")
            + chip.position.to_bytes(8, "big")
            + bytes((chip.pn, chip.value))
        )
        plan_digest.update(descriptor)

        state = hmac.new(
            key,
            b"FG830|actuate|" + bytes((chip.value,)) + descriptor,
            hashlib.sha256,
        ).digest()
        for round_index in range(4):
            state = hashlib.blake2s(
                bytes((chip.value, round_index)) + state,
                digest_size=32,
            ).digest()
        transcript.update(state)

        if interval:
            deadline = start + (index + 1) * interval
            remaining = deadline - time.monotonic()
            if remaining > 0.001:
                time.sleep(remaining - 0.0005)
            while time.monotonic() < deadline:
                pass

    elapsed = time.monotonic() - start
    return {
        "mode": "keyed-equal-work-local-modulation",
        "chips": len(plan),
        "duration_seconds_requested": duration_seconds,
        "duration_seconds_elapsed": round(elapsed, 6),
        "plan_sha256": plan_digest.hexdigest(),
        "transcript_sha256": transcript.hexdigest(),
        "network_writes": 0,
    }
