"""Tests for exhibit_industry_compare.py (proxy vs. direct sector bounds, #34)."""

import pandas as pd
import pytest

import schema
from exhibit_industry_compare import (
    industry_proxy_series,
    tightness_table,
    to_latex,
)


def _member_panel():
    dates = pd.to_datetime(["2010-01-31", "2010-02-28"])
    # three financial constituents (1,2,3)
    return pd.DataFrame({"date": list(dates) * 3,
                         "secid": [1, 1, 2, 2, 3, 3]}).astype({"secid": "Int64"})


def _secid_industry():
    return pd.DataFrame({"secid": [1, 2, 3], "ff_industry": ["Money", "Money", "Money"]})


def _etf_map():
    return pd.DataFrame({"ticker": ["XLF"], "secid": [110012]})


def _results():
    """Three financial names + the XLF ETF + SPX, q=0.80, horizon=1 and 12."""
    rows = []
    for date in ["2010-01-31", "2010-02-28"]:
        for horizon in (1, 12):
            for secid, lo, flag in [
                (1, 0.10, 1), (2, 0.14, 0), (3, 0.12, 1),   # constituents: avg lower 0.12
                (110012, 0.06, 0),                            # ETF: lower 0.06 (diversified)
                (schema.SPX_SECID, 0.05, 0),
            ]:
                rows.append(dict(date=pd.Timestamp(date), secid=secid, threshold_q=0.80,
                                 horizon_months=horizon, bound_lower=lo,
                                 prob_riskneutral=lo + 0.1, bound_upper=lo + 0.2,
                                 realized_gross_return=0.9, realized_flag=flag))
    df = pd.DataFrame(rows)
    df["realized_flag"] = df["realized_flag"].astype("Int64")
    return df


def test_proxy_is_equal_weighted_mean_of_constituents():
    prox = industry_proxy_series(_results(), _member_panel(), _secid_industry(),
                                 horizon=1, start=pd.Timestamp("2009-01-01"),
                                 end=pd.Timestamp("2011-12-31"))
    jan = prox[prox["date"] == "2010-01-31"].iloc[0]
    assert jan["ff_industry"] == "Money"
    assert jan["proxy_lower"] == pytest.approx((0.10 + 0.14 + 0.12) / 3)  # 0.12


def test_tightness_gaps_from_realized():
    tbl = tightness_table(_results(), _member_panel(), _secid_industry(), _etf_map(),
                          start=pd.Timestamp("2009-01-01"), end=pd.Timestamp("2011-12-31"))
    row = tbl[tbl["ticker"] == "XLF"].iloc[0]
    assert row["proxy_lower"] == pytest.approx(0.12)   # avg of names
    assert row["direct_lower"] == pytest.approx(0.06)  # the ETF itself
    # realized_freq: XLF flag is 0 both months -> 0.0
    assert row["realized_freq"] == pytest.approx(0.0)
    # each measure's distance from realized; the direct measure is the tighter one
    assert row["proxy_gap"] == pytest.approx(0.12)
    assert row["direct_gap"] == pytest.approx(0.06)
    assert abs(row["direct_gap"]) < abs(row["proxy_gap"])


def test_to_latex_renders_matched_sectors():
    tex = to_latex(tightness_table(_results(), _member_panel(), _secid_industry(), _etf_map()))
    assert r"\begin{tabular}" in tex and r"\bottomrule" in tex
    assert "Finance" in tex and "XLF" in tex
