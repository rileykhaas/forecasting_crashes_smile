# Methodology

## Approach

Each month, for the S&P 500 index and every constituent, we turn the
option-implied volatility smile into a crash-probability estimate, the paper's
option-implied **lower bound**, then test it against the realized crash. The
pipeline builds that estimate from raw WRDS data and validates it against the
paper, then extends it past the paper's sample.

## Estimation chain (A1–A5)

1. **Risk-neutral density**: Black–Scholes OTM prices on a fine moneyness grid;
   differentiate (Breeden–Litzenberger) → risk-neutral CDF; isotonic + winsorize.
2. **Risk-neutral crash prob**: `P*[R ≤ q] = Q(q)` (the "crying wolf" number).
3. **Fear correction**: a power-utility investor (γ = 2) reweights toward the
   physical measure.
4. **Copula bounds**: Fréchet–Hoeffding → lower/upper bounds; the **lower bound**
   (comonotone) is the forecaster.
5. **Calibration test**: regress realized `I(R ≤ q)` on each probability; the test
   is **β = 1**, not β = 0.

## Pipeline (PyDoit)

`doit` runs the whole project end-to-end. The tasks, in dependency order:

1. **`config`**: create the `_data/` and `_output/` directories.
2. **`pull_crsp_stock`**: pull the CRSP monthly stock panel (plus the sector-ETF permnos) from WRDS.
3. **`pull_sp500_constituents`**: pull S&P 500 membership (`crsp.msp500list`).
4. **`pull_crsp_optionm_link`**: pull the CRSP–OptionMetrics link table.
5. **`pull_optionmetrics`**: pull the option surface, zero curve, and security names for constituents, the index, and the ETFs.
6. **`build_secid_universe`**: build the month-end constituent → OptionMetrics `secid` panel.
7. **`build_realized_returns`**: build CRSP forward realized gross returns (delisting folded in).
8. **`clean_rates`**: interpolate the zero curve to the horizon maturities (`rates.parquet`).
9. **`clean_surface`**: apply the Appendix-D filters and attach spot (`clean_surface.parquet`).
10. **`pipeline`**: run the engine A1–A5 into `results.parquet` (the crash bounds).
11. **`table1`, `table2`**: the replication summary and calibration tables.
12. **`fig1`, `fig2`, `fig6`**: the replication figures.
13. **`eda`**: our per-year coverage table and 2×2 EDA panel.
14. **`etf_bounds`**: the direct sector-ETF crash bounds.
15. **`industry_compare`**: the proxy-vs-direct industry comparison.
16. **`pull_svb_daily` → `svb_case_study`**: the daily SVB case study.
17. **`chart_html`, `table_parquet`**: chartbook render artifacts (HTML charts, table parquets).
18. **`run_notebooks`**: execute the data-tour notebook.
19. **`compile_latex_docs`**: compile the report PDF.
20. **`build_chartbook_site`**: build this chartbook.
21. **`run_pytest`**: run the test suite.

Table schemas are fixed in `src/schema.py`; each cleaned table is registered in this chartbook.

## Design choices

Modeling and data decisions we made (following Appendix D unless noted):

- **Spot from CRSP** (Appendix D criterion 1), constituents via the
  CRSP↔OptionMetrics link, the index via CRSP `spindx`.
- **Grid & smile**: fine grid `K/S ∈ [1/L, L]` (L = 3 for 1/3/6-month, 5 for
  12-month); implied vol interpolated linearly within observed strikes, held flat
  outside.
- **γ = 2, zero dividends**: the paper's calibrated risk aversion; clean BS prices
  assume zero dividend yield.
- **Total returns, delisting folded in**: realized returns use CRSP CIZ `mthret`,
  so wipeouts (e.g. SVB) register as crashes.
- **Financials kept**: no industry screen; the universe is pure S&P 500 membership.
- **Rate units**: `rates.parquet` is in percent; the engine converts to a decimal
  at the seam.
- **Membership freeze past the vintage**: `crsp.msp500list` ends current members
  at the CRSP vintage (2024-12-31); to reach Aug 2025 we hold them forward, each
  frozen row flagged `carried_forward = True`. A deliberate stale-membership
  approximation (not look-ahead); off for paper-exact `END_DATE = 2022-12-31`.
- **ETFs priced like any secid, excluded from replication**: the sector ETFs are
  force-pulled into CRSP (they are not `EQTY`), spot-matched via their own permno, and
  priced by the unchanged engine; they never enter the replication cross-section, which
  inner-joins to the S&P 500 constituent universe (so Tables 1–2 stay exactly the
  paper's). A regression test pins that exclusion.
- **FF12 industries from CRSP SIC**: the industry proxy assigns each constituent a
  Fama–French 12-industry code from the modal CRSP SIC, matched to the six SPDR sectors
  with a clean correspondence.
- **SVB is daily and self-contained**: a separate daily pull (surface + OptionMetrics
  `secprd` spot + zero curve) for four securities over Feb–Mar 2023, priced by the same
  engine; it does not touch the monthly pipeline. SIVB's surface ends at its 9-March
  collapse, the truncation is the event, not a gap.

## Replication & validation

- Reproduce **Table 1** (realized frequency hugs the lower bound), **Table 2**
  (lower-bound β ≈ 1 vs inflated risk-neutral ≈ 0.7), and **Figures 1, 2, 6** over
  1996–2022.
- **Unit tests** pin our numbers to the paper within a chosen tolerance; a flat-vol
  smile is checked against the closed-form lognormal CDF.
- **Low R² (~2–6%) is expected**: crashes are rare binary events; the meaningful
  comparison is bound vs risk-neutral on the same sample.

## Beyond the paper (built)

- **Through 2025**: every exhibit has an `_ext` variant past the 2022 cutoff, and the
  charts in this chartbook show the extended series; March-2023 supplies fresh realized
  crash events.
- **Own EDA**: a per-year coverage table and a 2×2 panel (coverage, moneyness ×
  maturity availability, the IV smile, the realized-return distribution) of the
  constituent option/return panel.
- **Sector ETFs**: the same engine applied directly to the 11 Select Sector
  SPDRs (+ KRE): a *direct* per-sector crash probability, in contrast to the paper's
  average-of-constituents proxy. Comonotonicity is more plausible for a diversified
  ETF, so the lower bound should bind tighter.
- **Proxy vs. direct**: the paper's proxy (equal-weighted average of constituent
  bounds, by Fama–French industry) put against the direct ETF bound: the proxy
  overstates the realized sector crash frequency in every sector, while the direct
  measure hugs it for the broad diversified sectors.
- **SVB case study**: the engine at daily frequency through March 2023, one
  event at three levels (SIVB → KRE → XLF), with a known-resolution table pairing peak
  crash probability against realized drawdown.
- **`crashbounds`**: the pipeline as a pip-installable package. *Planned.*
