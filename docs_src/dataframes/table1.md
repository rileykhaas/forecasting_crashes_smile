Replication of Martin & Shi (2025) Table 1, summary statistics of the bounds vs. realized crashes. Regenerate with `doit table1`.

## Data Dictionary

- **q**: `float64`, crash threshold (0.70 / 0.80 / 0.90).
- **measure**: `str`, `realized`, `lower bound`, `risk-neutral`, or `upper bound`.
- **horizon**: `int64`, forecast horizon τ ∈ {1, 3, 6, 12}.
- **block**: `str`, `firms` (across-firms / T) or `time` (across-time / N).
- **mean**: `float64`, mean of the block's averages.
- **sd**: `float64`, standard deviation of the block's averages.
