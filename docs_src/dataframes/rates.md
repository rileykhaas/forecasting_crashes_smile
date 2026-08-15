## Description

The **cleaned risk-free zero curve**: the OptionMetrics zero-coupon curve, sampled
at each month-end formation date and linearly interpolated to the four surface
maturities (30, 91, 182, 365 days = the paper's 1/3/6/12-month horizons). It is
index-level (not per-secid) and joins onto `clean_surface` on `(date,
days_to_maturity)` to supply the discount rate for option pricing.

Following Martin & Shi (2025), Appendix D, rates for maturities not directly
observed are linearly interpolated from the OptionMetrics curve; beyond the
observed tenors the curve is held flat (the four targets sit inside the curve's
range in practice, so extrapolation rarely binds).

`zero_rate` is carried through exactly as OptionMetrics reports it — annualized,
continuously compounded, in **percentage points**. The conversion to a discount
factor (`Rf = exp(zero_rate/100 · τ)`) happens in the engine (#18), not here.

Cleaned output — lives in the gitignored `_data/`; regenerate with `doit rates`.

## Data Dictionary

- **date**: `datetime64[ns]` — month-end formation date (matches clean_surface).
- **days_to_maturity**: `int64` — maturity in days ∈ {30, 91, 182, 365}.
- **zero_rate**: `float64` — zero-coupon rate (annualized, continuously compounded, %).
