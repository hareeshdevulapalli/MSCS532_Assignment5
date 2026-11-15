"""
Quicksort: a deterministic version, a randomized version, and a
three-way randomized version for inputs with many duplicate keys.

The code follows QUICKSORT, PARTITION and RANDOMIZED-QUICKSORT from
Introduction to Algorithms (Cormen et al., 4th ed., ch. 7), using
0-based, inclusive index ranges arr[lo..hi].

    quicksort(arr)                   pivot = last item of the subarray
    randomized_quicksort(arr)        pivot = uniformly random item
    randomized_quicksort_3way(arr)   random pivot, splits into < = > groups

All three sort in place and also return the list, so they can be used
like `sorted()` on a copy. They only use the comparison operators
(`<=` for the two-way versions, `<` for the three-way one), so they work
on anything mutually comparable: ints, floats, strings, tuples...

Every call can take an optional QuickSortStats object that records the
number of partition calls and how deep the recursion went. The
benchmarks use it to back up the space-complexity discussion.
"""

import random


class QuickSortStats:
    """Counters filled in by a sort when one is passed in.

    partitions   number of times PARTITION ran
    max_depth    deepest level of the recursion tree that was partitioned
                 (the root call is level 0). This is the depth the plain
                 textbook version would reach on the call stack.
    max_stack    deepest *actual* Python call stack used by this code,
                 which recurses only into the smaller side (see below).
    """

    __slots__ = ("partitions", "max_depth", "max_stack")

    def __init__(self):
        self.partitions = 0
        self.max_depth = 0
        self.max_stack = 0

    def record(self, depth, stack):
        self.partitions += 1
        if depth > self.max_depth:
            self.max_depth = depth
        if stack > self.max_stack:
            self.max_stack = stack

    def __repr__(self):
        return (f"QuickSortStats(partitions={self.partitions}, "
                f"max_depth={self.max_depth}, max_stack={self.max_stack})")


# ---------------------------------------------------------------------------
# Partitioning
# ---------------------------------------------------------------------------

def partition(arr, lo, hi):
    """Lomuto partition of arr[lo..hi] around the pivot arr[hi].

    Returns the pivot's final index p. Afterwards
        arr[lo..p-1] <= arr[p] < arr[p+1..hi].

    Loop invariant, at the top of each pass with index j:
        arr[lo..i]     are <= pivot
        arr[i+1..j-1]  are >  pivot
        arr[j..hi-1]   have not been looked at yet
        arr[hi]        is the pivot
    Exactly hi - lo comparisons are made, so one call is Theta(n).
    """
    pivot = arr[hi]
    i = lo - 1
    for j in range(lo, hi):
        if arr[j] <= pivot:
            i += 1
            arr[i], arr[j] = arr[j], arr[i]
    arr[i + 1], arr[hi] = arr[hi], arr[i + 1]
    return i + 1


def randomized_partition(arr, lo, hi, rng=random):
    """Swap a uniformly random item of arr[lo..hi] into arr[hi], then partition.

    After the swap every item is equally likely to be the pivot, whatever
    order the input was in.
    """
    k = rng.randint(lo, hi)
    arr[k], arr[hi] = arr[hi], arr[k]
    return partition(arr, lo, hi)


def three_way_partition(arr, lo, hi, rng=random):
    """Dijkstra's "Dutch national flag" partition around a random pivot.

    Returns (lt, gt) such that afterwards
        arr[lo..lt-1] < pivot,  arr[lt..gt] == pivot,  arr[gt+1..hi] > pivot.

    Keys equal to the pivot end up in the middle block and are never
    looked at again, which is what fixes the many-duplicates worst case
    of the two-way versions.
    """
    k = rng.randint(lo, hi)
    pivot = arr[k]
    lt, i, gt = lo, lo, hi
    while i <= gt:
        x = arr[i]
        if x < pivot:
            arr[lt], arr[i] = x, arr[lt]
            lt += 1
            i += 1
        elif pivot < x:
            arr[i], arr[gt] = arr[gt], x
            gt -= 1
        else:
            i += 1
    return lt, gt


# ---------------------------------------------------------------------------
# Recursive drivers
# ---------------------------------------------------------------------------
#
# The textbook QUICKSORT recurses into both sides. On a bad split that
# makes the call stack n levels deep, which in Python would hit the
# recursion limit (~1000) long before the Theta(n^2) running time could
# be measured. So, as in CLRS problem 7-4, these drivers recurse only into
# the *smaller* side and loop on the larger side. The work done (and so
# the comparisons and the running time) is exactly the same as the
# textbook version; only the stack depth changes, from O(n) worst case
# to O(lg n) worst case.

def _quicksort(arr, lo, hi, part, stats, depth, stack):
    while lo < hi:
        if stats is not None:
            stats.record(depth, stack)
        # Divide: arr[lo..p-1] <= arr[p] < arr[p+1..hi].
        p = part(arr, lo, hi)
        # Conquer: sort the two sides. Combine: nothing to do.
        if p - lo < hi - p:
            _quicksort(arr, lo, p - 1, part, stats, depth + 1, stack + 1)
            lo = p + 1
        else:
            _quicksort(arr, p + 1, hi, part, stats, depth + 1, stack + 1)
            hi = p - 1
        depth += 1


def _quicksort_3way(arr, lo, hi, rng, stats, depth, stack):
    while lo < hi:
        if stats is not None:
            stats.record(depth, stack)
        lt, gt = three_way_partition(arr, lo, hi, rng)
        if lt - lo < hi - gt:
            _quicksort_3way(arr, lo, lt - 1, rng, stats, depth + 1, stack + 1)
            lo = gt + 1
        else:
            _quicksort_3way(arr, gt + 1, hi, rng, stats, depth + 1, stack + 1)
            hi = lt - 1
        depth += 1


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def quicksort(arr, stats=None):
    """Deterministic Quicksort (CLRS QUICKSORT): the pivot is always arr[hi].

    Sorts `arr` in place and returns it.

    Time:  best/average Theta(n lg n), worst Theta(n^2). The worst case
           happens on already-sorted and reverse-sorted input, and on
           input with very few distinct keys.
    Space: O(lg n) stack (smaller-side recursion), no other extra memory.
    """
    _quicksort(arr, 0, len(arr) - 1, partition, stats, 0, 1)
    return arr


def randomized_quicksort(arr, rng=None, stats=None):
    """Randomized Quicksort (CLRS RANDOMIZED-QUICKSORT).

    The pivot is chosen uniformly at random from the current subarray.
    Pass `rng` (e.g. random.Random(42)) for reproducible runs.

    Time:  expected Theta(n lg n) on *every* input of distinct keys;
           worst case is still Theta(n^2) but has negligible probability.
           Many equal keys still cause Theta(n^2) (see the 3-way version).
    Space: O(lg n) stack, always.
    """
    rng = rng or random
    part = lambda a, lo, hi: randomized_partition(a, lo, hi, rng)
    _quicksort(arr, 0, len(arr) - 1, part, stats, 0, 1)
    return arr


def randomized_quicksort_3way(arr, rng=None, stats=None):
    """Randomized Quicksort with three-way partitioning.

    Same as randomized_quicksort on distinct keys, but runs in
    Theta(n lg k) expected time when there are only k distinct keys,
    so all-equal input takes linear time instead of quadratic.
    """
    rng = rng or random
    _quicksort_3way(arr, 0, len(arr) - 1, rng, stats, 0, 1)
    return arr


if __name__ == "__main__":
    data = [38, 27, 43, 3, 9, 82, 10, 3, 55, 21]
    print("input:                   ", data)
    for name, fn in [("quicksort", quicksort),
                     ("randomized_quicksort", randomized_quicksort),
                     ("randomized_quicksort_3way", randomized_quicksort_3way)]:
        print(f"{name + ':':26} {fn(data[:])}")

    print("\nRecursion on sorted input of 500 items:")
    for name, fn in [("deterministic", quicksort),
                     ("randomized", lambda a, stats: randomized_quicksort(
                         a, random.Random(1), stats))]:
        s = QuickSortStats()
        fn(list(range(500)), stats=s)
        print(f"  {name:13} {s}")
