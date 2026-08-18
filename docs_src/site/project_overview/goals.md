# Goals

## The idea

Replicate and extend **Martin & Shi (2025), "Forecasting Crashes with a Smile"**:
option prices, the shape of the implied-vol **smile**, carry a model-free signal
for the *physical* probability a stock or the market crashes over the next 1–12
months.

1. **Smile → density.** OTM puts trade rich (crash insurance), so the smile turns
   up at the edges; Breeden–Litzenberger recovers the risk-neutral return CDF.
2. **Risk-neutral "cries wolf."** The raw risk-neutral crash probability overstates
   risk, worst in crises, because it carries a fear premium.
3. **The fix.** A power-utility investor (γ = 2) corrects the bias; Fréchet–Hoeffding
   **copula bounds** handle the unknown stock–market correlation. The **lower bound**
   ≈ the truth (tight under comonotonicity), the forecaster.

## Objectives

- **Replicate** (1996–2022, unit-tested to tolerance): Table 1 (realized frequency
  hugs the lower bound), Table 2 (lower-bound β ≈ 1 vs inflated risk-neutral ≈ 0.7),
  and Figures 1, 2, 6. *Done.*
- **Reproduce through 2025**: every table and figure has an extended-sample variant;
  the charts in this chartbook show the through-2025 series, with March-2023 bank
  stress supplying fresh realized crash events. *Done.*
- **Our own EDA**: a per-year coverage table and a 2×2 panel (coverage over time,
  moneyness × maturity availability, the implied-vol smile, the realized-return
  distribution) of the underlying option/return panel. *Done.*
- **Extensions beyond the paper**: direct per-sector bounds from the 11 Select Sector
  SPDRs (+ KRE); a proxy-vs-direct comparison against the paper's
  average-of-constituents industry measure (Fama–French); and a daily SVB case study
  (SIVB → KRE → XLF), with a known-resolution check. *Done.*
- **`crashbounds` package**: the pipeline as a pip-installable library
  (`crash_probability("AAPL", 12)` → bounds + fear gap). *Planned.*

## Success criteria

- Replicated numbers match the paper within tolerance; the lower bound's β ≈ 1
  calibration reproduces. *Met.*
- Full pipeline runs end-to-end via `doit` on a clean clone; every exhibit
  regenerates through 2025. *Met.*
- Our own EDA and the three extensions produce their exhibits, all wired into the
  report and this chartbook. *Met.* (The `crashbounds` package is the remaining item.)
