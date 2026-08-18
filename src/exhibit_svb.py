"""X: Silicon Valley Bank case study -- one event read at three levels (#31).

A DAILY exhibit over Feb-Mar 2023. The same engine that prices the monthly panel
(rnd -> fear correction -> Frechet-Hoeffding bounds) is run day by day on the
case-study surfaces, so each asset gets a daily lower bound P^L and risk-neutral
probability P* of a 20% crash. Three levels:

  * SIVB -- the failed bank (the crash itself),
  * KRE  -- the regional-bank ETF (the sector layer),
  * XLF  -- broad financials (the systemic layer).

How to read it (the theory's structural weak point): the lower bound is tight under
market comonotonicity but conservative for an *idiosyncratic* crash, where the
risk-neutral probability -- carrying no fear premium to remove -- is the better
estimate. SVB is exactly that scenario, with a known resolution (the bank failed, the
index did not). If the risk-neutral is elevated while the lower bound and the broad
index stay subdued, the market priced the event as *contained*; if every series rises
together, *systemic*.

Built from pull_svb_daily's three daily parquets; nothing here touches the monthly
pipeline. SIVB's surface (hence its bounds) ends on 2023-03-09, the day it collapsed.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: save files, never open a window
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import MaxNLocator

import schema
from pull_svb_daily import CASE_LABELS, KRE_SECID, SIVB_SECID, XLF_SECID
from rates import build_rates
from run_pipeline import run_pipeline
from settings import config

OUTPUT_DIR = Path(config("OUTPUT_DIR"))

THRESHOLD_Q = 0.80  # a 20% crash
HORIZON_DAYS = 30  # the 1-month surface -- most responsive to an acute crisis
COLLAPSE_DATE = pd.Timestamp("2023-03-10")  # SVB closed by regulators (options halted)
REF_DATE = pd.Timestamp("2023-03-08")  # last trading day before the collapse
LEVEL = {SIVB_SECID: "name", KRE_SECID: "sector", XLF_SECID: "systemic"}
TITLE = "SVB, One Event at Three Levels: Daily Option-Implied Crash Probabilities"

# The three display panels, top (name) to bottom (systemic).
PANELS = [
    (SIVB_SECID, "SIVB — SVB Financial (the failed name)"),
    (KRE_SECID, "KRE — Regional Banks (the sector)"),
    (XLF_SECID, "XLF — Broad Financials (the systemic layer)"),
]

C_LB = "#2c6fbb"  # blue -- the fear-corrected lower bound P^L
C_RN = "#c0392b"  # red  -- the risk-neutral probability P* ("crying wolf")


def daily_clean_surface(raw_surface, spot_daily):
    """Appendix-D cleaning at DAILY frequency: like clean_surface.clean_surface, but
    the CRSP-month-end spot join is replaced by an exact-date OptionMetrics spot join.

    ``spot_daily`` has [secid, date, spot_price]. Returns the schema.clean_surface
    columns, one row per surviving (date, secid, maturity, delta, cp_flag)."""
    df = raw_surface.copy()
    df["secid"] = df["secid"].astype("int64")
    # Criteria 2 & 3: positive strike; dispersion strictly inside (0, 0.05).
    df = df[
        (df["impl_strike"] > 0) & (df["dispersion"] > 0) & (df["dispersion"] < 0.05)
    ]
    # Criterion 1: a spot must exist -> inner join on the exact trading day.
    df = df.merge(spot_daily, on=["secid", "date"], how="inner")
    df["moneyness"] = df["impl_strike"] / df["spot_price"]
    df = df.rename(
        columns={"days": "days_to_maturity", "impl_volatility": "implied_vol"}
    )
    # Criterion 4: more than 10 distinct strikes per firm-day-maturity.
    n_strikes = df.groupby(["date", "secid", "days_to_maturity"])[
        "impl_strike"
    ].transform("nunique")
    df = df[n_strikes > 10]
    out = df[
        [
            "date",
            "secid",
            "days_to_maturity",
            "moneyness",
            "implied_vol",
            "spot_price",
            "cp_flag",
        ]
    ].copy()
    out["secid"] = out["secid"].astype("int64")
    out["days_to_maturity"] = out["days_to_maturity"].astype("int64")
    return out.sort_values(
        ["date", "secid", "days_to_maturity", "moneyness"]
    ).reset_index(drop=True)


def _empty_realized():
    """A correctly-typed empty realized-returns frame (the case study is
    forward-looking -- no realized outcome to join)."""
    return pd.DataFrame(
        {
            "date": pd.Series([], dtype="datetime64[ns]"),
            "secid": pd.Series([], dtype="int64"),
            "horizon_months": pd.Series([], dtype="int64"),
            "realized_gross_return": pd.Series([], dtype="float64"),
        }
    )


def compute_svb_bounds(raw_surface, spot_daily, zero_curve):
    """Daily P^L / P* / P^U for every case-study secid, via the monthly engine run on
    daily data. Returns a results-schema DataFrame (realized columns are NA)."""
    clean = daily_clean_surface(raw_surface, spot_daily)
    rates = build_rates(zero_curve)  # month_ends=None -> keep every day
    return run_pipeline(clean, rates, _empty_realized())


def _panel_series(bounds, secid, threshold_q, horizon_days):
    horizon = schema.HORIZON_TO_MATURITY_DAYS  # {months: days}
    months = {v: k for k, v in horizon.items()}[horizon_days]
    d = bounds[
        (bounds["secid"] == secid)
        & (bounds["threshold_q"] == threshold_q)
        & (bounds["horizon_months"] == months)
    ]
    return d.sort_values("date")


def svb_realized_table(
    bounds,
    spot_daily,
    threshold_q=THRESHOLD_Q,
    horizon_days=HORIZON_DAYS,
    ref_date=REF_DATE,
):
    """The known-resolution table: each asset's peak crash probability during the
    episode against what actually happened -- its realized drawdown from ``ref_date``
    (the pre-collapse level) to the March trough, and whether a 20% crash occurred.

    Columns [ticker, level, peak_pstar, peak_lower, peak_date, realized_drawdown,
    crashed]."""
    rows = []
    for secid, _ in PANELS:
        s = _panel_series(bounds, secid, threshold_q, horizon_days)
        ps = (
            spot_daily[spot_daily["secid"] == secid]
            .sort_values("date")
            .set_index("date")["spot_price"]
        )
        if s.empty or ref_date not in ps.index:
            continue
        i = s["prob_riskneutral"].idxmax()
        p0 = float(ps.loc[ref_date])
        drawdown = float(ps.loc[ref_date:].min()) / p0 - 1.0
        rows.append(
            {
                "ticker": CASE_LABELS[secid],
                "level": LEVEL[secid],
                "peak_pstar": float(s.loc[i, "prob_riskneutral"]),
                "peak_lower": float(s.loc[i, "bound_lower"]),
                "peak_date": s.loc[i, "date"],
                "realized_drawdown": drawdown,
                "crashed": bool(drawdown <= -(1.0 - threshold_q)),
            }
        )
    return pd.DataFrame(rows)


def realized_to_latex(table, threshold_q=THRESHOLD_Q):
    """Render the known-resolution table as a LaTeX tabular."""
    drop = round((1 - threshold_q) * 100)
    lines = [
        r"\begin{tabular}{llrrrc}",
        r"\toprule",
        (
            r"Asset & Level & Peak $P^*$ & Peak $P^L$ & Realized & "
            rf"{drop}\% crash? \\"
        ),
        r" & & & & drawdown & \\",
        r"\midrule",
    ]
    for _, r in table.iterrows():
        crash = "Yes" if r["crashed"] else "No"
        lines.append(
            rf"{r['ticker']} & {r['level']} & {100 * r['peak_pstar']:.1f}\% "
            rf"& {100 * r['peak_lower']:.1f}\% & {100 * r['realized_drawdown']:.1f}\% & {crash} \\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines)


def build_figure_svb(
    bounds, threshold_q=THRESHOLD_Q, horizon_days=HORIZON_DAYS, title=TITLE
):
    """Three stacked daily panels (SIVB, KRE, XLF): lower bound vs risk-neutral."""
    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.92, bottom=0.07, hspace=0.28)

    for ax, (secid, label) in zip(axes, PANELS):
        s = _panel_series(bounds, secid, threshold_q, horizon_days)
        ax.plot(
            s["date"],
            100 * s["prob_riskneutral"],
            color=C_RN,
            lw=1.6,
            marker="o",
            ms=3,
            label=r"Risk-neutral $P^*$",
        )
        ax.plot(
            s["date"],
            100 * s["bound_lower"],
            color=C_LB,
            lw=1.6,
            marker="o",
            ms=3,
            label=r"Lower bound $P^L$",
        )
        ax.axvline(COLLAPSE_DATE, color="#333333", lw=1.0, ls="--")
        top = ax.get_ylim()[1]
        ax.text(
            COLLAPSE_DATE,
            top * 0.97,
            " SVB fails (Mar 10)",
            fontsize=8,
            color="#333333",
            ha="left",
            va="top",
        )
        ax.set_title(label, fontsize=10.5, loc="left", pad=4)
        ax.set_ylabel("P(20% crash)")
        ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
        ax.yaxis.set_major_locator(MaxNLocator(nbins=5, steps=[1, 2, 5, 10]))
        ax.grid(True, color="#e6e6e6", linewidth=0.6)
        ax.set_axisbelow(True)
        for sp in ax.spines.values():
            sp.set_edgecolor("#333333")
            sp.set_linewidth(0.8)
        ax.margins(x=0.01)

    axes[0].legend(frameon=False, fontsize=9, loc="upper left")
    axes[-1].xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    axes[-1].set_xlabel("2023")
    fig.suptitle(title, fontsize=13, y=0.975)
    return fig


if __name__ == "__main__":
    from pull_svb_daily import load_svb_spot, load_svb_surface, load_svb_zero

    spot = load_svb_spot()
    bounds = compute_svb_bounds(load_svb_surface(), spot, load_svb_zero())
    bounds.to_parquet(OUTPUT_DIR / "svb_daily_bounds.parquet")
    build_figure_svb(bounds).savefig(
        OUTPUT_DIR / "fig_svb_case_study.png", dpi=150, bbox_inches="tight"
    )

    tbl = svb_realized_table(bounds, spot)
    tbl.to_csv(OUTPUT_DIR / "svb_realized.csv", index=False)
    (OUTPUT_DIR / "svb_realized.tex").write_text(realized_to_latex(tbl))
    print(tbl.to_string(index=False))
    # A compact peak-value summary for the text.
    for secid, label in PANELS:
        s = _panel_series(bounds, secid, THRESHOLD_Q, HORIZON_DAYS)
        if len(s):
            i = s["prob_riskneutral"].idxmax()
            print(
                f"{CASE_LABELS[secid]}: P* peak {100 * s.loc[i, 'prob_riskneutral']:.1f}% "
                f"(P^L {100 * s.loc[i, 'bound_lower']:.1f}%) on {s.loc[i, 'date'].date()}; "
                f"last surface {s['date'].max().date()}"
            )
    print("wrote svb_daily_bounds.parquet and fig_svb_case_study.png")
