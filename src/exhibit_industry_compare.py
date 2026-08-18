"""X: Industry proxy vs. direct sector-ETF bounds -- the gap our extension fills (#34).

The paper measures an industry's crash risk as the equal-weighted average of the
single-stock lower bounds of its constituents (their Figure 10). But an average of
individual crash probabilities is not the probability the *sector* crashes: a
diversified sector can be calm while its members are each risky. Our sector-ETF
surfaces (exhibit_etf_bounds, #34) give the sector's crash probability directly.

This exhibit puts the two on the same axes. For each Fama-French industry with a
clean Select Sector SPDR counterpart (ff_industry.FF12_TO_ETF), it plots:
  * the *proxy* -- the equal-weighted mean constituent lower bound (Figure 10), and
  * the *direct* measure -- the sector ETF's own lower bound,
with the S&P 500 index bound as a common reference. The companion table quantifies
the "tightness" gap: the proxy sits well above the direct measure, which in turn
hugs the sector's realized crash frequency.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: save files, never open a window
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402
import pandas as pd  # noqa: E402

import schema  # noqa: E402
from ff_industry import FF12_LABELS, FF12_SHORT, FF12_TO_ETF  # noqa: E402
from settings import config  # noqa: E402

OUTPUT_DIR = Path(config("OUTPUT_DIR"))
DATA_DIR = Path(config("DATA_DIR"))

THRESHOLD_Q = 0.80
FIG_HORIZON = 1       # one-month crash probability for the time series
TABLE_HORIZON = 12    # 12-month horizon for the realized-frequency comparison
REPL_START = pd.Timestamp("1996-01-01")
REPL_END = pd.Timestamp("2022-12-31")
EXT_END = pd.Timestamp("2025-12-31")
FIG_TITLE = "Industry Proxy (avg. of constituents) vs. Direct Sector-ETF Bound"

C_PROXY = "#e0873a"   # orange -- the paper's average-of-constituents proxy
C_DIRECT = "#2c6fbb"  # blue   -- our direct sector-ETF bound
C_MARKET = "#9a9a9a"  # grey   -- the S&P 500 reference


def industry_proxy_series(results, member_panel, secid_industry,
                          threshold_q=THRESHOLD_Q, horizon=FIG_HORIZON,
                          start=REPL_START, end=REPL_END):
    """Figure-10 proxy: equal-weighted mean constituent lower bound per (industry,
    date). Restricts results to constituent member-months, tags each by FF industry.

    Returns long [ff_industry, date, proxy_lower]."""
    members = member_panel[["date", "secid"]].dropna(subset=["secid"]).copy()
    members["secid"] = members["secid"].astype("int64")
    df = results.merge(members.drop_duplicates(), on=["date", "secid"], how="inner")
    df = df[(df["threshold_q"] == threshold_q) & (df["horizon_months"] == horizon)
            & (df["date"] >= start) & (df["date"] <= end)]
    df = df.merge(secid_industry, on="secid", how="inner")
    prox = (df.groupby(["ff_industry", "date"])["bound_lower"].mean()
            .reset_index().rename(columns={"bound_lower": "proxy_lower"}))
    return prox.sort_values(["ff_industry", "date"])


def _etf_series(results, etf_secid_map, ticker, threshold_q, horizon, start, end):
    """Lower-bound series for one ETF ticker (or SPX if ticker is None)."""
    secid = (schema.SPX_SECID if ticker is None
             else int(etf_secid_map.loc[etf_secid_map["ticker"] == ticker, "secid"].iloc[0]))
    d = results[(results["secid"] == secid) & (results["threshold_q"] == threshold_q)
                & (results["horizon_months"] == horizon)
                & (results["date"] >= start) & (results["date"] <= end)]
    return d.sort_values("date")[["date", "bound_lower"]]


def tightness_table(results, member_panel, secid_industry, etf_secid_map,
                    threshold_q=THRESHOLD_Q, horizon=TABLE_HORIZON,
                    start=REPL_START, end=REPL_END):
    """Per matched sector: mean proxy bound, mean direct ETF bound, and the ETF's
    realized crash frequency -- the "tightness" comparison.

    Columns [ff_industry, sector, ticker, proxy_lower, direct_lower, realized_freq,
    proxy_gap, direct_gap], where the gaps are each measure's distance from the
    realized frequency (its "tightness"). The proxy overstates the sector's realized
    crash frequency in every sector; the direct measure is closer for the broad,
    diversified sectors."""
    proxy = industry_proxy_series(results, member_panel, secid_industry,
                                  threshold_q, horizon, start, end)
    proxy_mean = proxy.groupby("ff_industry")["proxy_lower"].mean()
    rows = []
    for ff, ticker in FF12_TO_ETF.items():
        if ticker not in set(etf_secid_map["ticker"]):
            continue
        secid = int(etf_secid_map.loc[etf_secid_map["ticker"] == ticker, "secid"].iloc[0])
        d = results[(results["secid"] == secid) & (results["threshold_q"] == threshold_q)
                    & (results["horizon_months"] == horizon)
                    & (results["date"] >= start) & (results["date"] <= end)]
        realized = d["realized_flag"].dropna()
        pl = float(proxy_mean.get(ff, float("nan")))
        dl = float(d["bound_lower"].mean())
        rf = float(realized.astype(float).mean()) if len(realized) else float("nan")
        rows.append(dict(
            ff_industry=ff, sector=FF12_SHORT[ff], ticker=ticker,
            proxy_lower=pl, direct_lower=dl, realized_freq=rf,
            proxy_gap=pl - rf, direct_gap=dl - rf,
        ))
    return pd.DataFrame(rows)


def to_latex(table, threshold_q=THRESHOLD_Q, horizon=TABLE_HORIZON):
    """Render the tightness table as a LaTeX tabular."""
    drop = int(round((1 - threshold_q) * 100))
    lines = [
        r"\begin{tabular}{llrrrrr}",
        r"\toprule",
        r"Sector (FF) & ETF & Proxy $\overline{P^L}$ & Direct $\overline{P^L}$ "
        rf"& Realized & Proxy$-$Real. & Direct$-$Real. \\",
        rf" & & (avg. of names) & (ETF) & ({horizon}-mo. {drop}\%) & & \\",
        r"\midrule",
    ]
    for _, r in table.iterrows():
        realized = "" if pd.isna(r["realized_freq"]) else f"{r['realized_freq']:.3f}"
        lines.append(
            rf"{r['sector']} & {r['ticker']} & {r['proxy_lower']:.3f} "
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


def build_figure_compare(results, member_panel, secid_industry, etf_secid_map,
                         threshold_q=THRESHOLD_Q, horizon=FIG_HORIZON,
                         start=REPL_START, end=REPL_END, title=FIG_TITLE):
    """Small-multiple figure: proxy vs direct ETF bound + SPX, per matched sector."""
    proxy = industry_proxy_series(results, member_panel, secid_industry,
                                  threshold_q, horizon, start, end)
    matched = [(ff, t) for ff, t in FF12_TO_ETF.items()
               if t in set(etf_secid_map["ticker"])]

    n = len(matched)
    ncol = 3
    nrow = (n + ncol - 1) // ncol
    fig, axes = plt.subplots(nrow, ncol, figsize=(14, 3.2 * nrow),
                             sharex=True, squeeze=False)
    fig.subplots_adjust(left=0.06, right=0.99, top=0.90, bottom=0.09,
                        hspace=0.30, wspace=0.16)
    for ax, (ff, ticker) in zip([a for row in axes for a in row], matched):
        p = proxy[proxy["ff_industry"] == ff]
        d = _etf_series(results, etf_secid_map, ticker, threshold_q, horizon, start, end)
        ax.plot(p["date"], p["proxy_lower"], color=C_PROXY, lw=1.2,
                label="Proxy (avg. of names)")
        ax.plot(d["date"], d["bound_lower"], color=C_DIRECT, lw=1.2, label="Direct (ETF)")
        ax.set_xlim(start, end)
        ax.set_ylim(bottom=0)
        ax.set_title(f"{FF12_SHORT[ff]} — {ticker}", fontsize=9.5, pad=4)
        _style(ax)
    for ax in [a for row in axes for a in row][n:]:
        ax.set_visible(False)

    axes[0][0].legend(frameon=False, fontsize=8, loc="upper right")
    fig.suptitle(title, fontsize=13, y=0.965)
    fig.supylabel("Lower-bound probability of a 20% crash", fontsize=10, x=0.012)
    return fig


if __name__ == "__main__":
    from pull_CRSP_stock import load_CRSP_monthly_file
    from sp500_secid_universe import load_sp500_secid_universe
    from ff_industry import build_secid_sic, assign_ff12
    from exhibit_etf_bounds import etf_secid_map

    results = pd.read_parquet(OUTPUT_DIR / "results.parquet")
    universe = load_sp500_secid_universe()
    secid_industry = assign_ff12(build_secid_sic(universe, load_CRSP_monthly_file()))
    emap = etf_secid_map()

    # Replication window (1996-2022).
    tbl = tightness_table(results, universe, secid_industry, emap)
    tbl.to_csv(OUTPUT_DIR / "industry_tightness.csv", index=False)
    (OUTPUT_DIR / "industry_tightness.tex").write_text(to_latex(tbl))
    build_figure_compare(results, universe, secid_industry, emap).savefig(
        OUTPUT_DIR / "fig_industry_compare.png", dpi=150, bbox_inches="tight")

    # Extension through the most recent data.
    tbl_ext = tightness_table(results, universe, secid_industry, emap, end=EXT_END)
    tbl_ext.to_csv(OUTPUT_DIR / "industry_tightness_ext.csv", index=False)
    (OUTPUT_DIR / "industry_tightness_ext.tex").write_text(to_latex(tbl_ext))
    build_figure_compare(results, universe, secid_industry, emap, end=EXT_END,
                         title=FIG_TITLE + " (extended sample)").savefig(
        OUTPUT_DIR / "fig_industry_compare_ext.png", dpi=150, bbox_inches="tight")
    print("wrote industry_tightness.{tex,csv} and fig_industry_compare.png (+ _ext)")
