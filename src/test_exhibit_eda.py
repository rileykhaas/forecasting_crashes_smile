"""Tests for exhibit_eda.py (EDA coverage/availability/smile compute helpers)."""

from pathlib import Path

import pandas as pd
import pytest

from exhibit_eda import (
    availability_grid,
    constituent_frame,
    coverage_by_year,
    iv_smile,
    to_latex,
)

SURFACE_PATH = Path(__file__).resolve().parent.parent / "_data" / "clean_surface.parquet"
RETURNS_PATH = Path(__file__).resolve().parent.parent / "_data" / "realized_returns.parquet"


def _surface():
    """Two firms, one month, two maturities x two moneyness points (P and C)."""
    rows = []
    for secid in (1, 2):
        for mat in (30, 365):
            for mny, iv, cp in [(0.75, 0.50, "P"), (1.00, 0.30, "C")]:
                rows.append(dict(date=pd.Timestamp("2005-01-31"), secid=secid,
                                 days_to_maturity=mat, moneyness=mny,
                                 implied_vol=iv, spot_price=100.0, cp_flag=cp))
    return pd.DataFrame(rows)


def _returns():
    """12-month horizon: firm 1 crashes (0.70 <= 0.80), firm 2 does not (0.90)."""
    return pd.DataFrame([
        dict(date=pd.Timestamp("2005-01-31"), secid=1, horizon_months=12,
             realized_gross_return=0.70),
        dict(date=pd.Timestamp("2005-01-31"), secid=2, horizon_months=12,
             realized_gross_return=0.90),
        # a 1-month decoy row that the 12-month crash column must ignore
        dict(date=pd.Timestamp("2005-01-31"), secid=1, horizon_months=1,
             realized_gross_return=0.10),
    ])


def test_coverage_counts_and_crash_frequency():
    cov = coverage_by_year(_surface(), _returns())
    assert len(cov) == 1
    row = cov.iloc[0]
    assert row["year"] == 2005
    assert row["n_names"] == 2
    assert row["n_firm_months"] == 2          # (date, secid) pairs
    assert row["n_quotes"] == 8               # 2 firms x 2 mats x 2 strikes
    assert row["quotes_per_fm"] == 4          # median quotes per firm-month
    assert row["median_iv"] == pytest.approx(0.40)  # median of {.5,.3,.5,.3,...}
    assert row["crash_freq"] == pytest.approx(0.5)   # firm 1 crashes, firm 2 not


def test_availability_grid_is_share_of_firm_months():
    grid = availability_grid(_surface())
    # both firms carry the 0.75 (bin [0.70,0.80)) and 1.00 (bin [1.00,1.05)) points
    # at both maturities -> those cells are fully covered (share 1.0).
    assert grid.loc[30].max() == pytest.approx(1.0)
    assert grid.loc[365].max() == pytest.approx(1.0)
    # a moneyness bin with no quotes (e.g. deep ITM 1.35-1.60) is absent/NaN.
    assert grid.to_numpy().shape[0] == 4  # one row per maturity


def test_iv_smile_median_by_maturity():
    smile = iv_smile(_surface())
    # 0.75 bin -> median IV 0.50; 1.00 bin -> median IV 0.30, at every maturity.
    got = smile.loc[30].dropna().tolist()
    assert 0.50 in [round(v, 2) for v in got]
    assert 0.30 in [round(v, 2) for v in got]


def test_to_latex_has_one_row_per_year():
    tex = to_latex(coverage_by_year(_surface(), _returns()))
    assert r"\begin{tabular}" in tex and r"\bottomrule" in tex
    assert "2005 &" in tex


@pytest.mark.skipif(not (SURFACE_PATH.exists() and RETURNS_PATH.exists()),
                    reason="clean_surface/realized_returns parquet not built yet")
def test_real_panel_coverage_is_broad_and_continuous():
    surface = pd.read_parquet(SURFACE_PATH)
    returns = pd.read_parquet(RETURNS_PATH)
    universe = pd.read_parquet(
        Path(__file__).resolve().parent.parent / "_data" / "sp500_secid_universe.parquet")
    cov = coverage_by_year(
        constituent_frame(surface, universe),
        constituent_frame(returns, universe))
    # the replication panel spans 1996-2022 with ~500 constituent names each year.
    assert cov["year"].min() == 1996 and cov["year"].max() == 2022
    assert cov["n_names"].between(400, 600).all()
    assert (cov["crash_freq"] >= 0).all() and (cov["crash_freq"] <= 1).all()
