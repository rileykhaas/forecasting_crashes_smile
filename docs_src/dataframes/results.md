## Description

The **engine output**: one row per (date, secid, horizon, threshold) with the
option-implied crash-probability bounds of Martin & Shi (2025), Result 3 — the
lower bound `P^L`, the risk-neutral probability `P*`, and the upper bound `P^U` —
alongside the realized forward return and the realized crash flag it is tested
against.

Built by `run_pipeline.py` (task `pipeline`): for each (date, maturity) it
recovers the risk-neutral CDF from the cleaned smile (`rnd.py`), applies the
power-utility fear correction and the Fréchet–Hoeffding bounds
(`utility_correction.py`, `bounds.py`), then joins the realized gross return.

Key properties:

- **Includes the S&P 500 index itself** (secid 108105), the `i = m` case of
  Result 3 where the lower bound holds with equality (eq. 7) — the series behind
  Figure 2 and the γ calibration. The firm exhibits (Table 1) exclude it.
- **Bound ordering** `P^L ≤ P* ≤ P^U` holds on every row (checked at write time,
  `schema.check_bound_ordering`).
- **`realized_flag`** is `1{realized_gross_return ≤ threshold_q}`, left `<NA>`
  for recent formation dates whose forward window has not closed.

Engine output; lives in the gitignored `_output/`; regenerate with
`doit pipeline`.

## Data Dictionary

- **date**: `datetime64[ns]` — formation date (last trading day of month *t*).
- **secid**: `int64` — OptionMetrics security id (108105 = S&P 500 index).
- **horizon_months**: `int64` — forecast horizon τ ∈ {1, 3, 6, 12}.
- **threshold_q**: `float64` — crash threshold q ∈ {0.70, 0.80, 0.90}.
- **bound_lower**: `float64` — lower bound `P^L` on `P[R ≤ q]`.
- **prob_riskneutral**: `float64` — risk-neutral `P*[R ≤ q]`.
- **bound_upper**: `float64` — upper bound `P^U` on `P[R ≤ q]`.
- **realized_gross_return**: `float64` — realized `R_{t→t+τ}` (0.80 = down 20%).
- **realized_flag**: `Int64` — `1{R ≤ q}`, `<NA>` where no realized outcome yet.
