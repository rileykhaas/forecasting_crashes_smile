## Description

An **original extension** (issue #34): the paper's crash-probability bounds computed
directly on sector-ETF option surfaces. Per Select Sector SPDR ETF (11 sectors + KRE)
and the S&P 500 index, this table reports the mean lower bound, risk-neutral
probability, and upper bound against the realized 20% crash frequency, at the
12-month horizon (where sector crashes are observable often enough to compare).

Built by `exhibit_etf_bounds.py` (task `etf_bounds`) from `results.parquet`, selecting
the `sector_etf` secids from the OptionMetrics pull manifest plus `SPX_SECID`. One row
per ETF, with the index as the benchmark row.

The takeaways: for the **diversified broad sectors** the lower bound hugs the realized
frequency (financials 0.079 vs. 0.073; the index itself 0.055 vs. 0.068), while the
risk-neutral probability again runs two- to three-fold too high — the paper's "crying
wolf" result, reproduced directly at the sector level. The bound is more conservative
for the **concentrated, higher-beta** sleeves (energy, technology, regional banks),
consistent with comonotonicity binding tightest where diversification is greatest.

Lives in the gitignored `_output/`; regenerate with `doit etf_bounds`. The `_ext`
variant extends the sample through the latest data.

## Data Dictionary

- **ticker**: `str` — ETF ticker (XLB … XLY, KRE), or `SPX` for the index row.
- **secid**: `int64` — OptionMetrics security id.
- **mean_lower**: `float64` — mean lower bound `P^L` (20% crash, 12-month).
- **mean_rn**: `float64` — mean risk-neutral probability `P^*`.
- **mean_upper**: `float64` — mean upper bound `P^U`.
- **realized_freq**: `float64` — realized frequency of a 20% crash over 12 months.
- **n_obs**: `int64` — months with an observed 12-month outcome (fewer for the
  later-launched ETFs, XLRE from 2015 and XLC from 2018).
