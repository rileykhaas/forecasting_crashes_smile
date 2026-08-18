"""E: Replicate Figure 2 -- cross-sectional median bounds + the S&P 500 index.

Plots, over time, the cross-sectional median across S&P 500 constituents of the
lower and upper option-implied bounds on the probability of a 20% crash over one
month (threshold_q = 0.80, horizon_months = 1), together with the crash
probability of the S&P 500 index itself -- the i = m lower bound (Result 3, the
market crash probability of Martin 2017). Matches Martin & Shi (2025) Figure 2.
Defaults to the paper's 1996-2022 window; pass a later ``end`` for the extension.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: save files, never open a window
import matplotlib.pyplot as plt
import pandas as pd

import schema
from plot_style import paper_style
from settings import config

OUTPUT_DIR = Path(config("OUTPUT_DIR"))

THRESHOLD_Q = 0.80  # a 20% crash
HORIZON_MONTHS = 1  # one-month horizon
REPL_START = pd.Timestamp("1996-01-01")
REPL_END = pd.Timestamp("2022-12-31")
EXT_END = pd.Timestamp("2025-12-31")  # extension: through the most recent data
TITLE = "Cross-Sectional Median Bounds and the S&P 500 Index"

C_UPPER = "#e0576f"  # red
C_LOWER = "#4f9ed6"  # blue
C_MARKET = "#9a9a9a"  # grey


def cross_sectional_medians(results, member_panel, start=REPL_START, end=REPL_END):
    """Monthly cross-sectional medians of the lower/upper bounds across S&P 500
    constituent member-months (the inner join to the universe excludes the index
    and the extension ETFs). Columns [date, bound_lower, bound_upper]."""
    members = member_panel[["date", "secid"]].dropna(subset=["secid"]).copy()
    members["secid"] = members["secid"].astype("int64")
    df = results.merge(members.drop_duplicates(), on=["date", "secid"], how="inner")
    df = df[
        (df["threshold_q"] == THRESHOLD_Q)
        & (df["horizon_months"] == HORIZON_MONTHS)
        & (df["date"] >= start)
        & (df["date"] <= end)
    ]
    med = df.groupby("date")[["bound_lower", "bound_upper"]].median().reset_index()
    return med.sort_values("date")


def market_series(results, start=REPL_START, end=REPL_END):
    """The S&P 500 index crash probability = the SPX lower bound (i = m, eq. 7).
    Columns [date, bound_lower]."""
    spx = results[
        (results["secid"] == schema.SPX_SECID)
        & (results["threshold_q"] == THRESHOLD_Q)
        & (results["horizon_months"] == HORIZON_MONTHS)
        & (results["date"] >= start)
        & (results["date"] <= end)
    ]
    return spx.sort_values("date")[["date", "bound_lower"]]


def build_figure2(results, member_panel, start=REPL_START, end=REPL_END, title=TITLE):
    """Return the Figure 2 chart (matplotlib Figure)."""
    med = cross_sectional_medians(results, member_panel, start, end)
    mkt = market_series(results, start, end)
    ymax = max(float(med["bound_upper"].max()), float(mkt["bound_lower"].max()))

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(
        med["date"],
        med["bound_upper"],
        color=C_UPPER,
        lw=1.0,
        label="CS Median: upper bound",
    )
    ax.plot(
        med["date"],
        med["bound_lower"],
        color=C_LOWER,
        lw=1.0,
        label="CS Median: lower bound",
    )
    ax.plot(mkt["date"], mkt["bound_lower"], color=C_MARKET, lw=1.0, label="Market")

    paper_style(ax, ymax, y_floor=0.27, y_minor=0.025)
    ax.set_title(title, fontsize=12, pad=10)
    ax.set_ylabel("Probability of a 20% Crash")
    ax.legend(title="Probability:", frameon=False, loc="upper right")
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    from sp500_secid_universe import load_sp500_secid_universe

    results = pd.read_parquet(OUTPUT_DIR / "results.parquet")
    universe = load_sp500_secid_universe()
    # Replication window (1996-2022).
    build_figure2(results, universe).savefig(
        OUTPUT_DIR / "fig2_median_bounds_market.png", dpi=150, bbox_inches="tight"
    )
    # Extension through the most recent data.
    build_figure2(
        results, universe, end=EXT_END, title=TITLE + " (extended sample)"
    ).savefig(
        OUTPUT_DIR / "fig2_median_bounds_market_ext.png", dpi=150, bbox_inches="tight"
    )
    print("wrote fig2_median_bounds_market.png and fig2_median_bounds_market_ext.png")
