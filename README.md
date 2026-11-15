# MSCS532 Assignment 5: Quicksort

This repo has:

* a regular quick sort that always uses the last item as the pivot (Lomuto partition),
* a randomized quick sort that picks the pivot at random,
* a three-way randomized quick sort for lists with a lot of repeated values (an extra, not
  required by the assignment),
* a benchmark that compares them on random, sorted, reverse-sorted, nearly-sorted and
  few-unique lists, looking at running time, number of comparisons and recursion depth.

I based the algorithms on *Introduction to Algorithms* (Cormen et al., 4th ed., ch. 7). The
full write-up, with the design choices, best/average/worst-case analysis, space complexity, how
randomization helps, and a discussion of the results, is in **[REPORT.md](REPORT.md)**.

| File | What's in it |
|---|---|
| `quicksort.py` | `quick_sort`, `random_pivot_quick_sort`, `three_way_quick_sort`, the split functions (`lomuto_split`, `random_split`, `three_way_split`) and `SortTracker` |
| `run_benchmarks.py` | Timing, comparison counts, spread of comparison counts over many runs, and recursion depth |
| `test_quicksort.py` | 13 unit tests |
| `chart_style.py` | Shared chart styling |
| `results/` | CSV data, charts and terminal output from the last full run |

## Requirements

Python 3.8 or newer. The sorts and the tests only use the standard library. You need
`matplotlib` for the charts:

```bash
pip install matplotlib
```

## How to run it

```bash
python3 -m unittest -v test_quicksort
```

```bash
python3 quicksort.py
```

```bash
python3 run_benchmarks.py
```

```bash
python3 run_benchmarks.py --quick
```

* `python3 quicksort.py` sorts a small example with each version and prints how deep the
  recursion goes on a sorted list.
* `python3 run_benchmarks.py` runs the full benchmark (about a minute) and saves the CSV
  files, charts and `benchmark_output.txt` into `results/`.
* `--quick` uses smaller sizes and is done in about 5 seconds.

You can also call the functions directly:

```python
import random
from quicksort import quick_sort, random_pivot_quick_sort, SortTracker

nums = [5, 3, 8, 1, 9, 2]
quick_sort(nums)                                     # sorts in place and returns nums
random_pivot_quick_sort(nums, rng=random.Random(42)) # same pivots every run

t = SortTracker()
quick_sort(list(range(1000)), tracker=t)
print(t)   # SortTracker(split_calls=999, deepest_level=998, deepest_stack=1)
```

In the benchmark output and charts, "Deterministic" is `quick_sort`, "Randomized" is
`random_pivot_quick_sort` and "Randomized 3-way" is `three_way_quick_sort`.

## Summary of results

### Complexity

| | Fixed pivot | Random pivot |
|---|---|---|
| Best | Θ(n lg n) | Θ(n lg n) |
| Average / expected | Θ(n lg n), about 1.39 n lg n comparisons on a shuffled list | Θ(n lg n) expected on **any** list |
| Worst | Θ(n²), exactly n(n−1)/2 comparisons, on sorted and reversed lists | Θ(n²), but the chance of the full worst case is only 2ⁿ⁻¹/n! |
| Extra space | O(1) for the data + O(lg n) stack (recursing on the smaller half) | same |

The average case comes out to 2(n+1)H<sub>n</sub> − 4n comparisons. Two values
z<sub>i</sub> < z<sub>j</sub> are compared only if one of them is the first pivot picked from
z<sub>i</sub>..z<sub>j</sub>, which happens with probability 2/(j−i+1). Adding that up over every
pair gives about 2n ln n.

### Timings (median ms)

| n = 16,000 | random | sorted | reverse | nearly-sorted | few-unique |
|---|---:|---:|---:|---:|---:|
| Fixed pivot | 9.0 | **4,507.6** | **3,081.9** | 31.8 | **408.7** |
| Random pivot | 11.9 | 11.3 | 11.0 | 10.9 | **410.4** |
| Random 3-way | 17.8 | 17.5 | 16.9 | 17.3 | 2.5 |

* **Sorted and reversed lists are the worst case for the fixed pivot.** It made exactly
  n(n−1)/2 comparisons and got about 4× slower each time n doubled. On 16,000 sorted items it
  was around 400 times slower than the random pivot.
* **The random pivot takes about the same time whatever order the list is in.** It got about
  2.1× slower per doubling and made 1.09–1.18 n lg n comparisons on every input, close to the
  1.15 n lg n the formula gives at n = 4,000.
* **Random pivot on a sorted list behaves the same as fixed pivot on a shuffled list.** Over
  1,000 runs at n = 2,000 the averages were 24,747 and 24,736 comparisons, with 24,730 predicted,
  and the two histograms overlap. Even the worst run was only 1.25× the average.
* **Randomizing isn't free.** On a list that's already shuffled, generating a random number for
  every split made it 15–30% slower.
* **Randomizing doesn't help with repeated values.** With only 10 different values, both
  two-way versions went quadratic (about n²/20 comparisons). The three-way split handled the
  same list in 2.5 ms instead of about 410 ms.
* **Recursing on the smaller half keeps the stack at most lg n deep.** The book's version
  would need n − 2 levels on a sorted list, which crashes Python at around 1,000 items.

![Running time by input distribution](results/sort_times.png)

![Distribution of comparison counts](results/comparison_distribution.png)
