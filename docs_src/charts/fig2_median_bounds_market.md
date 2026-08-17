## Description

Our replication of **Figure 2** in Martin & Shi (2025): the time series of the
**cross-sectional median** across S&P 500 constituents of the lower and upper
option-implied bounds on the probability of a 20% crash over one month
(`threshold_q = 0.80`, `horizon_months = 1`), together with the **crash probability
of the S&P 500 index itself** — the `i = m` lower bound (the market crash
probability of Martin 2017), for `secid = 108105`. Paper window 1996–2022.

Built by `exhibit_fig2.py` from `results.parquet`: the medians are taken over
constituent member-months (inner-joined to `sp500_secid_universe`, which excludes
the index and the extension ETFs); the market line is the index's own lower bound.

## What it shows

The median constituent bounds spike in every crisis — sharply in 2008–09, again in
2020 — but the **market** crash probability (grey) is consistently **lower and
smoother** than the typical constituent's. The diversified index is less
crash-prone than the individual stocks that compose it, and its option-implied
crash probability is far steadier than the cross-section of single names.

Regenerate with `doit fig2`.
