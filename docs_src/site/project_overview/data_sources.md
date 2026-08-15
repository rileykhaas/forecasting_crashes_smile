# Data Sources

## Overview

**All raw pulls and cleaning are complete.** The CRSP and OptionMetrics data
behind the firm-month panel has been fetched from WRDS and cleaned into the tidy
tables the analysis consumes. Everything regenerates end-to-end from WRDS via
`doit`; raw pulls cache to `DATA_DIR` (`_data/`, gitignored) and are never
committed.

The paper studies S&P 500 firms over January 1996 – December 2022; our build
extends the panel to the most recent data available (through Aug 2025) — see the
Methodology page for how membership is extended past the CRSP vintage.

## Datasets

| Source | Table | Used for |
|--------|-------|----------|
| OptionMetrics | `vsurfd` (volatility surface) | Risk-neutral probabilities and bounds — the core input (the "smile") |
| OptionMetrics | `zerocd` (zero-coupon curve) | Risk-free discounting in the bound formulas |
| OptionMetrics | `secnmd` (security name history) | secid lookup / labels — stocks and the sector ETFs |
| CRSP | `msf_v2` (monthly stock, CIZ 2.0) | Realized returns and crash events (delisting folded into `mthret` — captures SVB); prices, volume, shares |
| CRSP | `msp500list` (S&P 500 constituents) | Sample selection by month |
| CRSP | `msix` | S&P 500 index level (`spindx`) — the index "spot" |
| WRDS | `wrdsapps_link_crsp_optionm.opcrsphist` | Joining option data (`secid`) to CRSP returns (`permno`) |

Notes:
- **Financial firms are retained** — the universe is driven purely by S&P 500
  membership, with no industry screen (central to the SVB extension).
- **Option filtering** is largely handled upstream by OptionMetrics' standardized
  Volatility Surface; the paper's Appendix-D filters + flat extrapolation are
  applied in cleaning (see Methodology).
- Raw data is proprietary (WRDS subscription) and must not be committed to git.

## Pipeline

Pulls → cleaned / derived tables, all wired in `doit`:

- **Pulls** (`pull_crsp_stock`, `pull_sp500_constituents`, `pull_crsp_optionm_link`,
  `pull_optionmetrics`) hit WRDS and cache parquet to `_data/`; each `pull_*` has a
  matching `load_*` that reads the cache back without touching the network.
- **Cleans / builds**: `clean_surface`, `clean_rates` (Slice 1, OptionMetrics);
  `build_secid_universe`, `build_realized_returns` (Slice 2, CRSP).
- Every cleaned table is registered in this chartbook (see the Dataframes list).
