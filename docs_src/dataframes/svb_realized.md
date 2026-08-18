## Description

An **original extension** (issue #31): the known-resolution table that closes the
loop on the SVB case study — the option-implied crash probability against what
actually happened. Built by `exhibit_svb.py` (task `svb_case_study`).

One row per asset (SIVB, KRE, XLF): the peak risk-neutral and lower-bound 20% crash
probability during Feb–Mar 2023, and the realized drawdown from the pre-collapse close
(8 March) to the March trough, with a 20%-crash flag.

The takeaway: the peak probabilities (36% / 18% / 6%) rank-order the realized
drawdowns (−60% / −27% / −11%), and the 20% threshold cleanly separates the two that
crashed (SIVB, delisted; KRE) from the one that did not (XLF). The measure classified
the name, its sector, and the system correctly. (SIVB was closed by regulators on 10
March and its equity effectively wiped, so its −60% understates the true loss.)

Lives in the gitignored `_output/`; regenerate with `doit svb_case_study`.

## Data Dictionary

- **ticker**: `str` — SIVB, KRE, or XLF.
- **level**: `str` — name / sector / systemic.
- **peak_pstar**: `float64` — peak risk-neutral 20% crash probability during the episode.
- **peak_lower**: `float64` — the lower bound at that peak.
- **peak_date**: `datetime64[ns]` — the date of the peak.
- **realized_drawdown**: `float64` — return from the 8 March close to the March trough.
- **crashed**: `bool` — whether the drawdown breached −20%.
