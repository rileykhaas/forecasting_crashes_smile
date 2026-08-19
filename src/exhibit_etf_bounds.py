"""X: Sector-ETF crash-probability bounds -- an original extension (issue #34).

Applies the paper's single-name crash-probability machinery to the eleven Select
Sector SPDR ETFs plus KRE (regional banks). The ETFs are priced by the same engine
as the stocks (rnd -> fear correction -> Frechet-Hoeffding bounds) once their
surfaces are spot-matched (clean_surface, #34) and routed through run_pipeline, so
their lower bound P^L, risk-neutral P*, and upper bound P^U land in results.parquet
like any other secid.

Why this is a clean test of the theory, not a weakening of it: comonotonicity with
the market -- the assumption that makes the lower bound tight -- is far more
plausible for a diversified sector ETF than for a single name, so the lower bound
should bind *more* tightly here. And an average of individual crash probabilities is
not the probability the sector crashes; the ETF surface gives the direct measure.

Two exhibits, each with a ``_ext`` variant through the latest data:
  * a 3x4 small-multiple figure (``fig_etf_sector_bounds.png``): each sector ETF's
    lower-bound 20% one-month crash probability over time, with the S&P 500 index's
    own crash probability (SPX_SECID, the i=m bound) overlaid as the benchmark.
  * a calibration table (``etf_bounds.tex``/``.csv``): per ETF (and the SPX row),
    the mean lower bound / risk-neutral / upper bound against the realized crash
    frequency, at the 12-month horizon where sector crashes are observable.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: save files, never open a window
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import MaxNLocator

import schema
from settings import config

OUTPUT_DIR = Path(config("OUTPUT_DIR"))
DATA_DIR = Path(config("DATA_DIR"))

THRESHOLD_Q = 0.80  # a 20% crash
FIG_HORIZON = 1  # one-month crash probability for the time-series figure
TABLE_HORIZON = 12  # 12-month horizon for the calibration table (more events)
REPL_START = pd.Timestamp("1996-01-01")
REPL_END = pd.Timestamp("2022-12-31")
EXT_END = pd.Timestamp("2025-12-31")
FIG_TITLE = "Direct Sector-ETF Crash Probabilities vs. the S&P 500"

# Full sector names for panel titles; grid order is alphabetical by ticker with the
# regional-bank ETF (KRE, the SVB layer) placed last.
SECTOR_LABELS = {
    "XLB": "Materials",
    "XLC": "Comm. Services",
    "XLE": "Energy",
    "XLF": "Financials",
    "XLI": "Industrials",
    "XLK": "Technology",
    "XLP": "Cons. Staples",
    "XLRE": "Real Estate",
    "XLU": "Utilities",
    "XLV": "Health Care",
    "XLY": "Cons. Disc.",
    "KRE": "Regional Banks",
}
GRID_ORDER = [
    "XLB",
    "XLC",
    "XLE",
    "XLF",
    "XLI",
    "XLK",
    "XLP",
    "XLRE",
    "XLU",
    "XLV",
    "XLY",
    "KRE",
]

C_ETF = "#2c6fbb"  # blue -- the sector ETF's own lower bound
C_MARKET = "#9a9a9a"  # grey -- the SPX benchmark


def etf_secid_map(data_dir=DATA_DIR):
    """[ticker, secid] for the sector ETFs, from the pull manifest (source=='sector_etf')."""
    manifest = pd.read_parquet(Path(data_dir) / "optionm_pull_secids.parquet")
    m = manifest.loc[manifest["source"] == "sector_etf", ["ticker", "secid"]].copy()
    m["secid"] = m["secid"].astype("int64")
    return m


def _series(results, secid, threshold_q, horizon, start, end):
    """Lower-bound time series for one secid at (threshold_q, horizon), sorted by date."""
    d = results[
        (results["secid"] == secid)
        & (results["threshold_q"] == threshold_q)
        & (results["horizon_months"] == horizon)
        & (results["date"] >= start)
        & (results["date"] <= end)
    ]
    return d.sort_values("date")[["date", "bound_lower"]]


def etf_summary_table(
    results,
    secid_map,
    threshold_q=THRESHOLD_Q,
    horizon=TABLE_HORIZON,
    start=REPL_START,
    end=REPL_END,
):
    """Per-ETF (and SPX) mean bounds vs realized crash frequency at one (q, horizon).

    Columns [ticker, secid, mean_lower, mean_rn, mean_upper, realized_freq, n_obs].
    ``realized_freq`` is the mean of ``realized_flag`` over months with an observed
    outcome; ``n_obs`` is how many such months (short-history ETFs have fewer)."""
    rows = []
    ordered = [
        (t, int(secid_map.loc[secid_map["ticker"] == t, "secid"].iloc[0]))
        for t in GRID_ORDER
        if t in set(secid_map["ticker"])
    ]
    ordered.append(("SPX", schema.SPX_SECID))
    for ticker, secid in ordered:
        d = results[
            (results["secid"] == secid)
            & (results["threshold_q"] == threshold_q)
            & (results["horizon_months"] == horizon)
            & (results["date"] >= start)
            & (results["date"] <= end)
        ]
        realized = d["realized_flag"].dropna()
        rows.append(
            {
                "ticker": ticker,
                "secid": secid,
                "mean_lower": d["bound_lower"].mean(),
                "mean_rn": d["prob_riskneutral"].mean(),
                "mean_upper": d["bound_upper"].mean(),
                "realized_freq": (
                    float(realized.astype(float).mean())
                    if len(realized)
                    else float("nan")
                ),
                "n_obs": len(realized),
            }
        )
    return pd.DataFrame(rows)


def to_latex(table, threshold_q=THRESHOLD_Q, horizon=TABLE_HORIZON):
    """Render the ETF calibration table as a LaTeX tabular."""
    drop = round((1 - threshold_q) * 100)
    lines = [
        r"\begin{tabular}{llrrrrr}",
        r"\toprule",
        (
            r"Sector & Ticker & $\overline{P^L}$ & $\overline{P^*}$ & $\overline{P^U}$ "
            r"& Realized & $N$ \\"
        ),
        rf" & & & & & ({horizon}-mo. {drop}\%) & \\",
        r"\midrule",
    ]
    for _, r in table.iterrows():
        name = (
            "S\\&P 500 index"
            if r["ticker"] == "SPX"
            else SECTOR_LABELS.get(r["ticker"], r["ticker"]).replace("&", r"\&")
        )
        realized = "" if pd.isna(r["realized_freq"]) else f"{r['realized_freq']:.3f}"
        if r["ticker"] == "SPX":
            lines.append(r"\midrule")
        lines.append(
            rf"{name} & {r['ticker']} & {r['mean_lower']:.3f} & {r['mean_rn']:.3f} "
            rf"& {r['mean_upper']:.3f} & {realized} & {int(r['n_obs'])} \\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines)


def _style(ax):
    ax.grid(True, color="#e2e2e2", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v * 100:.0f}%")
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5, steps=[1, 2, 5, 10]))
    ax.xaxis.set_major_locator(mdates.YearLocator(6))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    for spine in ax.spines.values():
        spine.set_edgecolor("#333333")
        spine.set_linewidth(0.8)


def build_figure_etf(
    results,
    secid_map,
    threshold_q=THRESHOLD_Q,
    horizon=FIG_HORIZON,
    start=REPL_START,
    end=REPL_END,
    title=FIG_TITLE,
):
    """2-wide x 6-tall small-multiple figure: each sector ETF's lower bound + the SPX
    benchmark. The portrait 6x2 layout gives each panel roughly twice the width of a
    4-across grid, so the time series is legible."""
    spx = _series(results, schema.SPX_SECID, threshold_q, horizon, start, end)
    tickers = [t for t in GRID_ORDER if t in set(secid_map["ticker"])]

    # Shared y-top for comparability across sectors (include the SPX line).
    ymax = float(spx["bound_lower"].max()) if len(spx) else 0.0
    per = {}
    for t in tickers:
        sid = int(secid_map.loc[secid_map["ticker"] == t, "secid"].iloc[0])
        s = _series(results, sid, threshold_q, horizon, start, end)
        per[t] = s
        if len(s):
            ymax = max(ymax, float(s["bound_lower"].max()))
    ytop = ymax * 1.08

    fig, axes = plt.subplots(6, 2, figsize=(11, 10.2), sharex=True, sharey=True)
    fig.subplots_adjust(
        left=0.08, right=0.985, top=0.955, bottom=0.05, hspace=0.34, wspace=0.11
    )
    for ax, t in zip(axes.flat, tickers):
        s = per[t]
        if len(spx):
            ax.plot(
                spx["date"], spx["bound_lower"], color=C_MARKET, lw=1.0, label="S&P 500"
            )
        ax.plot(s["date"], s["bound_lower"], color=C_ETF, lw=1.1, label="Sector ETF")
        ax.set_ylim(-0.01 * ytop, ytop)
        ax.set_xlim(start, end)
        ax.set_title(f"{t} — {SECTOR_LABELS.get(t, t)}", fontsize=9.5, pad=4)
        _style(ax)
    # If fewer than 12 tickers, hide any leftover axes.
    for ax in list(axes.flat)[len(tickers) :]:
        ax.set_visible(False)

    axes.flat[0].legend(frameon=False, fontsize=8, loc="upper right")
    fig.suptitle(title, fontsize=13, y=0.978)
    fig.supylabel("Lower-bound probability of a 20% crash", fontsize=10, x=0.02)
    return fig


if __name__ == "__main__":
    results = pd.read_parquet(OUTPUT_DIR / "results.parquet")
    secid_map = etf_secid_map()

    # Replication window (1996-2022).
    tbl = etf_summary_table(results, secid_map)
    tbl.to_csv(OUTPUT_DIR / "etf_bounds.csv", index=False)
    (OUTPUT_DIR / "etf_bounds.tex").write_text(to_latex(tbl))
    build_figure_etf(results, secid_map).savefig(
        OUTPUT_DIR / "fig_etf_sector_bounds.png", dpi=150, bbox_inches="tight"
    )

    # Extension through the most recent data.
    tbl_ext = etf_summary_table(results, secid_map, end=EXT_END)
    tbl_ext.to_csv(OUTPUT_DIR / "etf_bounds_ext.csv", index=False)
    (OUTPUT_DIR / "etf_bounds_ext.tex").write_text(to_latex(tbl_ext))
    build_figure_etf(
        results, secid_map, end=EXT_END, title=FIG_TITLE + " (extended sample)"
    ).savefig(
        OUTPUT_DIR / "fig_etf_sector_bounds_ext.png", dpi=150, bbox_inches="tight"
    )
    print("wrote etf_bounds.{tex,csv} and fig_etf_sector_bounds.png (+ _ext)")
