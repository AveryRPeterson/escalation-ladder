import threading
import time
import unittest
from ttlcache import TTLCache


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def run_threads(n, target):
    barrier = threading.Barrier(n)
    out = [None] * n

    def go(i):
        barrier.wait()
        try:
            out[i] = ("ok", target(i))
        except BaseException as e:  # noqa
            out[i] = ("err", e)

    ts = [threading.Thread(target=go, args=(i,)) for i in range(n)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(20)
    return out


class H(unittest.TestCase):
    def test_single_flight_same_key(self):
        c = TTLCache(60)
        calls = []

        def fn():
            calls.append(1)
            time.sleep(0.3)
            return 42

        res = run_threads(8, lambda i: c.get_or_compute("k", fn))
        self.assertEqual(len(calls), 1)
        self.assertTrue(all(r == ("ok", 42) for r in res), res)

    def test_different_keys_do_not_block_each_other(self):
        c = TTLCache(60)

        def fn_for(k):
            def fn():
                time.sleep(0.4)
                return k
            return fn

        t0 = time.time()
        res = run_threads(4, lambda i: c.get_or_compute(f"k{i}", fn_for(i)))
        elapsed = time.time() - t0
        self.assertEqual([r[1] for r in res], [0, 1, 2, 3])
        self.assertLess(elapsed, 1.0, f"took {elapsed:.2f}s; keys are being serialised")

    def test_exception_reaches_all_waiters_and_is_not_cached(self):
        c = TTLCache(60)
        calls = []

        def bad():
            calls.append(1)
            time.sleep(0.3)
            raise ValueError("boom")

        res = run_threads(5, lambda i: c.get_or_compute("k", bad))
        self.assertEqual(len(calls), 1)
        self.assertTrue(all(r[0] == "err" and isinstance(r[1], ValueError) for r in res), res)
        self.assertEqual(c.get_or_compute("k", lambda: "fine"), "fine")

    def test_ttl_expiry_with_injected_clock(self):
        clock = Clock()
        c = TTLCache(10, clock=clock)
        n = []

        def fn():
            n.append(1)
            return len(n)

        self.assertEqual(c.get_or_compute("k", fn), 1)
        clock.t = 9.99
        self.assertEqual(c.get_or_compute("k", fn), 1)
        clock.t = 10
        self.assertEqual(c.get_or_compute("k", fn), 2)

    def test_none_is_cached(self):
        c = TTLCache(60)
        n = []

        def fn():
            n.append(1)
            return None

        self.assertIsNone(c.get_or_compute("k", fn))
        self.assertIsNone(c.get_or_compute("k", fn))
        self.assertEqual(len(n), 1)

    def test_ttl_counts_from_finish_not_start(self):
        clock = Clock()
        c = TTLCache(10, clock=clock)
        n = []

        def slow():
            n.append(1)
            clock.t += 5
            return "v"

        c.get_or_compute("k", slow)        # starts at 0, finishes at 5
        clock.t = 14
        c.get_or_compute("k", slow)        # still valid (5 + 10 = 15)
        self.assertEqual(len(n), 1)
        clock.t = 15
        c.get_or_compute("k", slow)
        self.assertEqual(len(n), 2)

    def test_late_arrival_after_failed_flight_retries(self):
        c = TTLCache(60)
        state = {"fail": True}

        def fn():
            if state["fail"]:
                raise RuntimeError("x")
            return "ok"

        with self.assertRaises(RuntimeError):
            c.get_or_compute("k", fn)
        state["fail"] = False
        self.assertEqual(c.get_or_compute("k", fn), "ok")

    def test_value_is_cached_after_flight_ends(self):
        c = TTLCache(60)
        calls = []

        def fn():
            calls.append(1)
            time.sleep(0.2)
            return "v"

        run_threads(6, lambda i: c.get_or_compute("k", fn))
        self.assertEqual(c.get_or_compute("k", fn), "v")
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
