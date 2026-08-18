Raw OptionMetrics zero-coupon yield curve, before interpolation to the horizon maturities. Regenerate with `doit pull_optionmetrics`.

## Data Dictionary

- **date**: `datetime64[ns]`, observation date of the curve.
- **days**: `float64`, maturity in calendar days.
- **rate**: `float64`, continuously-compounded zero-coupon rate at that maturity.
