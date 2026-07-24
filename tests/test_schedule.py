from __future__ import annotations

import unittest
from datetime import datetime

from temporal_mailbox.config import JST
from temporal_mailbox.service import transmission_target


class ScheduleTests(unittest.TestCase):
    def test_friday_before_20_is_not_due(self) -> None:
        self.assertIsNone(transmission_target(datetime(2026, 7, 24, 19, 59, tzinfo=JST)))

    def test_friday_at_20_targets_today(self) -> None:
        target = transmission_target(datetime(2026, 7, 24, 20, 0, tzinfo=JST))
        self.assertEqual(target.isoformat(), "2026-07-24")

    def test_saturday_grace_targets_previous_friday(self) -> None:
        target = transmission_target(datetime(2026, 7, 25, 2, 30, tzinfo=JST))
        self.assertEqual(target.isoformat(), "2026-07-24")

    def test_saturday_after_grace_is_not_due(self) -> None:
        self.assertIsNone(transmission_target(datetime(2026, 7, 25, 3, 0, tzinfo=JST)))


if __name__ == "__main__":
    unittest.main()
