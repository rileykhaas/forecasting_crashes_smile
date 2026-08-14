## Description

The **raw OptionMetrics volatility surface** is the option-implied "smile" from
which every crash-probability bound is computed. For the last trading day of each
month, it holds the standardized IvyDB surface — Black-Scholes implied volatilities
by strike and delta — for the S&P 500 index (`secid` 108105), all S&P 500
constituents (from the #14 universe), and the extension ETFs (the 11 Select Sector
SPDRs + KRE).

Following Martin & Shi (2025), the surface is taken at the four standardized
maturities that match the paper's forecast horizons — **30, 91, 182, 365 days**
(1, 3, 6, 12 months). Within each maturity slice the *full* smile is kept (all
deltas, both calls and puts), because the bounds integrate across strikes.

This table is the **raw pull** (`pull_optionmetrics.py`, issue #16): no quality
filtering is applied here. The Appendix-D filters (CRSP spot exists; strike > 0;
`dispersion` in (0, 0.05); >10 strikes per firm-month-maturity), linear
interpolation, and flat extrapolation happen downstream in `clean_surface.py`
(issue #17), which produces the analysis-ready `clean_surface.parquet`.

The underlying parquet is large (tens of millions of rows) and, like all raw
pulls, lives in the gitignored `_data/` — regenerate it with
`doit pull:optionmetrics`.

## Data Dictionary

- **secid**: `int64` — OptionMetrics security id (108105 = S&P 500 index).
- **date**: `datetime64[ns]` — last trading day of the month (surface observation date).
- **days**: `int64` — standardized maturity in calendar days ∈ {30, 91, 182, 365}.
- **cp_flag**: `str` — `C` (call) or `P` (put).
- **delta**: `float64` — option delta (the standardized surface's moneyness axis).
- **impl_volatility**: `float64` — Black-Scholes implied volatility at that (delta, maturity).
- **impl_strike**: `float64` — the strike implied by that delta/vol point.
- **dispersion**: `float64` — OptionMetrics surface goodness-of-fit; #17 keeps (0, 0.05).
