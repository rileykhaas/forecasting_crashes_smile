Sector-ETF mean crash bounds vs. realized frequency. Regenerate with `doit etf_bounds`.

## Data Dictionary

- **ticker**: `str`, ETF ticker (XLB … XLY, KRE), or `SPX` for the index row.
- **secid**: `int64`, OptionMetrics security id.
- **mean_lower**: `float64`, mean lower bound `P^L` (20% crash, 12-month).
- **mean_rn**: `float64`, mean risk-neutral probability `P^*`.
- **mean_upper**: `float64`, mean upper bound `P^U`.
- **realized_freq**: `float64`, realized frequency of a 20% crash over 12 months.
- **n_obs**: `int64`, months with an observed 12-month outcome (fewer for the
  later-launched ETFs, XLRE from 2015 and XLC from 2018).
