# Goals

## The idea

Replicate and extend **Martin & Shi (2025), "Forecasting Crashes with a Smile"**:
option prices — the shape of the implied-vol **smile** — carry a model-free signal
for the *physical* probability a stock or the market crashes over the next 1–12
months.

1. **Smile → density.** OTM puts trade rich (crash insurance), so the smile turns
   up at the edges; Breeden–Litzenberger recovers the risk-neutral return CDF.
2. **Risk-neutral "cries wolf."** The raw risk-neutral crash probability overstates
   risk — worst in crises — because it carries a fear premium.
3. **The fix.** A power-utility investor (γ = 2) corrects the bias; Fréchet–Hoeffding
   **copula bounds** handle the unknown stock–market correlation. The **lower bound**
   ≈ the truth (tight under comonotonicity) — the forecaster.

## Objectives

- **Replicate** (1996–2022, unit-tested to tolerance): Table 1 (realized frequency
  hugs the lower bound), Table 2 (lower-bound β ≈ 1 vs inflated risk-neutral ≈ 0.7),
  Figures 1, 2, 6.
- **Extend through 2025** — first test of whether the pattern survives post-2022,
  using March-2023 bank stress as fresh crash events.
- **Ship a product**: cleaned firm-month dataset + code, our own summary table and
  figures, and `crashbounds` (`crash_probability("AAPL", 12)` → bounds + fear gap).
- **Extensions**: per-sector crash series from the 11 Select Sector SPDRs (+ KRE);
  an SVB case study (SIVB → KRE → XLF).

## Success criteria

- Replicated numbers match the paper within tolerance; the lower bound's β ≈ 1
  calibration reproduces.
- Full pipeline runs end-to-end via `doit` on a clean clone; every exhibit
  regenerates through 2025.
- The extensions and the `crashbounds` package produce their outputs.
