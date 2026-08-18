Engine output: lower/risk-neutral/upper crash bounds and the realized outcome, per (date, secid, horizon, threshold), every exhibit reads from this. Regenerate with `doit pipeline`.

## Data Dictionary

- **date**: `datetime64[ns]`, formation date (last trading day of month *t*).
- **secid**: `int64`, OptionMetrics security id (108105 = S&P 500 index).
- **horizon_months**: `int64`, forecast horizon τ ∈ {1, 3, 6, 12}.
- **threshold_q**: `float64`, crash threshold q ∈ {0.70, 0.80, 0.90}.
- **bound_lower**: `float64`, lower bound `P^L` on `P[R ≤ q]`.
- **prob_riskneutral**: `float64`, risk-neutral `P*[R ≤ q]`.
- **bound_upper**: `float64`, upper bound `P^U` on `P[R ≤ q]`.
- **realized_gross_return**: `float64`, realized `R_{t→t+τ}` (0.80 = down 20%).
- **realized_flag**: `Int64`, `1{R ≤ q}`, `<NA>` where no realized outcome yet.
