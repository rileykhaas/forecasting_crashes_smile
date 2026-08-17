"""Tests for exhibit_table2.py (regression calibration logic)."""

import numpy as np
import pandas as pd
import pytest

import schema
from exhibit_table2 import _block_bootstrap_se, _ols, run_table2


def test_ols_recovers_a_known_line():
    x = pd.Series([0.0, 1.0, 2.0, 3.0, 4.0])
    y = 2.0 + 3.0 * x
    alpha, beta, r2, resid = _ols(x, y)
    assert alpha == pytest.approx(2.0)
    assert beta == pytest.approx(3.0)
    assert r2 == pytest.approx(1.0)
    assert resid.abs().max() == pytest.approx(0.0)


def test_block_bootstrap_returns_finite_positive_se():
    rng = np.random.default_rng(0)
    months = pd.to_datetime("2000-01-31") + pd.to_timedelta(
        np.repeat(np.arange(60) * 30, 10), unit="D"
    )
    x = pd.Series(rng.normal(size=600))
    y = pd.Series(0.5 * x.to_numpy() + rng.normal(size=600))
    se_a, se_b = _block_bootstrap_se(x, y, months, block_len=6, n_boot=200, seed=1)
    assert np.isfinite(se_a) and se_a > 0
    assert np.isfinite(se_b) and se_b > 0


def _synthetic_results(n_months=36):
    dates = pd.date_range("2005-01-31", periods=n_months, freq="ME")
    rng = np.random.default_rng(0)
    rows = []
    for date in dates:
        for secid in (1, 2, schema.SPX_SECID):  # 2 firms + the index
            for q in schema.THRESHOLDS_Q:
                for h in schema.HORIZONS_MONTHS:
                    lo = rng.uniform(0, 0.2)
                    rows.append(dict(date=date, secid=secid, threshold_q=q, horizon_months=h,
                                     bound_lower=lo, prob_riskneutral=lo + 0.05,
                                     bound_upper=lo + 0.1,
                                     realized_flag=int(rng.random() < lo)))
    return pd.DataFrame(rows)


def _members(n_months=36):
    dates = pd.date_range("2005-01-31", periods=n_months, freq="ME")
    return pd.DataFrame(
        {"date": list(dates) * 2, "secid": [1] * n_months + [2] * n_months}
    ).astype({"secid": "Int64"})


def test_run_table2_shape_and_columns():
    stats = run_table2(_synthetic_results(), _members(),
                       start=pd.Timestamp("2004-01-01"), end=pd.Timestamp("2010-12-31"),
                       n_boot=50)
    # 3 thresholds x 3 measures x 4 horizons
    assert len(stats) == 3 * 3 * 4
    assert {"q", "measure", "horizon", "alpha", "beta", "r2",
            "alpha_se_cl", "alpha_se_bs", "beta_se_cl", "beta_se_bs"} <= set(stats.columns)
    # the index (secid 108105) is excluded by the member-panel join, so nothing blew up
    assert stats["beta"].notna().all()
