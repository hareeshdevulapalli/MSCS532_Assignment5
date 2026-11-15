"""
Tests for the three Quicksort versions and their partition routines.

Run with:  python3 -m unittest -v test_quicksort
"""

import random
import unittest

from quicksort import (QuickSortStats, partition, quicksort,
                       randomized_partition, randomized_quicksort,
                       randomized_quicksort_3way, three_way_partition)

SORTS = {
    "quicksort": quicksort,
    "randomized_quicksort": randomized_quicksort,
    "randomized_quicksort_3way": randomized_quicksort_3way,
}


class SortCorrectness(unittest.TestCase):
    EDGE_CASES = [[], [1], [2, 1], [1, 2], [3, 3, 3], [5, -1, 0, 5, -1],
                  list(range(60)), list(range(60, 0, -1)),
                  [0.5, -2.25, 3.0, 1e9, -1e9], [7] * 100]

    def all_cases(self):
        rand = random.Random(1)
        cases = list(self.EDGE_CASES)
        cases += [[rand.randint(-100, 100) for _ in range(n)] for n in range(2, 400, 23)]
        cases.append([rand.randint(0, 3) for _ in range(600)])  # lots of duplicates
        nearly = list(range(300))
        for _ in range(5):
            a, b = rand.randrange(300), rand.randrange(300)
            nearly[a], nearly[b] = nearly[b], nearly[a]
        cases.append(nearly)
        return cases

    def test_matches_sorted(self):
        for name, fn in SORTS.items():
            for case in self.all_cases():
                with self.subTest(sort=name, case=case[:8]):
                    self.assertEqual(fn(case[:]), sorted(case))

    def test_sorts_in_place_and_returns_same_list(self):
        for name, fn in SORTS.items():
            data = [5, 2, 9, 1]
            with self.subTest(sort=name):
                self.assertIs(fn(data), data)
                self.assertEqual(data, [1, 2, 5, 9])

    def test_other_comparable_types(self):
        words = ["pear", "apple", "fig", "kiwi", "apple", "banana"]
        tuples = [(2, "b"), (1, "z"), (2, "a"), (0, "q")]
        for name, fn in SORTS.items():
            with self.subTest(sort=name):
                self.assertEqual(fn(words[:]), sorted(words))
                self.assertEqual(fn(tuples[:]), sorted(tuples))

    def test_large_sorted_input_does_not_overflow_stack(self):
        # 5000 > Python's default recursion limit of 1000, so this only
        # passes because the drivers recurse into the smaller side.
        data = list(range(5000))
        self.assertEqual(quicksort(data[:]), data)

    def test_randomized_is_reproducible_with_seed(self):
        a, b = QuickSortStats(), QuickSortStats()
        randomized_quicksort(list(range(1000)), random.Random(7), a)
        randomized_quicksort(list(range(1000)), random.Random(7), b)
        self.assertEqual((a.partitions, a.max_depth), (b.partitions, b.max_depth))


class PartitionTests(unittest.TestCase):
    def check_two_way(self, arr, lo, hi, p, pivot):
        self.assertEqual(arr[p], pivot)
        self.assertTrue(all(x <= pivot for x in arr[lo:p]))
        self.assertTrue(all(x > pivot for x in arr[p + 1:hi + 1]))

    def test_lomuto_partition(self):
        rand = random.Random(2)
        for _ in range(200):
            arr = [rand.randint(0, 20) for _ in range(rand.randint(1, 40))]
            before = sorted(arr)
            pivot = arr[-1]
            p = partition(arr, 0, len(arr) - 1)
            self.check_two_way(arr, 0, len(arr) - 1, p, pivot)
            self.assertEqual(sorted(arr), before)  # same items, just moved

    def test_partition_only_touches_its_range(self):
        arr = [9, 9, 3, 1, 2, 9, 9]
        partition(arr, 2, 4)
        self.assertEqual(arr[:2] + arr[5:], [9, 9, 9, 9])
        self.assertEqual(arr[2:5], [1, 2, 3])

    def test_randomized_partition(self):
        rand = random.Random(3)
        for _ in range(200):
            arr = [rand.randint(0, 20) for _ in range(rand.randint(1, 40))]
            before = sorted(arr)
            p = randomized_partition(arr, 0, len(arr) - 1, rand)
            self.check_two_way(arr, 0, len(arr) - 1, p, arr[p])
            self.assertEqual(sorted(arr), before)

    def test_random_pivot_is_roughly_uniform(self):
        # On 0..9 the pivot's final index equals its value, so each index
        # should come up about 1/10 of the time.
        rand = random.Random(4)
        counts = [0] * 10
        trials = 20000
        for _ in range(trials):
            counts[randomized_partition(list(range(10)), 0, 9, rand)] += 1
        for c in counts:
            self.assertAlmostEqual(c / trials, 0.1, delta=0.015)

    def test_three_way_partition(self):
        rand = random.Random(5)
        for _ in range(200):
            arr = [rand.randint(0, 6) for _ in range(rand.randint(1, 50))]
            before = sorted(arr)
            lt, gt = three_way_partition(arr, 0, len(arr) - 1, rand)
            pivot = arr[lt]
            self.assertTrue(all(x < pivot for x in arr[:lt]))
            self.assertTrue(all(x == pivot for x in arr[lt:gt + 1]))
            self.assertTrue(all(x > pivot for x in arr[gt + 1:]))
            self.assertEqual(sorted(arr), before)


class RecursionStats(unittest.TestCase):
    def test_deterministic_sorted_input_is_worst_case(self):
        n = 300
        s = QuickSortStats()
        quicksort(list(range(n)), stats=s)
        # Every split is (n-1, 0): n-1 partitions, recursion tree n-2 deep...
        self.assertEqual(s.partitions, n - 1)
        self.assertEqual(s.max_depth, n - 2)
        # ...but the real stack never grows, because the empty side is
        # the one we "recurse" into and it returns immediately.
        self.assertEqual(s.max_stack, 1)

    def test_stack_depth_is_logarithmic(self):
        rand = random.Random(6)
        n = 4096
        for fn in SORTS.values():
            s = QuickSortStats()
            data = [rand.random() for _ in range(n)]
            if fn is quicksort:
                fn(data, stats=s)
            else:
                fn(data, rand, s)
            self.assertLessEqual(s.max_stack, 12 + 1)  # lg 4096 = 12

    def test_all_equal_keys(self):
        n = 400
        two_way, three_way = QuickSortStats(), QuickSortStats()
        randomized_quicksort([1] * n, random.Random(0), two_way)
        randomized_quicksort_3way([1] * n, random.Random(0), three_way)
        self.assertEqual(two_way.partitions, n - 1)  # quadratic behaviour
        self.assertEqual(three_way.partitions, 1)    # one pass, done


if __name__ == "__main__":
    unittest.main()
