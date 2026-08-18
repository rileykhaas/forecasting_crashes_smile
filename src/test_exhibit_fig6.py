"""Tests for exhibit_fig6.py (Figure 6 out-of-sample R^2 logic)."""

import numpy as np
import pandas as pd

from exhibit_fig6 import (
    _firm_benchmark,
    _ols_from_suff,
    compute_oos_r2,
)


def test_ols_from_suff_recovers_known_line():
    # y = 1 + 2x on points x = 0,1,2,3 -> exact fit, alpha=1, beta=2.
    x = np.array([0.0, 1.0, 2.0, 3.0])
    y = 1.0 + 2.0 * x
    n = len(x)
    alpha, beta = _ols_from_suff(n, x.sum(), y.sum(), (x * x).sum(), (x * y).sum())
    assert np.isclose(alpha, 1.0)
    assert np.isclose(beta, 2.0)


def test_ols_from_suff_degenerate_returns_nan():
    # Fewer than 2 points, or no x variation, is undefined.
    assert all(np.isnan(v) for v in _ols_from_suff(1, 0.5, 1.0, 0.25, 0.5))
    assert all(
        np.isnan(v) for v in _ols_from_suff(4, 2.0, 2.0, 1.0, 1.0)
    )  # x const -> denom 0


def test_firm_benchmark_uses_only_observable_history():
    # One firm, monthly, tau=1: p_{i,t} = mean of y over origins s <= t - 1 month.
    dates = pd.to_datetime(["2005-01-31", "2005-02-28", "2005-03-31", "2005-04-30"])
    df = pd.DataFrame({"date": dates, "secid": 7, "y": [0.0, 1.0, 0.0, 1.0]})
    out = _firm_benchmark(df, tau=1).sort_values("date")
    bench = out["bench"].tolist()
    assert np.isnan(bench[0])  # no observable history yet
    assert bench[1] == 0.0  # mean of {Jan:0}
    assert np.isclose(bench[2], 0.5)  # mean of {Jan:0, Feb:1}
    assert np.isclose(bench[3], 1 / 3)  # mean of {Jan:0, Feb:1, Mar:0}


def test_firm_benchmark_respects_horizon_lag():
    # tau=3: at each origin only outcomes from origins <= t-3 months are known.
    dates = pd.date_range("2005-01-31", periods=6, freq="ME")
    df = pd.DataFrame({"date": dates, "secid": 1, "y": [1.0, 1.0, 1.0, 0.0, 0.0, 0.0]})
    out = _firm_benchmark(df, tau=3).sort_values("date").reset_index(drop=True)
    # First three origins have no observable 3-month-old history.
    assert out["bench"][:3].isna().all()
    assert out["bench"][3] == 1.0  # only Jan observable -> mean {1}
    assert np.isclose(out["bench"][5], 1.0)  # Jan,Feb,Mar observable -> mean {1,1,1}


def _synthetic_panel():
    """Two firms, monthly 1996-2003, q=0.80/h=1. Firm A crashes every 8th month."""
    months = pd.date_range("1996-01-31", "2003-12-31", freq="ME")
    rows = []
    for k, d in enumerate(months):
        for sid, flag in [(1, int(k % 8 == 0)), (2, int(k % 5 == 0))]:
            rows.append(
                {
                    "date": d,
                    "secid": sid,
                    "threshold_q": 0.80,
                    "horizon_months": 1,
                    "bound_lower": float(flag),
                    "prob_riskneutral": 0.10,
                    "bound_upper": 0.5,
                    "realized_flag": flag,
                }
            )
    results = pd.DataFrame(rows)
    members = results[["date", "secid"]].copy()
    return results, members


def test_compute_oos_r2_shape_and_index():
    results, members = _synthetic_panel()
    r2 = compute_oos_r2(
        results,
        members,
        tau=1,
        start=pd.Timestamp("1996-01-01"),
        end=pd.Timestamp("2003-12-31"),
        burn_in_years=1,
    )
    assert list(r2.columns) == ["OIB_LB", "RN_raw", "RN_adj_exp", "RN_adj_roll"]
    assert isinstance(r2.index, pd.DatetimeIndex)
    assert r2.index.is_monotonic_increasing
    assert np.isfinite(r2.to_numpy()).all()


def test_compute_oos_r2_perfect_forecaster_scores_one():
    # bound_lower is set equal to the realized crash flag, so the lower-bound
    # forecast has zero squared error and R^2_oos must equal 1 everywhere.
    results, members = _synthetic_panel()
    r2 = compute_oos_r2(
        results,
        members,
        tau=1,
        start=pd.Timestamp("1996-01-01"),
        end=pd.Timestamp("2003-12-31"),
        burn_in_years=1,
    )
    assert np.allclose(r2["OIB_LB"].to_numpy(), 1.0)
