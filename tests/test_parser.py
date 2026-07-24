from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path

from temporal_mailbox.result_fetcher import ResultNotPublished, parse_mizuho_text


class ParserTests(unittest.TestCase):
    def test_fixture(self) -> None:
        fixture = Path("tests/fixtures/mizuho_687.html").read_text(encoding="utf-8")
        result = parse_mizuho_text(fixture, date(2026, 7, 24))
        self.assertEqual(result.draw, 687)
        self.assertEqual(result.main, (15, 22, 23, 24, 25, 29, 36))
        self.assertEqual(result.bonus, (35, 37))

    def test_not_published(self) -> None:
        with self.assertRaises(ResultNotPublished):
            parse_mizuho_text(
                "第686回 2026年7月17日 本数字 01 02 03 04 05 06 07 "
                "ボーナス数字 08 09",
                date(2026, 7, 24),
            )


if __name__ == "__main__":
    unittest.main()
