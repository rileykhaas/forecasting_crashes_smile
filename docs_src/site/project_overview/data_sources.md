# Data Sources

## Overview

We replicate Martin & Shi (2025), "Forecasting Crashes with a Smile," and extend
the sample beyond the paper's window. The paper studies firms in the S&P 500
index over January 1996 – December 2022; our build pushes the panel forward to
the most recent data available (see the vintage note below). All raw pulls are
written to `DATA_DIR` (`_data/`, gitignored) and can be regenerated from WRDS via
`doit`.

## Datasets

| Dataset | Source (WRDS table) | Frequency | Description |
|---------|---------------------|-----------|-------------|
| S&P 500 constituents | CRSP (`crsp.msp500list`) | Membership spells | One row per index-membership spell (`permno`, `start`, `ending`); defines the firm universe. |
| CRSP–OptionMetrics link | `wrdsapps_link_crsp_optionm.opcrsphist` | Linkage spells | Maps CRSP `permno` ↔ OptionMetrics `secid` over `[sdate, edate]` with a match `score` (1 = best). |
| Volatility surfaces | OptionMetrics | Monthly (month-end) | Standardized implied-vol surfaces for the S&P 500 index (`secid` 108105) and each constituent. |
| Zero-coupon rates | OptionMetrics | Monthly | Risk-free curve used to discount / form gross returns. |
| Stock prices, returns, volume, shares | CRSP (`crspm.msf_v2`, CIZ 2.0) | Monthly | Firm-month panel inputs; delisting returns are built into `mthret`. |

Notes:
- **Financial firms are retained.** Unlike much of the literature, the paper does
  not drop financials, and neither do we — the universe is driven purely by index
  membership, with no industry screen.
- **Option filtering** is largely handled upstream by OptionMetrics' standardized
  Volatility Surface product; outside the range of observed strikes the smile is
  extrapolated flat (Appendix D of the paper).

## Data Pipeline

- **Pulls** (`pull_sp500.py`, `pull_link.py`, plus the OptionMetrics/CRSP-stock
  slices) hit WRDS and cache parquet to `_data/`. Each `pull_*` has a matching
  `load_*` that reads the cache back without touching the network.
- **`sp500_secid_universe.py`** expands index membership onto the last NYSE
  trading day of each month (via `pandas-market-calendars`) and attaches the
  best-score `secid`, producing `sp500_secid_universe.parquet`
  (`[date, permno, secid, score, carried_forward]`). This is the secid list the
  OptionMetrics pull iterates over and the (date, permno, secid) linkage used to
  attach realized returns.
- Run order: `doit pull:sp500_constituents pull:crsp_optionm_link` →
  `doit build_sp500_secid_universe`.

## Constituent vintage cap and the forward-freeze assumption

`crsp.msp500list` marks names still in the index at the **last CRSP update** with
a common `ending` sentinel — the data vintage. In the current pull that vintage
is **2024-12-31** (503 names end on exactly that date, versus genuine historical
deletions which carry their own earlier `ending`).

To extend the firm-month panel past the vintage, `build_sp500_secid_universe`
**freezes current members forward**: any spell ending at the vintage cap is held
in the index through the end of the month-end grid (`END_DATE`, currently
2025-08-31 → last session 2025-08-29), while spells that ended earlier are left
deleted. This carried the panel from 348 months (through Dec 2024) to 356 months
(through Aug 2025), adding 8 frozen months.

This is a **deliberate approximation**, not sourced membership:

- The ~20–25 S&P 500 add/deletes per year are ignored over the frozen tail, so a
  small, growing fraction of names is misclassified the further past the vintage
  one goes (roughly ~3% by Aug 2025; near-zero in Jan 2025).
- It is **not** look-ahead or survivorship bias — it uses *stale* membership, not
  future information; delisted names drop out naturally when CRSP/OptionMetrics
  data is missing.
- Every frozen row is flagged `carried_forward = True`, so the 2025 tail can be
  isolated or dropped in any robustness check, and the pure-CRSP panel recovered.

The behaviour is **off by default** (`carry_forward_current=False`) and enabled
only in the pipeline `__main__`. For paper-exact replication set
`END_DATE=2022-12-31`; no freezing occurs when `END_DATE ≤` the vintage cap. When
CRSP refreshes `msp500list`, re-running the two pulls plus the build extends the
real (unfrozen) panel automatically — no code change needed.
