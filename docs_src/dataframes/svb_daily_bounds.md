## Description

An **original extension** (issue #31): daily option-implied crash bounds for the
Silicon Valley Bank case study. Built by `exhibit_svb.py` (task `svb_case_study`) by
running the monthly engine (rnd → fear correction → Fréchet–Hoeffding bounds) day by
day on the case-study surfaces pulled by `pull_svb_daily`.

One row per (date, secid, horizon, threshold) for SIVB, KRE, XLF, and the S&P 500 over
Feb–Mar 2023 — the same schema as the monthly `results.parquet`, but daily and with
no realized-outcome columns (the case study is forward-looking). SIVB's rows end
2023-03-09, the day it collapsed ~60% and last traded as a going concern; its options
were halted with the stock on 2023-03-10.

The takeaway the series carries: SIVB's risk-neutral crash probability explodes to 36%
at the collapse, then the sector (KRE, 17.6% peak) and broad financials (XLF, 6.1%)
register progressively less stress — the market pricing the event as contained rather
than systemic.

Lives in the gitignored `_output/`; regenerate with `doit svb_case_study`.

## Data Dictionary

- **date**: `datetime64[ns]` — trading day.
- **secid**: `int64` — OptionMetrics security id (SIVB 110169, KRE 127104, XLF 110012, SPX 108105).
- **horizon_months**: `int64` — forecast horizon (1/3/6/12; the figure uses 1 = 30-day).
- **threshold_q**: `float64` — crash threshold (0.70/0.80/0.90; the figure uses 0.80).
- **bound_lower**: `float64` — option-implied lower bound `P^L`.
- **prob_riskneutral**: `float64` — risk-neutral crash probability `P^*`.
- **bound_upper**: `float64` — option-implied upper bound `P^U`.
- **realized_gross_return** / **realized_flag**: NA (forward-looking case study).
