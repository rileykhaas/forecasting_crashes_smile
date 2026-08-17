# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.18.1
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Data Tour: Forecasting Crashes with a Smile
#
# ## Summary
#
# This repository replicates and extends Martin & Shi (2025), *"Forecasting Crashes
# with a Smile."* The paper shows that the shape of the option-implied **volatility
# smile** carries a model-free signal for the *physical* probability that a stock
# crashes over the next one to twelve months. Read directly from option prices, the
# risk-neutral crash probability "cries wolf" — it overstates crash risk, worst in
# crises, because it carries a fear premium. The paper's contribution is a
# theory-based correction: reweighting by a power-utility investor's marginal value
# of a dollar ($\gamma = 2$) and closing the unknown stock–market dependence with
# Fréchet–Hoeffding copula bounds yields a **lower bound** that, under mild
# comonotonicity, sits close to the true crash probability.
#
# This notebook is a tour of the code you just cloned. It follows a single
# month-end from the cleaned inputs to a crash-probability forecast, calling the
# same functions the `doit` build uses, so a first-time reader can see how the
# pieces fit together.

# %% [markdown]
# ## Game Plan
#
# The pipeline follows the paper's Appendix D and is wired end-to-end in `dodo.py`.
# Its stages, each a module in `src/`:
#
# | Stage | Module | What it produces |
# |-------|--------|------------------|
# | Pull | `pull_optionmetrics`, `pull_CRSP_stock`, `pull_link`, `pull_sp500` | raw WRDS data |
# | Clean (Slice 1) | `clean_surface`, `rates` | the tidy volatility surface + zero curve |
# | Build (Slice 2) | `sp500_secid_universe`, `realized_returns` | the firm universe + realized crashes |
# | Engine (A1–A5) | `rnd`, `utility_correction`, `bounds`, `run_pipeline` | the crash-probability bounds |
# | Exhibits | `exhibit_table1` | the replicated tables and figures |
#
# Table schemas are fixed centrally in `schema.py`, and every intermediate table is
# a tidy, documented parquet registered in the chartbook. We walk the engine stages
# below on one concrete smile.

# %%
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import schema
from settings import config
from clean_surface import load_clean_surface
from rnd import risk_neutral_cdf
from bounds import crash_bounds

# %matplotlib inline
DATA_DIR = Path(config("DATA_DIR"))
OUTPUT_DIR = Path(config("OUTPUT_DIR"))
plt.rcParams["figure.figsize"] = (8, 4.5)

# %% [markdown]
# ## Step 1. Load the cleaned data
#
# `clean_surface.parquet` is the analysis-ready volatility surface produced by
# `clean_surface.py`: one row per (date, secid, maturity, moneyness) that survives
# the paper's four Appendix-D filters (a CRSP spot exists, positive strike,
# OptionMetrics dispersion in $(0, 0.05)$, and more than ten strikes per
# firm-month-maturity). `secid = 108105` is the S&P 500 index itself; moneyness is
# `strike / spot`, so a strike and a gross-return level are the same number.

# %%
surface = load_clean_surface()
surface.info()

# %%
surface.head()

# %% [markdown]
# ## Step 2. Inspect one volatility smile
#
# We isolate a single smile — the S&P 500 index, the most recent month-end in the
# sample, the **1-year (365-day)** maturity — and plot implied volatility against
# moneyness. We use the one-year horizon deliberately: over a single month a 20–30%
# crash is essentially impossible, so the risk-neutral probabilities there round to
# zero and illustrate nothing. One year is also the horizon where Martin & Shi find
# the lower bound tightest — closest to the true crash probability — so it is the
# natural showcase. The upward tilt toward low moneyness is the **skew**:
# out-of-the-money puts (crash insurance) trade at higher implied volatility, the
# asymmetry the whole method extracts.

# %%
date = surface.loc[surface["secid"] == schema.SPX_SECID, "date"].max()
smile = surface[
    (surface["secid"] == schema.SPX_SECID)
    & (surface["date"] == date)
    & (surface["days_to_maturity"] == 365)
].sort_values("moneyness")
smile.head()

# %%
fig, ax = plt.subplots()
ax.plot(smile["moneyness"], smile["implied_vol"], marker="o", ms=3)
ax.axvline(1.0, color="grey", ls="--", lw=0.8, label="at-the-money")
ax.set_xlabel("moneyness  (strike / spot)")
ax.set_ylabel("implied volatility")
ax.set_title(f"S&P 500 implied-vol smile, 1-year, {date.date()}")
ax.legend()
fig

# %% [markdown]
# ## Step 3. Recover the risk-neutral density
#
# `rnd.risk_neutral_cdf` implements stage A1. It prices out-of-the-money options
# across a fine moneyness grid ($K/S \in [1/L, L]$), differentiates the call curve
# (Breeden–Litzenberger) to recover the risk-neutral CDF of the gross return, and
# enforces a valid, monotone distribution with an isotonic fit. The return is a
# callable CDF, `Q(q) = P*[R <= q]`.

# %%
rate = 0.03  # illustrative flat rate; the pipeline uses the matched zero-curve value
cdf = risk_neutral_cdf(smile, rate)

fig, ax = plt.subplots()
ax.plot(cdf.grid, cdf.values)
ax.set_xlabel("gross return  q = S_T / S_0")
ax.set_ylabel(r"$Q(q) = \mathbb{P}^*[R \leq q]$")
ax.set_title(f"Risk-neutral CDF of the 1-year S&P 500 return, {date.date()}")
for q in schema.THRESHOLDS_Q:
    ax.axvline(q, color="grey", ls="--", lw=0.7)
    ax.annotate(f"q={q}", (q, 0.02), rotation=90, va="bottom", fontsize=8)
fig

# %% [markdown]
# ## Step 4. The risk-neutral crash probability ("crying wolf")
#
# Reading the CDF at each crash threshold $q$ (a gross return at or below $q$ is a
# crash of $1-q$) gives the risk-neutral crash probability. This is the number the
# paper argues *overstates* the true probability — it has not yet been corrected
# for the fear premium.

# %%
pd.DataFrame(
    {
        "threshold_q": schema.THRESHOLDS_Q,
        "crash_size": [f"{int((1 - q) * 100)}%" for q in schema.THRESHOLDS_Q],
        "risk_neutral_crash_prob": [round(float(cdf(q)), 4) for q in schema.THRESHOLDS_Q],
    }
)

# %% [markdown]
# ## Step 5. Fear correction and the Fréchet–Hoeffding bounds
#
# `bounds.crash_bounds` combines stages A3 and A4: it applies the power-utility
# fear correction ($\gamma = 2$) via `utility_correction.py` and forms the
# Fréchet–Hoeffding bounds, using the market (index) distribution as the reference.
# For the index itself ($i = m$) the market is comonotonic with itself, so the
# lower bound holds with equality — this is the market crash probability of the
# paper's Result 3. Note how the fear-corrected lower bound falls *below* the
# risk-neutral probability from Step 4.

# %%
pd.DataFrame(
    [
        dict(
            zip(
                ["threshold_q", "lower_bound", "risk_neutral", "upper_bound"],
                [q, *[round(x, 4) for x in crash_bounds(cdf, cdf, rate, q)]],
            )
        )
        for q in schema.THRESHOLDS_Q
    ]
)

# %% [markdown]
# ## Step 6. The full results table
#
# Running the engine over every date, name, horizon, and threshold produces
# `results.parquet` (`run_pipeline.py`, stage A5): one row per
# (date, secid, horizon, threshold) with the lower bound, risk-neutral probability,
# upper bound, and the realized gross return and crash flag the forecast is tested
# against. This is the single table every figure and table reads from.

# %%
results = pd.read_parquet(OUTPUT_DIR / "results.parquet")
results.info()

# %%
results.head()

# %% [markdown]
# ## Step 7. Replication check — does the lower bound track realized crashes?
#
# The paper's central claim: pooled across firms, the mean **lower bound sits close
# to the realized crash frequency**, while the risk-neutral probability and the
# upper bound overstate. We check the 20%-drop ($q = 0.80$), 12-month cell over the
# constituent cross-section (excluding the index), on the paper's 1996–2022 window,
# and compare to the paper's published Table 1 values.

# %%
panel = results[
    (results["threshold_q"] == 0.80)
    & (results["horizon_months"] == 12)
    & (results["secid"] != schema.SPX_SECID)
    & (results["date"] <= "2022-12-31")
    & (results["realized_flag"].notna())
]

check = pd.DataFrame(
    {
        "measure": ["realized crash freq.", "lower bound", "risk-neutral", "upper bound"],
        "ours": [
            panel["realized_flag"].mean(),
            panel["bound_lower"].mean(),
            panel["prob_riskneutral"].mean(),
            panel["bound_upper"].mean(),
        ],
        "paper (Table 1)": [0.152, 0.123, 0.236, 0.340],
    }
)
check["ours"] = check["ours"].round(3)
check

# %% [markdown]
# ## Step 8. The picture
#
# The bar chart makes the takeaway visual: the realized crash frequency and the
# option-implied lower bound sit side by side, while the risk-neutral probability
# and (more so) the upper bound run well above both. This is the pattern Table 1
# reproduces across every threshold and horizon — the formal, tolerance-tested
# version lives in `exhibit_table1.py` and the report.

# %%
fig, ax = plt.subplots()
colors = ["#444444", "#1f77b4", "#ff7f0e", "#d62728"]
ax.bar(check["measure"], check["ours"], color=colors)
ax.set_ylabel("mean probability / frequency")
ax.set_title("20% drop over 12 months, S&P 500 constituents, 1996–2022")
for i, v in enumerate(check["ours"]):
    ax.annotate(f"{v:.3f}", (i, v), ha="center", va="bottom", fontsize=9)
plt.xticks(rotation=15)
fig
