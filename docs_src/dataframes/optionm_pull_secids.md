Manifest of the secids pulled, tagged `index` / `constituent` / `sector_etf`. Regenerate with `doit pull_optionmetrics`.

## Data Dictionary

- **secid**: `int64`, OptionMetrics security id pulled.
- **source**: `str`, `index`, `constituent`, or `sector_etf`.
- **ticker**: `str`, ETF ticker for `sector_etf` rows; null otherwise.
