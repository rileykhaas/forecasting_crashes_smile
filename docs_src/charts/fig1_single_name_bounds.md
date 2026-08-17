## Description

Our replication of **Figure 1** in Martin & Shi (2025): the option-implied lower
and upper bounds on the probability that a single stock crashes by at least 20%
over a one-month horizon (`threshold_q = 0.80`, `horizon_months = 1`), plotted over
time for **Apple** and **AIG** across the paper's 1996–2022 sample.

For each name the shaded band spans the lower and upper bound, built by
`exhibit_fig1.py` from `results.parquet`.

## What it shows

The bounds vary sharply across firms and over time — the single-name signal the
paper's cross-sectional statistics (Table 1) average over. **AIG**'s crash risk
spikes toward ~50% during the 2008–09 financial crisis, exactly when the
uncorrected risk-neutral reading "cries wolf" loudest; **Apple**'s is elevated
during the early-2000s tech unwind and comparatively muted thereafter. The gap
between a name's lower and upper bound is the copula uncertainty about its
dependence on the market.

Regenerate with `doit fig1`.
