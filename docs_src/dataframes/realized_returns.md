## Description

The **realized forward returns** are the outcome side of the study: for each
formation date (the last trading day of month *t*), each firm, and each horizon
τ ∈ {1, 3, 6, 12} months, the gross return `R_{t→t+τ}` actually realized over the
next τ months. These are what the option-implied crash bounds are *tested*
against — the regression `I(R_{t→t+τ} ≤ q) = α + β·bound` compares the forecast
to this realized outcome.

Key properties, following Martin & Shi (2025) and issue #15:

- **Gross returns** (`0.80` = a 20% drop), matching the paper's crash-threshold
  convention `q`.
- **Delisting folded in.** Built from CRSP's CIZ `mthret`, which integrates the
  delisting return, so a bankruptcy/wipeout (e.g. SIVB, Lehman) shows up as a
  gross return near 0 rather than silently vanishing. The forward compounding
  uses a direct product (not a log-sum) specifically so those zeros survive.
- **Threshold-independent.** It stores the realized return itself, not a crash
  flag; the flag is derived per threshold later (results, task A5), so
  re-thresholding never recomputes returns.
- **Keyed by secid**, via the date-valid, best-score CRSP–OptionMetrics link, and
  scoped to the analysis universe (`optionm_pull_secids`) so it covers the ~1.2k
  names actually studied rather than all of CRSP.

Formation dates run from 1996-01 to the last month with a complete forward window
(longer horizons truncate earlier at the sample's end — an unbalanced panel, as
in the paper). Cleaned output; lives in the gitignored `_data/`; regenerate with
`doit build_realized_returns`.

## Data Dictionary

- **date**: `datetime64[ns]` — formation date (last trading day of month *t*).
- **secid**: `int64` — OptionMetrics security id.
- **horizon_months**: `int64` — forecast horizon τ ∈ {1, 3, 6, 12}.
- **realized_gross_return**: `float64` — `R_{t→t+τ}`, gross (0.80 = down 20%),
  with delisting returns integrated.
