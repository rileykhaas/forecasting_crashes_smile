## Description

An **original extension** (issue #34): the paper's single-name crash-probability
machinery applied directly to the eleven Select Sector SPDR ETFs plus KRE (regional
banks). Built by `exhibit_etf_bounds.py` (task `etf_bounds`) from `results.parquet` —
the ETFs are priced by the same engine as the stocks once their surfaces are
spot-matched in cleaning and routed through the pipeline (`pull_CRSP_stock` now
force-includes their permnos; `clean_surface` attaches their CRSP spot).

A 3×4 small-multiple grid: each panel is one sector's **direct** lower-bound
one-month 20% crash probability (blue), with the S&P 500 index's own crash
probability (grey, the `i = m` bound) overlaid as the benchmark. `threshold_q = 0.80`,
`horizon_months = 1`.

## What it shows

The direct sector measure — as opposed to the paper's average-of-constituent-bounds
proxy — behaves exactly as economic intuition demands: **technology** (XLK) spikes
through the 2000–02 dot-com unwind, **financials** (XLF) and **regional banks** (KRE)
in 2008–09, **energy** (XLE) in the 2014–16 oil collapse, and KRE again at the
2023 SVB stress. **Defensive** sectors (staples XLP, utilities XLU, health care XLV)
stay quiet and below the index throughout. This is a clean test of the theory, not a
weakening of it: comonotonicity with the market — the condition that makes the lower
bound tight — is most plausible for a diversified ETF.

Regenerate with `doit etf_bounds`.
