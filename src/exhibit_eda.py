"""E: Exploratory summary of the underlying option/return panel (issue #33).

Our own summary statistics of the *raw inputs* the bounds are built from -- the
cleaned OptionMetrics volatility surface (``clean_surface.parquet``) and the CRSP
forward realized returns (``realized_returns.parquet``) -- as distinct from the
replication Table 1 (which reports the paper's statistics on the *derived*
crash-probability bounds). Restricted to S&P 500 constituent member-months (an inner
join to sp500_secid_universe, which also drops the index and the extension ETFs), so
the coverage described here is the coverage of the replication sample itself.

Two exhibits, each with a ``_ext`` variant through the latest data:
  * a per-year coverage table (``eda_coverage.tex`` / ``.csv``): # names, firm-months,
    option quotes, quotes per firm-month, median implied vol, and the realized 20%
    (12-month) crash frequency -- showing the panel is broad and continuous while the
    event being forecast is rare and time-varying.
  * a 2x2 panel figure (``eda_panel.png``): (a) cross-section size over time,
    (b) a moneyness x maturity availability heatmap, (c) the implied-volatility smile
    by maturity, and (d) the realized-return distribution at 1- vs 12-month horizons.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: save files, never open a window
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from settings import config  # noqa: E402

OUTPUT_DIR = Path(config("OUTPUT_DIR"))

REPL_START = pd.Timestamp("1996-01-01")
REPL_END = pd.Timestamp("2022-12-31")
EXT_END = pd.Timestamp("2025-12-31")  # extension: through the most recent data
TITLE = "The Underlying Option-Return Panel at a Glance"

CRASH_Q = 0.80        # a 20% crash (gross return <= 0.8)
CRASH_HORIZON = 12    # the 12-month horizon used for the table's crash column
MATURITIES = [30, 91, 182, 365]  # days_to_maturity present in the surface

# Moneyness (K/S) bin edges for the smile and the availability heatmap. The bound
# reads the out-of-the-money-put (low-moneyness) tail, so the grid is finer there.
MONEYNESS_EDGES = [0.50, 0.70, 0.80, 0.90, 0.95, 1.00,
                   1.05, 1.10, 1.20, 1.35, 1.60]

C_COVER = "#4f9ed6"   # blue -- coverage line
MAT_COLORS = {30: "#c7e0f4", 91: "#7fb8e6", 182: "#3b83c0", 365: "#1f4e79"}
C_H1 = "#9a9a9a"      # grey -- 1-month return distribution
C_H12 = "#e46fb0"     # pink -- 12-month return distribution


# --------------------------------------------------------------------------- #
# Sample restriction
# --------------------------------------------------------------------------- #
def constituent_frame(panel, member_panel, start=REPL_START, end=REPL_END):
    """Restrict a (date, secid, ...) panel to S&P 500 constituent member-months
    within [start, end]. Mirrors the inner join used by the other exhibits."""
    members = member_panel[["date", "secid"]].dropna(subset=["secid"]).copy()
    members["secid"] = members["secid"].astype("int64")
    members = members.drop_duplicates()
    out = panel.merge(members, on=["date", "secid"], how="inner")
    return out[(out["date"] >= start) & (out["date"] <= end)].copy()


# --------------------------------------------------------------------------- #
# Table: per-year coverage
# --------------------------------------------------------------------------- #
def coverage_by_year(surface_c, returns_c, crash_q=CRASH_Q, crash_horizon=CRASH_HORIZON):
    """Per-year coverage statistics of the (already constituent-restricted) panel.

    Columns [year, n_names, n_firm_months, n_quotes, quotes_per_fm, median_iv,
    crash_freq], where crash_freq is the realized frequency of a ``crash_q`` crash
    at ``crash_horizon`` months among that year's formation months.
    """
    s = surface_c.copy()
    s["year"] = s["date"].dt.year
    fm = s.drop_duplicates(["year", "date", "secid"])
    quotes_per_fm = s.groupby(["date", "secid"]).size()
    qpf_year = quotes_per_fm.reset_index(name="q").assign(
        year=lambda d: d["date"].dt.year).groupby("year")["q"].median()

    cov = pd.DataFrame({
        "n_names": s.groupby("year")["secid"].nunique(),
        "n_firm_months": fm.groupby("year").size(),
        "n_quotes": s.groupby("year").size(),
        "quotes_per_fm": qpf_year,
        "median_iv": s.groupby("year")["implied_vol"].median().astype("float64"),
    })

    r = returns_c[returns_c["horizon_months"] == crash_horizon].copy()
    r["year"] = r["date"].dt.year
    r["crash"] = (r["realized_gross_return"] <= crash_q).astype(float)
    cov["crash_freq"] = r.groupby("year")["crash"].mean()

    return cov.reset_index().sort_values("year").reset_index(drop=True)


def to_latex(cov, crash_q=CRASH_Q, crash_horizon=CRASH_HORIZON):
    """Render the per-year coverage table as a LaTeX tabular."""
    drop = int(round((1 - crash_q) * 100))
    lines = [
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        r"Year & Names & Firm-mo. & Quotes & Quotes & Median & "
        rf"{crash_horizon}-mo. {drop}\% \\",
        r" & ($N$) & & (000s) & /firm-mo. & IV & crash freq. \\",
        r"\midrule",
    ]
    for _, row in cov.iterrows():
        crash = "" if pd.isna(row["crash_freq"]) else f"{row['crash_freq']:.3f}"
        lines.append(
            rf"{int(row['year'])} & {int(row['n_names'])} & "
            rf"{int(row['n_firm_months'])} & {row['n_quotes'] / 1000:.0f} & "
            rf"{row['quotes_per_fm']:.0f} & {row['median_iv']:.3f} & {crash} \\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Figure helpers (pure -- unit tested)
# --------------------------------------------------------------------------- #
def names_over_time(surface_c):
    """Monthly count of distinct constituent names carrying a surface. Series
    indexed by date."""
    return surface_c.groupby("date")["secid"].nunique().sort_index()


def availability_grid(surface_c, edges=MONEYNESS_EDGES, maturities=MATURITIES):
    """Fraction of firm-months whose surface has >=1 quote in each
    (maturity, moneyness-bin) cell. Rows = maturities, columns = moneyness bins."""
    s = surface_c[["date", "secid", "days_to_maturity", "moneyness"]].copy()
    s["mbin"] = pd.cut(s["moneyness"].astype("float64"), bins=edges, right=False)
    s = s.dropna(subset=["mbin"])
    total_fm = s.drop_duplicates(["date", "secid"]).shape[0]
    covered = (s.drop_duplicates(["date", "secid", "days_to_maturity", "mbin"])
               .groupby(["days_to_maturity", "mbin"], observed=True).size())
    grid = (covered / total_fm).unstack("mbin")
    return grid.reindex(index=maturities)


def iv_smile(surface_c, edges=MONEYNESS_EDGES, maturities=MATURITIES):
    """Median implied vol in each moneyness bin, per maturity. Rows = maturities,
    columns = moneyness bins."""
    s = surface_c[["days_to_maturity", "moneyness", "implied_vol"]].copy()
    s["moneyness"] = s["moneyness"].astype("float64")
    s["implied_vol"] = s["implied_vol"].astype("float64")
    s["mbin"] = pd.cut(s["moneyness"], bins=edges, right=False)
    med = (s.dropna(subset=["mbin"])
           .groupby(["days_to_maturity", "mbin"], observed=True)["implied_vol"]
           .median().unstack("mbin"))
    return med.reindex(index=maturities)


def _bin_centers(edges):
    return [(a + b) / 2 for a, b in zip(edges[:-1], edges[1:])]


# --------------------------------------------------------------------------- #
# Figure
# --------------------------------------------------------------------------- #
def build_figure_eda(surface, returns, member_panel, start=REPL_START,
                     end=REPL_END, title=TITLE):
    """Return the 2x2 EDA panel figure for the constituent panel over [start, end]."""
    surface_c = constituent_frame(surface, member_panel, start, end)
    returns_c = constituent_frame(returns, member_panel, start, end)
    centers = _bin_centers(MONEYNESS_EDGES)

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    fig.subplots_adjust(left=0.07, right=0.97, top=0.90, bottom=0.08,
                        hspace=0.32, wspace=0.24)

    # (a) Cross-section size over time -----------------------------------------
    ax = axes[0, 0]
    n = names_over_time(surface_c)
    ax.plot(n.index, n.values, color=C_COVER, lw=1.2)
    ax.fill_between(n.index, n.values, color=C_COVER, alpha=0.12)
    ax.set_ylim(0, n.max() * 1.1)
    ax.set_title("(a) Constituents with an option surface, by month", fontsize=10.5)
    ax.set_ylabel("Number of names")
    ax.xaxis.set_major_locator(mdates.YearLocator(4))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    _grid(ax)

    # (b) Moneyness x maturity availability heatmap ----------------------------
    ax = axes[0, 1]
    grid = availability_grid(surface_c)
    im = ax.imshow(grid.to_numpy(dtype=float), aspect="auto", cmap="Blues",
                   origin="upper", vmin=0.0, vmax=1.0)
    ax.set_xticks(range(len(centers)))
    ax.set_xticklabels([f"{c:.2f}" for c in centers], rotation=45, fontsize=7.5)
    ax.set_yticks(range(len(MATURITIES)))
    ax.set_yticklabels([f"{m}d" for m in MATURITIES])
    ax.set_title("(b) Quote availability: moneyness $\\times$ maturity", fontsize=10.5)
    ax.set_xlabel("Moneyness $K/S$")
    ax.set_ylabel("Maturity")
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    cbar.set_label("Share of firm-months covered", fontsize=8)
    ax.axvline(_atm_index(centers) - 0.5, color="#333333", lw=0.8, ls=":")

    # (c) The implied-volatility smile -----------------------------------------
    ax = axes[1, 0]
    smile = iv_smile(surface_c)
    for m in MATURITIES:
        if m in smile.index:
            ax.plot(centers, smile.loc[m].to_numpy(dtype=float), marker="o", ms=3,
                    lw=1.2, color=MAT_COLORS[m], label=f"{m}d")
    ax.axvline(1.0, color="#9a9a9a", lw=0.8, ls=(0, (4, 3)))
    ax.set_title("(c) The implied-volatility smile, by maturity", fontsize=10.5)
    ax.set_xlabel("Moneyness $K/S$")
    ax.set_ylabel("Median implied volatility")
    ax.legend(title="Maturity", frameon=False, fontsize=8, ncol=2)
    _grid(ax)

    # (d) Realized-return distribution -----------------------------------------
    ax = axes[1, 1]
    bins = np.linspace(0.4, 1.8, 57)
    for tau, color, lab in [(1, C_H1, "1 month"), (12, C_H12, "12 months")]:
        vals = returns_c.loc[returns_c["horizon_months"] == tau,
                             "realized_gross_return"].to_numpy(dtype=float)
        vals = vals[(vals >= bins[0]) & (vals <= bins[-1])]  # trim tails (no edge pile-up)
        ax.hist(vals, bins=bins, density=True, histtype="step", lw=1.5,
                color=color, label=lab)
    ax.axvline(CRASH_Q, color="#333333", lw=0.9, ls="--")
    ax.text(CRASH_Q, ax.get_ylim()[1] * 0.92, " 20% crash", fontsize=7.5,
            color="#333333", ha="left", va="top")
    ax.axvline(0.70, color="#333333", lw=0.7, ls=":")
    ax.text(0.70, ax.get_ylim()[1] * 0.78, " 30%", fontsize=7.5,
            color="#333333", ha="left", va="top")
    ax.set_title("(d) Realized gross-return distribution, by horizon", fontsize=10.5)
    ax.set_xlabel("Gross return $R_{t\\to t+\\tau}$")
    ax.set_ylabel("Density")
    ax.legend(title="Horizon", frameon=False, fontsize=8)
    _grid(ax)

    fig.suptitle(title, fontsize=13, y=0.965)
    return fig


def _grid(ax):
    ax.grid(True, color="#e2e2e2", linewidth=0.6)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_edgecolor("#333333")
        spine.set_linewidth(0.8)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6, steps=[1, 2, 5, 10]))


def _atm_index(centers):
    """Index of the moneyness bin whose center is closest to at-the-money (1.0)."""
    return int(np.argmin([abs(c - 1.0) for c in centers]))


if __name__ == "__main__":
    from clean_surface import load_clean_surface
    from realized_returns import load_realized_returns
    from sp500_secid_universe import load_sp500_secid_universe

    surface = load_clean_surface()
    returns = load_realized_returns()
    universe = load_sp500_secid_universe()

    # Replication window (1996-2022): table + figure.
    cov = coverage_by_year(
        constituent_frame(surface, universe, REPL_START, REPL_END),
        constituent_frame(returns, universe, REPL_START, REPL_END))
    cov.to_csv(OUTPUT_DIR / "eda_coverage.csv", index=False)
    (OUTPUT_DIR / "eda_coverage.tex").write_text(to_latex(cov))
    build_figure_eda(surface, returns, universe).savefig(
        OUTPUT_DIR / "eda_panel.png", dpi=150, bbox_inches="tight")

    # Extension through the most recent data.
    cov_ext = coverage_by_year(
        constituent_frame(surface, universe, REPL_START, EXT_END),
        constituent_frame(returns, universe, REPL_START, EXT_END))
    cov_ext.to_csv(OUTPUT_DIR / "eda_coverage_ext.csv", index=False)
    (OUTPUT_DIR / "eda_coverage_ext.tex").write_text(to_latex(cov_ext))
    build_figure_eda(surface, returns, universe, end=EXT_END,
                     title=TITLE + " (extended sample)").savefig(
        OUTPUT_DIR / "eda_panel_ext.png", dpi=150, bbox_inches="tight")
    print("wrote eda_coverage.{tex,csv} and eda_panel.png (+ _ext)")
