import unittest
from ratelimit import SlidingWindowLimiter


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class Basic(unittest.TestCase):
    def test_limit(self):
        c = Clock()
        lim = SlidingWindowLimiter(2, 10, clock=c)
        self.assertTrue(lim.allow("a"))
        self.assertTrue(lim.allow("a"))
        self.assertFalse(lim.allow("a"))

    def test_keys_are_independent(self):
        c = Clock()
        lim = SlidingWindowLimiter(1, 10, clock=c)
        self.assertTrue(lim.allow("a"))
        self.assertTrue(lim.allow("b"))


if __name__ == "__main__":
    unittest.main()
