import unittest
from wlru import WeightedLRU


class H(unittest.TestCase):
    def test_basic_put_get(self):
        c = WeightedLRU(10)
        self.assertTrue(c.put("a", 1))
        self.assertEqual(c.get("a"), 1)
        self.assertEqual(c.get("zzz", "d"), "d")
        self.assertEqual(len(c), 1)
        self.assertEqual(c.total_weight(), 1)

    def test_eviction_order_is_lru(self):
        c = WeightedLRU(3)
        for k in "abc":
            c.put(k, k)
        c.get("a")
        c.put("d", "d")
        self.assertEqual(c.keys(), ["c", "a", "d"])
        self.assertNotIn("b", c)

    def test_peek_and_contains_do_not_refresh(self):
        c = WeightedLRU(2)
        c.put("a", 1)
        c.put("b", 2)
        self.assertEqual(c.peek("a"), 1)
        self.assertIn("a", c)
        c.put("c", 3)
        self.assertEqual(c.keys(), ["b", "c"])

    def test_heavy_entry_evicts_several(self):
        c = WeightedLRU(10)
        c.put("a", 1, 3)
        c.put("b", 2, 3)
        c.put("c", 3, 3)
        self.assertTrue(c.put("d", 4, 7))
        self.assertEqual(c.keys(), ["c", "d"])
        self.assertEqual(c.total_weight(), 10)

    def test_too_heavy_is_rejected_and_changes_nothing(self):
        c = WeightedLRU(5)
        c.put("a", 1, 2)
        c.put("b", 2, 2)
        self.assertFalse(c.put("big", 9, 6))
        self.assertEqual(c.keys(), ["a", "b"])
        self.assertEqual(c.total_weight(), 4)

    def test_too_heavy_update_leaves_existing_entry(self):
        c = WeightedLRU(5)
        c.put("a", "old", 2)
        c.put("b", "b", 1)
        self.assertFalse(c.put("a", "new", 9))
        self.assertEqual(c.peek("a"), "old")
        self.assertEqual(c.keys(), ["a", "b"])
        self.assertEqual(c.total_weight(), 3)

    def test_update_replaces_value_and_weight_and_refreshes(self):
        c = WeightedLRU(10)
        c.put("a", 1, 2)
        c.put("b", 2, 2)
        c.put("a", 10, 5)
        self.assertEqual(c.peek("a"), 10)
        self.assertEqual(c.keys(), ["b", "a"])
        self.assertEqual(c.total_weight(), 7)

    def test_update_can_evict_others_but_never_itself(self):
        c = WeightedLRU(6)
        c.put("a", 1, 2)
        c.put("b", 2, 2)
        c.put("c", 3, 2)
        self.assertTrue(c.put("a", 11, 6))
        self.assertEqual(c.keys(), ["a"])
        self.assertEqual(c.total_weight(), 6)

    def test_update_to_lighter_weight_frees_room(self):
        c = WeightedLRU(5)
        c.put("a", 1, 4)
        c.put("a", 1, 1)
        self.assertEqual(c.total_weight(), 1)
        c.put("b", 2, 4)
        self.assertEqual(c.keys(), ["a", "b"])

    def test_weight_exactly_capacity(self):
        c = WeightedLRU(4)
        c.put("a", 1, 1)
        self.assertTrue(c.put("b", 2, 4))
        self.assertEqual(c.keys(), ["b"])

    def test_none_value(self):
        c = WeightedLRU(2)
        c.put("a", None)
        self.assertIn("a", c)
        self.assertIsNone(c.get("a", "default"))
        self.assertIsNone(c.peek("a", "default"))

    def test_validation(self):
        for bad in (0, -1, 1.5, "3", None):
            with self.subTest(capacity=bad):
                with self.assertRaises(ValueError):
                    WeightedLRU(bad)
        c = WeightedLRU(5)
        c.put("a", 1, 2)
        for bad in (0, -2, 1.5, "1", None):
            with self.subTest(weight=bad):
                with self.assertRaises(ValueError):
                    c.put("a", 99, bad)
                self.assertEqual(c.peek("a"), 1)
        self.assertEqual(c.total_weight(), 2)

    def test_get_missing_does_not_create(self):
        c = WeightedLRU(3)
        self.assertIsNone(c.get("x"))
        self.assertEqual(len(c), 0)
        self.assertEqual(c.keys(), [])


if __name__ == "__main__":
    unittest.main()
