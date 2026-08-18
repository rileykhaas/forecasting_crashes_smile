CRSP forward gross returns per (secid, horizon), with delisting returns integrated. Regenerate with `doit build_realized_returns`.

## Data Dictionary

- **date**: `datetime64[ns]`, formation date (last trading day of month *t*).
- **secid**: `int64`, OptionMetrics security id.
- **horizon_months**: `int64`, forecast horizon τ ∈ {1, 3, 6, 12}.
- **realized_gross_return**: `float64`, `R_{t→t+τ}`, gross (0.80 = down 20%),
  with delisting returns integrated.
