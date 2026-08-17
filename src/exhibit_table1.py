"""E1: Replicate Table 1 (summary statistics) of Martin & Shi (2025).

Rebuilds the paper's Table 1 from results.parquet over the REPLICATION window
(formation months Jan 1996 - Dec 2022, T = 324). Table 1 is the cross-section of
the N S&P 500 constituent firms, so we restrict to constituent member-months by
inner-joining results to sp500_secid_universe -- which also excludes the S&P 500
index itself (its own exhibit, Figure 2) and the extension sector ETFs.

For each crash threshold q in {0.7, 0.8, 0.9}, horizon tau in {1, 3, 6, 12}, and
measure -- the realized crash indicator 1{R <= q}, the lower bound, the
risk-neutral probability, and the upper bound -- the table reports two blocks,
exactly as the paper:

  "averaged across firms" (T = 324): each month, average the measure across
      firms -> a length-T series; report its mean and s.d.
  "averaged across time"  (N firms): each firm, average the measure across
      months -> a length-N series; report its mean and s.d.

The means/s.d. differ slightly between blocks because the panel is unbalanced.
"""

from pathlib import Path

import pandas as pd

import schema
from settings import config

OUTPUT_DIR = Path(config("OUTPUT_DIR"))

# Replication sample: monthly, Jan 1996 - Dec 2022 (T = 324 formation months).
REPL_START = pd.Timestamp("1996-01-01")
REPL_END = pd.Timestamp("2022-12-31")

# (display label, results column), in the paper's row order.
MEASURES = [
    ("realized", "realized_flag"),
    ("lower bound", "bound_lower"),
    ("risk-neutral", "prob_riskneutral"),
    ("upper bound", "bound_upper"),
]

# (q, panel letter, description) for the three panels.
PANELS = [
    (0.70, "A", "down by over 30%"),
    (0.80, "B", "down by over 20%"),
    (0.90, "C", "down by over 10%"),
]


def build_table1(results, member_panel, start=REPL_START, end=REPL_END):
    """Return Table 1's statistics as a long-format DataFrame.

    Parameters
    ----------
    results : DataFrame
        schema.SCHEMAS['results'] -- the engine output (run_pipeline).
    member_panel : DataFrame
        A firm-month membership panel with at least [date, secid]
        (sp500_secid_universe). results is inner-joined to it so only constituent
        member-months enter, matching the paper's N-firm cross-section.
    start, end : Timestamp
        Formation-date window (inclusive). Defaults to the paper's 1996-2022.

    Returns columns [q, measure, horizon, block, mean, sd], where block is
    'firms' (the across-firms / T column set) or 'time' (across-time / N set).
    """
    members = member_panel[["date", "secid"]].dropna(subset=["secid"]).copy()
    members["secid"] = members["secid"].astype("int64")
    members = members.drop_duplicates()
    df = results.merge(members, on=["date", "secid"], how="inner")
    df = df[(df["date"] >= start) & (df["date"] <= end)].copy()
    # realized_flag is nullable Int64; float lets groupby.mean skip missing.
    df["realized_flag"] = df["realized_flag"].astype("float64")

    rows = []
    for q in schema.THRESHOLDS_Q:
        for label, col in MEASURES:
            for tau in schema.HORIZONS_MONTHS:
                sub = df[(df["threshold_q"] == q) & (df["horizon_months"] == tau)]
                across_firms = sub.groupby("date")[col].mean()  # T monthly means
                across_time = sub.groupby("secid")[col].mean()  # N firm means
                rows.append(
                    dict(q=q, measure=label, horizon=tau, block="firms",
                         mean=across_firms.mean(), sd=across_firms.std())
                )
                rows.append(
                    dict(q=q, measure=label, horizon=tau, block="time",
                         mean=across_time.mean(), sd=across_time.std())
                )
    out = pd.DataFrame(rows)
    # Sample sizes for the two block headers: T months (across firms), N firms
    # (across time). Carried as frame metadata so to_latex can label them.
    out.attrs["n_months"] = int(df["date"].nunique())
    out.attrs["n_firms"] = int(df["secid"].nunique())
    return out


def _cells(stats, q, measure, stat):
    """The 8 display values for one (q, measure, stat) row: firms 1/3/6/12 then
    time 1/3/6/12."""
    vals = []
    for block in ("firms", "time"):
        for tau in schema.HORIZONS_MONTHS:
            m = stats[
                (stats["q"] == q)
                & (stats["measure"] == measure)
                & (stats["block"] == block)
                & (stats["horizon"] == tau)
            ]
            vals.append(float(m[stat].iloc[0]))
    return vals


def to_latex(stats):
    """Render the statistics table as a LaTeX table matching the paper's Table 1."""
    horizons = schema.HORIZONS_MONTHS
    head = " & ".join(str(h) for h in horizons)
    t_obs = stats.attrs.get("n_months")
    n_firms = stats.attrs.get("n_firms")
    t_lab = f"$T = {t_obs}$" if t_obs else "$T$"
    n_lab = f"$N = {n_firms}$" if n_firms else "$N$"
    lines = [
        r"\begin{tabular}{ll" + "r" * (2 * len(horizons)) + "}",
        r"\toprule",
        r" & & \multicolumn{4}{c}{averaged across firms} "
        r"& \multicolumn{4}{c}{averaged across time} \\",
        rf" & & \multicolumn{{4}}{{c}}{{(number of obs. {t_lab})}} "
        rf"& \multicolumn{{4}}{{c}}{{(number of obs. {n_lab})}} \\",
        rf" & horizon & {head} & {head} \\",
        r"\midrule",
    ]
    for q, letter, desc in PANELS:
        # % is LaTeX's comment char -- escape it in the panel description.
        desc_tex = desc.replace("%", r"\%")
        lines.append(
            rf"\multicolumn{{10}}{{c}}{{Panel {letter}: $q = {q:.1f}$, {desc_tex}}} \\"
        )
        for label, _ in MEASURES:
            means = _cells(stats, q, label, "mean")
            sds = _cells(stats, q, label, "sd")
            fmt = lambda xs: " & ".join(f"{x:.3f}" for x in xs)
            lines.append(rf"\multirow{{2}}{{*}}{{{label}}} & mean & {fmt(means)} \\")
            lines.append(rf" & s.d. & {fmt(sds)} \\")
        lines.append(r"\midrule")
    lines[-1] = r"\bottomrule"
    lines.append(r"\end{tabular}")
    return "\n".join(lines)


def to_markdown(stats):
    """Compact markdown rendering (means only) for quick inspection / chartbook."""
    horizons = schema.HORIZONS_MONTHS
    header = ["measure", "block"] + [f"h{h}" for h in horizons]
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for q, letter, desc in PANELS:
        out.append(f"| **Panel {letter}: q={q:.1f} ({desc})** |" + " |" * len(horizons))
        for label, _ in MEASURES:
            for block in ("firms", "time"):
                vals = [
                    stats[(stats["q"] == q) & (stats["measure"] == label)
                          & (stats["block"] == block) & (stats["horizon"] == h)]["mean"].iloc[0]
                    for h in horizons
                ]
                out.append(f"| {label} | {block} | " + " | ".join(f"{v:.3f}" for v in vals) + " |")
    return "\n".join(out)


if __name__ == "__main__":
    from sp500_secid_universe import load_sp500_secid_universe

    results = pd.read_parquet(OUTPUT_DIR / "results.parquet")
    universe = load_sp500_secid_universe()
    stats = build_table1(results, universe)

    stats.to_csv(OUTPUT_DIR / "table1.csv", index=False)
    (OUTPUT_DIR / "table1.tex").write_text(to_latex(stats))
    print(to_markdown(stats))
