The cleaned volatility surface (Appendix-D filters, CRSP spot attached), the engine's input. Regenerate with `doit clean_surface`.

## Data Dictionary

- **date**: `datetime64[ns]`, last trading day of the month (formation date).
- **secid**: `int64`, OptionMetrics security id (108105 = S&P 500 index).
- **days_to_maturity**: `int64`, standardized maturity in days ∈ {30, 91, 182, 365}.
- **moneyness**: `float64`, `impl_strike / spot_price` (K/S).
- **implied_vol**: `float64`, Black-Scholes implied volatility at that point.
- **spot_price**: `float64`, CRSP spot (S); constant within a (date, secid).
- **cp_flag**: `string`, `P` (put) or `C` (call); the engine keeps the OTM side.
