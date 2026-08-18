"""Tests for exhibit_fig2.py (Figure 2 selection/aggregation logic)."""

import pandas as pd

import schema
from exhibit_fig2 import cross_sectional_medians, market_series


def _results():
    """Two months, two constituents (1, 2) + the index, at q=0.80/h=1."""
    rows = []
    for date, lo1, hi1, lo2, hi2, spx_lo in [
        ("2005-01-31", 0.02, 0.06, 0.04, 0.10, 0.01),
        ("2005-02-28", 0.03, 0.09, 0.05, 0.11, 0.02),
    ]:
        rows += [
            {
                "date": pd.Timestamp(date),
                "secid": 1,
                "threshold_q": 0.80,
                "horizon_months": 1,
                "bound_lower": lo1,
                "prob_riskneutral": 0.5,
                "bound_upper": hi1,
            },
            {
                "date": pd.Timestamp(date),
                "secid": 2,
                "threshold_q": 0.80,
                "horizon_months": 1,
                "bound_lower": lo2,
                "prob_riskneutral": 0.5,
                "bound_upper": hi2,
            },
            {
                "date": pd.Timestamp(date),
                "secid": schema.SPX_SECID,
                "threshold_q": 0.80,
                "horizon_months": 1,
                "bound_lower": spx_lo,
                "prob_riskneutral": 0.5,
                "bound_upper": 0.9,
            },
        ]
    # a q=0.70 decoy row that must be ignored
    rows.append(
        {
            "date": pd.Timestamp("2005-01-31"),
            "secid": 1,
            "threshold_q": 0.70,
            "horizon_months": 1,
            "bound_lower": 0.99,
            "prob_riskneutral": 0.5,
            "bound_upper": 0.99,
        }
    )
    return pd.DataFrame(rows)


def _members():
    dates = pd.to_datetime(["2005-01-31", "2005-02-28"])
    return pd.DataFrame({"date": list(dates) * 2, "secid": [1, 1, 2, 2]}).astype(
        {"secid": "Int64"}
    )


def test_cross_sectional_medians_over_constituents_only():
    med = cross_sectional_medians(
        _results(),
        _members(),
        start=pd.Timestamp("2005-01-01"),
        end=pd.Timestamp("2005-12-31"),
    )
    jan = med[med["date"] == "2005-01-31"].iloc[0]
    # median across firms 1,2 (index excluded): lower med(0.02,0.04)=0.03, upper med(0.06,0.10)=0.08
    assert jan["bound_lower"] == 0.03
    assert jan["bound_upper"] == 0.08


def test_market_series_is_the_index_lower_bound():
    mkt = market_series(
        _results(), start=pd.Timestamp("2005-01-01"), end=pd.Timestamp("2005-12-31")
    )
    assert list(mkt["bound_lower"]) == [0.01, 0.02]  # SPX lower bound, sorted by date
    assert "secid" not in mkt.columns
