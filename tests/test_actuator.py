from __future__ import annotations

import unittest
from datetime import date

from temporal_mailbox.actuator import run_actuator
from temporal_mailbox.models import Loto7Result
from temporal_mailbox.protocol import encode_frame


class ActuatorTests(unittest.TestCase):
    def test_zero_duration_is_deterministic(self) -> None:
        key = b"k" * 32
        result = Loto7Result(
            draw=687,
            draw_date=date(2026, 7, 24),
            main=(15, 22, 23, 24, 25, 29, 36),
            bonus=(35, 37),
            source_url="fixture",
        )
        frame = encode_frame(result, key)
        first = run_actuator(frame, key, result.draw_date, 4096, 2, 0)
        second = run_actuator(frame, key, result.draw_date, 4096, 2, 0)
        self.assertEqual(first["plan_sha256"], second["plan_sha256"])
        self.assertEqual(first["transcript_sha256"], second["transcript_sha256"])
        self.assertEqual(first["network_writes"], 0)


if __name__ == "__main__":
    unittest.main()
