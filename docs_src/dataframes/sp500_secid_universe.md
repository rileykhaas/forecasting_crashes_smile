## Description

The month-end **S&P 500 constituent secid universe** is the firm universe on
which every crash-probability bound in this project is computed. It answers, for
the last NYSE trading day of each month, "which firms were S&P 500 index members,
and what is each one's OptionMetrics `secid`?"

It is built in two steps (see `src/sp500_secid_universe.py`):

1. **Membership** — index-membership spells are pulled from `crsp.msp500list`
   (`pull_sp500.py`) and expanded onto the last trading day of each month
   (NYSE calendar via `pandas-market-calendars`). A permno is a member on a
   formation date when `start <= date <= ending`.
2. **Linkage** — the WRDS CRSP–OptionMetrics link table
   (`wrdsapps_link_crsp_optionm.opcrsphist`, via `pull_link.py`) attaches the
   OptionMetrics `secid`, choosing the best-scoring (`score = 1`) match valid on
   that date. Members with no valid option link are kept with a null `secid`.

This mirrors the sample construction in Martin & Shi (2025), Section 2: "the last
trading day of each month t … all firms that are S&P 500 constituents during
month t." Financial firms are **not** dropped.

**Date-extension note.** `crsp.msp500list` marks names still in the index at the
last CRSP update with a common `ending` sentinel (the data vintage, currently
`2024-12-31`). To extend the panel past that vintage, current members are frozen
forward to `END_DATE` and every such row is flagged `carried_forward = True`. This
is a deliberate approximation (index add/deletes over the frozen tail are ignored)
and is off in paper-exact replication. See the Data Sources page for the full
rationale.

## Data Dictionary

- **date**: `datetime64[ns]` — last NYSE trading day of the month (the formation
  date on which membership is evaluated).
- **permno**: `int64` — CRSP permanent security identifier of an S&P 500 member
  on `date`.
- **secid**: `Int64` (nullable) — OptionMetrics security id linked to the permno;
  null when the member has no valid CRSP–OptionMetrics link that month.
- **score**: `Int64` (nullable) — WRDS link match quality (1 = best); null when
  `secid` is null.
- **carried_forward**: `bool` — True when the row falls past the CRSP constituent
  vintage and its membership was frozen from the last known date; always False in
  paper-exact replication.
