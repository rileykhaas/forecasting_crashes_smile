"""Tests for exhibit_etf_bounds.py (sector-ETF extension, #34)."""

import pandas as pd
import pytest

import schema
from exhibit_etf_bounds import etf_summary_table, to_latex


def _secid_map():
    """Two ETFs for the tests: XLF and KRE."""
    return pd.DataFrame({"ticker": ["XLF", "KRE"], "secid": [110012, 127104]})


def _results():
    """q=0.80, horizon=12 rows for XLF, KRE, and SPX over two months."""
    rows = []
    spec = [
        (110012, 0.08, 0.18, 0.27, 1),  # XLF: realized crash
        (127104, 0.10, 0.21, 0.31, 0),  # KRE: no crash
        (schema.SPX_SECID, 0.05, 0.14, 0.22, 0),
    ]
    for date in ["2010-01-31", "2010-02-28"]:
        for secid, lo, rn, up, flag in spec:
            rows.append(
                {
                    "date": pd.Timestamp(date),
                    "secid": secid,
                    "threshold_q": 0.80,
                    "horizon_months": 12,
                    "bound_lower": lo,
                    "prob_riskneutral": rn,
                    "bound_upper": up,
                    "realized_flag": flag,
                }
            )
    # a decoy q/horizon that must be ignored
    rows.append(
        {
            "date": pd.Timestamp("2010-01-31"),
            "secid": 110012,
            "threshold_q": 0.70,
            "horizon_months": 1,
            "bound_lower": 0.99,
            "prob_riskneutral": 0.99,
            "bound_upper": 0.99,
            "realized_flag": 1,
        }
    )
    df = pd.DataFrame(rows)
    df["realized_flag"] = df["realized_flag"].astype("Int64")
    return df


def test_summary_table_rows_and_means():
    tbl = etf_summary_table(
        _results(),
        _secid_map(),
        start=pd.Timestamp("2009-01-01"),
        end=pd.Timestamp("2011-12-31"),
    )
    # one row per ETF plus an SPX row, SPX last
    assert list(tbl["ticker"]) == ["XLF", "KRE", "SPX"]
    xlf = tbl[tbl["ticker"] == "XLF"].iloc[0]
    assert xlf["mean_lower"] == pytest.approx(0.08)  # ignores the q=0.70 decoy
    assert xlf["mean_rn"] == pytest.approx(0.18)
    assert xlf["realized_freq"] == pytest.approx(1.0)  # both months flagged a crash
    assert xlf["n_obs"] == 2
    kre = tbl[tbl["ticker"] == "KRE"].iloc[0]
    assert kre["realized_freq"] == pytest.approx(0.0)


def test_lower_bound_below_risk_neutral_below_upper():
    """The bound ordering P^L <= P* <= P^U must hold for every ETF row."""
    tbl = etf_summary_table(_results(), _secid_map())
    assert (tbl["mean_lower"] <= tbl["mean_rn"] + 1e-12).all()
    assert (tbl["mean_rn"] <= tbl["mean_upper"] + 1e-12).all()


def test_to_latex_has_sector_names_and_spx_row():
    tex = to_latex(etf_summary_table(_results(), _secid_map()))
    assert r"\begin{tabular}" in tex and r"\bottomrule" in tex
    assert "Financials" in tex and "Regional Banks" in tex
    assert "S\\&P 500 index" in tex  # the benchmark row
