"""Guardrail: the extension sector ETFs (#34) must NEVER enter the replication
exhibits (Tables 1-2, Figures 1-2/6, the EDA panel), only the extension ones.

The ETFs now live in results.parquet alongside the constituents, so the invariant
that keeps the replication faithful is that every replication exhibit restricts to
the S&P 500 constituent universe (or hardcoded names), which excludes both the ETFs
and the SPX index. These tests pin that invariant with synthetic frames, plus a
real-data check that the cached universe carries no ETF/index secid.
"""

from pathlib import Path

import pandas as pd
import pytest

import schema
from exhibit_eda import constituent_frame
from exhibit_fig2 import cross_sectional_medians
from exhibit_table1 import build_table1

ETF_SECIDS = {
    110007,
    110008,
    110009,
    110010,
    110011,
    110012,
    110013,
    110014,
    110015,
    127104,
    208181,
    213084,
}
DATA_DIR = Path(__file__).resolve().parent.parent / "_data"


def _member_panel():
    dates = pd.to_datetime(["2010-01-31", "2010-02-28"])
    return pd.DataFrame({"date": list(dates) * 2, "secid": [1, 1, 2, 2]}).astype(
        {"secid": "Int64"}
    )


def _results_with_etf():
    """Constituents 1 & 2 plus a sector ETF (110012) with deliberately extreme
    bounds, at q=0.80/horizon=1, over two months."""
    rows = []
    for date in ["2010-01-31", "2010-02-28"]:
        for secid, lo, hi in [(1, 0.02, 0.06), (2, 0.04, 0.10), (110012, 0.99, 0.99)]:
            rows.append(
                {
                    "date": pd.Timestamp(date),
                    "secid": secid,
                    "threshold_q": 0.80,
                    "horizon_months": 1,
                    "bound_lower": lo,
                    "prob_riskneutral": 0.5,
                    "bound_upper": hi,
                    "realized_gross_return": 1.0,
                    "realized_flag": 0,
                }
            )
    df = pd.DataFrame(rows)
    df["realized_flag"] = df["realized_flag"].astype("Int64")
    return df


def test_fig2_medians_ignore_etf_rows():
    """An ETF in results but not in the member panel must not move the medians."""
    med = cross_sectional_medians(
        _results_with_etf(),
        _member_panel(),
        start=pd.Timestamp("2010-01-01"),
        end=pd.Timestamp("2010-12-31"),
    )
    jan = med[med["date"] == "2010-01-31"].iloc[0]
    # median over constituents {1,2} only: lower med(0.02,0.04)=0.03 (not the 0.99 ETF)
    assert jan["bound_lower"] == 0.03


def test_table1_excludes_etf_rows():
    """Table 1's across-firms mean is over constituents only (the 0.99 ETF is gone)."""
    stats = build_table1(
        _results_with_etf(),
        _member_panel(),
        start=pd.Timestamp("2010-01-01"),
        end=pd.Timestamp("2010-12-31"),
    )
    lb = stats[
        (stats["q"] == 0.80)
        & (stats["measure"] == "lower bound")
        & (stats["block"] == "firms")
        & (stats["horizon"] == 1)
    ]["mean"].iloc[0]
    assert lb == pytest.approx(0.03)  # mean of monthly cross-firm means over {1,2}
    assert stats.attrs["n_firms"] == 2  # the ETF is not counted as a firm


def test_eda_constituent_frame_drops_etfs():
    """constituent_frame keeps only member-months, dropping ETF secids."""
    surface = pd.DataFrame(
        {
            "date": pd.to_datetime(["2010-01-31"] * 3),
            "secid": [1, 2, 110012],
            "days_to_maturity": [30, 30, 30],
            "moneyness": [1.0, 1.0, 1.0],
            "implied_vol": [0.2, 0.2, 0.2],
            "spot_price": [100.0, 100.0, 100.0],
            "cp_flag": ["C", "C", "C"],
        }
    )
    out = constituent_frame(surface, _member_panel())
    assert set(out["secid"]) == {1, 2}
    assert 110012 not in set(out["secid"])


@pytest.mark.skipif(
    not (DATA_DIR / "sp500_secid_universe.parquet").exists(),
    reason="universe parquet not built yet",
)
def test_universe_carries_no_etf_or_index_secid():
    uni = pd.read_parquet(DATA_DIR / "sp500_secid_universe.parquet", columns=["secid"])
    usec = set(pd.to_numeric(uni["secid"], errors="coerce").dropna().astype(int))
    assert ETF_SECIDS.isdisjoint(usec)  # no sector ETF is a constituent
    assert schema.SPX_SECID not in usec  # nor is the index
