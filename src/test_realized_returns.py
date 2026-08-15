"""Unit tests for the realized forward-return builder (realized_returns.py).

These pin the logic the crash regressions depend on, on tiny synthetic frames
(no WRDS): forward gross compounding over each horizon, that a total wipeout
(gross return 0, e.g. a delisting) survives rather than being dropped, and the
date-valid best-score secid join.
"""

import pandas as pd

import schema
from realized_returns import build_realized_returns


def _crsp(permno, rets, start="2020-01-31"):
    """CRSP-style monthly frame: one permno, consecutive month-ends, given rets."""
    dates = pd.date_range(start, periods=len(rets), freq="ME")
    return pd.DataFrame({"permno": permno, "date": dates, "ret": rets})


def _link(rows):
    """Link frame from (secid, permno, score, sdate, edate) tuples."""
    df = pd.DataFrame(rows, columns=["secid", "permno", "score", "sdate", "edate"])
    df["sdate"] = pd.to_datetime(df["sdate"])
    df["edate"] = pd.to_datetime(df["edate"])
    return df


def test_forward_gross_compounding():
    """R_{t->t+h} is the product of the next h monthly gross returns."""
    # gross returns from Feb on: 0.80, 1.00, 1.50, 1.10, 1.00
    crsp = _crsp(1, [0.10, -0.20, 0.00, 0.50, 0.10, 0.00])
    link = _link([(500, 1, 1, "2019-01-01", "2025-01-01")])
    out = build_realized_returns(crsp, link)

    first_1m = out[out.horizon_months == 1].sort_values("date").iloc[0]
    assert abs(first_1m.realized_gross_return - 0.80) < 1e-9  # Jan -> Feb

    first_3m = out[out.horizon_months == 3].sort_values("date").iloc[0]
    assert abs(first_3m.realized_gross_return - 0.80 * 1.00 * 1.50) < 1e-9


def test_total_wipeout_is_captured():
    """A -100% month (gross return 0, e.g. a delisting) survives, not NaN-dropped."""
    crsp = _crsp(2, [0.0, -1.0])  # gross Feb == 0
    link = _link([(600, 2, 1, "2019-01-01", "2025-01-01")])
    out = build_realized_returns(crsp, link)
    assert (out[out.horizon_months == 1].realized_gross_return == 0.0).any()


def test_secid_join_is_date_valid_and_best_score():
    """Among links, the lowest score that is date-valid wins; invalid links drop."""
    crsp = _crsp(3, [0.0, 0.10])
    link = _link(
        [
            (300, 3, 1, "2019-01-01", "2025-01-01"),  # valid, best score -> wins
            (700, 3, 5, "2019-01-01", "2025-01-01"),  # valid, worse score
            (999, 3, 1, "2021-01-01", "2025-01-01"),  # score 1 but not valid in 2020
        ]
    )
    out = build_realized_returns(crsp, link)
    assert set(out.secid.unique()) == {300}


def test_universe_secids_restricts_output():
    """universe_secids scopes the panel to the analysis names only."""
    crsp = pd.concat([_crsp(1, [0.0, 0.1]), _crsp(2, [0.0, 0.1])])
    link = _link(
        [
            (500, 1, 1, "2019-01-01", "2025-01-01"),
            (600, 2, 1, "2019-01-01", "2025-01-01"),
        ]
    )
    out = build_realized_returns(crsp, link, universe_secids=[500])
    assert set(out.secid.unique()) == {500}


def test_schema_conforms():
    crsp = _crsp(1, [0.05, 0.05, 0.05, 0.05])
    link = _link([(500, 1, 1, "2019-01-01", "2025-01-01")])
    out = build_realized_returns(crsp, link)
    assert schema.validate_schema(out, "realized_returns")
