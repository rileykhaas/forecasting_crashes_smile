"""Unit tests for the S&P 500 secid-universe builder.

These test the membership/link logic on tiny synthetic frames, so they run with
no WRDS connection. They pin the behaviour that downstream slices rely on:
range-based membership, date-valid links, best-score selection, and keeping
index members that have no OptionMetrics linkage.
"""

import pandas as pd

from sp500_secid_universe import (
    build_sp500_secid_universe,
    get_universe_secids,
    month_end_trading_days,
)

# A three-month formation grid used by most tests.
MONTH_ENDS = pd.to_datetime(["2020-01-31", "2020-02-28", "2020-03-31"])


def test_membership_is_range_based():
    """A permno is a member exactly on the month-ends inside its spell."""
    constituents = pd.DataFrame(
        {
            "permno": [10001],
            "start": pd.to_datetime(["2020-02-01"]),
            "ending": pd.to_datetime(["2020-03-15"]),
        }
    )
    link = pd.DataFrame(
        {
            "secid": pd.Series([], dtype="int64"),
            "permno": pd.Series([], dtype="int64"),
            "score": pd.Series([], dtype="int64"),
            "sdate": pd.to_datetime([]),
            "edate": pd.to_datetime([]),
        }
    )
    out = build_sp500_secid_universe(constituents, link, month_ends=MONTH_ENDS)
    # Member on Feb 28 and Mar 31? No -- ending is Mar 15, so only Feb 28.
    assert list(out["date"]) == [pd.Timestamp("2020-02-28")]
    assert out.loc[0, "permno"] == 10001
    assert pd.isna(out.loc[0, "secid"])  # no link exists


def test_best_score_link_wins():
    """When two secids link a permno on a date, the lowest score is chosen."""
    constituents = pd.DataFrame(
        {
            "permno": [10001],
            "start": pd.to_datetime(["2019-01-01"]),
            "ending": pd.to_datetime(["2025-01-01"]),
        }
    )
    link = pd.DataFrame(
        {
            "secid": [500, 999],
            "permno": [10001, 10001],
            "score": [1, 5],  # 500 is the better match
            "sdate": pd.to_datetime(["2019-01-01", "2019-01-01"]),
            "edate": pd.to_datetime(["2025-01-01", "2025-01-01"]),
        }
    )
    out = build_sp500_secid_universe(constituents, link, month_ends=MONTH_ENDS)
    assert (out["secid"] == 500).all()
    assert get_universe_secids(out) == [500]


def test_link_must_be_date_valid():
    """A link whose window does not cover the date is not applied."""
    constituents = pd.DataFrame(
        {
            "permno": [10001],
            "start": pd.to_datetime(["2020-01-01"]),
            "ending": pd.to_datetime(["2020-12-31"]),
        }
    )
    # Link only valid from March onward.
    link = pd.DataFrame(
        {
            "secid": [500],
            "permno": [10001],
            "score": [1],
            "sdate": pd.to_datetime(["2020-03-01"]),
            "edate": pd.to_datetime(["2020-12-31"]),
        }
    )
    out = build_sp500_secid_universe(constituents, link, month_ends=MONTH_ENDS)
    by_date = out.set_index("date")["secid"]
    assert pd.isna(by_date[pd.Timestamp("2020-01-31")])
    assert pd.isna(by_date[pd.Timestamp("2020-02-28")])
    assert by_date[pd.Timestamp("2020-03-31")] == 500


def test_secid_universe_dedupes_and_sorts():
    """get_universe_secids returns sorted unique linked secids only."""
    constituents = pd.DataFrame(
        {
            "permno": [1, 2, 3],
            "start": pd.to_datetime(["2019-01-01"] * 3),
            "ending": pd.to_datetime(["2025-01-01"] * 3),
        }
    )
    link = pd.DataFrame(
        {
            "secid": [700, 300, 300],  # permnos 2 and 3 share a secid; 1 unlinked
            "permno": [2, 3, 3],
            "score": [1, 1, 2],
            "sdate": pd.to_datetime(["2019-01-01"] * 3),
            "edate": pd.to_datetime(["2025-01-01"] * 3),
        }
    )
    out = build_sp500_secid_universe(constituents, link, month_ends=MONTH_ENDS)
    assert get_universe_secids(out) == [300, 700]
    # permno 1 is retained as a member even with no secid.
    assert (out["permno"] == 1).any()


def test_carry_forward_current_members():
    """Current members (spell ends at the vintage cap) freeze forward; a genuine
    earlier deletion does not, and the carried_forward flag marks frozen rows."""
    month_ends = pd.to_datetime(
        ["2024-06-28", "2024-12-31", "2025-01-31", "2025-02-28"]
    )
    constituents = pd.DataFrame(
        {
            "permno": [1, 2],
            "start": pd.to_datetime(["2000-01-01", "2000-01-01"]),
            # permno 1 is current (ends at the cap); permno 2 was deleted earlier.
            "ending": pd.to_datetime(["2024-12-31", "2024-06-30"]),
        }
    )
    link = pd.DataFrame(
        {
            "secid": [11, 22],
            "permno": [1, 2],
            "score": [1, 1],
            "sdate": pd.to_datetime(["2000-01-01", "2000-01-01"]),
            "edate": pd.to_datetime(["2030-01-01", "2030-01-01"]),
        }
    )

    # Without carry-forward: no members past the vintage cap (2024-12-31).
    off = build_sp500_secid_universe(constituents, link, month_ends=month_ends)
    assert off["date"].max() == pd.Timestamp("2024-12-31")
    assert not off["carried_forward"].any()

    # With carry-forward: permno 1 persists into 2025; permno 2 (deleted in
    # June, before the cap) never returns.
    on = build_sp500_secid_universe(
        constituents, link, month_ends=month_ends, carry_forward_current=True
    )
    by = on.groupby("date")["permno"].apply(set)
    assert by[pd.Timestamp("2024-06-28")] == {1, 2}
    assert by[pd.Timestamp("2024-12-31")] == {1}
    assert by[pd.Timestamp("2025-01-31")] == {1}
    assert by[pd.Timestamp("2025-02-28")] == {1}
    # Only the frozen 2025 rows are flagged.
    assert on.loc[on["date"] > pd.Timestamp("2024-12-31"), "carried_forward"].all()
    assert not on.loc[on["date"] <= pd.Timestamp("2024-12-31"), "carried_forward"].any()


def test_month_end_trading_days_are_real_sessions():
    """The grid returns one last-trading-day per month, on weekdays."""
    days = month_end_trading_days("2021-01-01", "2021-03-31")
    assert len(days) == 3
    # Jan 2021 last session is Fri Jan 29 (30/31 are weekend).
    assert days[0] == pd.Timestamp("2021-01-29")
    assert all(d.weekday() < 5 for d in days)
