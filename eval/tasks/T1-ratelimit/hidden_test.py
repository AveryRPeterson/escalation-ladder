import unittest
from ratelimit import SlidingWindowLimiter


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def make(limit=2, window=10):
    c = Clock()
    return c, SlidingWindowLimiter(limit, window, clock=c)


class H(unittest.TestCase):
    def test_basic_limit(self):
        c, l = make()
        self.assertTrue(l.allow("a"))
        self.assertTrue(l.allow("a"))
        self.assertFalse(l.allow("a"))

    def test_event_expires_exactly_at_window_age(self):
        c, l = make(2, 10)
        self.assertTrue(l.allow("a"))
        c.t = 5
        self.assertTrue(l.allow("a"))
        c.t = 9.99
        self.assertFalse(l.allow("a"))
        c.t = 10
        self.assertTrue(l.allow("a"))

    def test_denied_attempts_do_not_extend_the_block(self):
        c, l = make(1, 10)
        self.assertTrue(l.allow("a"))
        for t in range(1, 10):
            c.t = t
            self.assertFalse(l.allow("a"))
        c.t = 10
        self.assertTrue(l.allow("a"))

    def test_retry_after_counts_down_from_oldest_event(self):
        c, l = make(2, 10)
        l.allow("a")
        c.t = 4
        l.allow("a")
        c.t = 6
        self.assertAlmostEqual(l.retry_after("a"), 4.0)
        c.t = 9
        self.assertAlmostEqual(l.retry_after("a"), 1.0)

    def test_retry_after_unchanged_by_denied_attempt(self):
        c, l = make(2, 10)
        l.allow("a")
        c.t = 4
        l.allow("a")
        c.t = 6
        self.assertFalse(l.allow("a"))
        self.assertAlmostEqual(l.retry_after("a"), 4.0)

    def test_retry_after_zero_when_allowed(self):
        c, l = make()
        self.assertEqual(l.retry_after("x"), 0.0)
        l.allow("x")
        self.assertEqual(l.retry_after("x"), 0.0)

    def test_retry_after_does_not_consume_a_slot(self):
        c, l = make(1, 10)
        l.allow("a")
        l.retry_after("a")
        l.retry_after("a")
        c.t = 10
        self.assertTrue(l.allow("a"))
        self.assertFalse(l.allow("a"))

    def test_retry_after_after_window_slides(self):
        c, l = make(2, 10)
        l.allow("a")
        c.t = 3
        l.allow("a")
        c.t = 10
        self.assertTrue(l.allow("a"))
        self.assertAlmostEqual(l.retry_after("a"), 3.0)

    def test_keys_independent(self):
        c, l = make(1, 10)
        self.assertTrue(l.allow("a"))
        self.assertTrue(l.allow("b"))
        self.assertFalse(l.allow("a"))
        self.assertEqual(l.retry_after("c"), 0.0)


if __name__ == "__main__":
    unittest.main()
