Daily crash bounds for SIVB/KRE/XLF/SPX through the March-2023 SVB collapse. Regenerate with `doit svb_case_study`.

## Data Dictionary

- **date**: `datetime64[ns]`, trading day.
- **secid**: `int64`, OptionMetrics security id (SIVB 110169, KRE 127104, XLF 110012, SPX 108105).
- **horizon_months**: `int64`, forecast horizon (1/3/6/12; the figure uses 1 = 30-day).
- **threshold_q**: `float64`, crash threshold (0.70/0.80/0.90; the figure uses 0.80).
- **bound_lower**: `float64`, option-implied lower bound `P^L`.
- **prob_riskneutral**: `float64`, risk-neutral crash probability `P^*`.
- **bound_upper**: `float64`, option-implied upper bound `P^U`.
- **realized_gross_return** / **realized_flag**: NA (forward-looking case study).
