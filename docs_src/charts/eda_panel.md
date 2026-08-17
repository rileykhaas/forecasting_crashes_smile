## Description

Our own **exploratory data analysis** of the raw inputs the bounds are built from
(issue #33) — distinct from the replication exhibits, which report statistics on the
*derived* crash-probability bounds. A 2×2 panel figure over S&P 500 constituent
member-months (1996–2022), built by `exhibit_eda.py` from `clean_surface.parquet` and
`realized_returns.parquet`, inner-joined to `sp500_secid_universe` so it describes
exactly the replication sample.

- **(a) Cross-section over time** — number of constituents carrying an option surface
  each month.
- **(b) Moneyness × maturity availability** — share of firm-months with ≥1 quote in
  each cell of the surface grid.
- **(c) The implied-volatility smile** — median implied vol by moneyness, one line per
  maturity.
- **(d) Realized-return distribution** — gross returns at 1- vs 12-month horizons, with
  the 20% (`0.80`) and 30% (`0.70`) crash thresholds marked.

## What it shows

The panel is broad and continuous (~500 names, dipping only briefly in March 2020),
and — the point that matters for trusting the method — the **out-of-the-money-put
tail** the lower bound integrates is well populated, especially at the longer
maturities used for multi-month horizons. Panel (c) is the paper's "smile": the
downside skew the bound reads as crash risk. Panel (d) shows the realized-return
distribution growing a **fat left tail** as the horizon lengthens, placing real mass
beyond the crash thresholds — the rare events the bounds are asked to forecast.

Regenerate with `doit eda`.
