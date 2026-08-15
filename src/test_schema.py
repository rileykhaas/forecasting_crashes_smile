"""Unit tests for the agreed table schemas and the bound-ordering invariant.

These tests check STRUCTURE, not analysis logic, so they run before any real
pull/clean/analysis code exists. They fail in CI if anyone changes a cleaned
table's columns without updating schema.py -- turning the README agreement into
an enforced contract.
"""

import numpy as np
import pandas as pd
import pytest

import schema


def _valid_frame(table):
    """Build a tiny synthetic frame that satisfies the given table's schema."""
    builders = {
        "clean_surface": {
            "date": pd.to_datetime(["2020-01-31", "2020-02-28"]),
            "secid": np.array([schema.SPX_SECID, 5001], dtype="int64"),
            "days_to_maturity": np.array([30, 91], dtype="int64"),
            "moneyness": np.array([0.9, 1.0], dtype="float64"),
            "implied_vol": np.array([0.25, 0.20], dtype="float64"),
            "spot_price": np.array([3200.0, 3100.0], dtype="float64"),
            "cp_flag": np.array(["P", "C"]),
        },
        "rates": {
            "date": pd.to_datetime(["2020-01-31", "2020-01-31"]),
            "days_to_maturity": np.array([30, 91], dtype="int64"),
            "zero_rate": np.array([0.015, 0.016], dtype="float64"),
        },
        "realized_returns": {
            "date": pd.to_datetime(["2020-01-31", "2020-01-31"]),
            "secid": np.array([5001, 5002], dtype="int64"),
            "horizon_months": np.array([1, 12], dtype="int64"),
            "realized_gross_return": np.array([0.95, 1.10], dtype="float64"),
        },
        "results": {
            "date": pd.to_datetime(["2020-01-31", "2020-01-31"]),
            "secid": np.array([5001, 5002], dtype="int64"),
            "horizon_months": np.array([1, 1], dtype="int64"),
            "threshold_q": np.array([0.80, 0.80], dtype="float64"),
            "bound_lower": np.array([0.02, 0.03], dtype="float64"),
            "prob_riskneutral": np.array([0.04, 0.05], dtype="float64"),
            "bound_upper": np.array([0.07, 0.09], dtype="float64"),
            "realized_gross_return": np.array([0.95, 0.78], dtype="float64"),
            "realized_flag": np.array([0, 1], dtype="int64"),
        },
    }
    return pd.DataFrame(builders[table])


@pytest.mark.parametrize("table", sorted(schema.SCHEMAS))
def test_valid_frame_passes(table):
    """A correctly built frame validates for every declared table."""
    assert schema.validate_schema(_valid_frame(table), table)


@pytest.mark.parametrize("table", sorted(schema.SCHEMAS))
def test_missing_column_fails(table):
    """Dropping a required column is rejected."""
    df = _valid_frame(table).drop(columns=[schema.columns(table)[0]])
    with pytest.raises(ValueError):
        schema.validate_schema(df, table)


@pytest.mark.parametrize("table", sorted(schema.SCHEMAS))
def test_extra_column_fails(table):
    """An unexpected extra column is rejected."""
    df = _valid_frame(table).assign(surprise=1)
    with pytest.raises(ValueError):
        schema.validate_schema(df, table)


def test_wrong_dtype_fails():
    """A column with the wrong dtype kind is rejected."""
    df = _valid_frame("results")
    df["secid"] = df["secid"].astype("float64")  # should be integer
    with pytest.raises(ValueError):
        schema.validate_schema(df, "results")


def test_bound_ordering_holds_on_valid_results():
    """The P^L <= P^* <= P^U invariant passes on a well-formed results frame."""
    assert schema.check_bound_ordering(_valid_frame("results"))


def test_bound_ordering_violation_detected():
    """A results frame that violates P^L <= P^* <= P^U is rejected."""
    df = _valid_frame("results")
    df.loc[0, "bound_lower"] = 0.99  # now exceeds prob_riskneutral
    with pytest.raises(ValueError):
        schema.check_bound_ordering(df)


def test_constants_match_paper():
    """Guard the fixed parameters against accidental edits."""
    assert schema.GAMMA == 2
    assert schema.HORIZONS_MONTHS == [1, 3, 6, 12]
    assert schema.THRESHOLDS_Q == [0.70, 0.80, 0.90]
    assert schema.SPX_SECID == 108105
    assert all(q < 1 for q in schema.THRESHOLDS_Q)  # crash thresholds, not rally
