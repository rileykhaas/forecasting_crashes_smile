Replication of Table 2, calibration regressions (α, β, R²) of realized crashes on each measure. Regenerate with `doit table2`.

## Data Dictionary

- **q**: `float64`, crash threshold (0.70 / 0.80 / 0.90).
- **measure**: `str`, `lower bound`, `risk-neutral`, or `upper bound`.
- **horizon**: `int64`, forecast horizon τ ∈ {1, 3, 6, 12}.
- **alpha**: **beta**, **r2**: `float64`, regression intercept, slope, R².
- **alpha_se_cl**: **beta_se_cl**: `float64`, two-way clustered standard errors.
- **alpha_se_bs**: **beta_se_bs**: `float64`, block-bootstrap standard errors.

Long-format; lives in the gitignored `_output/`; regenerate with `doit table2`.
