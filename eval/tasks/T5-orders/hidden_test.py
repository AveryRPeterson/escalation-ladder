import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    with open(os.path.join(HERE, name)) as f:
        return json.load(f)


class H(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.want = load("hidden_expected.json")
        try:
            cls.got = load("report.json")
        except Exception as e:  # noqa
            cls.got = None
            cls.err = e

    def test_report_exists_and_is_object(self):
        self.assertIsInstance(self.got, dict, getattr(self, "err", None))

    def test_months_match(self):
        self.assertIsInstance(self.got, dict)
        self.assertEqual(sorted(self.got), sorted(self.want))

    def test_keys_ascending(self):
        self.assertIsInstance(self.got, dict)
        self.assertEqual(list(self.got), sorted(self.got))

    def test_each_month(self):
        self.assertIsInstance(self.got, dict)
        for month, w in self.want.items():
            with self.subTest(month=month):
                self.assertEqual(self.got.get(month), w)


if __name__ == "__main__":
    unittest.main()
