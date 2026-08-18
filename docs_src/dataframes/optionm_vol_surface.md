Raw OptionMetrics standardized volatility surface (monthly) for the pulled secids, before cleaning. Regenerate with `doit pull_optionmetrics`.

## Data Dictionary

- **secid**: `int64`, OptionMetrics security id (108105 = S&P 500 index).
- **date**: `datetime64[ns]`, last trading day of the month (surface observation date).
- **days**: `int64`, standardized maturity in calendar days ∈ {30, 91, 182, 365}.
- **cp_flag**: `str`, `C` (call) or `P` (put).
- **delta**: `float64`, option delta (the standardized surface's moneyness axis).
- **impl_volatility**: `float64`, Black-Scholes implied volatility at that (delta, maturity).
- **impl_strike**: `float64`, the strike implied by that delta/vol point.
- **dispersion**: `float64`, OptionMetrics surface goodness-of-fit; #17 keeps (0, 0.05).
