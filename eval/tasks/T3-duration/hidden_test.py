import unittest
from durations import parse_duration

VALID = {
    "1h30m": 5400.0,
    "1H30M": 5400.0,
    "1h 30m": 5400.0,
    "1 h30 m": 5400.0,
    "  45s ": 45.0,
    "1w2d3h4m5s": 604800 + 2 * 86400 + 3 * 3600 + 4 * 60 + 5.0,
    "90m": 5400.0,
    "0": 0.0,
    " 0 ": 0.0,
    "0s": 0.0,
    "1.5h": 5400.0,
    "1h30.5m": 5430.0,
    "0.5s": 0.5,
    "2d12h": 2 * 86400 + 12 * 3600.0,
    "1M": 60.0,
    "10 S": 10.0,
}

INVALID = [
    "", "   ", "5", "1h30", "30m1h", "1h1h", ".5h", "5.h", "1.5h30m",
    "-5m", "+5m", "1h,30m", "1mo", "1y", "abc", "h", "1 5m", "1h 30", "m30",
    "1.2.3s", "0x10s",
]


class H(unittest.TestCase):
    def test_valid(self):
        for text, want in VALID.items():
            with self.subTest(text=text):
                self.assertAlmostEqual(parse_duration(text), want, places=6)

    def test_valid_cases_return_float(self):
        self.assertIsInstance(parse_duration("1h"), float)
        self.assertIsInstance(parse_duration("0"), float)

    def test_invalid(self):
        for text in INVALID:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse_duration(text)

    def test_non_string(self):
        for bad in (None, 5, 1.5, b"1h", ["1h"]):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    parse_duration(bad)

    def test_order_and_duplicates_specifically(self):
        self.assertEqual(parse_duration("1d1h1m1s"), 86400 + 3600 + 60 + 1)
        with self.assertRaises(ValueError):
            parse_duration("1s1m")
        with self.assertRaises(ValueError):
            parse_duration("1m1m")

    def test_fraction_only_last(self):
        self.assertAlmostEqual(parse_duration("2h0.25m"), 7200 + 15)
        with self.assertRaises(ValueError):
            parse_duration("0.5h1m")


if __name__ == "__main__":
    unittest.main()
