# crashbounds

Option-implied crash-probability bounds (Martin & Shi, 2025, "Forecasting
Crashes with a Smile"). Given a ticker, this package pulls its current
option-implied volatility surface from WRDS/OptionMetrics and returns the
Fréchet-Hoeffding bounds (Result 3) on the probability the stock falls below
a given fraction of today's price by a given horizon, plus the model's
risk-neutral point estimate.

It wraps the engine (A1-A4) implemented in the parent repo's `src/` -- it
does not duplicate that logic, only imports it, so the package and the
engine's own tests always agree.

## Install

```bash
pip install -e crashbounds/
```

You'll also need a WRDS account with OptionMetrics access, and either a
`WRDS_USERNAME` in your environment/`.env` or a value passed explicitly (see
below) -- otherwise `wrds.Connection()` will prompt interactively.

## Quickstart

```python
from crashbounds import crash_probability, report

result = crash_probability("AAPL", horizon_months=1, threshold_q=0.80)
print(report(result))
# AAPL vs SPX, 1-month horizon, as of 2025-08-29 (latest WRDS had -- see fetch_data's WRDS-lag note)
# P[AAPL <= 80% of today's price]:
#   lower bound:        0.29%
#   risk-neutral (P*):  0.40%
#   upper bound:        0.47%
```

`horizon_months` must be one of the horizons the paper uses (1, 3, 6, 12 --
see `schema.HORIZON_TO_MATURITY_DAYS`); `threshold_q` is the price fraction
that defines a "crash" (e.g. 0.80 = a 20% drop). There's no default for
either -- the paper doesn't calibrate one, so picking one for you would be
inventing a result, not reporting one.

For more control -- e.g. reusing one market (SPX) fetch across several
names instead of re-fetching it every call -- use `fetch_data()` and
`bounds()` directly:

```python
from crashbounds import fetch_data, bounds, risk_neutral_prob

market = fetch_data("SPX", maturity_days=30)
aapl = fetch_data("AAPL", maturity_days=30)

lower, p_star, upper = bounds(aapl, market, threshold_q=0.80)
risk_neutral_prob(aapl, threshold_q=0.80)  # == p_star, no market data needed
```

### WRDS-lag caveat

`fetch_data` returns the most recent surface WRDS actually has, not
"today's" -- OptionMetrics data through WRDS lags real time noticeably
(often several months to about a year, depending on when in the year you
ask; CRSP stock prices lag much less). Always check `result.date` before
treating a result as current -- see `crashbounds.api`'s module docstring
for details.

## Development

```bash
pip install -e crashbounds/
pytest crashbounds/tests/
pytest --doctest-modules crashbounds/src/crashbounds/
```
