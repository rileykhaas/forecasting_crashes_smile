"""E: Replicate Figure 1 -- single-name crash-probability bounds for AAPL & AIG.

Plots the option-implied lower and upper bounds on the probability of a 20% crash
(threshold_q = 0.80) over a one-month horizon, over time, for Apple and AIG, from
results.parquet. Matches Martin & Shi (2025) Figure 1: a fan chart with the band
between each name's lower and upper bound shaded. Defaults to the paper's
1996-2022 window; pass a later ``end`` for the extension version.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: save files, never open a window
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import MultipleLocator, PercentFormatter  # noqa: E402

from settings import config  # noqa: E402

OUTPUT_DIR = Path(config("OUTPUT_DIR"))

THRESHOLD_Q = 0.80  # a 20% crash
HORIZON_MONTHS = 1  # one-month horizon
REPL_START = pd.Timestamp("1996-01-01")
REPL_END = pd.Timestamp("2022-12-31")

# (label, OptionMetrics secid, lower-bound color, upper-bound color).
NAMES = [
    ("AIG", 101397, "#e79ac2", "#e0576f"),    # pink / red
    ("Apple", 101594, "#5fc0e8", "#4f74c0"),  # light blue / blue
]


def series_for(results, secid, threshold=THRESHOLD_Q, horizon=HORIZON_MONTHS,
               start=REPL_START, end=REPL_END):
    """The (date, bound_lower, bound_upper) series for one name, sorted by date."""
    sel = results[
        (results["secid"] == secid)
        & (results["threshold_q"] == threshold)
        & (results["horizon_months"] == horizon)
        & (results["date"] >= start)
        & (results["date"] <= end)
    ]
    return sel.sort_values("date")


def build_figure1(results, names=NAMES, start=REPL_START, end=REPL_END):
    """Return the Figure 1 fan chart (matplotlib Figure)."""
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ymax = 0.0
    for label, secid, c_lo, c_hi in names:
        s = series_for(results, secid, start=start, end=end)
        ymax = max(ymax, float(s["bound_upper"].max()))
        ax.fill_between(s["date"], s["bound_lower"], s["bound_upper"],
                        color=c_hi, alpha=0.15, linewidth=0)
        ax.plot(s["date"], s["bound_upper"], color=c_hi, lw=1.0,
                label=f"{label}: upper bound")
        ax.plot(s["date"], s["bound_lower"], color=c_lo, lw=1.0,
                label=f"{label}: lower bound")

    # x spans the full width (no left/right gap); y reaches at least 60% (the
    # paper's axis) with 0% floating just off the bottom axis.
    ax.margins(x=0)
    ax.set_ylim(-0.012, max(0.62, ymax * 1.05))
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1.0))
    # Biennial year ticks (1998, 2000, ..., 2022), matching the paper.
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    # Faint ggplot-style grid: light-grey major lines, fainter minor between.
    ax.xaxis.set_minor_locator(mdates.YearLocator(1))
    ax.yaxis.set_minor_locator(MultipleLocator(0.05))
    ax.grid(True, which="major", color="#d0d0d0", linewidth=0.6)
    ax.grid(True, which="minor", color="#ececec", linewidth=0.4)
    ax.set_axisbelow(True)  # grid behind the data
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xlabel("Date")
    ax.set_ylabel("Probability of a 20% Crash")
    ax.legend(title="Probability:", frameon=False, loc="upper right")
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    results = pd.read_parquet(OUTPUT_DIR / "results.parquet")
    fig = build_figure1(results)
    fig.savefig(OUTPUT_DIR / "fig1_single_name_bounds.png", dpi=150, bbox_inches="tight")
    print(f"wrote {OUTPUT_DIR / 'fig1_single_name_bounds.png'}")
