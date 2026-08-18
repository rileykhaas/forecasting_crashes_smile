The zero curve interpolated to the four horizon maturities, per formation date. Regenerate with `doit clean_rates`.

## Data Dictionary

- **date**: `datetime64[ns]`, month-end formation date (matches clean_surface).
- **days_to_maturity**: `int64`, maturity in days ∈ {30, 91, 182, 365}.
- **zero_rate**: `float64`, zero-coupon rate (annualized, continuously compounded, %).
