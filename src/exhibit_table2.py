"""E: Replicate Table 2 -- regression calibration tests (Martin & Shi 2025, eq. 9).

For each crash size q in {0.7, 0.8, 0.9}, horizon tau in {1, 3, 6, 12}, and
right-hand-side measure X in {lower bound, risk-neutral prob, upper bound}, we run
the pooled OLS over S&P 500 constituent member-months (1996-2022):

    I(R_{i,t->t+tau} <= q) = alpha + beta * X_{it}(tau, q) + eps,

and report alpha, beta, and R^2. A bound that equals the true crash probability
gives alpha = 0 and beta = 1, so the test is beta = 1 (not 0). Following the paper,
each coefficient carries two standard errors: two-way (firm and month) clustered
(Thompson 2011), in parentheses, and month block-bootstrap (2500 samples), in
square brackets.
"""

from pathlib import Path

import numpy as np
import pandas as pd

import schema
from settings import config

OUTPUT_DIR = Path(config("OUTPUT_DIR"))

REPL_START = pd.Timestamp("1996-01-01")
REPL_END = pd.Timestamp("2022-12-31")
N_BOOT = 2500
SEED = 0

# (display label, results column), in the paper's column order.
MEASURES = [
    ("lower bound", "bound_lower"),
    ("risk-neutral", "prob_riskneutral"),
    ("upper bound", "bound_upper"),
]
PANELS = [(0.70, "A", "down by over 30%"),
          (0.80, "B", "down by over 20%"),
          (0.90, "C", "down by over 10%")]


def _ols(x, y):
    """Simple OLS y = alpha + beta x. Returns (alpha, beta, r2, residuals)."""
    xb, yb = x.mean(), y.mean()
    sxx = ((x - xb) ** 2).sum()
    beta = ((x - xb) * (y - yb)).sum() / sxx
    alpha = yb - beta * xb
    resid = y - (alpha + beta * x)
    r2 = 1.0 - (resid ** 2).sum() / ((y - yb) ** 2).sum()
    return alpha, beta, r2, resid


def _clustered_meat(X, u, groups):
    """Sum over clusters g of (sum_{i in g} X_i u_i)(...)' -- the sandwich meat."""
    Xu = pd.DataFrame(X * u[:, None])
    Xu["g"] = np.asarray(groups)
    S = Xu.groupby("g").sum().to_numpy()  # one row per cluster: sum of X_i u_i
    return S.T @ S


def _twoway_clustered_se(x, y, firm, month, alpha, beta):
    """Two-way (firm & month) clustered SEs (Cameron-Gelbach-Miller / Thompson).

    V = V_firm + V_month - V_white, sandwiched with (X'X)^{-1}.
    """
    n = len(x)
    X = np.column_stack([np.ones(n), x])
    u = (y - (alpha + beta * x)).to_numpy(float)
    bread = np.linalg.inv(X.T @ X)
    V_firm = bread @ _clustered_meat(X, u, firm) @ bread
    V_month = bread @ _clustered_meat(X, u, month) @ bread
    Xu = X * u[:, None]
    V_white = bread @ (Xu.T @ Xu) @ bread  # firm x month intersections are singletons
    V = V_firm + V_month - V_white
    se = np.sqrt(np.maximum(np.diag(V), 0.0))  # guard rare non-PSD
    return se[0], se[1]  # (se_alpha, se_beta)


def _block_bootstrap_se(x, y, month, block_len, n_boot=N_BOOT, seed=SEED):
    """Overlapping-block bootstrap over months, per Martin & Wagner (2019) App. B.

    Their procedure (which Martin & Shi follow): draw overlapping blocks of
    consecutive months (Kuensch 1989) with replacement until the sample has the
    same number of time periods as the data, with block length equal to the
    forecast horizon T -- their footnote 15, "to account for overlapping
    observations". This preserves the serial correlation from the overlapping
    tau-month crash windows (a 12-month indicator at month t overlaps t+1..t+11),
    which grows the standard error at long horizons. Their footnote 16 notes that
    "selecting a subset of firms or including all firms available in a drawn block
    leads to identical results", so we keep all firms in each block. Simple OLS has
    a closed form, so we bootstrap on per-month sufficient statistics via a
    cumulative sum -- fast and exact for the slope/intercept.
    """
    xa, ya = np.asarray(x, float), np.asarray(y, float)
    d = pd.DataFrame({"x": xa, "y": ya, "xx": xa * xa, "xy": xa * ya, "m": np.asarray(month)})
    g = d.groupby("m")  # groups come out sorted by month (chronological)
    stats = np.column_stack([g.size().to_numpy(), g[["x", "y", "xx", "xy"]].sum().to_numpy()])
    M = len(stats)
    L = int(max(1, min(block_len, M)))
    n_blocks = int(np.ceil(M / L))
    csum = np.vstack([np.zeros(5), np.cumsum(stats, axis=0)])  # block sum = csum[s+L]-csum[s]

    rng = np.random.default_rng(seed)
    alphas = np.empty(n_boot)
    betas = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, M - L + 1, n_blocks)
        n, Sx, Sy, Sxx, Sxy = (csum[starts + L] - csum[starts]).sum(axis=0)
        beta = (Sxy - Sx * Sy / n) / (Sxx - Sx * Sx / n)
        betas[b] = beta
        alphas[b] = (Sy - beta * Sx) / n
    return alphas.std(ddof=1), betas.std(ddof=1)


def run_table2(results, member_panel, start=REPL_START, end=REPL_END,
               n_boot=N_BOOT, seed=SEED):
    """Return Table 2's regression results as a tidy long DataFrame.

    Columns: q, measure, horizon, alpha, alpha_se_cl, alpha_se_bs, beta,
    beta_se_cl, beta_se_bs, r2.
    """
    members = member_panel[["date", "secid"]].dropna(subset=["secid"]).copy()
    members["secid"] = members["secid"].astype("int64")
    df = results.merge(members.drop_duplicates(), on=["date", "secid"], how="inner")
    df = df[(df["date"] >= start) & (df["date"] <= end) & df["realized_flag"].notna()]
    df = df.assign(y=df["realized_flag"].astype(float))

    rows = []
    for q in schema.THRESHOLDS_Q:
        for label, col in MEASURES:
            for tau in schema.HORIZONS_MONTHS:
                d = df[(df["threshold_q"] == q) & (df["horizon_months"] == tau)]
                x, y = d[col], d["y"]
                alpha, beta, r2, _ = _ols(x, y)
                a_cl, b_cl = _twoway_clustered_se(x, y, d["secid"], d["date"], alpha, beta)
                a_bs, b_bs = _block_bootstrap_se(x, y, d["date"], tau, n_boot, seed)
                rows.append(dict(q=q, measure=label, horizon=tau, alpha=alpha,
                                 alpha_se_cl=a_cl, alpha_se_bs=a_bs, beta=beta,
                                 beta_se_cl=b_cl, beta_se_bs=b_bs, r2=r2))
    return pd.DataFrame(rows)


def _cells(stats, q, field):
    """The 12 values for one (q, field) row: lower 1/3/6/12, rn 1/3/6/12, upper."""
    out = []
    for label, _ in MEASURES:
        for tau in schema.HORIZONS_MONTHS:
            m = stats[(stats["q"] == q) & (stats["measure"] == label)
                      & (stats["horizon"] == tau)]
            out.append(float(m[field].iloc[0]))
    return out


def to_latex(stats):
    """Render Table 2 as a LaTeX tabular matching the paper's layout."""
    def row(vals, fmt):
        return " & ".join(fmt(v) for v in vals)

    num = lambda v: f"{v:.2f}"
    paren = lambda v: f"({v:.2f})"
    brack = lambda v: f"[{v:.2f}]"
    pct = lambda v: f"{v * 100:.2f}\\%"

    lines = [
        r"\begin{tabular}{l" + "rrrr" * 3 + "}",
        r"\toprule",
        r" & \multicolumn{4}{c}{lower bound} & \multicolumn{4}{c}{risk-neutral}"
        r" & \multicolumn{4}{c}{upper bound} \\",
        r"horizon & 1 & 3 & 6 & 12 & 1 & 3 & 6 & 12 & 1 & 3 & 6 & 12 \\",
        r"\midrule",
    ]
    for q, letter, desc in PANELS:
        lines.append(rf"\multicolumn{{13}}{{c}}{{Panel {letter}: $q = {q:.2f}$, "
                     rf"{desc.replace('%', r'\%')}}} \\")
        lines.append(rf"$\alpha$ & {row(_cells(stats, q, 'alpha'), num)} \\")
        lines.append(rf" & {row(_cells(stats, q, 'alpha_se_cl'), paren)} \\")
        lines.append(rf" & {row(_cells(stats, q, 'alpha_se_bs'), brack)} \\")
        lines.append(rf"$\beta$ & {row(_cells(stats, q, 'beta'), num)} \\")
        lines.append(rf" & {row(_cells(stats, q, 'beta_se_cl'), paren)} \\")
        lines.append(rf" & {row(_cells(stats, q, 'beta_se_bs'), brack)} \\")
        lines.append(rf"$R^2$ & {row(_cells(stats, q, 'r2'), pct)} \\")
        lines.append(r"\midrule")
    lines[-1] = r"\bottomrule"
    lines.append(r"\end{tabular}")
    return "\n".join(lines)


if __name__ == "__main__":
    from sp500_secid_universe import load_sp500_secid_universe

    results = pd.read_parquet(OUTPUT_DIR / "results.parquet")
    stats = run_table2(results, load_sp500_secid_universe())
    stats.to_csv(OUTPUT_DIR / "table2.csv", index=False)
    (OUTPUT_DIR / "table2.tex").write_text(to_latex(stats))
    print(stats[["q", "measure", "horizon", "beta", "r2"]].to_string(index=False))
