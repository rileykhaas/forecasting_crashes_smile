## Description

An **original extension** (issue #34): a direct test of the proposal's core claim
that an average of individual crash probabilities is not the probability the *sector*
crashes. Built by `exhibit_industry_compare.py` (task `industry_compare`) from
`results.parquet` plus CRSP SIC codes.

For each Fama-French industry with a clean Select Sector SPDR counterpart
(`ff_industry.FF12_TO_ETF` — Finance/XLF, Energy/XLE, Utilities/XLU, Health/XLV,
Business Equip./XLK, Manufacturing/XLI), a small-multiple panel plots:

- **Proxy** (orange) — the equal-weighted mean lower bound of the constituents
  assigned to that FF12 industry (the paper's Figure-10 measure).
- **Direct** (blue) — the sector ETF's own lower bound (our extension).

`threshold_q = 0.80`, `horizon_months = 1`.

## What it shows

The proxy lies **above** the direct measure in every sector and at almost every date:
averaging individually risky names systematically overstates the diversified sector's
crash probability. **Health care** is the clearest case — biotech and single-drug
names keep the proxy elevated (~11%) while the diversified sector's own bound is a
quarter of that and near zero outside crises. The gap between the two lines is the
"proxy problem" the direct measure resolves. See the companion table
(`industry_tightness`) for the numeric gap and the comparison to realized frequencies.

Regenerate with `doit industry_compare`.
