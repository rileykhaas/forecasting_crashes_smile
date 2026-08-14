## Description

The **OptionMetrics pull universe** — the exact set of secids the volatility
surface was pulled for, each tagged by `source`. It is the bridge between the
replication and the extension: it records that the surface covers the S&P 500
index, its month-end constituents, *and* the extension ETFs, so downstream code
can cleanly select one group or the other.

- `index` — the S&P 500 index (`secid` 108105), the "market."
- `constituent` — S&P 500 member secids from the #14 universe (the replication set).
- `sector_etf` — the 11 Select Sector SPDR ETFs plus KRE (SPDR S&P Regional
  Banking), added for the sector-ETF and SVB extensions. These carry a `ticker`.

Built in `pull_optionmetrics.py` (issue #16) as the union of
`get_universe_secids()` (#14) + `SPX_SECID` + the `secnmd`-resolved ETF secids.
Lives in the gitignored `_data/`.

## Data Dictionary

- **secid**: `int64` — OptionMetrics security id pulled.
- **source**: `str` — `index`, `constituent`, or `sector_etf`.
- **ticker**: `str` — ETF ticker for `sector_etf` rows; null otherwise.
