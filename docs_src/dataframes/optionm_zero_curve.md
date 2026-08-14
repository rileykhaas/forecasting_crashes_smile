## Description

The **raw OptionMetrics zero-coupon yield curve**: the risk-free term structure
OptionMetrics publishes, one rate per maturity (in days) per date. These are the
risk-free rates Martin & Shi (2025) use — to convert implied volatilities into
"clean" European option prices and to form gross returns (Appendix D).

This is the **raw pull** (`pull_optionmetrics.py`, issue #16), taken over the full
sample window. Per-date interpolation to the exact horizon maturities happens
downstream in `rates.py` (issue #17), which produces the analysis-ready
`rates.parquet`.

The table is small; it is pulled whole. Like all raw pulls it lives in the
gitignored `_data/` — regenerate with `doit pull:optionmetrics`.

## Data Dictionary

- **date**: `datetime64[ns]` — observation date of the curve.
- **days**: `float64` — maturity in calendar days.
- **rate**: `float64` — continuously-compounded zero-coupon rate at that maturity.
