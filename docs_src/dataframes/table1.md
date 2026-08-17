## Description

Our **replication of Table 1** in Martin & Shi (2025): summary statistics of the
realized crash frequency, the lower/upper option-implied bounds, and the
risk-neutral crash probability, over the paper's window (formation months
January 1996 – December 2022, T = 324) for the S&P 500 constituent cross-section.

Built by `exhibit_table1.py` (task `table1`) from `results.parquet`, restricted
to constituent member-months (inner-joined to `sp500_secid_universe`, which also
drops the index and the extension ETFs). For each threshold q ∈ {0.7, 0.8, 0.9}
and horizon τ ∈ {1, 3, 6, 12}, two blocks are reported, exactly as the paper:

- **averaged across firms** — each month, average across firms → T values; report
  their mean and s.d.
- **averaged across time** — each firm, average across months → N values; report
  their mean and s.d.

The takeaway the table reproduces: the **lower bound hugs the realized crash
frequency**, while the risk-neutral probability and (more so) the upper bound
overstate crash risk. A tolerance test (`test_exhibit_table1.py`) pins each mean
cell to the paper's published number.

Long-format (one row per q × measure × horizon × block); lives in the gitignored
`_output/`; regenerate with `doit table1`.

## Data Dictionary

- **q**: `float64` — crash threshold (0.70 / 0.80 / 0.90).
- **measure**: `str` — `realized`, `lower bound`, `risk-neutral`, or `upper bound`.
- **horizon**: `int64` — forecast horizon τ ∈ {1, 3, 6, 12}.
- **block**: `str` — `firms` (across-firms / T) or `time` (across-time / N).
- **mean**: `float64` — mean of the block's averages.
- **sd**: `float64` — standard deviation of the block's averages.
