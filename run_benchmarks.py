"""
Empirical comparison of deterministic and randomized Quicksort.

Part 1: running time. Each version sorts random, sorted, reverse-sorted,
nearly-sorted and few-unique lists of doubling size. I take the median
of several runs, each on a fresh copy. Quadratic cases get slow fast,
so a series stops once a single run takes longer than TIME_LIMIT
seconds; the larger sizes are reported as "skipped".

Part 2: comparisons and recursion depth. Timing in Python is noisy, so
every value is also wrapped in a class that counts comparisons. The
counts are checked against the formulas from the analysis:
    worst case            n(n-1)/2
    expected (random)     2(n+1)H_n - 4n  ~  1.39 n lg n

Part 3: how much luck is involved. Randomized Quicksort is run many
times on the *same* sorted input (only the random pivots change), and
deterministic Quicksort is run on many random permutations. The
analysis says both should give the same distribution of comparison
counts, tightly packed around 2(n+1)H_n - 4n.

Part 4: recursion depth of randomized Quicksort for n up to 2^17, versus
the lg n and 4.311 ln n reference curves.

    python3 run_benchmarks.py           # full run, about 2-3 minutes
    python3 run_benchmarks.py --quick   # smaller sizes, about 15 seconds
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

from quicksort import (QuickSortStats, quicksort, randomized_quicksort,
                       randomized_quicksort_3way)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
TIME_LIMIT = 2.0  # seconds for one run before a series is cut off

SORTERS = {
    "Deterministic": quicksort,
    "Randomized": randomized_quicksort,
    "Randomized 3-way": randomized_quicksort_3way,
}
INPUT_TYPES = ["random", "sorted", "reverse", "nearly-sorted", "few-unique"]


# ---------------------------------------------------------------------------
# Inputs and helpers
# ---------------------------------------------------------------------------

def make_input(kind, n, rand):
    if kind == "random":            # random permutation, all keys distinct
        data = list(range(n))
        rand.shuffle(data)
        return data
    if kind == "sorted":
        return list(range(n))
    if kind == "reverse":
        return list(range(n, 0, -1))
    if kind == "nearly-sorted":     # sorted, then 1% of positions swapped
        data = list(range(n))
        for _ in range(max(1, n // 100)):
            a, b = rand.randrange(n), rand.randrange(n)
            data[a], data[b] = data[b], data[a]
        return data
    if kind == "few-unique":        # only 10 distinct keys
        return [rand.randint(0, 9) for _ in range(n)]
    raise ValueError(f"unknown input type: {kind}")


def run_sort(name, data, rand, stats=None):
    fn = SORTERS[name]
    if fn is quicksort:
        return fn(data, stats=stats)
    return fn(data, rand, stats)


def harmonic(n):
    return sum(1.0 / k for k in range(1, n + 1))


def expected_comparisons(n):
    """Exact expected comparisons of randomized Quicksort, distinct keys."""
    return 2 * (n + 1) * harmonic(n) - 4 * n


class CountingValue:
    """Wraps a value and counts every comparison made on it."""
    __slots__ = ("val",)
    compares = 0

    def __init__(self, val):
        self.val = val

    def __lt__(self, other):
        CountingValue.compares += 1
        return self.val < other.val

    def __le__(self, other):
        CountingValue.compares += 1
        return self.val <= other.val

    def __gt__(self, other):
        CountingValue.compares += 1
        return self.val > other.val


def count_run(name, data, rand):
    wrapped = [CountingValue(v) for v in data]
    CountingValue.compares = 0
    stats = QuickSortStats()
    run_sort(name, wrapped, rand, stats)
    compares = CountingValue.compares   # read before the check below adds more
    assert all(wrapped[i].val <= wrapped[i + 1].val for i in range(len(wrapped) - 1))
    return compares, stats


def fmt_ms(seconds):
    return "skipped" if seconds is None else f"{seconds * 1000:,.1f}"


# ---------------------------------------------------------------------------
# Part 1: timing
# ---------------------------------------------------------------------------

def time_one(name, data, rand, runs):
    """Median time over `runs` runs; just one run if the first is slow."""
    times = []
    out = None
    gc.disable()
    try:
        for r in range(runs):
            fresh = data[:]
            start = time.perf_counter()
            out = run_sort(name, fresh, rand)
            times.append(time.perf_counter() - start)
            if r == 0 and times[0] > 0.25:
                break
    finally:
        gc.enable()
    assert out == sorted(data), f"{name} gave the wrong answer"
    return statistics.median(times)


def part1_timing(sizes, runs, rand, log):
    log("=" * 78)
    log("PART 1: running time in ms (median of up to "
        f"{runs} runs; series stop after a run > {TIME_LIMIT:.0f} s)")
    log("=" * 78)
    rows = []
    results = {}
    for kind in INPUT_TYPES:
        log(f"\n{kind}")
        log(f"{'n':>8} " + "".join(f"{name:>18}" for name in SORTERS))
        stopped = set()
        for n in sizes:
            data = make_input(kind, n, rand)
            line = f"{n:>8} "
            for name in SORTERS:
                t = None
                if name not in stopped:
                    t = time_one(name, data, rand, runs)
                    if t > TIME_LIMIT:
                        stopped.add(name)
                results[(kind, name, n)] = t
                rows.append({"input": kind, "algorithm": name, "n": n,
                             "seconds": "" if t is None else f"{t:.6f}"})
                line += f"{fmt_ms(t):>18}"
            log(line)
            sys.stdout.flush()

    # Growth factor when n doubles: about 2.1 for n lg n, 4 for n^2.
    log("\nAverage time ratio t(2n)/t(n) over the measured sizes "
        "(n lg n -> ~2.1, n^2 -> 4.0):")
    log(f"{'input':>14} " + "".join(f"{name:>18}" for name in SORTERS))
    for kind in INPUT_TYPES:
        line = f"{kind:>14} "
        for name in SORTERS:
            ratios = []
            for a, b in zip(sizes, sizes[1:]):
                ta, tb = results[(kind, name, a)], results[(kind, name, b)]
                if ta and tb and ta > 0.002:   # ignore tiny, noisy timings
                    ratios.append(tb / ta)
            line += f"{(statistics.mean(ratios) if ratios else float('nan')):>18.2f}"
        log(line)
    return rows, results


# ---------------------------------------------------------------------------
# Part 2: comparisons and recursion depth
# ---------------------------------------------------------------------------

def part2_comparisons(sizes, rand, log):
    log("\n" + "=" * 78)
    log("PART 2: comparisons and recursion depth (one run each)")
    log("=" * 78)
    log("  comparisons / (n lg n);  depth = deepest recursion-tree level;"
        "  stack = deepest real call stack")
    rows = []
    for n in sizes:
        nlgn = n * math.log2(n)
        log(f"\nn = {n:,}   (n(n-1)/2 = {n * (n - 1) // 2:,};  "
            f"2(n+1)H_n - 4n = {expected_comparisons(n):,.0f} = "
            f"{expected_comparisons(n) / nlgn:.3f} n lg n;  lg n = {math.log2(n):.1f})")
        log(f"{'input':>14} {'algorithm':>18} {'comparisons':>13} "
            f"{'/ n lg n':>9} {'partitions':>11} {'depth':>7} {'stack':>6}")
        for kind in INPUT_TYPES:
            data = make_input(kind, n, rand)
            for name in SORTERS:
                c, s = count_run(name, data, rand)
                rows.append({"input": kind, "algorithm": name, "n": n,
                             "comparisons": c, "per_nlgn": f"{c / nlgn:.4f}",
                             "partitions": s.partitions, "max_depth": s.max_depth,
                             "max_stack": s.max_stack})
                log(f"{kind:>14} {name:>18} {c:>13,} {c / nlgn:>9.3f} "
                    f"{s.partitions:>11,} {s.max_depth:>7,} {s.max_stack:>6}")
    return rows


# ---------------------------------------------------------------------------
# Part 3: distribution over many runs
# ---------------------------------------------------------------------------

def part3_distribution(n, trials, rand, log):
    log("\n" + "=" * 78)
    log(f"PART 3: distribution of comparisons over {trials} trials, n = {n:,}")
    log("=" * 78)
    sorted_input = list(range(n))
    rand_on_sorted, det_on_random = [], []
    depth_rand, depth_det = [], []
    for t in range(trials):
        c, s = count_run("Randomized", sorted_input, random.Random(10_000 + t))
        rand_on_sorted.append(c)
        depth_rand.append(s.max_depth)
        perm = make_input("random", n, rand)
        c, s = count_run("Deterministic", perm, rand)
        det_on_random.append(c)
        depth_det.append(s.max_depth)

    mean_theory = expected_comparisons(n)
    sd_theory = math.sqrt(7 - 2 * math.pi ** 2 / 3) * n   # ~0.648 n
    worst = n * (n - 1) // 2
    log(f"theory: mean = 2(n+1)H_n - 4n = {mean_theory:,.0f},  "
        f"sd ~ sqrt(7 - 2pi^2/3) n = {sd_theory:,.0f},  worst case = {worst:,}")
    log(f"{'':34} {'mean':>9} {'sd':>7} {'min':>8} {'max':>8} "
        f"{'max/mean':>9} {'mean depth':>11} {'max depth':>10}")
    summary = {}
    for label, xs, ds in [("Randomized on one sorted input", rand_on_sorted, depth_rand),
                          ("Deterministic on random inputs", det_on_random, depth_det)]:
        m, sd = statistics.mean(xs), statistics.stdev(xs)
        summary[label] = (m, sd)
        log(f"{label:34} {m:>9,.0f} {sd:>7,.0f} {min(xs):>8,} {max(xs):>8,} "
            f"{max(xs) / m:>9.3f} {statistics.mean(ds):>11.1f} {max(ds):>10}")
    log(f"Deterministic on the sorted input, for comparison: {worst:,} comparisons "
        f"({worst / mean_theory:.0f}x the randomized mean)")
    return rand_on_sorted, det_on_random, mean_theory, sd_theory, n


# ---------------------------------------------------------------------------
# Part 4: recursion depth of randomized Quicksort
# ---------------------------------------------------------------------------

def part4_depth(exponents, trials, log):
    log("\n" + "=" * 78)
    log(f"PART 4: recursion depth of randomized Quicksort on sorted input "
        f"({trials} trials per n)")
    log("=" * 78)
    log(f"{'n':>8} {'lg n':>6} {'4.311 ln n':>11} {'mean depth':>11} "
        f"{'max depth':>10} {'max stack':>10} {'deterministic depth':>20}")
    rows = []
    for e in exponents:
        n = 2 ** e
        depths, stacks = [], []
        for t in range(trials):
            s = QuickSortStats()
            randomized_quicksort(list(range(n)), random.Random(t), s)
            depths.append(s.max_depth)
            stacks.append(s.max_stack)
        row = {"n": n, "lg_n": e, "ref_4_311_ln_n": 4.311 * math.log(n),
               "mean_depth": statistics.mean(depths), "max_depth": max(depths),
               "max_stack": max(stacks), "deterministic_depth": n - 2}
        rows.append(row)
        log(f"{n:>8,} {e:>6} {row['ref_4_311_ln_n']:>11.1f} {row['mean_depth']:>11.1f} "
            f"{row['max_depth']:>10} {row['max_stack']:>10} {n - 2:>20,}")
    return rows


# ---------------------------------------------------------------------------
# Graphs
# ---------------------------------------------------------------------------

def make_graphs(sizes, results, comp_rows, dist, depth_rows):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping graphs")
        return
    import chart_style as cs
    cs.setup(plt)
    color = {name: cs.COLORS[i] for i, name in enumerate(SORTERS)}
    marker = {name: cs.MARKERS[i] for i, name in enumerate(SORTERS)}

    # 1. Running time per input type -------------------------------------
    fig, axes = plt.subplots(2, 3, figsize=(12, 7.2))
    for ax, kind in zip(axes.flat, INPUT_TYPES):
        for name in SORTERS:
            pts = [(n, results[(kind, name, n)] * 1000) for n in sizes
                   if results[(kind, name, n)] is not None]
            if pts:
                xs, ys = zip(*pts)
                ax.plot(xs, ys, marker=marker[name], color=color[name], label=name)
        # reference slopes, anchored at the smallest size
        n0 = sizes[0]
        base = min(results[(kind, nm, n0)] for nm in SORTERS) * 1000
        xs = [n for n in sizes]
        ax.plot(xs, [base * (n * math.log2(n)) / (n0 * math.log2(n0)) for n in xs],
                ls=":", color=cs.LIGHT_TEXT, lw=1, label="∝ n lg n")
        ax.plot(xs, [base * (n / n0) ** 2 for n in xs],
                ls="--", color=cs.LIGHT_TEXT, lw=1, label="∝ n²")
        top = max(results[(kind, nm, n)] or 0 for nm in SORTERS for n in sizes) * 1000
        ax.set_ylim(base / 2, top * 3)
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_title(kind)
        ax.set_xlabel("n (list size)")
        ax.set_ylabel("time (ms)")
    axes.flat[0].legend(loc="upper left")
    # last panel: comparisons / (n lg n) at the largest counted n
    ax = axes.flat[5]
    n_max = max(r["n"] for r in comp_rows)
    width = 0.27
    for i, name in enumerate(SORTERS):
        vals = [next(float(r["per_nlgn"]) for r in comp_rows
                     if r["n"] == n_max and r["input"] == k and r["algorithm"] == name)
                for k in INPUT_TYPES]
        ax.bar([j + (i - 1) * width for j in range(len(INPUT_TYPES))], vals, width,
               color=color[name], label=name)
    ax.axhline(expected_comparisons(n_max) / (n_max * math.log2(n_max)),
               color=cs.LIGHT_TEXT, ls=":", lw=1)
    ax.set_yscale("log")
    ax.set_xticks(range(len(INPUT_TYPES)))
    ax.set_xticklabels(INPUT_TYPES, rotation=20)
    ax.set_title(f"comparisons / (n lg n), n = {n_max:,}")
    ax.grid(axis="x", visible=False)
    fig.suptitle("Quicksort running time by input distribution (log–log)",
                 fontweight="bold", color=cs.TEXT)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "sort_times.png"), dpi=150)
    plt.close(fig)

    # 2. Distribution of comparison counts --------------------------------
    rand_on_sorted, det_on_random, mean_theory, sd_theory, n = dist
    fig, ax = plt.subplots(figsize=(8, 4.2))
    lo = min(rand_on_sorted + det_on_random)
    hi = max(rand_on_sorted + det_on_random)
    bins = [lo + (hi - lo) * i / 40 for i in range(41)]
    ax.hist(rand_on_sorted, bins=bins, alpha=0.6, color=color["Randomized"],
            label="Randomized, same sorted input every time")
    ax.hist(det_on_random, bins=bins, alpha=0.6, color=color["Deterministic"],
            label="Deterministic, a new random permutation each time")
    ax.axvline(mean_theory, color=cs.TEXT, lw=1.2, ls="--",
               label=f"theory mean 2(n+1)Hₙ − 4n = {mean_theory:,.0f}")
    ax.set_xlabel("number of comparisons")
    ax.set_ylabel("trials")
    ax.legend(loc="upper right")
    ax.set_title(f"Comparison counts over {len(rand_on_sorted):,} runs, "
                 f"n = {n:,}")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "comparison_distribution.png"), dpi=150)
    plt.close(fig)

    # 3. Recursion depth ---------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ns = [r["n"] for r in depth_rows]
    ax.plot(ns, [r["deterministic_depth"] for r in depth_rows], marker="o",
            color=color["Deterministic"], label="Deterministic on sorted input (n − 2)")
    ax.plot(ns, [r["mean_depth"] for r in depth_rows], marker="s",
            color=color["Randomized"], label="Randomized on sorted input, mean")
    ax.plot(ns, [r["max_depth"] for r in depth_rows], marker="s", ls="none",
            mfc="none", color=color["Randomized"], label="Randomized, worst trial")
    ax.plot(ns, [r["ref_4_311_ln_n"] for r in depth_rows], ls=":",
            color=cs.LIGHT_TEXT, lw=1, label="4.311 ln n")
    ax.plot(ns, [r["max_stack"] for r in depth_rows], marker="^",
            color=color["Randomized 3-way"],
            label="Real call-stack depth (smaller-side recursion)")
    ax.plot(ns, [r["lg_n"] for r in depth_rows], ls="--", color=cs.LIGHT_TEXT,
            lw=1, label="lg n")
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xlabel("n (list size)")
    ax.set_ylabel("recursion depth")
    ax.set_title("Recursion depth: Θ(n) for bad pivots, Θ(lg n) with random pivots")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "recursion_depth.png"), dpi=150)
    plt.close(fig)


def write_csv(name, rows):
    if not rows:
        return
    with open(os.path.join(OUT_DIR, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--quick", action="store_true", help="smaller, faster run")
    args = parser.parse_args()

    if args.quick:
        sizes = [500, 1000, 2000, 4000, 8000]
        comp_sizes = [1000]
        dist_n, dist_trials = 1000, 100
        depth_exps, depth_trials = list(range(8, 15)), 5
        runs = 3
    else:
        sizes = [1000, 2000, 4000, 8000, 16000, 32000, 64000, 128000]
        comp_sizes = [1000, 4000]
        dist_n, dist_trials = 2000, 1000
        depth_exps, depth_trials = list(range(8, 18)), 20
        runs = 5

    os.makedirs(OUT_DIR, exist_ok=True)
    rand = random.Random(532)
    lines = []

    def log(msg=""):
        print(msg)
        lines.append(msg)

    log(f"Python {sys.version.split()[0]}  |  "
        f"{'quick' if args.quick else 'full'} run  |  seed 532")
    start = time.perf_counter()
    time_rows, results = part1_timing(sizes, runs, rand, log)
    comp_rows = part2_comparisons(comp_sizes, rand, log)
    dist = part3_distribution(dist_n, dist_trials, rand, log)
    depth_rows = part4_depth(depth_exps, depth_trials, log)
    log(f"\nTotal time: {time.perf_counter() - start:.0f} s")

    write_csv("sort_times.csv", time_rows)
    write_csv("comparisons.csv", comp_rows)
    write_csv("recursion_depth.csv", depth_rows)
    write_csv("comparison_distribution.csv",
              [{"trial": i, "randomized_on_sorted": a, "deterministic_on_random": b}
               for i, (a, b) in enumerate(zip(dist[0], dist[1]))])
    with open(os.path.join(OUT_DIR, "benchmark_output.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    make_graphs(sizes, results, comp_rows, dist, depth_rows)
    print(f"\nResults written to {OUT_DIR}")


if __name__ == "__main__":
    main()
