"""Unit tests for utility_correction.py (A3) and bounds.py (A4).

Same idea as test_rnd.py: a flat implied-vol surface makes the CDF exactly
lognormal, giving closed forms to check the moments (A3) and, combining two
flat-vol names, the assembled bounds (A4). A skewed smile has no closed
form, so it's only checked for the ordering invariant (bound_lower <=
prob_riskneutral <= bound_upper).
"""

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm

import schema
from bounds import crash_bounds
from rnd import risk_neutral_cdf
from utility_correction import market_moment, weighted_tail_expectation

RATE = 0.03
MATURITY_DAYS = 30
MATURITY_YEARS = MATURITY_DAYS / 365.0
GAMMA = schema.GAMMA


def _surface_slice(
    moneyness, implied_vol, days_to_maturity=MATURITY_DAYS, secid=None, rate=RATE
):
    """Build a synthetic slice with each point labeled on its own OTM side
    (P at/below the forward, C above it) -- see test_rnd.py's _surface_slice.
    """
    n = len(moneyness)
    moneyness = np.asarray(moneyness, dtype="float64")
    forward = np.exp(rate * (days_to_maturity / 365.0))
    cp_flag = np.where(moneyness <= forward, "P", "C")
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-31"] * n),
            "secid": np.full(n, secid or schema.SPX_SECID, dtype="int64"),
            "days_to_maturity": np.full(n, days_to_maturity, dtype="int64"),
            "moneyness": moneyness,
            "implied_vol": np.asarray(implied_vol, dtype="float64"),
            "spot_price": np.full(n, 100.0),
            "cp_flag": cp_flag,
        }
    )


def _flat_vol_slice(vol, secid=None):
    moneyness = np.linspace(0.5, 1.5, 25)
    return _surface_slice(moneyness, np.full_like(moneyness, vol), secid=secid)


def _lognormal_params(vol, maturity_years=MATURITY_YEARS, rate=RATE):
    mu = (rate - 0.5 * vol**2) * maturity_years
    sigma = vol * np.sqrt(maturity_years)
    return mu, sigma


def _closed_form_moment(vol, gamma, maturity_years=MATURITY_YEARS, rate=RATE):
    mu, sigma = _lognormal_params(vol, maturity_years, rate)
    return np.exp(gamma * mu + 0.5 * gamma**2 * sigma**2)


def _closed_form_lower_partial_moment(vol, k, gamma, maturity_years=MATURITY_YEARS, rate=RATE):
    mu, sigma = _lognormal_params(vol, maturity_years, rate)
    d = (np.log(k) - mu) / sigma
    return _closed_form_moment(vol, gamma, maturity_years, rate) * norm.cdf(
        d - gamma * sigma
    )


@pytest.fixture
def flat_vol_25():
    return _flat_vol_slice(0.25)


@pytest.fixture
def flat_vol_20_index():
    return _flat_vol_slice(0.20, secid=schema.SPX_SECID)


@pytest.fixture
def flat_vol_35_name():
    return _flat_vol_slice(0.35, secid=5001)


@pytest.fixture
def smile_slice():
    moneyness = np.linspace(0.5, 1.5, 25)
    implied_vol = 0.20 + 0.15 * (1.0 - moneyness)
    return _surface_slice(moneyness, implied_vol)


# --- A3: utility_correction --------------------------------------------------


def test_market_moment_matches_lognormal_closed_form(flat_vol_25):
    cdf = risk_neutral_cdf(flat_vol_25, RATE)
    expected = _closed_form_moment(0.25, GAMMA)
    assert market_moment(cdf, RATE, gamma=GAMMA) == pytest.approx(expected, rel=5e-3)


def test_weighted_tail_expectation_lower_matches_closed_form(flat_vol_25):
    cdf = risk_neutral_cdf(flat_vol_25, RATE)
    for k in [0.70, 0.80, 0.90, 1.10]:
        expected = _closed_form_lower_partial_moment(0.25, k, GAMMA)
        got = weighted_tail_expectation(cdf, RATE, k, tail="lower", gamma=GAMMA)
        assert got == pytest.approx(expected, rel=5e-3, abs=1e-6)


def test_lower_plus_upper_tail_equals_total_moment(flat_vol_25):
    """lower + upper should recover the total moment. Tolerance is loose
    because splitting at an arbitrary k (not a grid point) means the two
    discrete sums don't partition the grid exactly like an analytic integral
    would -- an expected side effect of the midpoint-rule discretization.
    """
    cdf = risk_neutral_cdf(flat_vol_25, RATE)
    total = market_moment(cdf, RATE, gamma=GAMMA)
    for k in [0.70, 0.85, 1.00, 1.20]:
        lower = weighted_tail_expectation(cdf, RATE, k, tail="lower", gamma=GAMMA)
        upper = weighted_tail_expectation(cdf, RATE, k, tail="upper", gamma=GAMMA)
        assert lower + upper == pytest.approx(total, rel=5e-3)


def test_invalid_tail_raises(flat_vol_25):
    cdf = risk_neutral_cdf(flat_vol_25, RATE)
    with pytest.raises(ValueError):
        weighted_tail_expectation(cdf, RATE, 0.8, tail="sideways")


# --- A4: bounds ---------------------------------------------------------------


@pytest.mark.parametrize("threshold_q", schema.THRESHOLDS_Q)
def test_crash_bounds_matches_closed_form(flat_vol_20_index, flat_vol_35_name, threshold_q):
    """Two independent flat-vol (lognormal) marginals give a closed form:

    bound_lower = Phi(Phi^-1(p) - gamma*sigma_m), bound_upper = Phi(Phi^-1(p) + gamma*sigma_m),
    where p = Q_i(q) and sigma_m is the index's log-return vol.
    """
    cdf_m = risk_neutral_cdf(flat_vol_20_index, RATE)
    cdf_i = risk_neutral_cdf(flat_vol_35_name, RATE)

    bound_lower, prob_riskneutral, bound_upper = crash_bounds(
        cdf_i, cdf_m, RATE, threshold_q
    )

    _, sigma_m = _lognormal_params(0.20)
    z = norm.ppf(prob_riskneutral)
    expected_lower = norm.cdf(z - GAMMA * sigma_m)
    expected_upper = norm.cdf(z + GAMMA * sigma_m)

    assert bound_lower == pytest.approx(expected_lower, rel=5e-3, abs=1e-6)
    assert bound_upper == pytest.approx(expected_upper, rel=5e-3, abs=1e-6)


@pytest.mark.parametrize("threshold_q", schema.THRESHOLDS_Q)
def test_crash_bounds_ordering_holds(flat_vol_20_index, flat_vol_35_name, threshold_q):
    """Result 3: bound_lower <= prob_riskneutral <= bound_upper."""
    cdf_m = risk_neutral_cdf(flat_vol_20_index, RATE)
    cdf_i = risk_neutral_cdf(flat_vol_35_name, RATE)
    bounds = crash_bounds(cdf_i, cdf_m, RATE, threshold_q)
    results = pd.DataFrame(
        {
            "bound_lower": [bounds[0]],
            "prob_riskneutral": [bounds[1]],
            "bound_upper": [bounds[2]],
        }
    )
    assert schema.check_bound_ordering(results)


@pytest.mark.parametrize("threshold_q", schema.THRESHOLDS_Q)
def test_crash_bounds_ordering_holds_with_smile(smile_slice, flat_vol_35_name, threshold_q):
    """Result 3 should hold regardless of smile shape, not just flat-vol names."""
    cdf_m = risk_neutral_cdf(smile_slice, RATE)
    cdf_i = risk_neutral_cdf(flat_vol_35_name, RATE)
    bounds = crash_bounds(cdf_i, cdf_m, RATE, threshold_q)
    results = pd.DataFrame(
        {
            "bound_lower": [bounds[0]],
            "prob_riskneutral": [bounds[1]],
            "bound_upper": [bounds[2]],
        }
    )
    assert schema.check_bound_ordering(results)
