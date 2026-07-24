from __future__ import annotations

import hashlib
import os
import time
import zlib
from pathlib import Path


def collect_noise(size: int) -> tuple[bytes, dict[str, object]]:
    if size < 4096:
        raise ValueError("noise size must be at least 4096 bytes")

    operating_system = os.urandom(size)
    jitter = bytearray()
    previous = time.perf_counter_ns()
    for index in range(16_384):
        digest = hashlib.blake2s(
            previous.to_bytes(8, "big") + index.to_bytes(4, "big"),
            digest_size=16,
        ).digest()
        current = time.perf_counter_ns()
        delta = current - previous
        jitter.extend(delta.to_bytes(8, "big", signed=False))
        jitter.extend(digest)
        previous = current

    mask = hashlib.shake_256(b"FG830|local-noise|" + bytes(jitter)).digest(size)
    packet = bytes(left ^ right for left, right in zip(operating_system, mask))
    metadata = {
        "bytes": len(packet),
        "sha256": hashlib.sha256(packet).hexdigest(),
        "jitter_samples": 16_384,
        "collector": "os.urandom XOR SHAKE256(perf_counter jitter)",
    }
    return packet, metadata


def save_compressed(packet: bytes, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(zlib.compress(packet, level=9))
    temporary.replace(path)


def load_compressed(path: Path) -> bytes:
    return zlib.decompress(path.read_bytes())
