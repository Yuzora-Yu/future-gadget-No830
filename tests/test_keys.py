from __future__ import annotations

import unittest

from temporal_mailbox.keys import decode_secret, generate_key


class KeyTests(unittest.TestCase):
    def test_generated_key_decodes(self) -> None:
        encoded, fingerprint = generate_key()
        self.assertEqual(len(decode_secret(encoded)), 32)
        self.assertEqual(len(fingerprint), 64)

    def test_short_key_rejected(self) -> None:
        with self.assertRaises(ValueError):
            decode_secret("abc")


if __name__ == "__main__":
    unittest.main()
