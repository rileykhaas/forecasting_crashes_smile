"""Tests for the SVB case study (exhibit_svb.py, #31)."""

from pathlib import Path

import pandas as pd
import pytest

from exhibit_svb import (
    _empty_realized,
    _panel_series,
    compute_svb_bounds,
    daily_clean_surface,
    realized_to_latex,
    svb_realized_table,
)
from pull_svb_daily import SIVB_SECID, XLF_SECID

DATA_DIR = Path(__file__).resolve().parent.parent / "_data"


def _raw(secid=110012, date="2023-03-09", days=30, n=12, dispersion=0.01, strike0=90.0):
    """n standardized-surface rows for one secid-day-maturity (distinct strikes)."""
    return pd.DataFrame(
        {
            "secid": secid,
            "date": pd.Timestamp(date),
            "days": days,
            "cp_flag": "C",
            "delta": 0.5,
            "impl_volatility": 0.3,
            "impl_strike": [strike0 + i for i in range(n)],
            "dispersion": dispersion,
        }
    )


def test_daily_clean_uses_exact_date_spot():
    """Spot is joined per trading day, so the same strike gives a different moneyness
    on two days with different spot."""
    raw = pd.concat(
        [_raw(date="2023-03-08", strike0=100.0), _raw(date="2023-03-09", strike0=100.0)]
    )
    spot = pd.DataFrame(
        {
            "secid": [110012, 110012],
            "date": pd.to_datetime(["2023-03-08", "2023-03-09"]),
            "spot_price": [100.0, 50.0],  # spot halves on the 9th
        }
    )
    out = daily_clean_surface(raw, spot)
    m8 = out[out["date"] == "2023-03-08"]["moneyness"].min()
    m9 = out[out["date"] == "2023-03-09"]["moneyness"].min()
    assert m8 == pytest.approx(1.00)  # 100 / 100
    assert m9 == pytest.approx(2.00)  # 100 / 50


def test_daily_clean_applies_appendix_d_filters():
    raw = pd.concat(
        [
            _raw(secid=1, dispersion=0.03),  # kept
            _raw(secid=2, dispersion=0.06),  # dispersion too high -> dropped
            _raw(secid=3, n=10),  # only 10 strikes -> dropped
        ]
    )
    spot = pd.DataFrame(
        {
            "secid": [1, 2, 3],
            "date": [pd.Timestamp("2023-03-09")] * 3,
            "spot_price": [100.0] * 3,
        }
    )
    assert set(daily_clean_surface(raw, spot)["secid"]) == {1}


def test_empty_realized_is_typed_and_empty():
    er = _empty_realized()
    assert len(er) == 0
    assert list(er.columns) == [
        "date",
        "secid",
        "horizon_months",
        "realized_gross_return",
    ]


def test_realized_table_flags_crash_by_drawdown():
    """A 20% threshold: a -25% drawdown is a crash, a -10% one is not."""
    bounds = pd.DataFrame(
        {  # peak P* for one secid at q=0.80, 30-day
            "date": pd.to_datetime(["2023-03-09", "2023-03-09"]),
            "secid": [SIVB_SECID, XLF_SECID],
            "threshold_q": [0.80, 0.80],
            "horizon_months": [1, 1],
            "bound_lower": [0.30, 0.04],
            "prob_riskneutral": [0.35, 0.06],
            "bound_upper": [0.4, 0.1],
        }
    )
    spot = pd.DataFrame(
        {
            "secid": [SIVB_SECID, SIVB_SECID, XLF_SECID, XLF_SECID],
            "date": pd.to_datetime(
                ["2023-03-08", "2023-03-20", "2023-03-08", "2023-03-20"]
            ),
            "spot_price": [100.0, 75.0, 100.0, 90.0],  # SIVB -25%, XLF -10%
        }
    )
    tbl = svb_realized_table(bounds, spot)
    by = tbl.set_index("ticker")
    assert by.loc["SIVB", "realized_drawdown"] == pytest.approx(-0.25)
    assert bool(by.loc["SIVB", "crashed"]) is True
    assert by.loc["XLF", "realized_drawdown"] == pytest.approx(-0.10)
    assert bool(by.loc["XLF", "crashed"]) is False
    assert "Yes" in realized_to_latex(tbl) and "No" in realized_to_latex(tbl)


@pytest.mark.skipif(
    not (DATA_DIR / "svb_daily_surface.parquet").exists(),
    reason="SVB daily pull not run yet",
)
def test_real_svb_story_holds():
    """On the pulled data: SIVB's surface ends at its 2023-03-09 collapse, and the
    stress is contained (SIVB peak > KRE > XLF)."""
    from pull_svb_daily import KRE_SECID, load_svb_spot, load_svb_surface, load_svb_zero

    bounds = compute_svb_bounds(load_svb_surface(), load_svb_spot(), load_svb_zero())
    sivb = _panel_series(bounds, SIVB_SECID, 0.80, 30)
    assert sivb["date"].max() == pd.Timestamp("2023-03-09")  # ends at the collapse
    peak = lambda sid: _panel_series(bounds, sid, 0.80, 30)["prob_riskneutral"].max()
    assert (
        peak(SIVB_SECID) > peak(KRE_SECID) > peak(XLF_SECID)
    )  # contained, not systemic
