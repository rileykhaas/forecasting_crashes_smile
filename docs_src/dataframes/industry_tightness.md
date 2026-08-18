## Description

An **original extension** (issue #34): the numeric "tightness" comparison behind the
proxy-vs-direct figure. Built by `exhibit_industry_compare.py` (task
`industry_compare`) from `results.parquet` plus CRSP SIC codes.

For each Fama-French industry with a clean Select Sector SPDR counterpart, one row
comparing, at the 12-month horizon:

- the **proxy** lower bound (equal-weighted mean of that industry's constituents' lower
  bounds — the paper's Figure-10 measure), against
- the **direct** sector-ETF lower bound (our extension), and
- the sector's **realized** 20% crash frequency.

The takeaways: the proxy exceeds the direct measure in **every** sector (by 3–7
percentage points), so averaging individually risky names overstates the diversified
sector's crash risk. The direct measure hugs the realized frequency for the broad
diversified sectors (financials 0.079 vs. 0.073; manufacturing 0.067 vs. 0.066) and is
more conservative for the higher-beta, less internally diversified sleeves (energy,
technology) — consistent with a lower bound that binds tightest where market
comonotonicity is most plausible.

Lives in the gitignored `_output/`; regenerate with `doit industry_compare`. The
`_ext` variant extends the sample through the latest data.

## Data Dictionary

- **ff_industry**: `str` — FF12 industry code (Money, Enrgy, Utils, Hlth, BusEq, Manuf).
- **sector**: `str` — short industry label.
- **ticker**: `str` — the matched Select Sector SPDR ETF.
- **proxy_lower**: `float64` — mean equal-weighted constituent lower bound (Figure-10 proxy).
- **direct_lower**: `float64` — mean sector-ETF lower bound (direct measure).
- **realized_freq**: `float64` — realized frequency of a 20% crash over 12 months.
- **proxy_gap**: `float64` — the proxy's distance from realized (`proxy_lower − realized_freq`).
- **direct_gap**: `float64` — the direct measure's distance from realized (`direct_lower − realized_freq`).
