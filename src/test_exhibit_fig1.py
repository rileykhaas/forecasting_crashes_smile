"""Tests for exhibit_fig1.py (Figure 1 selection logic)."""

import pandas as pd

from exhibit_fig1 import series_for


def _results():
    dates = pd.to_datetime(
        ["2005-06-30", "2005-05-31", "2030-01-31"]
    )  # incl. out-of-window
    rows = []
    for secid in (101397, 999):  # AIG + a decoy name
        for q in (0.70, 0.80):
            for h in (1, 12):
                for d in dates:
                    rows.append(
                        {
                            "date": d,
                            "secid": secid,
                            "threshold_q": q,
                            "horizon_months": h,
                            "bound_lower": 0.1,
                            "prob_riskneutral": 0.15,
                            "bound_upper": 0.2,
                        }
                    )
    return pd.DataFrame(rows)


def test_series_for_filters_name_threshold_horizon_and_window():
    s = series_for(_results(), 101397)  # AIG, q=0.80, h=1 by default
    assert set(s["secid"]) == {101397}
    assert set(s["threshold_q"]) == {0.80}
    assert set(s["horizon_months"]) == {1}
    # the 2030 row is outside the 1996-2022 default window -> dropped
    assert s["date"].max() <= pd.Timestamp("2022-12-31")
    assert len(s) == 2  # the two in-window month-ends


def test_series_for_is_sorted_by_date():
    s = series_for(_results(), 101397)
    assert list(s["date"]) == sorted(s["date"])
