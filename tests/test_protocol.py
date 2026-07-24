from __future__ import annotations

import math
import unittest
from datetime import date

from temporal_mailbox.models import Loto7Result
from temporal_mailbox.protocol import (
    FRAME_BYTES,
    combination_rank,
    combination_unrank,
    decode_frame,
    encode_frame,
)


class ProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.key = bytes(range(32))
        self.result = Loto7Result(
            draw=687,
            draw_date=date(2026, 7, 24),
            main=(15, 22, 23, 24, 25, 29, 36),
            bonus=(35, 37),
            source_url="fixture",
        )

    def test_round_trip(self) -> None:
        frame = encode_frame(self.result, self.key)
        self.assertEqual(len(frame), FRAME_BYTES)
        decoded = decode_frame(frame, self.key)
        self.assertEqual(decoded.draw, self.result.draw)
        self.assertEqual(decoded.draw_date, self.result.draw_date)
        self.assertEqual(decoded.main, self.result.main)
        self.assertEqual(decoded.bonus, self.result.bonus)

    def test_wrong_key_rejected(self) -> None:
        frame = encode_frame(self.result, self.key)
        with self.assertRaises(ValueError):
            decode_frame(frame, b"x" * 32)

    def test_combinations_round_trip(self) -> None:
        samples = ((1, 2, 3), (1, 5, 9), (7, 8, 10), (8, 9, 10))
        for combo in samples:
            rank = combination_rank(combo, 10, 3)
            self.assertEqual(combination_unrank(rank, 10, 3), combo)
        self.assertEqual(combination_rank((8, 9, 10), 10, 3), math.comb(10, 3) - 1)


if __name__ == "__main__":
    unittest.main()
