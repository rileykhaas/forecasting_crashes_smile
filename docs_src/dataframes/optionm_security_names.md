## Description

The **OptionMetrics security name history** (`secnmd`) for every secid in the pull
universe. Each row is one name spell — the ticker, issuer, and identifiers that
were in effect from `effect_date` onward — so a security that changed ticker over
the 1996–2025 sample (renames, ticker reuse) appears as multiple rows.

Two uses in this project:

1. **ETF ticker resolution.** The extension ETFs (Select Sector SPDRs + KRE) are
   not S&P 500 constituents and have no CRSP link, so their secids are resolved
   from tickers here. Because `secnmd` carries `effect_date`, resolution picks the
   secid whose *most recent* name spell holds the ticker — the security that
   currently trades under it. (This is why KRE resolves to the live ETF and not an
   older, unrelated security that once used the ticker.)
2. **As-of-date labels.** A `(secid, date)` panel row can be labelled with the
   ticker/issuer active in that month via a `merge_asof` on `effect_date` —
   historically correct, unlike a single "current ticker" snapshot.

Raw pull (`pull_optionmetrics.py`, issue #16); lives in the gitignored `_data/`.

## Data Dictionary

- **secid**: `int64` — OptionMetrics security id.
- **ticker**: `str` — ticker symbol in effect for this name spell.
- **issuer**: `str` — issuing-company description.
- **issue**: `str` — issue description.
- **cusip**: `str` — CUSIP for this spell.
- **class**: `str` — share-class designator.
- **sic**: `str` — SIC industry code.
- **effect_date**: `datetime64[ns]` — first date this name spell is in effect.
