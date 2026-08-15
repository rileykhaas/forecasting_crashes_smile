## Description

The **cleaned volatility surface** is the analysis-ready option-implied "smile"
the crash-probability bounds are computed from. For the last trading day of each
month, and at the four standardized maturities matching the paper's 1/3/6/12-month
horizons, it holds the implied-volatility points of the S&P 500 index and each
S&P 500 constituent, expressed against **moneyness** (`impl_strike / CRSP spot`),
with the CRSP spot carried alongside.

It applies the four filtering criteria of Martin & Shi (2025), Appendix D:

1. a **CRSP spot** must exist for the firm-month (spot: constituents via the #14
   secid↔permno link and CRSP `|prc|`; the index via the CRSP S&P 500 level
   `spindx`);
2. **strike > 0**;
3. the OptionMetrics **`dispersion`** (surface goodness-of-fit) lies strictly in
   **(0, 0.05)**;
4. **more than 10 distinct strikes** per firm-month-maturity.

**Boundary with the engine.** This table is deliberately just the *filtered
observed* surface — it does **not** interpolate, extrapolate, or price. The
linear-within / flat-outside interpolation, the 2000-step Black-Scholes grid, and
the Breeden-Litzenberger marginals live in the engine (`rnd.py`, #18), keeping
cleaning separate from analysis. Both put and call quotes are kept (`cp_flag`), so
the engine can select the out-of-the-money side (puts below the forward, calls
above) before building the smile — as the paper does. Put and call implied vol
differ at the same moneyness, so keeping `cp_flag` avoids interleaving them into a
non-monotonic curve.

The extension ETFs (Select Sector SPDRs + KRE) are outside the paper's scope and
are not spot-matched here; they are handled with the sector-ETF extension (#34).
Cleaned output — lives in the gitignored `_data/`; regenerate with
`doit clean_surface`.

## Data Dictionary

- **date**: `datetime64[ns]` — last trading day of the month (formation date).
- **secid**: `int64` — OptionMetrics security id (108105 = S&P 500 index).
- **days_to_maturity**: `int64` — standardized maturity in days ∈ {30, 91, 182, 365}.
- **moneyness**: `float64` — `impl_strike / spot_price` (K/S).
- **implied_vol**: `float64` — Black-Scholes implied volatility at that point.
- **spot_price**: `float64` — CRSP spot (S); constant within a (date, secid).
- **cp_flag**: `string` — `P` (put) or `C` (call); the engine keeps the OTM side.
