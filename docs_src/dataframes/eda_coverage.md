Per-year coverage of the underlying option/return panel. Regenerate with `doit eda`.

## Data Dictionary

- **year**: `int64`, calendar year of the formation (surface) date.
- **n_names**: `int64`, distinct constituent secids with a surface that year.
- **n_firm_months**: `int64`, distinct (date, secid) firm-months that year.
- **n_quotes**: `int64`, option quotes (rows of the cleaned surface) that year.
- **quotes_per_fm**: `float64`, median number of quotes per firm-month.
- **median_iv**: `float64`, median implied volatility across that year's quotes.
- **crash_freq**: `float64`, realized frequency of a 20% crash (gross return ≤ 0.80)
  over the next 12 months, among that year's formation months.
