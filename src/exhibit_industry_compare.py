"""X: Industry proxy vs. direct sector-ETF bounds -- the gap our extension fills (#34).

The paper measures an industry's crash risk as the equal-weighted average of the
single-stock lower bounds of its constituents (their Figure 10, defined on the
**Fama-French 49 industry classification**). But an average of individual crash
probabilities is not the probability the *sector* crashes: a diversified sector can be
calm while its members are each risky. Our sector-ETF surfaces (exhibit_etf_bounds,
#34) give the sector's crash probability directly.

This exhibit puts the two on the same axes for all eleven Select Sector SPDR sectors.
We reproduce the paper's FF49 industry assignment (ff_industry.assign_sector) and roll
the FF49 industries up to the SPDR sector they compose. Five sectors map cleanly
(Financials, Technology, Health Care, Energy, Utilities); the other six are best-fit
approximations (flagged with an asterisk) because FF49's manufacturing/consumer
industries straddle GICS lines. For each sector it plots:
  * the *proxy* -- the equal-weighted mean constituent lower bound (Figure 10), and
  * the *direct* measure -- the sector ETF's own lower bound.
Both use the paper's Figure-10 horizon: the one-year (12-month) probability of a 20%
crash. The companion table quantifies the "tightness" gap: the proxy sits well above
the direct measure, which in turn hugs the sector's realized crash frequency.
(KRE, the regional-bank ETF, is not a GICS sector and is left to the SVB case study.)
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: save files, never open a window
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import MaxNLocator

import schema
from ff_industry import CLEAN_SECTORS, FF49_TO_ETF
from settings import config

OUTPUT_DIR = Path(config("OUTPUT_DIR"))
DATA_DIR = Path(config("DATA_DIR"))

THRESHOLD_Q = 0.80  # 20% crash, matching the paper's Figure 10
HORIZON = 12  # one-year horizon, matching the paper's Figure 10
REPL_START = pd.Timestamp("1996-01-01")
REPL_END = pd.Timestamp("2022-12-31")
EXT_END = pd.Timestamp("2025-12-31")
FIG_TITLE = "Industry Proxy (avg. of constituents) vs. Direct Sector-ETF Bound"

# Stable display order for the eleven Select Sector SPDR sectors: the five cleanly
# mapped sectors first, then the six best-fit ones.
SECTOR_ORDER = [
    "Financials",
    "Technology",
    "Health Care",
    "Energy",
    "Utilities",
    "Consumer Discretionary",
    "Consumer Staples",
    "Industrials",
    "Materials",
    "Communication Services",
    "Real Estate",
]

C_PROXY = "#e0873a"  # orange -- the paper's average-of-constituents proxy
C_DIRECT = "#2c6fbb"  # blue   -- our direct sector-ETF bound


def industry_proxy_series(
    results,
    member_panel,
    secid_sector,
    threshold_q=THRESHOLD_Q,
    horizon=HORIZON,
    start=REPL_START,
    end=REPL_END,
):
    """Figure-10 proxy rolled up to the sector: equal-weighted mean constituent lower
    bound per (sector, date). Restricts results to constituent member-months and tags
    each by its Select Sector SPDR (from ff_industry.assign_sector).

    ``secid_sector`` is [secid, sector, ticker]; names with no sector are dropped.
    Returns long [sector, ticker, date, proxy_lower]."""
    members = member_panel[["date", "secid"]].dropna(subset=["secid"]).copy()
    members["secid"] = members["secid"].astype("int64")
    df = results.merge(members.drop_duplicates(), on=["date", "secid"], how="inner")
    df = df[
        (df["threshold_q"] == threshold_q)
        & (df["horizon_months"] == horizon)
        & (df["date"] >= start)
        & (df["date"] <= end)
    ]
    sect = secid_sector.dropna(subset=["sector"])[["secid", "sector", "ticker"]]
    df = df.merge(sect, on="secid", how="inner")
    prox = (
        df.groupby(["sector", "ticker", "date"])["bound_lower"]
        .mean()
        .reset_index()
        .rename(columns={"bound_lower": "proxy_lower"})
    )
    return prox.sort_values(["sector", "date"])


def _etf_series(results, etf_secid_map, ticker, threshold_q, horizon, start, end):
    """Lower-bound series for one ETF ticker (or SPX if ticker is None)."""
    secid = (
        schema.SPX_SECID
        if ticker is None
        else int(etf_secid_map.loc[etf_secid_map["ticker"] == ticker, "secid"].iloc[0])
    )
    d = results[
        (results["secid"] == secid)
        & (results["threshold_q"] == threshold_q)
        & (results["horizon_months"] == horizon)
        & (results["date"] >= start)
        & (results["date"] <= end)
    ]
    return d.sort_values("date")[["date", "bound_lower"]]


def _matched_sectors(etf_secid_map):
    """(sector, ticker) pairs that both map cleanly to FF49 and have ETF data,
    in display order."""
    have = set(etf_secid_map["ticker"])
    ordered = [(s, FF49_TO_ETF[s][0]) for s in SECTOR_ORDER if s in FF49_TO_ETF]
    return [(s, t) for s, t in ordered if t in have]


def tightness_table(
    results,
    member_panel,
    secid_sector,
    etf_secid_map,
    threshold_q=THRESHOLD_Q,
    horizon=HORIZON,
    start=REPL_START,
    end=REPL_END,
):
    """Per sector: mean proxy bound, mean direct ETF bound, and the ETF's realized
    crash frequency -- the "tightness" comparison, for all eleven SPDR sectors.

    Columns [sector, ticker, clean, proxy_lower, direct_lower, realized_freq,
    proxy_gap, direct_gap], where the gaps are each measure's distance from the realized
    frequency (its "tightness") and ``clean`` flags the five unambiguous FF49->GICS
    sectors. The proxy overstates the sector's realized crash frequency in every sector;
    the direct measure is closer for the broad, diversified sectors."""
    proxy = industry_proxy_series(
        results, member_panel, secid_sector, threshold_q, horizon, start, end
    )
    proxy_mean = proxy.groupby("sector")["proxy_lower"].mean()
    rows = []
    for sector, ticker in _matched_sectors(etf_secid_map):
        secid = int(
            etf_secid_map.loc[etf_secid_map["ticker"] == ticker, "secid"].iloc[0]
        )
        d = results[
            (results["secid"] == secid)
            & (results["threshold_q"] == threshold_q)
            & (results["horizon_months"] == horizon)
            & (results["date"] >= start)
            & (results["date"] <= end)
        ]
        realized = d["realized_flag"].dropna()
        pl = float(proxy_mean.get(sector, float("nan")))
        dl = float(d["bound_lower"].mean())
        rf = float(realized.astype(float).mean()) if len(realized) else float("nan")
        rows.append(
            dict(
                sector=sector,
                ticker=ticker,
                clean=sector in CLEAN_SECTORS,
                proxy_lower=pl,
                direct_lower=dl,
                realized_freq=rf,
                proxy_gap=pl - rf,
                direct_gap=dl - rf,
            )
        )
    return pd.DataFrame(rows)


def to_latex(table, threshold_q=THRESHOLD_Q, horizon=HORIZON):
    """Render the tightness table as a LaTeX tabular."""
    drop = int(round((1 - threshold_q) * 100))
    lines = [
        r"\begin{tabular}{llrrrrr}",
        r"\toprule",
        r"Sector (FF49) & ETF & Proxy $\overline{P^L}$ & Direct $\overline{P^L}$ "
        r"& Realized & Proxy$-$Real. & Direct$-$Real. \\",
        rf" & & (avg. of names) & (ETF) & ({horizon}-mo. {drop}\%) & & \\",
        r"\midrule",
    ]
    for _, r in table.iterrows():
        realized = "" if pd.isna(r["realized_freq"]) else f"{r['realized_freq']:.3f}"
        # asterisk marks the six best-fit (non-clean) FF49->GICS sector mappings
        mark = "" if r.get("clean", True) else r"$^{*}$"
        lines.append(
            rf"{r['sector']}{mark} & {r['ticker']} & {r['proxy_lower']:.3f} "
            rf"& {r['direct_lower']:.3f} & {realized} & {r['proxy_gap']:+.3f} "
            rf"& {r['direct_gap']:+.3f} \\"
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


def build_figure_compare(
    results,
    member_panel,
    secid_sector,
    etf_secid_map,
    threshold_q=THRESHOLD_Q,
    horizon=HORIZON,
    start=REPL_START,
    end=REPL_END,
    title=FIG_TITLE,
):
    """Small-multiple figure: proxy vs direct ETF bound, one panel per SPDR sector.
    An asterisk marks the six best-fit (non-clean) FF49->GICS sector mappings."""
    proxy = industry_proxy_series(
        results, member_panel, secid_sector, threshold_q, horizon, start, end
    )
    matched = _matched_sectors(etf_secid_map)

    n = len(matched)
    ncol = 3
    nrow = (n + ncol - 1) // ncol
    fig, axes = plt.subplots(
        nrow, ncol, figsize=(14, 2.9 * nrow), sharex=True, squeeze=False
    )
    fig.subplots_adjust(
        left=0.06, right=0.99, top=0.93, bottom=0.05, hspace=0.34, wspace=0.16
    )
    for ax, (sector, ticker) in zip([a for row in axes for a in row], matched):
        p = proxy[proxy["sector"] == sector]
        d = _etf_series(
            results, etf_secid_map, ticker, threshold_q, horizon, start, end
        )
        ax.plot(
            p["date"],
            p["proxy_lower"],
            color=C_PROXY,
            lw=1.2,
            label="Proxy (avg. of names)",
        )
        ax.plot(
            d["date"], d["bound_lower"], color=C_DIRECT, lw=1.2, label="Direct (ETF)"
        )
        ax.set_xlim(start, end)
        ax.set_ylim(bottom=0)
        mark = "" if sector in CLEAN_SECTORS else " *"
        ax.set_title(f"{sector}{mark} — {ticker}", fontsize=9.5, pad=4)
        _style(ax)
    for ax in [a for row in axes for a in row][n:]:
        ax.set_visible(False)

    axes[0][0].legend(frameon=False, fontsize=8, loc="upper right")
    fig.suptitle(title, fontsize=13, y=0.985)
    fig.supylabel(
        "Lower-bound probability of a 20% crash (1-year)", fontsize=10, x=0.012
    )
    return fig


if __name__ == "__main__":
    from exhibit_etf_bounds import etf_secid_map
    from ff_industry import assign_sector, build_secid_sic
    from pull_CRSP_stock import load_CRSP_monthly_file
    from sp500_secid_universe import load_sp500_secid_universe

    results = pd.read_parquet(OUTPUT_DIR / "results.parquet")
    universe = load_sp500_secid_universe()
    secid_sector = assign_sector(build_secid_sic(universe, load_CRSP_monthly_file()))
    emap = etf_secid_map()

    # Replication window (1996-2022).
    tbl = tightness_table(results, universe, secid_sector, emap)
    tbl.to_csv(OUTPUT_DIR / "industry_tightness.csv", index=False)
    (OUTPUT_DIR / "industry_tightness.tex").write_text(to_latex(tbl))
    build_figure_compare(results, universe, secid_sector, emap).savefig(
        OUTPUT_DIR / "fig_industry_compare.png", dpi=150, bbox_inches="tight"
    )

    # Extension through the most recent data.
    tbl_ext = tightness_table(results, universe, secid_sector, emap, end=EXT_END)
    tbl_ext.to_csv(OUTPUT_DIR / "industry_tightness_ext.csv", index=False)
    (OUTPUT_DIR / "industry_tightness_ext.tex").write_text(to_latex(tbl_ext))
    build_figure_compare(
        results,
        universe,
        secid_sector,
        emap,
        end=EXT_END,
        title=FIG_TITLE + " (extended sample)",
    ).savefig(OUTPUT_DIR / "fig_industry_compare_ext.png", dpi=150, bbox_inches="tight")
    print("wrote industry_tightness.{tex,csv} and fig_industry_compare.png (+ _ext)")
