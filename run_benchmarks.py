"""
Benchmarks comparing the fixed-pivot and random-pivot quick sorts.

Part 1 - timing. Every version sorts random, sorted, reverse-sorted,
nearly-sorted and few-unique lists, doubling the size each step. I use
the median of a few runs, each on a fresh copy. The quadratic cases get
slow very quickly, so once one run takes more than RUN_CUTOFF seconds I
stop that series and the bigger sizes show up as "skipped".

Part 2 - comparisons and recursion depth. Python timings are noisy, so
I also wrap each value in a class that counts comparisons and check the
counts against the formulas from the report:
    worst case               n(n-1)/2
    expected (random)        2(n+1)H_n - 4n, roughly 1.39 n lg n

Part 3 - how much does luck matter? I run the random-pivot sort many
times on the *same* sorted list (only the pivot choices change), and the
fixed-pivot sort on many different random lists. If the theory is right,
both should give the same spread of comparison counts, bunched up
around 2(n+1)H_n - 4n.

Part 4 - recursion depth of the random-pivot sort up to n = 2^17,
plotted next to lg n and 4.311 ln n.

    python3 run_benchmarks.py           # full run, roughly a minute
    python3 run_benchmarks.py --quick   # smaller sizes, a few seconds
"""

import argparse
import csv
import gc
import math
import os
import random
import statistics
import sys
import time

from quicksort import (SortTracker, quick_sort, random_pivot_quick_sort,
                       three_way_quick_sort)

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
RUN_CUTOFF = 2.0  # seconds; a single run slower than this ends the series

ALGORITHMS = {
    "Deterministic": quick_sort,
    "Randomized": random_pivot_quick_sort,
    "Randomized 3-way": three_way_quick_sort,
}
DISTRIBUTIONS = ["random", "sorted", "reverse", "nearly-sorted", "few-unique"]


# ----------------------------------------------------------------------
# Building inputs and small helpers
# ----------------------------------------------------------------------

def build_list(kind, n, gen):
    if kind == "random":            # shuffled 0..n-1, so no repeats
        nums = list(range(n))
        gen.shuffle(nums)
        return nums
    if kind == "sorted":
        return list(range(n))
    if kind == "reverse":
        return list(range(n, 0, -1))
    if kind == "nearly-sorted":     # sorted, then swap n/100 random pairs
        nums = list(range(n))
        for _ in range(max(1, n // 100)):
            a, b = gen.randrange(n), gen.randrange(n)
            nums[a], nums[b] = nums[b], nums[a]
        return nums
    if kind == "few-unique":        # just the values 0-9
        return [gen.randint(0, 9) for _ in range(n)]
    raise ValueError(f"unknown input type: {kind}")


def call_sort(label, nums, gen, tracker=None):
    sort_fn = ALGORITHMS[label]
    if sort_fn is quick_sort:
        return sort_fn(nums, tracker=tracker)
    return sort_fn(nums, gen, tracker)


def harmonic_number(n):
    return sum(1.0 / k for k in range(1, n + 1))


def avg_compares_formula(n):
    """Exact expected comparisons for random-pivot quick sort (distinct values)."""
    return 2 * (n + 1) * harmonic_number(n) - 4 * n


class Counted:
    """Holds a value and bumps a shared counter whenever it's compared."""
    __slots__ = ("val",)
    total = 0

    def __init__(self, val):
        self.val = val

    def __lt__(self, other):
        Counted.total += 1
        return self.val < other.val

    def __le__(self, other):
        Counted.total += 1
        return self.val <= other.val

    def __gt__(self, other):
        Counted.total += 1
        return self.val > other.val


def count_compares(label, nums, gen):
    wrapped = [Counted(v) for v in nums]
    Counted.total = 0
    tracker = SortTracker()
    call_sort(label, wrapped, gen, tracker)
    compares = Counted.total   # grab it now, the check below would add more
    assert all(wrapped[k].val <= wrapped[k + 1].val for k in range(len(wrapped) - 1))
    return compares, tracker


def as_ms(seconds):
    return "skipped" if seconds is None else f"{seconds * 1000:,.1f}"


# ----------------------------------------------------------------------
# Part 1: timing
# ----------------------------------------------------------------------

def median_runtime(label, nums, gen, repeats):
    """Median over `repeats` runs. If the first run is slow I don't repeat it."""
    durations = []
    result = None
    gc.disable()
    try:
        for attempt in range(repeats):
            copy = nums[:]
            t0 = time.perf_counter()
            result = call_sort(label, copy, gen)
            durations.append(time.perf_counter() - t0)
            if attempt == 0 and durations[0] > 0.25:
                break
    finally:
        gc.enable()
    assert result == sorted(nums), f"{label} gave the wrong answer"
    return statistics.median(durations)


def timing_experiment(sizes, repeats, gen, log):
    log("=" * 78)
    log("PART 1: running time in ms (median of up to "
        f"{repeats} runs; series stop after a run > {RUN_CUTOFF:.0f} s)")
    log("=" * 78)
    csv_rows = []
    timings = {}
    for kind in DISTRIBUTIONS:
        log(f"\n{kind}")
        log(f"{'n':>8} " + "".join(f"{label:>18}" for label in ALGORITHMS))
        given_up = set()
        for n in sizes:
            nums = build_list(kind, n, gen)
            line = f"{n:>8} "
            for label in ALGORITHMS:
                secs = None
                if label not in given_up:
                    secs = median_runtime(label, nums, gen, repeats)
                    if secs > RUN_CUTOFF:
                        given_up.add(label)
                timings[(kind, label, n)] = secs
                csv_rows.append({"input": kind, "algorithm": label, "n": n,
                                 "seconds": "" if secs is None else f"{secs:.6f}"})
                line += f"{as_ms(secs):>18}"
            log(line)
            sys.stdout.flush()

    # How much slower each time n doubles: ~2.1 means n lg n, 4 means n^2
    log("\nAverage time ratio t(2n)/t(n) over the measured sizes "
        "(n lg n -> ~2.1, n^2 -> 4.0):")
    log(f"{'input':>14} " + "".join(f"{label:>18}" for label in ALGORITHMS))
    for kind in DISTRIBUTIONS:
        line = f"{kind:>14} "
        for label in ALGORITHMS:
            growth = []
            for small, big in zip(sizes, sizes[1:]):
                t_small, t_big = timings[(kind, label, small)], timings[(kind, label, big)]
                if t_small and t_big and t_small > 0.002:   # skip tiny noisy ones
                    growth.append(t_big / t_small)
            line += f"{(statistics.mean(growth) if growth else float('nan')):>18.2f}"
        log(line)
    return csv_rows, timings


# ----------------------------------------------------------------------
# Part 2: comparison counts and recursion depth
# ----------------------------------------------------------------------

def comparison_experiment(sizes, gen, log):
    log("\n" + "=" * 78)
    log("PART 2: comparisons and recursion depth (one run each)")
    log("=" * 78)
    log("  comparisons / (n lg n);  depth = deepest recursion-tree level;"
        "  stack = deepest real call stack")
    csv_rows = []
    for n in sizes:
        n_lg_n = n * math.log2(n)
        log(f"\nn = {n:,}   (n(n-1)/2 = {n * (n - 1) // 2:,};  "
            f"2(n+1)H_n - 4n = {avg_compares_formula(n):,.0f} = "
            f"{avg_compares_formula(n) / n_lg_n:.3f} n lg n;  lg n = {math.log2(n):.1f})")
        log(f"{'input':>14} {'algorithm':>18} {'comparisons':>13} "
            f"{'/ n lg n':>9} {'partitions':>11} {'depth':>7} {'stack':>6}")
        for kind in DISTRIBUTIONS:
            nums = build_list(kind, n, gen)
            for label in ALGORITHMS:
                c, t = count_compares(label, nums, gen)
                csv_rows.append({"input": kind, "algorithm": label, "n": n,
                                 "comparisons": c, "per_nlgn": f"{c / n_lg_n:.4f}",
                                 "partitions": t.split_calls,
                                 "max_depth": t.deepest_level,
                                 "max_stack": t.deepest_stack})
                log(f"{kind:>14} {label:>18} {c:>13,} {c / n_lg_n:>9.3f} "
                    f"{t.split_calls:>11,} {t.deepest_level:>7,} {t.deepest_stack:>6}")
    return csv_rows


# ----------------------------------------------------------------------
# Part 3: spread of comparison counts over many runs
# ----------------------------------------------------------------------

def spread_experiment(n, rounds, gen, log):
    log("\n" + "=" * 78)
    log(f"PART 3: distribution of comparisons over {rounds} trials, n = {n:,}")
    log("=" * 78)
    ordered = list(range(n))
    random_on_sorted, fixed_on_shuffled = [], []
    levels_random, levels_fixed = [], []
    for r in range(rounds):
        c, t = count_compares("Randomized", ordered, random.Random(10_000 + r))
        random_on_sorted.append(c)
        levels_random.append(t.deepest_level)
        shuffled = build_list("random", n, gen)
        c, t = count_compares("Deterministic", shuffled, gen)
        fixed_on_shuffled.append(c)
        levels_fixed.append(t.deepest_level)

    predicted_mean = avg_compares_formula(n)
    predicted_sd = math.sqrt(7 - 2 * math.pi ** 2 / 3) * n   # about 0.648 n
    worst = n * (n - 1) // 2
    log(f"theory: mean = 2(n+1)H_n - 4n = {predicted_mean:,.0f},  "
        f"sd ~ sqrt(7 - 2pi^2/3) n = {predicted_sd:,.0f},  worst case = {worst:,}")
    log(f"{'':34} {'mean':>9} {'sd':>7} {'min':>8} {'max':>8} "
        f"{'max/mean':>9} {'mean depth':>11} {'max depth':>10}")
    for title, counts, levels in [
            ("Randomized on one sorted input", random_on_sorted, levels_random),
            ("Deterministic on random inputs", fixed_on_shuffled, levels_fixed)]:
        avg, sd = statistics.mean(counts), statistics.stdev(counts)
        log(f"{title:34} {avg:>9,.0f} {sd:>7,.0f} {min(counts):>8,} {max(counts):>8,} "
            f"{max(counts) / avg:>9.3f} {statistics.mean(levels):>11.1f} {max(levels):>10}")
    log(f"Deterministic on the sorted input, for comparison: {worst:,} comparisons "
        f"({worst / predicted_mean:.0f}x the randomized mean)")
    return random_on_sorted, fixed_on_shuffled, predicted_mean, predicted_sd, n


# ----------------------------------------------------------------------
# Part 4: recursion depth of the random-pivot version
# ----------------------------------------------------------------------

def depth_experiment(powers, rounds, log):
    log("\n" + "=" * 78)
    log(f"PART 4: recursion depth of randomized Quicksort on sorted input "
        f"({rounds} trials per n)")
    log("=" * 78)
    log(f"{'n':>8} {'lg n':>6} {'4.311 ln n':>11} {'mean depth':>11} "
        f"{'max depth':>10} {'max stack':>10} {'deterministic depth':>20}")
    csv_rows = []
    for p in powers:
        n = 2 ** p
        levels, stacks = [], []
        for r in range(rounds):
            t = SortTracker()
            random_pivot_quick_sort(list(range(n)), random.Random(r), t)
            levels.append(t.deepest_level)
            stacks.append(t.deepest_stack)
        row = {"n": n, "lg_n": p, "ref_4_311_ln_n": 4.311 * math.log(n),
               "mean_depth": statistics.mean(levels), "max_depth": max(levels),
               "max_stack": max(stacks), "deterministic_depth": n - 2}
        csv_rows.append(row)
        log(f"{n:>8,} {p:>6} {row['ref_4_311_ln_n']:>11.1f} {row['mean_depth']:>11.1f} "
            f"{row['max_depth']:>10} {row['max_stack']:>10} {n - 2:>20,}")
    return csv_rows


# ----------------------------------------------------------------------
# Charts
# ----------------------------------------------------------------------

def draw_charts(sizes, timings, compare_rows, spread, depth_rows):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping graphs")
        return
    import chart_style as style
    style.setup(plt)
    colour = {label: style.COLORS[k] for k, label in enumerate(ALGORITHMS)}
    marker = {label: style.MARKERS[k] for k, label in enumerate(ALGORITHMS)}

    # Chart 1: running time for each input type
    fig, axes = plt.subplots(2, 3, figsize=(12, 7.2))
    for ax, kind in zip(axes.flat, DISTRIBUTIONS):
        for label in ALGORITHMS:
            points = [(n, timings[(kind, label, n)] * 1000) for n in sizes
                      if timings[(kind, label, n)] is not None]
            if points:
                xs, ys = zip(*points)
                ax.plot(xs, ys, marker=marker[label], color=colour[label], label=label)
        # grey guide lines for n lg n and n^2, starting at the smallest size
        first_n = sizes[0]
        start_ms = min(timings[(kind, lbl, first_n)] for lbl in ALGORITHMS) * 1000
        ax.plot(sizes, [start_ms * (n * math.log2(n)) / (first_n * math.log2(first_n))
                        for n in sizes],
                ls=":", color=style.LIGHT_TEXT, lw=1, label="∝ n lg n")
        ax.plot(sizes, [start_ms * (n / first_n) ** 2 for n in sizes],
                ls="--", color=style.LIGHT_TEXT, lw=1, label="∝ n²")
        slowest = max(timings[(kind, lbl, n)] or 0
                      for lbl in ALGORITHMS for n in sizes) * 1000
        ax.set_ylim(start_ms / 2, slowest * 3)
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_title(kind)
        ax.set_xlabel("n (list size)")
        ax.set_ylabel("time (ms)")
    axes.flat[0].legend(loc="upper left")
    # bottom-right: comparisons / (n lg n) at the biggest n we counted
    ax = axes.flat[5]
    biggest = max(r["n"] for r in compare_rows)
    bar_w = 0.27
    for k, label in enumerate(ALGORITHMS):
        heights = [next(float(r["per_nlgn"]) for r in compare_rows
                        if r["n"] == biggest and r["input"] == kind
                        and r["algorithm"] == label)
                   for kind in DISTRIBUTIONS]
        ax.bar([j + (k - 1) * bar_w for j in range(len(DISTRIBUTIONS))], heights,
               bar_w, color=colour[label], label=label)
    ax.axhline(avg_compares_formula(biggest) / (biggest * math.log2(biggest)),
               color=style.LIGHT_TEXT, ls=":", lw=1)
    ax.set_yscale("log")
    ax.set_xticks(range(len(DISTRIBUTIONS)))
    ax.set_xticklabels(DISTRIBUTIONS, rotation=20)
    ax.set_title(f"comparisons / (n lg n), n = {biggest:,}")
    ax.grid(axis="x", visible=False)
    fig.suptitle("Quicksort running time by input distribution (log–log)",
                 fontweight="bold", color=style.TEXT)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "sort_times.png"), dpi=150)
    plt.close(fig)

    # Chart 2: histogram of comparison counts
    random_on_sorted, fixed_on_shuffled, predicted_mean, _, n = spread
    fig, ax = plt.subplots(figsize=(8, 4.2))
    lowest = min(random_on_sorted + fixed_on_shuffled)
    highest = max(random_on_sorted + fixed_on_shuffled)
    edges = [lowest + (highest - lowest) * k / 40 for k in range(41)]
    ax.hist(random_on_sorted, bins=edges, alpha=0.6, color=colour["Randomized"],
            label="Randomized, same sorted input every time")
    ax.hist(fixed_on_shuffled, bins=edges, alpha=0.6, color=colour["Deterministic"],
            label="Deterministic, a new random permutation each time")
    ax.axvline(predicted_mean, color=style.TEXT, lw=1.2, ls="--",
               label=f"theory mean 2(n+1)Hₙ − 4n = {predicted_mean:,.0f}")
    ax.set_xlabel("number of comparisons")
    ax.set_ylabel("trials")
    ax.legend(loc="upper right")
    ax.set_title(f"Comparison counts over {len(random_on_sorted):,} runs, n = {n:,}")
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "comparison_distribution.png"), dpi=150)
    plt.close(fig)

    # Chart 3: recursion depth
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ns = [r["n"] for r in depth_rows]
    ax.plot(ns, [r["deterministic_depth"] for r in depth_rows], marker="o",
            color=colour["Deterministic"], label="Deterministic on sorted input (n − 2)")
    ax.plot(ns, [r["mean_depth"] for r in depth_rows], marker="s",
            color=colour["Randomized"], label="Randomized on sorted input, mean")
    ax.plot(ns, [r["max_depth"] for r in depth_rows], marker="s", ls="none",
            mfc="none", color=colour["Randomized"], label="Randomized, worst trial")
    ax.plot(ns, [r["ref_4_311_ln_n"] for r in depth_rows], ls=":",
            color=style.LIGHT_TEXT, lw=1, label="4.311 ln n")
    ax.plot(ns, [r["max_stack"] for r in depth_rows], marker="^",
            color=colour["Randomized 3-way"],
            label="Real call-stack depth (smaller-side recursion)")
    ax.plot(ns, [r["lg_n"] for r in depth_rows], ls="--", color=style.LIGHT_TEXT,
            lw=1, label="lg n")
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xlabel("n (list size)")
    ax.set_ylabel("recursion depth")
    ax.set_title("Recursion depth: Θ(n) for bad pivots, Θ(lg n) with random pivots")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "recursion_depth.png"), dpi=150)
    plt.close(fig)


def save_csv(filename, rows):
    if not rows:
        return
    with open(os.path.join(RESULTS_DIR, filename), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--quick", action="store_true", help="smaller, faster run")
    args = parser.parse_args()

    if args.quick:
        sizes = [500, 1000, 2000, 4000, 8000]
        count_sizes = [1000]
        spread_n, spread_rounds = 1000, 100
        depth_powers, depth_rounds = list(range(8, 15)), 5
        repeats = 3
    else:
        sizes = [1000, 2000, 4000, 8000, 16000, 32000, 64000, 128000]
        count_sizes = [1000, 4000]
        spread_n, spread_rounds = 2000, 1000
        depth_powers, depth_rounds = list(range(8, 18)), 20
        repeats = 5

    os.makedirs(RESULTS_DIR, exist_ok=True)
    gen = random.Random(532)
    output_lines = []

    def log(msg=""):
        print(msg)
        output_lines.append(msg)

    log(f"Python {sys.version.split()[0]}  |  "
        f"{'quick' if args.quick else 'full'} run  |  seed 532")
    began = time.perf_counter()
    time_rows, timings = timing_experiment(sizes, repeats, gen, log)
    compare_rows = comparison_experiment(count_sizes, gen, log)
    spread = spread_experiment(spread_n, spread_rounds, gen, log)
    depth_rows = depth_experiment(depth_powers, depth_rounds, log)
    log(f"\nTotal time: {time.perf_counter() - began:.0f} s")

    save_csv("sort_times.csv", time_rows)
    save_csv("comparisons.csv", compare_rows)
    save_csv("recursion_depth.csv", depth_rows)
    save_csv("comparison_distribution.csv",
             [{"trial": k, "randomized_on_sorted": a, "deterministic_on_random": b}
              for k, (a, b) in enumerate(zip(spread[0], spread[1]))])
    with open(os.path.join(RESULTS_DIR, "benchmark_output.txt"), "w") as f:
        f.write("\n".join(output_lines) + "\n")
    draw_charts(sizes, timings, compare_rows, spread, depth_rows)
    print(f"\nResults written to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
