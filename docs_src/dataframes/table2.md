## Description

Our replication of **Table 2** in Martin & Shi (2025): the regression calibration
tests over 1996–2022. For each crash size q ∈ {0.7, 0.8, 0.9}, horizon
τ ∈ {1, 3, 6, 12}, and right-hand-side measure X (the lower bound, the risk-neutral
probability, or the upper bound), we run the pooled OLS over S&P 500 constituent
member-months (eq. 9 of the paper):

`I(R_{i,t→t+τ} ≤ q) = α + β·X_{it}(τ, q) + ε`.

A measure that equals the true crash probability gives α = 0 and β = 1, so the test
is **β = 1**, not β = 0.

Built by `exhibit_table2.py` from `results.parquet`. Each coefficient carries two
standard errors, exactly as the paper:

- **Two-way clustered** (firm and month), following Thompson (2011) — reported in
  parentheses in the LaTeX table (`table2.tex`).
- **Block bootstrap**, following Martin & Wagner (2019) Appendix B: overlapping
  blocks of consecutive months with block length equal to the forecast horizon τ
  (to preserve the overlapping-window serial correlation), 2500 samples — reported
  in square brackets.

## What it shows

The **lower bound calibrates at β ≈ 1** across crash sizes and horizons, while the
risk-neutral probability (β ≈ 0.7) and the upper bound (β ≈ 0.5) are badly
miscalibrated — the formal counterpart of Table 1's visual message. Intercepts are
≈ 0 and R² is a few percent (crashes are rare binary events).

## Data Dictionary

- **q**: `float64` — crash threshold (0.70 / 0.80 / 0.90).
- **measure**: `str` — `lower bound`, `risk-neutral`, or `upper bound`.
- **horizon**: `int64` — forecast horizon τ ∈ {1, 3, 6, 12}.
- **alpha**, **beta**, **r2**: `float64` — regression intercept, slope, R².
- **alpha_se_cl**, **beta_se_cl**: `float64` — two-way clustered standard errors.
- **alpha_se_bs**, **beta_se_bs**: `float64` — block-bootstrap standard errors.

Long-format; lives in the gitignored `_output/`; regenerate with `doit table2`.
