## Description

Our own **per-year coverage summary** of the underlying option/return panel
(issue #33) — the exploratory counterpart to the replication tables, describing the
*raw inputs* rather than the *derived* crash-probability bounds.

Built by `exhibit_eda.py` (task `eda`) from `clean_surface.parquet` and
`realized_returns.parquet`, restricted to S&P 500 constituent member-months
(inner-joined to `sp500_secid_universe`, which also drops the index and the extension
ETFs), so it profiles exactly the sample the replication runs on. One row per calendar
year.

The takeaways: coverage is **broad and continuous** (~500 constituent names every
year, at a stable ~120–133 quotes per firm-month), median implied volatility traces
the volatility cycle (peaks in 2000, 2008, 2020), and the realized 12-month 20% crash
frequency is **low on average but strongly time-varying** — above 0.45 for surfaces
formed in 2007–2008, near zero in calm years. The bounds rest on a consistent panel,
and the event they forecast is genuinely rare.

Lives in the gitignored `_output/`; regenerate with `doit eda`. The `_ext` variant
extends the sample through the latest data.

## Data Dictionary

- **year**: `int64` — calendar year of the formation (surface) date.
- **n_names**: `int64` — distinct constituent secids with a surface that year.
- **n_firm_months**: `int64` — distinct (date, secid) firm-months that year.
- **n_quotes**: `int64` — option quotes (rows of the cleaned surface) that year.
- **quotes_per_fm**: `float64` — median number of quotes per firm-month.
- **median_iv**: `float64` — median implied volatility across that year's quotes.
- **crash_freq**: `float64` — realized frequency of a 20% crash (gross return ≤ 0.80)
  over the next 12 months, among that year's formation months.
