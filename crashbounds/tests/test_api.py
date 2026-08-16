"""Unit tests for crashbounds.api -- everything except fetch_data() itself,
which needs a live WRDS connection and isn't exercised here (see #28's
fetch_data docstring; it was verified manually against real WRDS data while
building #28). Everything else (bounds, risk_neutral_prob, report, plot) is
pure computation once you have a MarketData object, so it's tested directly
against synthetic MarketData built by hand -- no network, runs anywhere.
"""

import matplotlib

matplotlib.use("Agg")  # no display/Qt event loop needed for automated tests

import numpy as np
import pandas as pd
import pytest

import crashbounds
from crashbounds.api import MarketData

RATE = 0.03
MATURITY_DAYS = 30


def _surface_slice(secid, vol, rate=RATE, days_to_maturity=MATURITY_DAYS):
    moneyness = np.linspace(0.5, 1.5, 25)
    forward = np.exp(rate * (days_to_maturity / 365.0))
    cp_flag = np.where(moneyness <= forward, "P", "C")
    n = len(moneyness)
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-31"] * n),
            "secid": np.full(n, secid, dtype="int64"),
            "days_to_maturity": np.full(n, days_to_maturity, dtype="int64"),
            "moneyness": moneyness,
            "implied_vol": np.full(n, vol),
            "spot_price": np.full(n, 100.0),
            "cp_flag": cp_flag,
        }
    )


def _market_data(ticker, secid, vol):
    return MarketData(
        ticker=ticker,
        secid=secid,
        date=pd.Timestamp("2020-01-31"),
        days_to_maturity=MATURITY_DAYS,
        spot_price=100.0,
        rate=RATE,
        surface_slice=_surface_slice(secid, vol),
    )


@pytest.fixture
def name_data():
    return _market_data("AAPL", 5001, vol=0.35)


@pytest.fixture
def market_data():
    return _market_data("SPX", 108105, vol=0.20)


def test_risk_neutral_prob_is_a_probability(name_data):
    p = crashbounds.risk_neutral_prob(name_data, threshold_q=0.80)
    assert 0.0 <= p <= 1.0


def test_bounds_default_gamma_matches_engine_crash_bounds(name_data, market_data):
    """crashbounds.bounds() with the default gamma must give the exact same
    triple as calling the engine's crash_bounds() directly -- it's meant to
    be a thin pass-through, not a second implementation.
    """
    from rnd import risk_neutral_cdf

    cdf_i = risk_neutral_cdf(name_data.surface_slice, name_data.rate)
    cdf_m = risk_neutral_cdf(market_data.surface_slice, market_data.rate)
    expected = crashbounds.crash_bounds(cdf_i, cdf_m, name_data.rate, 0.80)

    got = crashbounds.bounds(name_data, market_data, threshold_q=0.80)
    assert got == pytest.approx(expected)


def test_bounds_ordering_holds(name_data, market_data):
    bound_lower, prob_riskneutral, bound_upper = crashbounds.bounds(
        name_data, market_data, threshold_q=0.80
    )
    assert bound_lower <= prob_riskneutral <= bound_upper


@pytest.mark.parametrize("gamma", [1, 2, 4, 8])
def test_bounds_widen_with_gamma(name_data, market_data, gamma):
    """Result 4: the lower bound falls and the upper bound rises as gamma
    increases past the paper's calibrated value (2).
    """
    base_lower, _, base_upper = crashbounds.bounds(name_data, market_data, 0.80, gamma=2)
    lower, _, upper = crashbounds.bounds(name_data, market_data, 0.80, gamma=gamma)
    if gamma >= 2:
        assert lower <= base_lower
        assert upper >= base_upper
    else:
        assert lower >= base_lower
        assert upper <= base_upper


def test_report_mentions_ticker_and_bounds(name_data, market_data):
    from crashbounds.api import CrashBoundsResult

    bound_lower, prob_riskneutral, bound_upper = crashbounds.bounds(
        name_data, market_data, threshold_q=0.80
    )
    result = CrashBoundsResult(
        ticker="AAPL",
        market_ticker="SPX",
        date=name_data.date,
        horizon_months=1,
        threshold_q=0.80,
        bound_lower=bound_lower,
        prob_riskneutral=prob_riskneutral,
        bound_upper=bound_upper,
    )
    text = crashbounds.report(result)
    assert "AAPL" in text
    assert "SPX" in text
    assert f"{prob_riskneutral:.2%}" in text


def test_plot_produces_a_figure(name_data, market_data):
    from crashbounds.api import CrashBoundsResult

    bound_lower, prob_riskneutral, bound_upper = crashbounds.bounds(
        name_data, market_data, threshold_q=0.80
    )
    result = CrashBoundsResult(
        ticker="AAPL",
        market_ticker="SPX",
        date=name_data.date,
        horizon_months=1,
        threshold_q=0.80,
        bound_lower=bound_lower,
        prob_riskneutral=prob_riskneutral,
        bound_upper=bound_upper,
    )
    ax = crashbounds.plot(result)
    assert ax.figure is not None


def test_market_tickers_are_recognized():
    from crashbounds.api import MARKET_TICKERS

    assert "SPX" in MARKET_TICKERS
