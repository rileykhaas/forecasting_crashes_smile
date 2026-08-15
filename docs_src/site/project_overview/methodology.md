# Methodology

## Approach

Each month, for the S&P 500 index and every constituent, we turn the
option-implied volatility smile into a crash-probability estimate — the paper's
option-implied **lower bound** — then test it against the realized crash. The
pipeline builds that estimate from raw WRDS data and validates it against the
paper, then extends it past the paper's sample.

## Estimation chain (A1–A5)

1. **Risk-neutral density** — Black–Scholes OTM prices on a fine moneyness grid;
   differentiate (Breeden–Litzenberger) → risk-neutral CDF; isotonic + winsorize.
2. **Risk-neutral crash prob** — `P*[R ≤ q] = Q(q)` (the "crying wolf" number).
3. **Fear correction** — a power-utility investor (γ = 2) reweights toward the
   physical measure.
4. **Copula bounds** — Fréchet–Hoeffding → lower/upper bounds; the **lower bound**
   (comonotone) is the forecaster.
5. **Calibration test** — regress realized `I(R ≤ q)` on each probability; the test
   is **β = 1**, not β = 0.

## Pipeline (PyDoit)

`pull_* → clean_surface / clean_rates (Slice 1) + build_secid_universe /
build_realized_returns (Slice 2) → engine (rnd → crash_prob → bounds → results) →
exhibits`. Table schemas are fixed in `src/schema.py`; each cleaned table is
registered in this chartbook.

## Design choices

Modeling and data decisions we made (following Appendix D unless noted):

- **Spot from CRSP** (Appendix D criterion 1) — constituents via the
  CRSP↔OptionMetrics link, the index via CRSP `spindx`.
- **Grid & smile** — fine grid `K/S ∈ [1/L, L]` (L = 3 for 1/3/6-month, 5 for
  12-month); implied vol interpolated linearly within observed strikes, held flat
  outside.
- **γ = 2, zero dividends** — the paper's calibrated risk aversion; clean BS prices
  assume zero dividend yield.
- **Total returns, delisting folded in** — realized returns use CRSP CIZ `mthret`,
  so wipeouts (e.g. SVB) register as crashes.
- **Financials kept** — no industry screen; the universe is pure S&P 500 membership.
- **Rate units** — `rates.parquet` is in percent; the engine converts to a decimal
  at the seam.
- **Membership freeze past the vintage** — `crsp.msp500list` ends current members
  at the CRSP vintage (2024-12-31); to reach Aug 2025 we hold them forward, each
  frozen row flagged `carried_forward = True`. A deliberate stale-membership
  approximation (not look-ahead); off for paper-exact `END_DATE = 2022-12-31`.

## Replication & validation

- Reproduce **Table 1** (realized frequency hugs the lower bound), **Table 2**
  (lower-bound β ≈ 1 vs inflated risk-neutral ≈ 0.7), and **Figures 1, 2, 6** over
  1996–2022.
- **Unit tests** pin our numbers to the paper within a chosen tolerance; a flat-vol
  smile is checked against the closed-form lognormal CDF.
- **Low R² (~2–6%) is expected** — crashes are rare binary events; the meaningful
  comparison is bound vs risk-neutral on the same sample.

## Beyond the paper

- **Through 2025** — extend every exhibit past the paper's 2022 cutoff;
  March-2023 supplies fresh realized crash events.
- **Sector ETFs** — per-sector crash series from the 11 Select Sector SPDRs (+ KRE),
  a *direct* measure vs the paper's average-of-constituents proxy.
- **SVB case study** — one event read at three levels (SIVB → KRE → XLF).
- **`crashbounds`** — the pipeline as a pip-installable package.
