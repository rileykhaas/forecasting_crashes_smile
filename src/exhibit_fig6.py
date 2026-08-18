"""E: Replicate Figure 6 -- out-of-sample R^2s of the lower bound vs. the
risk-neutral and adjusted risk-neutral crash forecasts (Martin & Shi 2025, eq. 10).

For 20% crashes (``threshold_q = 0.80``) at horizons tau in {1, 3, 6, 12} months,
we track, through time, the cumulative out-of-sample R^2

    R2_oos(T) = 1 - sum_{t<=T-tau} sum_i (y_{i,t} - F_{i,t})^2
                    / sum_{t<=T-tau} sum_i (y_{i,t} - p_{i,t})^2,

where y_{i,t} = I(R_{i,t->t+tau} <= 0.8) is the realized 20% crash indicator,
F_{i,t} is a forecaster, and the benchmark p_{i,t} is firm i's *historical average*
crash frequency over origins whose outcome is observable at t (origins s <= t-tau).
Everything is causal: benchmarks and regression adjustments only ever use data whose
crash outcome is already known at the forecast origin.

Three forecasters are compared (per the paper):
  * OIB-LB (alpha = 0, beta = 1): the option-implied lower bound, no free parameters.
  * RN (alpha = 0, beta = 1): the raw risk-neutral crash probability.
  * RN (alpha^, beta^): the adjusted risk-neutral forecast alpha^_t + beta^_t * P*_it,
    where (alpha^_t, beta^_t) are trailing OLS estimates of eq. (9), fit on an
    *expanding* window (Panel A) or a *3-year rolling* window (Panel B).

The figure is the paper's 2x4 small-multiple grid: Panel A (expanding) on top,
Panel B (3-year rolling) below, one column per horizon. Defaults to the paper's
1996-2022 window; pass a later ``end`` for the extension through the latest data.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: save files, never open a window
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FixedLocator, MaxNLocator

from settings import config

OUTPUT_DIR = Path(config("OUTPUT_DIR"))

THRESHOLD_Q = 0.80  # a 20% crash
HORIZONS = [1, 3, 6, 12]
SAMPLE_START = pd.Timestamp("1996-01-01")  # "period 1" for the expanding benchmark
BURN_IN_YEARS = 5  # initial training period before out-of-sample scoring begins
ROLLING_YEARS = 3  # Panel B rolling-regression window
REPL_START = pd.Timestamp("1996-01-01")
REPL_END = pd.Timestamp("2022-12-31")
EXT_END = pd.Timestamp("2025-12-31")  # extension: through the most recent data
TITLE = "Out-of-Sample $R^2$: the Lower Bound vs. the Risk-Neutral Forecasts"

C_LB = "#e46fb0"  # pink  -- OIB-LB
C_RN = "#4f9ed6"  # light blue -- raw risk-neutral
C_ADJ = "#12276e"  # dark navy  -- adjusted risk-neutral


def _month_index(dates):
    """Integer month index (year*12 + month) so month-end dates and calendar gaps
    compare cleanly: an origin s is observable at t iff its index is <= t's - tau."""
    d = pd.DatetimeIndex(dates)
    return (d.year * 12 + d.month).to_numpy()


def _firm_benchmark(df, tau):
    """Firm-specific historical-average crash forecast p_{i,t}.

    For firm i at origin t, the mean of its realized crash flags over origins s
    whose outcome is observable at t -- i.e. s <= t - tau months (the crash over
    s->s+tau is only realized at s+tau). Returns ``df`` with a ``bench`` column;
    the first origins of each firm (no observable history yet) get NaN.
    """
    df = df.sort_values(["secid", "date"]).copy()
    out = np.full(len(df), np.nan)
    pos = 0
    for _, g in df.groupby("secid", sort=False):
        idx = _month_index(g["date"])  # integer month index, robust to month-end/gaps
        csum = np.concatenate([[0.0], np.cumsum(g["y"].to_numpy(float))])
        k = np.searchsorted(idx, idx - tau, side="right")  # # observable prior origins
        out[pos : pos + len(g)] = np.where(k > 0, csum[k] / np.maximum(k, 1), np.nan)
        pos += len(g)
    df["bench"] = out
    return df


def _monthly_suff_stats(df):
    """Per origin-month pooled sufficient statistics for OLS of y on the
    risk-neutral probability (n, sum x, sum y, sum x^2, sum xy), sorted by date."""
    d = df.assign(_xx=df["RN"] ** 2, _xy=df["RN"] * df["y"])
    return (
        d.groupby("date")
        .agg(
            n=("y", "size"),
            Sx=("RN", "sum"),
            Sy=("y", "sum"),
            Sxx=("_xx", "sum"),
            Sxy=("_xy", "sum"),
        )
        .sort_index()
    )


def _ols_from_suff(n, Sx, Sy, Sxx, Sxy):
    """(alpha, beta) of y = alpha + beta x from pooled sufficient statistics."""
    denom = n * Sxx - Sx * Sx
    if n < 2 or denom <= 0:
        return np.nan, np.nan
    beta = (n * Sxy - Sx * Sy) / denom
    return (Sy - beta * Sx) / n, beta


def _trailing_coeffs(stats, tau, rolling_years=None):
    """Trailing OLS estimates (alpha^_t, beta^_t) of eq. (9) for each origin month.

    At origin t the regression uses only pooled firm-months whose crash outcome is
    observable at t (origins s <= t - tau months): all of them (``rolling_years is
    None``, expanding) or those within the trailing ``rolling_years`` (rolling).
    """
    sm = stats.index.to_numpy()  # sorted origin-month dates (datetime64)
    sidx = _month_index(stats.index)  # matching integer month indices
    ccum = np.vstack(
        [
            np.zeros(5),
            np.cumsum(stats[["n", "Sx", "Sy", "Sxx", "Sxy"]].to_numpy(), axis=0),
        ]
    )
    a_out, b_out = [], []
    for ti in sidx:
        hi = np.searchsorted(sidx, ti - tau, side="right")
        lo = (
            0
            if rolling_years is None
            else np.searchsorted(sidx, ti - tau - 12 * rolling_years, side="right")
        )
        a, b = _ols_from_suff(*(ccum[hi] - ccum[lo]))
        a_out.append(a)
        b_out.append(b)
    return pd.DataFrame({"date": sm, "alpha": a_out, "beta": b_out})


def compute_oos_r2(
    results,
    member_panel,
    tau,
    threshold_q=THRESHOLD_Q,
    start=REPL_START,
    end=REPL_END,
    burn_in_years=BURN_IN_YEARS,
    rolling_years=ROLLING_YEARS,
):
    """Cumulative out-of-sample R^2 time series for horizon ``tau``.

    Returns a DataFrame indexed by *evaluation date* T = origin + tau months, with
    columns ``OIB_LB``, ``RN_raw``, ``RN_adj_exp``, ``RN_adj_roll`` (fractions).
    The three forecasters share the same firm-historical-average denominator, so the
    lower-bound and raw risk-neutral series are identical across Panels A and B.
    """
    members = member_panel[["date", "secid"]].dropna(subset=["secid"]).copy()
    members["secid"] = members["secid"].astype("int64")
    df = results.merge(members.drop_duplicates(), on=["date", "secid"], how="inner")
    df = df[
        (df["threshold_q"] == threshold_q)
        & (df["horizon_months"] == tau)
        & df["realized_flag"].notna()
        & df["date"].le(end)
    ].copy()
    df["y"] = df["realized_flag"].astype(float)
    df["RN"] = df["prob_riskneutral"].astype(float)
    df["LB"] = df["bound_lower"].astype(float)
    df = df.dropna(subset=["RN", "LB"])

    df = _firm_benchmark(df, tau)
    stats = _monthly_suff_stats(df)
    exp = _trailing_coeffs(stats, tau, rolling_years=None).rename(
        columns={"alpha": "a_exp", "beta": "b_exp"}
    )
    roll = _trailing_coeffs(stats, tau, rolling_years=rolling_years).rename(
        columns={"alpha": "a_roll", "beta": "b_roll"}
    )
    df = df.merge(exp, on="date", how="left").merge(roll, on="date", how="left")
    df["F_adj_exp"] = df["a_exp"] + df["b_exp"] * df["RN"]
    df["F_adj_roll"] = df["a_roll"] + df["b_roll"] * df["RN"]

    oos_start = SAMPLE_START + pd.DateOffset(years=burn_in_years)
    scored = df[
        df["date"].ge(oos_start)
        & df["bench"].notna()
        & df["F_adj_exp"].notna()
        & df["F_adj_roll"].notna()
    ].copy()

    se = pd.DataFrame({"date": scored["date"]})
    se["bench"] = (scored["y"] - scored["bench"]) ** 2
    se["OIB_LB"] = (scored["y"] - scored["LB"]) ** 2
    se["RN_raw"] = (scored["y"] - scored["RN"]) ** 2
    se["RN_adj_exp"] = (scored["y"] - scored["F_adj_exp"]) ** 2
    se["RN_adj_roll"] = (scored["y"] - scored["F_adj_roll"]) ** 2
    cum = se.groupby("date").sum().sort_index().cumsum()

    r2 = pd.DataFrame(index=cum.index)
    for col in ["OIB_LB", "RN_raw", "RN_adj_exp", "RN_adj_roll"]:
        r2[col] = 1.0 - cum[col] / cum["bench"]
    r2.index = r2.index + pd.DateOffset(months=tau)  # index by evaluation date T
    return r2[r2.index >= start]


def _style_panel(ax, ylo, yhi, xstart, xend):
    """Apply the paper's small-multiple axis look (grid, spines, biennial-ish ticks)."""
    ax.axhline(
        0.0, color="#9a9a9a", lw=0.8, ls=(0, (4, 3)), zorder=1
    )  # dashed zero line
    ax.margins(x=0)
    ax.set_xlim(xstart, xend)
    ax.set_ylim(ylo, yhi)
    years = [y for y in range(2002, xend.year + 1, 8)]
    ax.xaxis.set_major_locator(
        FixedLocator(mdates.date2num([pd.Timestamp(f"{y}-01-01") for y in years]))
    )
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_minor_locator(mdates.YearLocator(2))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6, steps=[1, 2, 5, 10]))
    ax.grid(True, which="major", color="#d7d7d7", linewidth=0.6)
    ax.grid(True, which="minor", color="#eeeeee", linewidth=0.4)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_edgecolor("#333333")
        spine.set_linewidth(0.8)


def build_figure6(
    results,
    member_panel,
    start=REPL_START,
    end=REPL_END,
    title=TITLE,
    threshold_q=THRESHOLD_Q,
):
    """Return the Figure 6 chart: a 2 (panel) x 4 (horizon) grid of R^2_oos series."""
    series = {
        tau: compute_oos_r2(results, member_panel, tau, threshold_q, start, end)
        for tau in HORIZONS
    }
    xstart, xend = start, end

    # Shared y-top per column (both panels); per-subplot floor (0 unless it dips below).
    def pct(s):
        return 100.0 * s

    col_top = {}
    for tau in HORIZONS:
        r2 = series[tau]
        col_top[tau] = max(
            pct(r2[c]).max() for c in ["OIB_LB", "RN_raw", "RN_adj_exp", "RN_adj_roll"]
        )

    fig, axes = plt.subplots(2, 4, figsize=(15, 8), sharex="col")
    fig.subplots_adjust(
        left=0.05, right=0.99, top=0.87, bottom=0.07, hspace=0.45, wspace=0.30
    )
    panels = [
        (
            "A",
            "RN_adj_exp",
            "Expanding-window adjustments for the risk-neutral probabilities",
        ),
        (
            "B",
            "RN_adj_roll",
            "3-year rolling-window adjustments for the risk-neutral probabilities",
        ),
    ]

    for row, (letter, adj_col, subtitle) in enumerate(panels):
        for col, tau in enumerate(HORIZONS):
            ax = axes[row, col]
            r2 = series[tau]
            lb, rn, adj = pct(r2["OIB_LB"]), pct(r2["RN_raw"]), pct(r2[adj_col])
            ax.plot(
                r2.index,
                rn,
                color=C_RN,
                lw=1.1,
                ls=(0, (6, 1, 1, 1)),
                label=r"RN ($\alpha=0,\beta=1$)",
            )
            ax.plot(
                r2.index,
                adj,
                color=C_ADJ,
                lw=1.1,
                ls=(0, (6, 1, 1, 1)),
                label=r"RN ($\hat\alpha,\hat\beta$)",
            )
            ax.plot(
                r2.index, lb, color=C_LB, lw=1.4, label=r"OIB-LB ($\alpha=0,\beta=1$)"
            )
            top = col_top[tau] * 1.06
            floor = min(adj.min(), 0.0)
            ylo = floor * 1.12 if floor < 0 else -0.02 * top
            _style_panel(ax, ylo, top, xstart, xend)
            if row == 0:
                ax.set_title(f"20% crash in {tau} months", fontsize=10, pad=6)
            if row == 1:
                ax.set_xlabel("Date")
            if col == 0:
                ax.set_ylabel(r"$R^2_{\mathrm{oos}}$ (%)")
            if row == 0 and col == 0:
                ax.legend(
                    frameon=False,
                    fontsize=7.5,
                    loc="lower right",
                    handlelength=2.4,
                    borderpad=0.2,
                )
        # Panel subtitle spanning the row (in the whitespace just above it).
        y = 0.925 if row == 0 else 0.455
        fig.text(
            0.5,
            y,
            f"Panel {letter}: {subtitle}",
            ha="center",
            fontsize=11,
            style="italic",
        )

    fig.suptitle(title, fontsize=13, y=0.985)
    return fig


if __name__ == "__main__":
    from sp500_secid_universe import load_sp500_secid_universe

    results = pd.read_parquet(OUTPUT_DIR / "results.parquet")
    universe = load_sp500_secid_universe()
    # Replication window (1996-2022).
    build_figure6(results, universe).savefig(
        OUTPUT_DIR / "fig6_oos_r2.png", dpi=150, bbox_inches="tight"
    )
    # Extension through the most recent data.
    build_figure6(
        results, universe, end=EXT_END, title=TITLE + " (extended sample)"
    ).savefig(OUTPUT_DIR / "fig6_oos_r2_ext.png", dpi=150, bbox_inches="tight")
    print("wrote fig6_oos_r2.png and fig6_oos_r2_ext.png")
