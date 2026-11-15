"""
Quick sort, three ways.

    quick_sort(items)              always uses the last item as the pivot
    random_pivot_quick_sort(items) picks the pivot at random
    three_way_quick_sort(items)    random pivot, but splits into <, == and >
                                   groups so repeated values don't hurt

I followed the QUICKSORT, PARTITION and RANDOMIZED-QUICKSORT pseudocode
from CLRS chapter 7 (4th edition). The book uses 1-based arrays; here
everything is 0-based and ranges are inclusive, so items[start..end]
means items[start] up to and including items[end].

All three sort the list in place and also hand it back, so you can write
quick_sort(data[:]) the same way you'd write sorted(data). The only
operations used on the values are <= (two-way versions) and < (three-way),
so strings, tuples, floats etc. all work.

You can also pass in a SortTracker to see how many times the list was
split and how deep the recursion got. The benchmark uses this for the
space complexity part of the report.
"""

import random


class SortTracker:
    """Optional counters a sort fills in while it runs.

    split_calls     how many times the partition step ran
    deepest_level   deepest level of the recursion tree that got split
                    (top call = level 0). The plain textbook version
                    would need this many stack frames.
    deepest_stack   how deep the real Python call stack actually got.
                    This is much smaller because we only recurse into
                    the smaller half (explained further down).
    """

    __slots__ = ("split_calls", "deepest_level", "deepest_stack")

    def __init__(self):
        self.split_calls = 0
        self.deepest_level = 0
        self.deepest_stack = 0

    def note(self, level, stack):
        self.split_calls += 1
        if level > self.deepest_level:
            self.deepest_level = level
        if stack > self.deepest_stack:
            self.deepest_stack = stack

    def __repr__(self):
        return (f"SortTracker(split_calls={self.split_calls}, "
                f"deepest_level={self.deepest_level}, "
                f"deepest_stack={self.deepest_stack})")


# ----------------------------------------------------------------------
# Splitting the list around a pivot
# ----------------------------------------------------------------------

def lomuto_split(items, start, end):
    """Lomuto partition of items[start..end], using items[end] as the pivot.

    Returns where the pivot ends up (call it mid). After this,
    items[start..mid-1] are all <= pivot and items[mid+1..end] are all
    bigger than it.

    While the loop runs, with `scan` as the current position:
        items[start..boundary]       <= pivot
        items[boundary+1..scan-1]    >  pivot
        items[scan..end-1]           not checked yet
        items[end]                   the pivot itself
    It does exactly end - start comparisons, so one call is linear.
    """
    pivot = items[end]
    boundary = start - 1
    for scan in range(start, end):
        if items[scan] <= pivot:
            boundary += 1
            items[boundary], items[scan] = items[scan], items[boundary]
    # put the pivot between the two groups
    items[boundary + 1], items[end] = items[end], items[boundary + 1]
    return boundary + 1


def random_split(items, start, end, rng=random):
    """Move a random item of items[start..end] to the end, then do lomuto_split.

    After the swap, every item in the range has the same chance of being
    the pivot, no matter how the input was ordered.
    """
    pick = rng.randint(start, end)
    items[pick], items[end] = items[end], items[pick]
    return lomuto_split(items, start, end)


def three_way_split(items, start, end, rng=random):
    """Dijkstra's "Dutch national flag" split around a random pivot.

    Returns (low, high) so that afterwards
        items[start..low-1] < pivot
        items[low..high]    == pivot
        items[high+1..end]  > pivot

    Everything equal to the pivot lands in the middle block and never
    gets looked at again. That's what stops lists full of duplicates
    from going quadratic.
    """
    pivot = items[rng.randint(start, end)]
    low, cur, high = start, start, end
    while cur <= high:
        value = items[cur]
        if value < pivot:
            items[low], items[cur] = value, items[low]
            low += 1
            cur += 1
        elif pivot < value:
            items[cur], items[high] = items[high], value
            high -= 1
        else:
            cur += 1
    return low, high


# ----------------------------------------------------------------------
# Recursion
# ----------------------------------------------------------------------
#
# The book's QUICKSORT calls itself on both halves. When the split is
# as bad as it gets (n-1 on one side, 0 on the other) that means n
# nested calls, and Python gives up at around 1000 with RecursionError.
# I wanted to actually measure the slow worst case on big lists, so
# these helpers only recurse on the smaller half and handle the bigger
# half by looping (this is the trick from CLRS problem 7-4). The splits
# and comparisons are exactly the same as the book's version, so the
# running time doesn't change. Only the stack depth does: it can't go
# past about lg n now.

def _sort_range(items, start, end, split_fn, tracker, level, stack):
    while start < end:
        if tracker is not None:
            tracker.note(level, stack)
        # divide
        mid = split_fn(items, start, end)
        # conquer the smaller side by recursion, keep looping on the other
        # (nothing to combine afterwards, it's already in place)
        if mid - start < end - mid:
            _sort_range(items, start, mid - 1, split_fn, tracker, level + 1, stack + 1)
            start = mid + 1
        else:
            _sort_range(items, mid + 1, end, split_fn, tracker, level + 1, stack + 1)
            end = mid - 1
        level += 1


def _sort_range_3way(items, start, end, rng, tracker, level, stack):
    while start < end:
        if tracker is not None:
            tracker.note(level, stack)
        low, high = three_way_split(items, start, end, rng)
        if low - start < end - high:
            _sort_range_3way(items, start, low - 1, rng, tracker, level + 1, stack + 1)
            start = high + 1
        else:
            _sort_range_3way(items, high + 1, end, rng, tracker, level + 1, stack + 1)
            end = low - 1
        level += 1


# ----------------------------------------------------------------------
# The three sorts
# ----------------------------------------------------------------------

def quick_sort(items, tracker=None):
    """Plain quick sort from CLRS. The pivot is always the last item.

    Sorts in place and returns the same list.

    Time:  Theta(n lg n) best and average, Theta(n^2) worst. The worst
           case shows up on sorted and reverse-sorted lists, and on
           lists with only a handful of distinct values.
    Space: O(lg n) for the stack, nothing else extra.
    """
    _sort_range(items, 0, len(items) - 1, lomuto_split, tracker, 0, 1)
    return items


def random_pivot_quick_sort(items, rng=None, tracker=None):
    """Randomized quick sort (CLRS RANDOMIZED-QUICKSORT).

    Each pivot is picked at random from the part being sorted. Give it
    rng=random.Random(some_seed) if you want the same result every run.

    Time:  expected Theta(n lg n) on any list of distinct values. Theta(n^2)
           is still possible but extremely unlikely. Lots of equal values
           still make it quadratic though (use the 3-way version for that).
    Space: O(lg n) stack.
    """
    rng = rng or random
    split_fn = lambda arr, s, e: random_split(arr, s, e, rng)
    _sort_range(items, 0, len(items) - 1, split_fn, tracker, 0, 1)
    return items


def three_way_quick_sort(items, rng=None, tracker=None):
    """Randomized quick sort with a three-way split.

    Behaves like random_pivot_quick_sort when all values are different,
    but with only k different values it takes about n lg k time, so a
    list where everything is equal is sorted in one linear pass.
    """
    rng = rng or random
    _sort_range_3way(items, 0, len(items) - 1, rng, tracker, 0, 1)
    return items


if __name__ == "__main__":
    sample = [38, 27, 43, 3, 9, 82, 10, 3, 55, 21]
    print("input:                  ", sample)
    for label, sort_fn in [("quick_sort", quick_sort),
                           ("random_pivot_quick_sort", random_pivot_quick_sort),
                           ("three_way_quick_sort", three_way_quick_sort)]:
        print(f"{label + ':':25} {sort_fn(sample[:])}")

    print("\nRecursion on an already sorted list of 500 numbers:")
    t = SortTracker()
    quick_sort(list(range(500)), tracker=t)
    print(f"  fixed pivot   {t}")
    t = SortTracker()
    random_pivot_quick_sort(list(range(500)), random.Random(1), t)
    print(f"  random pivot  {t}")
