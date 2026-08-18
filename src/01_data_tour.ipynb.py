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
# **Can option prices tell you the odds a stock crashes next month?** Martin & Shi
# (2025) say yes. Investors pay up for crash insurance, out-of-the-money put options,
# and that premium is visible in the **volatility smile** (the way an option's implied
# volatility rises for strikes far below today's price). Read naively, the option-implied
# ("risk-neutral") crash probability *cries wolf*: it overstates real crash risk, worst
# in a crisis, because it bakes in a fear premium. The paper's fix is a theory-based
# correction that strips the fear out and leaves a **lower bound** that sits close to
# the true probability of a crash.
#
# This notebook is a hands-on tour of the repo. It follows one S&P 500 month-end from
# the cleaned option data all the way to a crash forecast, calling the exact functions
# the `doit` build uses, and ends on the extensions we built beyond the paper. No prior
# familiarity with the paper is assumed.
#
# ## How the correction works, in one paragraph
#
# The risk-neutral crash probability comes straight from option prices (via
# Breeden–Litzenberger) and needs no model, but it is a probability under the market's
# *risk-neutral* measure, which over-weights bad outcomes. To recover the *physical*
# (real-world) probability, the paper reweights by a power-utility investor's marginal
# value of a dollar ($\gamma = 2$), which removes the fear premium, and closes the one
# remaining unknown (how a single stock co-moves with the market) with
# **Fréchet–Hoeffding copula bounds**. The result is a lower and an upper bound on the
# true crash probability; under mild comonotonicity (stocks tend to crash *with* the
# market) the **lower bound is the tight, trustworthy one**. Every term in this
# paragraph is shown concretely below.

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
# | Exhibits | `exhibit_table1`, `exhibit_fig1/2/6` | the replicated tables and figures |
# | Extensions | `exhibit_etf_bounds`, `exhibit_industry_compare`, `exhibit_svb` | sector ETFs, proxy-vs-direct, the SVB case study |
#
# Table schemas are fixed centrally in `schema.py`, and every intermediate table is
# a tidy, documented parquet registered in the chartbook. We walk the engine stages
# below on one concrete smile, then close on the extensions.

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

AAPL_SECID = 101594  # Apple, from optionm_security_names, the firm we follow below
ONE_YEAR = 365       # the 1-year maturity: where Martin & Shi find the bound tightest
REPL_END = pd.Timestamp("2022-12-31")  # the paper's window; we stay inside it here

# %% [markdown]
# ## Walkthrough: from one smile to a forecast
#
# The steps below follow a single Apple month-end through the engine, from the raw
# volatility smile to a crash-probability forecast, and a check against the paper's
# published Table 1.

# %% [markdown]
# ### Step 1. Load the cleaned data
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
# ### Step 2. Inspect one volatility smile, Apple
#
# We follow a single, familiar name, **Apple (AAPL)**, through the engine. We take its
# **1-year (365-day)** smile on the most recent month-end *inside the paper's 1996–2022
# window* where both Apple and the S&P 500 have a clean surface (we need the market's
# surface in Step 5). One year is the horizon where Martin & Shi find the lower bound
# tightest, closest to the true crash probability, so it is the natural showcase. The
# upward tilt toward low moneyness is the **skew**: out-of-the-money puts (crash
# insurance) trade at higher implied volatility, and a single stock shows a more
# pronounced skew than the diversified index. That asymmetry is what the method extracts.

# %%
one_year = surface[
    (surface["days_to_maturity"] == ONE_YEAR) & (surface["date"] <= REPL_END)
]
# the latest paper-window month-end where both Apple and the market have a clean smile
common_dates = set(one_year.loc[one_year["secid"] == AAPL_SECID, "date"]) & set(
    one_year.loc[one_year["secid"] == schema.SPX_SECID, "date"]
)
date = max(common_dates)


def one_year_smile(secid):
    """The 1-year smile for one secid on the chosen date, sorted by moneyness."""
    return one_year[
        (one_year["secid"] == secid) & (one_year["date"] == date)
    ].sort_values("moneyness")


smile = one_year_smile(AAPL_SECID)
smile.head()

# %%
fig, ax = plt.subplots()
ax.plot(smile["moneyness"], smile["implied_vol"], marker="o", ms=3)
ax.axvline(1.0, color="grey", ls="--", lw=0.8, label="at-the-money")
ax.set_xlabel("moneyness  (strike / spot)")
ax.set_ylabel("implied volatility")
ax.set_title(f"Apple implied-vol smile, 1-year, {date.date()}")
ax.legend()
plt.show()

# %% [markdown]
# ### Step 3. Recover the risk-neutral density
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
ax.set_title(f"Risk-neutral CDF of Apple's 1-year return, {date.date()}")
for q in schema.THRESHOLDS_Q:
    ax.axvline(q, color="grey", ls="--", lw=0.7)
    ax.annotate(f"q={q}", (q, 0.02), rotation=90, va="bottom", fontsize=8)
plt.show()

# %% [markdown]
# ### Step 4. The risk-neutral crash probability ("crying wolf")
#
# Reading the CDF at each crash threshold $q$ (a gross return at or below $q$ is a
# crash of $1-q$) gives the risk-neutral crash probability. This is the number the
# paper argues *overstates* the true probability, it has not yet been corrected
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
# ### Step 5. Fear correction and the Fréchet–Hoeffding bounds
#
# `bounds.crash_bounds` combines stages A3 and A4: the power-utility fear correction
# ($\gamma = 2$, via `utility_correction.py`) and the Fréchet–Hoeffding bounds. Because
# Apple is *not* the market, the bounds do real work here, they bracket the true crash
# probability from below and above, closing the one unknown, how Apple co-moves with the
# market. That needs the **market's** distribution too, so we build the S&P 500's 1-year
# CDF for the same date and pass both. Notice the ordering: the fear-corrected
# **lower bound sits below the risk-neutral probability** from Step 4, the fear premium,
# removed, and below the upper bound.
#
# (The index is the special $i = m$ case: a security is comonotonic with itself, so its
# lower bound holds with *equality* and equals the market crash probability of the
# paper's Result 3, exactly how Figure 2's market line is computed.)

# %%
market_cdf = risk_neutral_cdf(one_year_smile(schema.SPX_SECID), rate)

pd.DataFrame(
    [
        dict(
            zip(
                ["threshold_q", "lower_bound", "risk_neutral", "upper_bound"],
                [q, *[round(x, 4) for x in crash_bounds(cdf, market_cdf, rate, q)]],
            )
        )
        for q in schema.THRESHOLDS_Q
    ]
)

# %% [markdown]
# ### Step 6. The full results table
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
# ### Step 7. Replication check, does the lower bound track realized crashes?
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
# ### Step 8. The picture
#
# The bar chart makes the takeaway visual: the realized crash frequency and the
# option-implied lower bound sit side by side, while the risk-neutral probability
# and (more so) the upper bound run well above both. This is the pattern Table 1
# reproduces across every threshold and horizon, the formal, tolerance-tested
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
plt.show()

# %% [markdown]
# ## The product: extensions beyond the paper
#
# The replication above is the foundation. The point of the project is what we build on
# top of it, the *same engine*, pointed at new questions. Three extensions live in the
# report and the chartbook:
#
# 1. **Sector-ETF crash bounds** (`exhibit_etf_bounds`), the machinery applied directly
#    to the eleven Select Sector SPDR ETFs (plus KRE), a cleaner test of the theory since
#    comonotonicity is more plausible for a diversified ETF than a single name.
# 2. **Proxy vs. direct** (`exhibit_industry_compare`), the paper measures an industry's
#    crash risk as the *average* of its constituents' bounds; we show that overstates the
#    diversified sector, which the direct ETF bound prices correctly.
# 3. **The SVB case study** (`exhibit_svb`), shown live below.
#
# ### Highlight: did the options market see SVB coming?
#
# We run the identical engine at **daily** frequency through the March 2023 collapse of
# Silicon Valley Bank, reading one event at three levels: the failed bank (SIVB), the
# regional-bank ETF (KRE), and broad financials (XLF). Because the outcome is known, the
# bank failed, the index did not, it is a clean test of whether the measure classifies
# the event as *contained* or *systemic*.

# %%
from pull_svb_daily import load_svb_surface, load_svb_spot, load_svb_zero
from exhibit_svb import build_figure_svb, compute_svb_bounds, svb_realized_table

svb_spot = load_svb_spot()
svb_bounds = compute_svb_bounds(load_svb_surface(), svb_spot, load_svb_zero())
build_figure_svb(svb_bounds)

# %% [markdown]
# The stress decays sharply across the three levels, SIVB's crash probability explodes
# to ~36% on 9 March (its last trading day, after which the surface simply ends), the
# regional-bank sector (KRE) peaks near 18%, and broad financials (XLF) reach only ~6%.
# The market priced the event as concentrated in the name and its sector, not systemic.
# And because the resolution is known, we can check the probabilities against what
# actually happened: the peak probabilities rank-order the realized drawdowns, and the
# 20% line separates the two that crashed from the one that did not.

# %%
svb_realized_table(svb_bounds, svb_spot)

# %% [markdown]
# ## Where to go next
#
# - **The report** (`reports/report.pdf`), the replicated Table 1–2 and Figures 1, 2, 6,
#   the extension exhibits above, and the full write-up.
# - **The chartbook** (`docs/`), every intermediate table and every figure, each with a
#   narrative page and its data dictionary.
# - **`dodo.py`**, the end-to-end build: `doit` reproduces every parquet, table, figure,
#   and this notebook from raw WRDS data.
