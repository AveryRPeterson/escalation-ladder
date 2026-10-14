import unittest
from intervals import merge, subtract, total_length, gaps


class H(unittest.TestCase):
    def test_merge_overlap_and_touch(self):
        self.assertEqual(merge([(5, 8), (1, 3), (3, 4), (2, 2.5)]), [(1, 4), (5, 8)])

    def test_merge_touching_only(self):
        self.assertEqual(merge([(1, 3), (3, 5)]), [(1, 5)])

    def test_merge_gap_kept(self):
        self.assertEqual(merge([(1, 2), (3, 4)]), [(1, 2), (3, 4)])

    def test_merge_drops_zero_length(self):
        self.assertEqual(merge([(2, 2), (1, 3)]), [(1, 3)])
        self.assertEqual(merge([(4, 4)]), [])
        self.assertEqual(merge([(1, 2), (2, 2), (3, 4)]), [(1, 2), (3, 4)])

    def test_merge_contained_and_equal(self):
        self.assertEqual(merge([(1, 10), (2, 3), (1, 10), (9, 10)]), [(1, 10)])

    def test_merge_input_not_modified_and_accepts_lists_and_iterators(self):
        data = [[5, 6], [1, 2]]
        out = merge(iter(data))
        self.assertEqual(out, [(1, 2), (5, 6)])
        self.assertEqual(data, [[5, 6], [1, 2]])
        self.assertTrue(all(isinstance(t, tuple) for t in out))

    def test_merge_invalid(self):
        with self.assertRaises(ValueError):
            merge([(3, 1)])
        with self.assertRaises(ValueError):
            merge([(1, 2), (5, 4)])

    def test_merge_empty(self):
        self.assertEqual(merge([]), [])

    def test_subtract_basic(self):
        self.assertEqual(subtract([(0, 10)], [(2, 3), (5, 7)]), [(0, 2), (3, 5), (7, 10)])

    def test_subtract_touching_boundaries(self):
        self.assertEqual(subtract([(0, 10)], [(0, 2), (8, 10)]), [(2, 8)])
        self.assertEqual(subtract([(0, 5)], [(5, 9)]), [(0, 5)])

    def test_subtract_everything(self):
        self.assertEqual(subtract([(2, 4)], [(0, 10)]), [])

    def test_subtract_merges_a_first(self):
        self.assertEqual(subtract([(0, 3), (3, 6), (2, 4)], [(1, 2)]), [(0, 1), (2, 6)])

    def test_subtract_no_b(self):
        self.assertEqual(subtract([(5, 6), (1, 2)], []), [(1, 2), (5, 6)])

    def test_subtract_validates(self):
        with self.assertRaises(ValueError):
            subtract([(1, 2)], [(4, 3)])
        with self.assertRaises(ValueError):
            subtract([(2, 1)], [])

    def test_total_length(self):
        self.assertEqual(total_length([(0, 5), (3, 8), (10, 12)]), 10)
        self.assertEqual(total_length([]), 0)
        self.assertEqual(total_length([(1, 1)]), 0)
        self.assertAlmostEqual(total_length([(0.5, 1.0), (0.75, 1.25)]), 0.75)

    def test_gaps_basic(self):
        self.assertEqual(gaps([(2, 4), (6, 8)], 0, 10), [(0, 2), (4, 6), (8, 10)])

    def test_gaps_clipped(self):
        self.assertEqual(gaps([(-5, 3), (8, 20)], 0, 10), [(3, 8)])

    def test_gaps_fully_covered_and_empty_window(self):
        self.assertEqual(gaps([(0, 10)], 2, 5), [])
        self.assertEqual(gaps([], 3, 3), [])

    def test_gaps_no_intervals(self):
        self.assertEqual(gaps([], 0, 4), [(0, 4)])

    def test_gaps_touching_edges(self):
        self.assertEqual(gaps([(0, 3), (3, 7)], 0, 10), [(7, 10)])

    def test_gaps_invalid_window(self):
        with self.assertRaises(ValueError):
            gaps([], 5, 1)


if __name__ == "__main__":
    unittest.main()
