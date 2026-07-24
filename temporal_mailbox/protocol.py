from __future__ import annotations

import hashlib
import hmac
import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable

from .config import FRAME_VERSION, KEY_ID, PROTOCOL_VERSION
from .models import Loto7Result

SYNC_WORD = 0x829A
EPOCH = date(2020, 1, 1)
FRAME_BYTES = 16
FRAME_BITS = FRAME_BYTES * 8


class FrameError(ValueError):
    pass


def crc16_ccitt(data: bytes, initial: int = 0xFFFF) -> int:
    crc = initial
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def combination_rank(values: Iterable[int], n: int, k: int) -> int:
    combo = tuple(values)
    if len(combo) != k or tuple(sorted(combo)) != combo:
        raise ValueError("combination must be sorted and have exactly k values")
    if len(set(combo)) != k or any(value < 1 or value > n for value in combo):
        raise ValueError("combination values out of range")

    rank = 0
    previous = 0
    for index, value in enumerate(combo):
        remaining = k - index - 1
        for candidate in range(previous + 1, value):
            rank += math.comb(n - candidate, remaining)
        previous = value
    return rank


def combination_unrank(rank: int, n: int, k: int) -> tuple[int, ...]:
    maximum = math.comb(n, k)
    if rank < 0 or rank >= maximum:
        raise ValueError("rank out of range")

    values: list[int] = []
    candidate = 1
    remaining_rank = rank
    for index in range(k):
        remaining = k - index - 1
        while candidate <= n:
            count = math.comb(n - candidate, remaining)
            if remaining_rank < count:
                values.append(candidate)
                candidate += 1
                break
            remaining_rank -= count
            candidate += 1
    return tuple(values)


def _pack_header(result: Loto7Result) -> bytes:
    result.validate()
    days = (result.draw_date - EPOCH).days
    if not 0 <= days < (1 << 14):
        raise ValueError("draw date is outside the v1 encodable range")

    main_rank = combination_rank(result.main, 37, 7)
    remaining = tuple(number for number in range(1, 38) if number not in result.main)
    bonus_indices = tuple(sorted(remaining.index(number) + 1 for number in result.bonus))
    bonus_rank = combination_rank(bonus_indices, 30, 2)

    value = 0
    value |= (FRAME_VERSION & 0xF) << 60
    value |= (result.draw & 0xFFF) << 48
    value |= (days & 0x3FFF) << 34
    value |= (main_rank & 0xFFFFFF) << 10
    value |= (bonus_rank & 0x1FF) << 1
    return value.to_bytes(8, "big")


def encode_frame(result: Loto7Result, key: bytes) -> bytes:
    header = _pack_header(result)
    sync = SYNC_WORD.to_bytes(2, "big")
    tag = hmac.new(
        key,
        b"FG830|frame-auth|" + KEY_ID.encode("ascii") + b"|" + header,
        hashlib.sha256,
    ).digest()[:4]
    body = sync + header + tag
    crc = crc16_ccitt(body).to_bytes(2, "big")
    frame = body + crc
    if len(frame) != FRAME_BYTES:
        raise AssertionError("invalid frame length")
    return frame


def decode_frame(frame: bytes, key: bytes, source_url: str = "temporal-noise") -> Loto7Result:
    if len(frame) != FRAME_BYTES:
        raise FrameError("frame must be exactly 16 bytes")
    if int.from_bytes(frame[:2], "big") != SYNC_WORD:
        raise FrameError("sync mismatch")
    if crc16_ccitt(frame[:-2]) != int.from_bytes(frame[-2:], "big"):
        raise FrameError("CRC mismatch")

    header = frame[2:10]
    expected_tag = hmac.new(
        key,
        b"FG830|frame-auth|" + KEY_ID.encode("ascii") + b"|" + header,
        hashlib.sha256,
    ).digest()[:4]
    if not hmac.compare_digest(frame[10:14], expected_tag):
        raise FrameError("authentication tag mismatch")

    value = int.from_bytes(header, "big")
    version = (value >> 60) & 0xF
    if version != FRAME_VERSION:
        raise FrameError(f"unsupported frame version: {version}")
    draw = (value >> 48) & 0xFFF
    days = (value >> 34) & 0x3FFF
    main_rank = (value >> 10) & 0xFFFFFF
    bonus_rank = (value >> 1) & 0x1FF
    if value & 1:
        raise FrameError("reserved bit is not zero")

    try:
        main = combination_unrank(main_rank, 37, 7)
    except ValueError as exc:
        raise FrameError("invalid main-number rank") from exc
    remaining = tuple(number for number in range(1, 38) if number not in main)
    try:
        bonus_indices = combination_unrank(bonus_rank, 30, 2)
    except ValueError as exc:
        raise FrameError("invalid bonus-number rank") from exc
    bonus = tuple(sorted(remaining[index - 1] for index in bonus_indices))

    result = Loto7Result(
        draw=draw,
        draw_date=EPOCH + timedelta(days=days),
        main=main,
        bonus=bonus,
        source_url=source_url,
    )
    result.validate()
    return result


def bytes_to_bits(data: bytes) -> tuple[int, ...]:
    return tuple((byte >> shift) & 1 for byte in data for shift in range(7, -1, -1))


def bits_to_bytes(bits: Iterable[int]) -> bytes:
    values = tuple(int(bit) for bit in bits)
    if len(values) % 8:
        raise ValueError("bit length must be a multiple of eight")
    output = bytearray()
    for offset in range(0, len(values), 8):
        byte = 0
        for bit in values[offset : offset + 8]:
            if bit not in (0, 1):
                raise ValueError("bits must contain only zero or one")
            byte = (byte << 1) | bit
        output.append(byte)
    return bytes(output)


@dataclass(frozen=True)
class Chip:
    bit_index: int
    sample_index: int
    position: int
    pn: int
    value: int
    order_key: bytes


def chip_descriptor(
    key: bytes,
    day: date,
    bit_index: int,
    sample_index: int,
    noise_size: int,
) -> tuple[int, int, bytes]:
    if noise_size <= 0:
        raise ValueError("noise_size must be positive")
    digest = hmac.new(
        key,
        (
            f"{PROTOCOL_VERSION}|spread|{day.isoformat()}|"
            f"{bit_index}|{sample_index}"
        ).encode("ascii"),
        hashlib.sha256,
    ).digest()
    position = int.from_bytes(digest[:8], "big") % noise_size
    pn = digest[8] & 1
    return position, pn, digest[9:17]


def build_chip_plan(
    frame: bytes,
    key: bytes,
    day: date,
    noise_size: int,
    samples_per_bit: int,
) -> list[Chip]:
    bits = bytes_to_bits(frame)
    if len(bits) != FRAME_BITS:
        raise ValueError("frame size mismatch")
    plan: list[Chip] = []
    for bit_index, bit in enumerate(bits):
        for sample_index in range(samples_per_bit):
            position, pn, order_key = chip_descriptor(
                key, day, bit_index, sample_index, noise_size
            )
            plan.append(
                Chip(
                    bit_index=bit_index,
                    sample_index=sample_index,
                    position=position,
                    pn=pn,
                    value=bit ^ pn,
                    order_key=order_key,
                )
            )
    plan.sort(key=lambda chip: (chip.order_key, chip.bit_index, chip.sample_index))
    return plan
