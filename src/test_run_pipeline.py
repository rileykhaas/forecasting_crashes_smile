"""Unit tests for run_pipeline.py (A5)."""

import numpy as np
import pandas as pd
import pytest

import schema
from run_pipeline import run_pipeline

RATE_PCT = 3.0  # rates.parquet stores zero_rate in percent
MATURITY_DAYS = 30
NAME_SECID = 5001


def _smile(secid, date, vol=0.25, days=MATURITY_DAYS):
    moneyness = np.linspace(0.5, 1.5, 25)
    forward = np.exp((RATE_PCT / 100.0) * (days / 365.0))
    cp_flag = np.where(moneyness <= forward, "P", "C")
    n = len(moneyness)
    return pd.DataFrame(
        {
            "date": pd.Timestamp(date),
            "secid": secid,
            "days_to_maturity": days,
            "moneyness": moneyness,
            "implied_vol": vol,
            "spot_price": 100.0,
            "cp_flag": cp_flag,
        }
    )


@pytest.fixture
def clean_surface_fixture():
    dates = ["2020-01-31", "2020-02-28"]
    frames = []
    for date in dates:
        frames.append(_smile(schema.SPX_SECID, date, vol=0.20))
        frames.append(_smile(NAME_SECID, date, vol=0.35))
    return pd.concat(frames, ignore_index=True)


@pytest.fixture
def rates_fixture():
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-31", "2020-02-28"]),
            "days_to_maturity": [MATURITY_DAYS, MATURITY_DAYS],
            "zero_rate": [RATE_PCT, RATE_PCT],
        }
    )


@pytest.fixture
def realized_returns_fixture():
    # Only January has a realized outcome -- February should come through
    # with realized_gross_return/realized_flag as NA (no forward month yet).
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2020-01-31"]),
            "secid": [NAME_SECID],
            "horizon_months": [1],
            "realized_gross_return": [0.75],
        }
    )


def test_schema_and_bound_ordering(clean_surface_fixture, rates_fixture, realized_returns_fixture):
    results = run_pipeline(clean_surface_fixture, rates_fixture, realized_returns_fixture)
    assert schema.validate_schema(results, "results")
    assert schema.check_bound_ordering(results)


def test_market_secid_is_excluded(clean_surface_fixture, rates_fixture, realized_returns_fixture):
    results = run_pipeline(clean_surface_fixture, rates_fixture, realized_returns_fixture)
    assert schema.SPX_SECID not in set(results["secid"])


def test_one_row_per_threshold(clean_surface_fixture, rates_fixture, realized_returns_fixture):
    results = run_pipeline(clean_surface_fixture, rates_fixture, realized_returns_fixture)
    # 2 dates x 1 name x 1 horizon x 3 thresholds
    assert len(results) == 2 * 1 * 1 * len(schema.THRESHOLDS_Q)
    assert set(results["threshold_q"]) == set(schema.THRESHOLDS_Q)


def test_realized_flag_matches_threshold(clean_surface_fixture, rates_fixture, realized_returns_fixture):
    results = run_pipeline(clean_surface_fixture, rates_fixture, realized_returns_fixture)
    jan = results[results["date"] == "2020-01-31"].set_index("threshold_q")
    # realized_gross_return = 0.75: a crash at q=0.80/0.90, not at q=0.70.
    assert jan.loc[0.70, "realized_flag"] == 0
    assert jan.loc[0.80, "realized_flag"] == 1
    assert jan.loc[0.90, "realized_flag"] == 1


def test_missing_realized_data_is_na(clean_surface_fixture, rates_fixture, realized_returns_fixture):
    results = run_pipeline(clean_surface_fixture, rates_fixture, realized_returns_fixture)
    feb = results[results["date"] == "2020-02-28"]
    assert feb["realized_gross_return"].isna().all()
    assert feb["realized_flag"].isna().all()


def test_smile_with_no_otm_quotes_is_skipped_not_fatal(
    clean_surface_fixture, rates_fixture, realized_returns_fixture
):
    """A smile that has no usable OTM side after rnd.py's filter (real data
    hits this for thin/illiquid names) must be skipped, not crash the run.
    """
    bad = _smile(9999, "2020-01-31", vol=0.30)
    # Flip every cp_flag to the ITM side, so nothing survives rnd.py's OTM filter.
    bad["cp_flag"] = np.where(bad["cp_flag"] == "P", "C", "P")
    broken_surface = pd.concat([clean_surface_fixture, bad], ignore_index=True)

    results = run_pipeline(broken_surface, rates_fixture, realized_returns_fixture)
    assert 9999 not in set(results["secid"])
    assert schema.validate_schema(results, "results")
