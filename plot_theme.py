"""Look and feel for the result charts.

Each algorithm keeps the same colour and marker on every chart so they
are easy to follow from one figure to the next:
    fixed pivot   -> navy, diamonds
    random pivot  -> brick red, circles
    3-way         -> teal, triangles
"""

PALETTE = {
    "Deterministic": "#1f3b73",
    "Randomized": "#c8553d",
    "Randomized 3-way": "#2a9d8f",
}
SHAPES = {
    "Deterministic": "D",
    "Randomized": "o",
    "Randomized 3-way": "v",
}
# what each algorithm is called on the charts
NICE_NAMES = {
    "Deterministic": "Fixed pivot (quick_sort)",
    "Randomized": "Random pivot (random_pivot_quick_sort)",
    "Randomized 3-way": "Random 3-way (three_way_quick_sort)",
}

INK = "#222222"
MUTED = "#6c757d"
FAINT = "#d9d9d9"
PAPER = "#ffffff"
SHADE = "#f4f1ea"   # background band used to highlight a region


def apply(plt):
    plt.rcParams.update({
        "figure.facecolor": PAPER,
        "savefig.facecolor": PAPER,
        "axes.facecolor": PAPER,
        "font.family": "serif",
        "font.serif": ["DejaVu Serif", "Times New Roman", "serif"],
        "mathtext.fontset": "dejavuserif",
        "axes.edgecolor": INK,
        "axes.linewidth": 0.7,
        "axes.labelcolor": INK,
        "axes.labelsize": 9.5,
        "axes.titlesize": 10.5,
        "axes.titleweight": "normal",
        "axes.titlelocation": "left",
        "axes.titlepad": 8,
        "axes.spines.top": True,
        "axes.spines.right": True,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": FAINT,
        "grid.linestyle": "--",
        "grid.linewidth": 0.5,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.top": True,
        "ytick.right": True,
        "xtick.color": INK,
        "ytick.color": INK,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "legend.fontsize": 8.5,
        "legend.frameon": True,
        "legend.framealpha": 0.95,
        "legend.edgecolor": FAINT,
        "legend.fancybox": False,
        "lines.linewidth": 1.6,
        "lines.markersize": 4.5,
        "figure.titlesize": 13,
        "figure.titleweight": "bold",
    })
