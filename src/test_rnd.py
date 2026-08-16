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


def _surface_slice(
    moneyness, implied_vol, days_to_maturity=MATURITY_DAYS, rate=RATE, cp_flag=None
):
    """Build a synthetic one-smile slice matching schema.SCHEMAS['clean_surface'].

    If ``cp_flag`` isn't given, each point is labeled on its own OTM side (P
    at/below the forward, C above it) -- i.e. by default this already IS a
    clean OTM-only smile, matching what real clean_surface.parquet rows look
    like after rnd.py's OTM filter. Pass explicit ``cp_flag`` to build a
    fixture with ITM-side rows too (see test_itm_side_is_ignored below).
    """
    n = len(moneyness)
    moneyness = np.asarray(moneyness, dtype="float64")
    if cp_flag is None:
        forward = np.exp(rate * (days_to_maturity / 365.0))
        cp_flag = np.where(moneyness <= forward, "P", "C")
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-31"] * n),
            "secid": np.full(n, schema.SPX_SECID, dtype="int64"),
            "days_to_maturity": np.full(n, days_to_maturity, dtype="int64"),
            "moneyness": moneyness,
            "implied_vol": np.asarray(implied_vol, dtype="float64"),
            "spot_price": np.full(n, 100.0),
            "cp_flag": np.asarray(cp_flag),
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
    assert risk_neutral_crash_prob(cdf, threshold_q) == pytest.approx(cdf(threshold_q))


def test_risk_neutral_crash_prob_matches_lognormal_closed_form(flat_vol_slice):
    cdf = risk_neutral_cdf(flat_vol_slice, RATE)
    for threshold_q in schema.THRESHOLDS_Q:
        expected = _lognormal_gross_return_cdf(threshold_q, vol=0.25)
        assert risk_neutral_crash_prob(cdf, threshold_q) == pytest.approx(
            expected, abs=2e-3
        )


@pytest.mark.parametrize(
    "days, expected_L", [(30, 3.0), (91, 3.0), (182, 3.0), (365, 5.0)]
)
def test_grid_spans_paper_moneyness_range(days, expected_L):
    """The fine grid is fixed to K/S in [1/L, L] (Appendix D: L=3, or 5 at 12m)."""
    slice_ = _surface_slice(
        np.linspace(0.7, 1.3, 15), np.full(15, 0.25), days_to_maturity=days
    )
    cdf = risk_neutral_cdf(slice_, RATE)
    assert cdf.grid.min() == pytest.approx(1.0 / expected_L)
    assert cdf.grid.max() == pytest.approx(expected_L)


def test_percent_rate_is_rejected(flat_vol_slice):
    """A percent rate (e.g. 3.0) is caught, not silently mispriced as r=300%."""
    with pytest.raises(ValueError, match="decimal"):
        risk_neutral_cdf(flat_vol_slice, 3.0)


@pytest.mark.parametrize("q_low, q_high", [(0.70, 0.80), (0.80, 0.90), (0.90, 1.00)])
def test_crash_prob_is_monotone_in_threshold(flat_vol_slice, q_low, q_high):
    """Property: P*[R<=q] can only rise (or stay flat) as q rises."""
    cdf = risk_neutral_cdf(flat_vol_slice, RATE)
    assert risk_neutral_crash_prob(cdf, q_low) <= risk_neutral_crash_prob(cdf, q_high)


def test_crash_prob_is_monotone_in_horizon():
    """Property: for a fixed sub-100% threshold, a longer horizon gives the
    price more time to drift below it, so P*[R<=q] should rise with maturity
    (true for a lognormal-type distribution once q is below the current
    price, which every threshold in schema.THRESHOLDS_Q is).
    """
    moneyness = np.linspace(0.5, 1.5, 9)
    probs = []
    for days in schema.MATURITIES_DAYS:
        slice_ = _surface_slice(moneyness, np.full_like(moneyness, 0.25), days_to_maturity=days)
        cdf = risk_neutral_cdf(slice_, RATE)
        probs.append(risk_neutral_crash_prob(cdf, 0.80))
    assert probs == sorted(probs)


def test_degenerate_surface_with_only_two_points():
    """The smallest possible smile (one OTM put, one OTM call) still yields
    a valid, monotone CDF -- no crash on a thin/illiquid name.
    """
    slice_ = _surface_slice([0.9, 1.1], [0.25, 0.25])
    cdf = risk_neutral_cdf(slice_, RATE)
    assert np.all(np.diff(cdf.values) >= 0)
    assert cdf.values.min() >= 0.0
    assert cdf.values.max() <= 1.0


def test_degenerate_surface_with_narrow_moneyness_cluster():
    """A smile bunched tightly around the money (no real tail coverage) must
    still produce a valid CDF, not NaNs or an exception.
    """
    moneyness = np.linspace(0.98, 1.02, 5)
    slice_ = _surface_slice(moneyness, np.full_like(moneyness, 0.25))
    cdf = risk_neutral_cdf(slice_, RATE)
    assert np.all(np.isfinite(cdf.values))
    assert np.all(np.diff(cdf.values) >= 0)


def test_itm_side_is_ignored_even_with_garbage_vol():
    """The ITM side of each strike must not influence the fitted smile at all.

    Regression test: clean_surface.parquet carries BOTH put and call quotes
    on the same moneyness axis (OptionMetrics gives a full delta grid for
    each side, not just the OTM half). Real put/call vol at similar moneyness
    can differ sharply -- e.g. AIG in Oct 2008 had adjacent points at 1.32 and
    1.43 vol -- so without an OTM filter the "smile" isn't even single-valued.
    Here the ITM side is planted with an absurd vol (5.0) that must be
    completely ignored, not just outweighed or smoothed over.
    """
    moneyness = np.linspace(0.5, 1.5, 25)
    forward = np.exp(RATE * MATURITY_YEARS)
    otm_flag = np.where(moneyness <= forward, "P", "C")
    itm_flag = np.where(moneyness <= forward, "C", "P")  # the wrong side

    otm_vol = np.full_like(moneyness, 0.25)
    garbage_itm_vol = np.full_like(moneyness, 5.0)

    both_sides = pd.concat(
        [
            _surface_slice(moneyness, otm_vol, cp_flag=otm_flag),
            _surface_slice(moneyness, garbage_itm_vol, cp_flag=itm_flag),
        ],
        ignore_index=True,
    )
    otm_only = _surface_slice(moneyness, otm_vol, cp_flag=otm_flag)

    cdf_with_garbage_itm = risk_neutral_cdf(both_sides, RATE)
    cdf_otm_only = risk_neutral_cdf(otm_only, RATE)

    q_levels = np.array([0.70, 0.80, 0.90, 1.00, 1.10])
    np.testing.assert_allclose(
        cdf_with_garbage_itm(q_levels), cdf_otm_only(q_levels), atol=1e-9
    )
