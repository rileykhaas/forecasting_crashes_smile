## Description

Our replication of **Figure 6** in Martin & Shi (2025): the **out-of-sample
forecasting performance** of the option-implied lower bound. For 20% crashes
(`threshold_q = 0.80`) at horizons of 1, 3, 6, and 12 months, we track through time
the cumulative out-of-sample R² (eq. 10),

```
R²_oos(T) = 1 − Σ_{t≤T−τ} Σ_i (y_it − F_it)²  /  Σ_{t≤T−τ} Σ_i (y_it − p_it)²,
```

where `y_it = I(R_{i,t→t+τ} ≤ 0.8)` is the realized crash indicator, `F_it` is a
forecaster, and the benchmark `p_it` is firm *i*'s **historical average** crash
frequency over origins whose outcome is already observable at *t*. Everything is
causal: the benchmark and the regression adjustment only ever use data whose crash
outcome is known at the forecast origin.

Built by `exhibit_fig6.py` from `results.parquet` (inner-joined to
`sp500_secid_universe`), it compares three forecasters:

- **OIB-LB (α = 0, β = 1)** — the lower bound, with no free parameters.
- **RN (α = 0, β = 1)** — the raw risk-neutral crash probability.
- **RN (α̂, β̂)** — the risk-neutral adjusted by a trailing regression (eq. 9) that
  tries to correct its upward bias: an **expanding** window in **Panel A**, a
  **3-year rolling** window in **Panel B**.

## What it shows

Each line is a **running out-of-sample score** against a naive benchmark (the firm's
own historical crash rate). The **lower bound (pink) wins**: it is on top at every
horizon and stays well above zero for 20+ years, despite having no fitted parameters.

Even the **repaired risk-neutral (dark navy) loses**. Re-estimating α̂ and β̂ in
**rolling** regressions (Panel B) *substantially worsens* forecasting at the longer
horizons — the adjusted forecast turns **negative** (below the naive benchmark) at 6
and 12 months in the aftermath of 2008-10. The statistical fear-correction goes stale
at regime changes, whereas the theory-based correction (the bound) adapts in real
time through option prices. The decline in the risk-neutral's performance around
2008-10 echoes Figure 5: risk-neutral probabilities overstate true crash risk most at
times of high market risk, and rolling regressions exacerbate this after a realized
crash.

**Extension (`_ext`, through 2025).** By the end of the paper's sample every line had
been declining for roughly a decade — consistent either with an unusually calm
post-2012 market (a crash forecaster with little to prove itself on) or with a genuine
fade in the bound's edge. The extended sample, which includes the March 2023 bank
stress as realized crash events, lets us look past that ambiguity: the lower bound
stays on top and above zero across the extension.

Regenerate with `doit fig6`.
