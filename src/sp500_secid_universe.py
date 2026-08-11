"""Build the month-end S&P 500 constituent *secid* universe (Slice 2).

This is where the two Slice-2 pulls meet. Martin & Shi (2025) form the panel on
"the last trading day of each month t" and study "all firms that are S&P 500
constituents during month t." This module turns:

    pull_sp500.py  -> which permnos are index members, by date range
    pull_link.py   -> permno <-> secid, by date range

into a firm-month panel keyed on the last trading day of each month: one row per
(date, permno) that is an index member on that date, with the OptionMetrics
``secid`` attached where one exists. Downstream:

    pull_optionmetrics.py -> needs the *set of secids* to pull vol surfaces for
                             (get_universe_secids)
    realized_returns.py   -> needs the (date, permno, secid) linkage

The month-end grid uses the NYSE trading calendar (pandas-market-calendars), so
"last trading day of the month" is a real session, not a calendar month-end.

Output columns (``sp500_secid_universe.parquet``)
-------------------------------------------------
date            : datetime  last NYSE trading day of the month (formation date)
permno          : int       CRSP permno, an S&P 500 member on ``date``
secid           : Int64     OptionMetrics secid (nullable: member may lack options)
score           : Int64     link match quality that produced ``secid`` (1 = best)
carried_forward : bool      row falls past the CRSP constituent vintage and its
                            membership was frozen from the last known date
                            (see ``carry_forward_current`` below); always False
                            for paper-exact replication

Extending past the CRSP constituent vintage
-------------------------------------------
``crsp.msp500list`` marks names still in the index at the last CRSP update with
a common "ending" sentinel (the data vintage, e.g. 2024-12-31). To push the
firm-month panel past that date, ``build_sp500_secid_universe`` can optionally
carry those *current* members forward, holding index membership fixed from the
vintage to the end of the month-end grid. This is a deliberate approximation:
the ~20-25 S&P 500 add/deletes per year are ignored over the extension tail, so
a small, growing fraction of names is misclassified the further past the vintage
one goes. It is off by default (paper replication and the synthetic tests never
freeze membership) and enabled explicitly in the pipeline ``__main__``.
"""

from pathlib import Path

import pandas as pd
import pandas_market_calendars as mcal

from settings import config

DATA_DIR = Path(config("DATA_DIR"))
START_DATE = config("START_DATE")
END_DATE = config("END_DATE")


def month_end_trading_days(start_date=START_DATE, end_date=END_DATE, calendar="NYSE"):
    """Return the last trading day of each month over [start_date, end_date].

    Uses the exchange calendar so month-ends fall on real sessions (e.g. a
    31st that is a Sunday resolves back to the prior Friday session).
    """
    cal = mcal.get_calendar(calendar)
    schedule = cal.schedule(start_date=start_date, end_date=end_date)
    days = pd.DatetimeIndex(schedule.index).normalize()
    # Last session within each calendar (year, month).
    last = (
        pd.Series(days, index=days)
        .groupby([days.year, days.month])
        .max()
    )
    return pd.DatetimeIndex(sorted(last.to_numpy()))


def build_sp500_secid_universe(
    constituents, link, month_ends=None, carry_forward_current=False
):
    """Expand membership to a month-end panel and attach the best secid.

    Parameters
    ----------
    constituents : DataFrame
        Output of ``pull_sp500.pull_sp500_constituents`` (permno, start, ending).
    link : DataFrame
        Output of ``pull_link.pull_crsp_optionm_link``
        (secid, permno, score, sdate, edate).
    month_ends : DatetimeIndex, optional
        Formation dates. Defaults to ``month_end_trading_days()`` over the
        configured sample window.
    carry_forward_current : bool, default False
        If True, freeze the membership of *current* constituents (those whose
        spell ends at the CRSP vintage cap, ``constituents["ending"].max()``)
        forward to the last formation date, so the panel can extend past the
        vintage. Historical deletions (ending before the cap) are never touched.
        Off by default so paper-exact replication and the synthetic tests are
        unaffected. See the module docstring for the caveats.

    Returns
    -------
    DataFrame with columns [date, permno, secid, score, carried_forward], one
    row per (date, permno) index member. ``secid``/``score`` are nullable Int64
    and are NaN for members with no valid OptionMetrics link on that date.
    ``carried_forward`` marks rows past the vintage cap (always False unless
    ``carry_forward_current`` is enabled).
    """
    if month_ends is None:
        month_ends = month_end_trading_days()
    month_ends = pd.DatetimeIndex(month_ends)

    constituents = constituents.copy()
    # The CRSP vintage cap: the common "ending" that marks names still in the
    # index at the last CRSP update. Used both to (optionally) carry current
    # members forward and to flag which output rows are frozen.
    vintage_cap = constituents["ending"].max() if len(constituents) else pd.NaT
    if (
        carry_forward_current
        and len(month_ends)
        and pd.notna(vintage_cap)
        and month_ends.max() > vintage_cap
    ):
        is_current = constituents["ending"] == vintage_cap
        constituents.loc[is_current, "ending"] = month_ends.max()

    grid = pd.DataFrame({"date": month_ends})

    # 1) Which permnos are index members on each formation date? A spell
    #    [start, ending] contributes date d iff start <= d <= ending.
    members = constituents.merge(grid, how="cross")
    in_spell = (members["start"] <= members["date"]) & (
        members["date"] <= members["ending"]
    )
    members = (
        members.loc[in_spell, ["date", "permno"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )

    # 2) Attach secid via a date-valid link, preferring the best (lowest) score.
    cand = members.merge(link, on="permno", how="left")
    valid = (cand["sdate"] <= cand["date"]) & (cand["date"] <= cand["edate"])
    best = (
        cand.loc[valid]
        .sort_values(["date", "permno", "score", "secid"])
        .drop_duplicates(["date", "permno"], keep="first")[
            ["date", "permno", "secid", "score"]
        ]
    )

    # 3) Left-join back so members without a valid link are kept (secid = NaN).
    out = members.merge(best, on=["date", "permno"], how="left")
    out["permno"] = out["permno"].astype("int64")
    out["secid"] = out["secid"].astype("Int64")
    out["score"] = out["score"].astype("Int64")
    # Flag rows whose membership was frozen past the CRSP vintage cap.
    out["carried_forward"] = (
        out["date"] > vintage_cap if pd.notna(vintage_cap) else False
    )
    return out.sort_values(["date", "secid"]).reset_index(drop=True)


def get_universe_secids(universe):
    """Return the sorted unique secids in the universe (drops unlinked members).

    This is the secid list ``pull_optionmetrics`` iterates over, plus the index
    itself (``schema.SPX_SECID``) which the caller adds separately.
    """
    secids = universe["secid"].dropna().astype("int64").unique()
    return sorted(int(s) for s in secids)


def load_sp500_secid_universe(data_dir=DATA_DIR):
    """Load the cached month-end secid universe from DATA_DIR."""
    path = Path(data_dir) / "sp500_secid_universe.parquet"
    return pd.read_parquet(path)


if __name__ == "__main__":
    from pull_link import load_crsp_optionm_link
    from pull_sp500 import load_sp500_constituents

    constituents = load_sp500_constituents()
    link = load_crsp_optionm_link()
    # Extend the panel past the CRSP constituent vintage by freezing current
    # members forward to END_DATE (see module docstring for the caveats).
    universe = build_sp500_secid_universe(
        constituents, link, carry_forward_current=True
    )
    universe.to_parquet(Path(DATA_DIR) / "sp500_secid_universe.parquet")
