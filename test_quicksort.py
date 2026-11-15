"""
Unit tests for the quick sort versions and the split functions.

Run with:  python3 -m unittest -v test_quicksort
"""

import random
import unittest

from quicksort import (SortTracker, lomuto_split, quick_sort,
                       random_pivot_quick_sort, random_split,
                       three_way_quick_sort, three_way_split)

ALL_SORTS = {
    "quick_sort": quick_sort,
    "random_pivot_quick_sort": random_pivot_quick_sort,
    "three_way_quick_sort": three_way_quick_sort,
}


class SortsGiveRightAnswer(unittest.TestCase):
    TRICKY_LISTS = [[], [1], [2, 1], [1, 2], [3, 3, 3], [5, -1, 0, 5, -1],
                    list(range(60)), list(range(60, 0, -1)),
                    [0.5, -2.25, 3.0, 1e9, -1e9], [7] * 100]

    def build_lists(self):
        gen = random.Random(1)
        lists = list(self.TRICKY_LISTS)
        lists += [[gen.randint(-100, 100) for _ in range(size)]
                  for size in range(2, 400, 23)]
        lists.append([gen.randint(0, 3) for _ in range(600)])  # loads of repeats
        almost = list(range(300))
        for _ in range(5):
            a, b = gen.randrange(300), gen.randrange(300)
            almost[a], almost[b] = almost[b], almost[a]
        lists.append(almost)
        return lists

    def test_matches_builtin_sorted(self):
        for label, sort_fn in ALL_SORTS.items():
            for lst in self.build_lists():
                with self.subTest(sort=label, start_of_list=lst[:8]):
                    self.assertEqual(sort_fn(lst[:]), sorted(lst))

    def test_sorts_in_place_and_returns_same_object(self):
        for label, sort_fn in ALL_SORTS.items():
            nums = [5, 2, 9, 1]
            with self.subTest(sort=label):
                self.assertIs(sort_fn(nums), nums)
                self.assertEqual(nums, [1, 2, 5, 9])

    def test_strings_and_tuples(self):
        fruit = ["pear", "apple", "fig", "kiwi", "apple", "banana"]
        pairs = [(2, "b"), (1, "z"), (2, "a"), (0, "q")]
        for label, sort_fn in ALL_SORTS.items():
            with self.subTest(sort=label):
                self.assertEqual(sort_fn(fruit[:]), sorted(fruit))
                self.assertEqual(sort_fn(pairs[:]), sorted(pairs))

    def test_big_sorted_list_no_recursion_error(self):
        # 5000 is way over Python's default limit of 1000 nested calls.
        # This only works because we recurse on the smaller half.
        nums = list(range(5000))
        self.assertEqual(quick_sort(nums[:]), nums)

    def test_same_seed_same_run(self):
        first, second = SortTracker(), SortTracker()
        random_pivot_quick_sort(list(range(1000)), random.Random(7), first)
        random_pivot_quick_sort(list(range(1000)), random.Random(7), second)
        self.assertEqual((first.split_calls, first.deepest_level),
                         (second.split_calls, second.deepest_level))


class SplitFunctions(unittest.TestCase):
    def assert_split_ok(self, items, start, end, mid, pivot):
        self.assertEqual(items[mid], pivot)
        self.assertTrue(all(v <= pivot for v in items[start:mid]))
        self.assertTrue(all(v > pivot for v in items[mid + 1:end + 1]))

    def test_lomuto(self):
        gen = random.Random(2)
        for _ in range(200):
            items = [gen.randint(0, 20) for _ in range(gen.randint(1, 40))]
            same_values = sorted(items)
            pivot = items[-1]
            mid = lomuto_split(items, 0, len(items) - 1)
            self.assert_split_ok(items, 0, len(items) - 1, mid, pivot)
            self.assertEqual(sorted(items), same_values)  # nothing lost or added

    def test_split_stays_inside_its_range(self):
        items = [9, 9, 3, 1, 2, 9, 9]
        lomuto_split(items, 2, 4)
        self.assertEqual(items[:2] + items[5:], [9, 9, 9, 9])
        self.assertEqual(items[2:5], [1, 2, 3])

    def test_random_split(self):
        gen = random.Random(3)
        for _ in range(200):
            items = [gen.randint(0, 20) for _ in range(gen.randint(1, 40))]
            same_values = sorted(items)
            mid = random_split(items, 0, len(items) - 1, gen)
            self.assert_split_ok(items, 0, len(items) - 1, mid, items[mid])
            self.assertEqual(sorted(items), same_values)

    def test_random_pivot_is_fair(self):
        # For 0..9 the pivot lands at the index equal to its value, so each
        # index should come up roughly 10% of the time.
        gen = random.Random(4)
        hits = [0] * 10
        rounds = 20000
        for _ in range(rounds):
            hits[random_split(list(range(10)), 0, 9, gen)] += 1
        for h in hits:
            self.assertAlmostEqual(h / rounds, 0.1, delta=0.015)

    def test_three_way(self):
        gen = random.Random(5)
        for _ in range(200):
            items = [gen.randint(0, 6) for _ in range(gen.randint(1, 50))]
            same_values = sorted(items)
            low, high = three_way_split(items, 0, len(items) - 1, gen)
            pivot = items[low]
            self.assertTrue(all(v < pivot for v in items[:low]))
            self.assertTrue(all(v == pivot for v in items[low:high + 1]))
            self.assertTrue(all(v > pivot for v in items[high + 1:]))
            self.assertEqual(sorted(items), same_values)


class TrackerNumbers(unittest.TestCase):
    def test_sorted_input_is_worst_case_for_fixed_pivot(self):
        n = 300
        t = SortTracker()
        quick_sort(list(range(n)), tracker=t)
        # every split is (n-1, 0): n-1 splits and a tree n-2 levels deep
        self.assertEqual(t.split_calls, n - 1)
        self.assertEqual(t.deepest_level, n - 2)
        # but the real stack stays at 1, since the side we recurse into
        # is the empty one and returns straight away
        self.assertEqual(t.deepest_stack, 1)

    def test_stack_stays_logarithmic(self):
        gen = random.Random(6)
        n = 4096
        for sort_fn in ALL_SORTS.values():
            t = SortTracker()
            nums = [gen.random() for _ in range(n)]
            if sort_fn is quick_sort:
                sort_fn(nums, tracker=t)
            else:
                sort_fn(nums, gen, t)
            self.assertLessEqual(t.deepest_stack, 12 + 1)  # lg 4096 = 12

    def test_all_values_equal(self):
        n = 400
        two_way, three_way = SortTracker(), SortTracker()
        random_pivot_quick_sort([1] * n, random.Random(0), two_way)
        three_way_quick_sort([1] * n, random.Random(0), three_way)
        self.assertEqual(two_way.split_calls, n - 1)   # quadratic
        self.assertEqual(three_way.split_calls, 1)     # one pass and done


if __name__ == "__main__":
    unittest.main()
