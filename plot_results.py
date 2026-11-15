"""
Draws the charts in results/ from the CSV files the benchmark saved.

Keeping the plotting separate means I can change how the charts look
without re-running the whole benchmark (and without the timings
shifting around). run_benchmarks.py calls draw_all() at the end, or you
can run this file on its own:

    python3 plot_results.py
"""

import csv
import math
import os
import re

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
ORDER = ["Deterministic", "Randomized", "Randomized 3-way"]
INPUTS = ["random", "sorted", "reverse", "nearly-sorted", "few-unique"]
PANEL_TITLES = {
    "random": "(a) Shuffled list",
    "sorted": "(b) Already sorted",
    "reverse": "(c) Reverse sorted",
    "nearly-sorted": "(d) Nearly sorted (1% swapped)",
    "few-unique": "(e) Only 10 distinct values",
}


def read_rows(filename):
    with open(os.path.join(RESULTS_DIR, filename), newline="") as f:
        return list(csv.DictReader(f))


def avg_compares_formula(n):
    return 2 * (n + 1) * sum(1.0 / k for k in range(1, n + 1)) - 4 * n


def spread_size():
    """The n used in Part 3 isn't in the CSV, so read it from the text output."""
    with open(os.path.join(RESULTS_DIR, "benchmark_output.txt")) as f:
        match = re.search(r"PART 3: .*?n = ([\d,]+)", f.read())
    return int(match.group(1).replace(",", ""))


# ----------------------------------------------------------------------
# 1. running time, one panel per input type
# ----------------------------------------------------------------------

def runtime_chart(plt, theme):
    rows = read_rows("sort_times.csv")
    sizes = sorted({int(r["n"]) for r in rows})
    ms = {(r["input"], r["algorithm"], int(r["n"])):
          (float(r["seconds"]) * 1000 if r["seconds"] else None) for r in rows}

    fig, axes = plt.subplots(2, 3, figsize=(12.5, 7.4))
    for ax, kind in zip(axes.flat, INPUTS):
        labelled = set()
        for algo in ORDER:
            pts = [(n, ms[(kind, algo, n)]) for n in sizes if ms[(kind, algo, n)] is not None]
            xs, ys = zip(*pts)
            ax.plot(xs, ys, color=theme.PALETTE[algo], marker=theme.SHAPES[algo],
                    mec="white", mew=0.6)
            # mark where a series was cut off for being too slow
            if len(pts) < len(sizes) and pts[-1][0] not in labelled:
                labelled.add(pts[-1][0])
                ax.annotate("stopped\n(> 2 s)", xy=(xs[-1], ys[-1]),
                            xytext=(6, -4), textcoords="offset points",
                            fontsize=7.5, color=theme.MUTED, va="top")
        # guide lines that start from the fastest point at the smallest size
        n0 = sizes[0]
        y0 = min(ms[(kind, a, n0)] for a in ORDER)
        ax.plot(sizes, [y0 * n * math.log2(n) / (n0 * math.log2(n0)) for n in sizes],
                color=theme.MUTED, lw=0.9, ls=(0, (1, 2)))
        ax.plot(sizes, [y0 * (n / n0) ** 2 for n in sizes],
                color=theme.MUTED, lw=0.9, ls=(0, (5, 3)))
        top = max(v for (k, _, _), v in ms.items() if k == kind and v)
        ax.set_ylim(y0 / 2, top * 4)
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_title(PANEL_TITLES[kind])
        ax.set_xlabel("list size n")
        ax.set_ylabel("median time (ms)")

    # the sixth slot holds the legend and a short note instead of a plot
    key = axes.flat[5]
    key.axis("off")
    handles = [plt.Line2D([], [], color=theme.PALETTE[a], marker=theme.SHAPES[a],
                          mec="white", label=theme.NICE_NAMES[a]) for a in ORDER]
    handles += [plt.Line2D([], [], color=theme.MUTED, lw=0.9, ls=(0, (1, 2)),
                           label="grows like n lg n"),
                plt.Line2D([], [], color=theme.MUTED, lw=0.9, ls=(0, (5, 3)),
                           label="grows like n²")]
    key.legend(handles=handles, loc="upper left", title="Legend",
               title_fontsize=9.5, borderpad=0.9, labelspacing=0.8)
    key.text(0.02, 0.18,
             "Both axes are logarithmic, so a slope of 1\n"
             "is roughly n lg n and a slope of 2 is n².\n"
             "Each point is the median of up to 5 runs.",
             transform=key.transAxes, fontsize=8.5, color=theme.MUTED, va="top")

    fig.suptitle("How long each version takes, by kind of input", x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(os.path.join(RESULTS_DIR, "sort_times.png"), dpi=150)
    plt.close(fig)


# ----------------------------------------------------------------------
# 2. comparisons / (n lg n) at the largest counted size
# ----------------------------------------------------------------------

def comparisons_chart(plt, theme):
    rows = read_rows("comparisons.csv")
    n = max(int(r["n"]) for r in rows)
    ratio = {(r["input"], r["algorithm"]): float(r["per_nlgn"])
             for r in rows if int(r["n"]) == n}

    fig, ax = plt.subplots(figsize=(8.5, 5.4))
    bar_h = 0.26
    for k, algo in enumerate(ORDER):
        ys = [j + (k - 1) * bar_h for j in range(len(INPUTS))]
        vals = [ratio[(kind, algo)] for kind in INPUTS]
        ax.barh(ys, vals, height=bar_h, color=theme.PALETTE[algo],
                label=theme.NICE_NAMES[algo], edgecolor="white", linewidth=0.5)
        for y, v in zip(ys, vals):
            ax.text(v * 1.08, y, f"{v:.2f}", va="center", fontsize=7.5, color=theme.INK)
    expected = avg_compares_formula(n) / (n * math.log2(n))
    ax.axvline(expected, color=theme.INK, lw=1, ls=(0, (4, 2)))
    ax.text(expected * 1.06, -0.5, f"average-case theory = {expected:.2f}",
            fontsize=8, color=theme.INK, va="bottom")
    ax.set_xscale("log")
    ax.set_xlim(0.3, 600)
    ax.set_yticks(range(len(INPUTS)))
    ax.set_yticklabels([PANEL_TITLES[k][4:] for k in INPUTS])
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("comparisons ÷ (n lg n)   [log scale]")
    ax.set_title(f"Comparisons made at n = {n:,} (lower is better)")
    ax.set_ylim(len(INPUTS) - 0.55, -0.75)
    ax.legend(loc="upper center", bbox_to_anchor=(0.42, -0.14), ncol=2)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "comparison_counts.png"), dpi=150)
    plt.close(fig)


# ----------------------------------------------------------------------
# 3. spread of comparison counts over many runs
# ----------------------------------------------------------------------

def spread_chart(plt, theme):
    rows = read_rows("comparison_distribution.csv")
    rand_counts = [int(r["randomized_on_sorted"]) for r in rows]
    fixed_counts = [int(r["deterministic_on_random"]) for r in rows]
    n = spread_size()
    mean = avg_compares_formula(n)
    sd = math.sqrt(7 - 2 * math.pi ** 2 / 3) * n

    lo, hi = min(rand_counts + fixed_counts), max(rand_counts + fixed_counts)
    width = (hi - lo) / 36
    edges = [lo + width * k for k in range(37)]

    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    ax.axvspan(mean - sd, mean + sd, color=theme.SHADE, zorder=0,
               label="theory mean ± 1 sd")
    ax.hist(rand_counts, bins=edges, histtype="step", lw=1.8,
            color=theme.PALETTE["Randomized"],
            label="Random pivot, same sorted list each run")
    ax.hist(fixed_counts, bins=edges, histtype="step", lw=1.8,
            color=theme.PALETTE["Deterministic"], ls=(0, (4, 1.5)),
            label="Fixed pivot, new shuffled list each run")
    # normal curve with the theoretical mean and sd, scaled to the bar width
    xs = [lo + (hi - lo) * k / 300 for k in range(301)]
    scale = len(rows) * width / (sd * math.sqrt(2 * math.pi))
    ax.plot(xs, [scale * math.exp(-0.5 * ((x - mean) / sd) ** 2) for x in xs],
            color=theme.MUTED, lw=1, label="normal curve from theory")
    ax.axvline(mean, color=theme.INK, lw=0.9)
    ax.set_xlabel("comparisons in one run")
    ax.set_ylabel("number of runs")
    ax.set_title(f"{len(rows):,} runs at n = {n:,}: the two versions give the same spread")
    ax.legend(loc="upper right")

    worst = n * (n - 1) // 2
    ax.text(0.985, 0.60,
            f"theory mean  {mean:,.0f}\n"
            f"random pivot {sum(rand_counts) / len(rows):,.0f}\n"
            f"fixed pivot  {sum(fixed_counts) / len(rows):,.0f}\n\n"
            f"fixed pivot on the sorted\nlist: {worst:,} (off the chart)",
            transform=ax.transAxes, va="top", ha="right", multialignment="left", fontsize=8, family="monospace",
            bbox=dict(boxstyle="square,pad=0.5", fc="white", ec=theme.FAINT))
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "comparison_distribution.png"), dpi=150)
    plt.close(fig)


# ----------------------------------------------------------------------
# 4. recursion depth
# ----------------------------------------------------------------------

def depth_chart(plt, theme):
    rows = read_rows("recursion_depth.csv")
    ns = [int(r["n"]) for r in rows]
    lgs = [int(r["lg_n"]) for r in rows]
    mean_d = [float(r["mean_depth"]) for r in rows]
    max_d = [int(r["max_depth"]) for r in rows]
    stack = [int(r["max_stack"]) for r in rows]
    fixed = [int(r["deterministic_depth"]) for r in rows]
    ref = [float(r["ref_4_311_ln_n"]) for r in rows]

    fig, (left, right) = plt.subplots(1, 2, figsize=(12, 4.6),
                                      gridspec_kw={"width_ratios": [1, 1.15]})

    left.plot(ns, fixed, color=theme.PALETTE["Deterministic"],
              marker=theme.SHAPES["Deterministic"], mec="white",
              label="fixed pivot (n − 2 levels)")
    left.plot(ns, mean_d, color=theme.PALETTE["Randomized"],
              marker=theme.SHAPES["Randomized"], mec="white",
              label="random pivot (average)")
    left.set_xscale("log", base=2)
    left.set_yscale("log")
    left.set_xlabel("list size n")
    left.set_ylabel("recursion-tree depth")
    left.set_title("(a) Sorted input: fixed vs. random pivot")
    left.legend(loc="upper left")

    right.fill_between(lgs, mean_d, max_d, color=theme.PALETTE["Randomized"],
                       alpha=0.15, lw=0, label="range up to the worst of 20 runs")
    right.plot(lgs, mean_d, color=theme.PALETTE["Randomized"],
               marker=theme.SHAPES["Randomized"], mec="white",
               label="random pivot, average tree depth")
    right.plot(lgs, ref, color=theme.MUTED, ls=(0, (5, 3)), lw=0.9,
               label="4.311 ln n (random BST height)")
    right.plot(lgs, lgs, color=theme.MUTED, ls=(0, (1, 2)), lw=0.9, label="lg n")
    right.step(lgs, stack, where="mid", color=theme.PALETTE["Randomized 3-way"],
               lw=1.6, label="real call stack (smaller-half recursion)")
    right.set_xticks(lgs)
    right.set_xticklabels([f"$2^{{{p}}}$" for p in lgs])
    right.set_xlabel("list size n  (x-axis is lg n, so straight lines mean Θ(lg n))")
    right.set_ylabel("depth")
    right.set_ylim(0, max(ref) * 1.1)
    right.set_title("(b) Random pivot up close")
    right.legend(loc="upper left")

    fig.suptitle("How deep the recursion goes", x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(os.path.join(RESULTS_DIR, "recursion_depth.png"), dpi=150)
    plt.close(fig)


def draw_all():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping graphs")
        return
    import plot_theme as theme
    theme.apply(plt)
    runtime_chart(plt, theme)
    comparisons_chart(plt, theme)
    spread_chart(plt, theme)
    depth_chart(plt, theme)


if __name__ == "__main__":
    draw_all()
    print(f"Charts written to {RESULTS_DIR}")
