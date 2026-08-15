"""Unit tests for rnd.risk_neutral_cdf and crash_prob.risk_neutral_crash_prob.

Runs against a synthetic surface fixture (per issue #18 -- no real
clean_surface.parquet exists yet, that's #17). The correctness check is: a
FLAT (no-smile) implied-vol surface is exactly the Black-Scholes/GBM
assumption, so Breeden-Litzenberger must recover the closed-form lognormal
CDF of the gross return. A skewed smile has no closed form, so it's only
checked for the structural properties Q(.) must have (monotone, in [0, 1]).
"""

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm

import schema
from crash_prob import risk_neutral_crash_prob
from rnd import risk_neutral_cdf

RATE = 0.03
MATURITY_DAYS = 30
MATURITY_YEARS = MATURITY_DAYS / 365.0


def _surface_slice(moneyness, implied_vol, days_to_maturity=MATURITY_DAYS):
    """Build a synthetic one-smile slice matching schema.SCHEMAS['clean_surface']."""
    n = len(moneyness)
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-31"] * n),
            "secid": np.full(n, schema.SPX_SECID, dtype="int64"),
            "days_to_maturity": np.full(n, days_to_maturity, dtype="int64"),
            "moneyness": np.asarray(moneyness, dtype="float64"),
            "implied_vol": np.asarray(implied_vol, dtype="float64"),
            "spot_price": np.full(n, 100.0),
        }
    )


def _lognormal_gross_return_cdf(k, vol, maturity_years=MATURITY_YEARS, rate=RATE):
    """Closed-form P*[R <= k] under GBM: R = S_T/S_0 ~ lognormal(mu, sigma^2*T)."""
    mu = (rate - 0.5 * vol**2) * maturity_years
    sigma = vol * np.sqrt(maturity_years)
    return norm.cdf((np.log(k) - mu) / sigma)


@pytest.fixture
def flat_vol_slice():
    moneyness = np.linspace(0.5, 1.5, 25)
    implied_vol = np.full_like(moneyness, 0.25)
    return _surface_slice(moneyness, implied_vol)


@pytest.fixture
def smile_slice():
    moneyness = np.linspace(0.5, 1.5, 25)
    # Downward-sloping equity skew: OTM puts (low moneyness) trade at higher
    # implied vol than OTM calls.
    implied_vol = 0.20 + 0.15 * (1.0 - moneyness)
    return _surface_slice(moneyness, implied_vol)


def test_flat_vol_recovers_lognormal_cdf(flat_vol_slice):
    """Breeden-Litzenberger on a flat smile must match the GBM closed form."""
    cdf = risk_neutral_cdf(flat_vol_slice, RATE)
    q_levels = np.array([0.70, 0.80, 0.90, 1.00, 1.10])
    expected = _lognormal_gross_return_cdf(q_levels, vol=0.25)
    np.testing.assert_allclose(cdf(q_levels), expected, atol=2e-3)


def test_cdf_is_monotone_and_bounded(smile_slice):
    cdf = risk_neutral_cdf(smile_slice, RATE)
    assert np.all(np.diff(cdf.values) >= 0)
    assert cdf.values.min() >= 0.0
    assert cdf.values.max() <= 1.0


def test_cdf_approaches_zero_and_one_in_the_tails(smile_slice):
    cdf = risk_neutral_cdf(smile_slice, RATE)
    assert cdf(cdf.grid.min()) < 0.05
    assert cdf(cdf.grid.max()) > 0.95


def test_inverse_round_trips_through_cdf(flat_vol_slice):
    cdf = risk_neutral_cdf(flat_vol_slice, RATE)
    q_levels = np.array([0.75, 0.85, 0.95, 1.05])
    p_levels = cdf(q_levels)
    np.testing.assert_allclose(cdf.inverse(p_levels), q_levels, atol=5e-3)


@pytest.mark.parametrize("threshold_q", schema.THRESHOLDS_Q)
def test_risk_neutral_crash_prob_matches_direct_cdf_call(flat_vol_slice, threshold_q):
    cdf = risk_neutral_cdf(flat_vol_slice, RATE)
    assert risk_neutral_crash_prob(cdf, threshold_q) == pytest.approx(
        cdf(threshold_q)
    )


def test_risk_neutral_crash_prob_matches_lognormal_closed_form(flat_vol_slice):
    cdf = risk_neutral_cdf(flat_vol_slice, RATE)
    for threshold_q in schema.THRESHOLDS_Q:
        expected = _lognormal_gross_return_cdf(threshold_q, vol=0.25)
        assert risk_neutral_crash_prob(cdf, threshold_q) == pytest.approx(
            expected, abs=2e-3
        )
