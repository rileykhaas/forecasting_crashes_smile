"""Pull raw OptionMetrics data from WRDS (Slice 1).

Fetches, for the last trading day of each month over [START_DATE, END_DATE], the
OptionMetrics inputs the bound calculation needs:

  - the IvyDB volatility surface (``vsurfd``) for the S&P 500 index (SPX_SECID),
    every S&P 500 constituent secid (from the #14 universe), AND the extension
    ETFs (the Select Sector SPDRs + KRE), at the four standardized maturities
    that match the paper's 1/3/6/12-month horizons;
  - the zero-coupon yield curve (``zerocd``);
  - the security NAME history (``secnmd``), used both to resolve the ETF tickers
    to secids (its ``effect_date`` disambiguates ticker reuse) and as an
    as-of-date name lookup for the pulled universe.

This file ONLY fetches and caches raw pulls to DATA_DIR (gitignored). The
Appendix-D quality filters (dispersion band, >10 strikes, flat extrapolation)
and interpolation live in clean_surface.py / rates.py (#17), NOT here.

WRDS specifics to verify against your subscription
--------------------------------------------------
The OptionMetrics library and table names differ across WRDS vintages. This
module centralises them in the constants below; check them in the WRDS data
dictionary (OptionMetrics) before the first run and adjust if needed:
  - ``OPTIONM_LIB``: "optionm_all" (combined) vs legacy "optionm".
  - the volatility surface is stored PER YEAR as ``vsurfd{YYYY}``.
  - ``secnmd`` / ``zerocd`` are single (not per-year) tables.

"pull_" = hits the network; a matching "load_" reads the cached pull back.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd
import wrds

from schema import EXTENSION_ETF_TICKERS, MATURITIES_DAYS, SPX_SECID
from settings import config
from sp500_secid_universe import (
    get_universe_secids,
    load_sp500_secid_universe,
    month_end_trading_days,
)

DATA_DIR = Path(config("DATA_DIR"))
# default="" so the module imports without WRDS credentials (the WRDS-free unit
# tests import assemble_pull_secids; CI has no WRDS_USERNAME). A real pull
# supplies the username via .env / environment.
WRDS_USERNAME = config("WRDS_USERNAME", default="")
START_DATE = config("START_DATE")
END_DATE = config("END_DATE")

# --- WRDS names (verify against the WRDS data dictionary; see module docstring)
OPTIONM_LIB = "optionm_all"
# secnmd = security NAME history (secid, ticker, effect_date, issuer, ...). Used
# for both ETF ticker resolution (effect_date disambiguates ticker reuse) and
# as-of-date name labels. Columns per the WRDS secnmd data dictionary.
SECNMD_TABLE = f"{OPTIONM_LIB}.secnmd"
ZEROCD_TABLE = f"{OPTIONM_LIB}.zerocd"
VSURFD_TABLE_FMT = OPTIONM_LIB + ".vsurfd{year}"  # per-year surface tables


def _sql_int_list(values):
    """Render an iterable of ints as a SQL ``IN`` list body: ``1, 2, 3``."""
    return ", ".join(str(int(v)) for v in values)


def _sql_str_list(values):
    """Render an iterable of strings as a SQL ``IN`` list body: ``'A', 'B'``."""
    return ", ".join("'" + str(v).replace("'", "''") + "'" for v in values)


def resolve_etf_secids(tickers=EXTENSION_ETF_TICKERS, wrds_username=WRDS_USERNAME):
    """Resolve extension-ETF tickers to OptionMetrics secids via ``secnmd``.

    A ticker can be reused across securities over time (e.g. KRE mapped to both an
    old secid and the current ETF), so we resolve on the security NAME history and
    pick the secid whose MOST RECENT name spell carries the ticker -- i.e. the
    security that currently trades under it. ``securd`` (the reference file) has no
    dates and cannot make this distinction.

    Returns
    -------
    DataFrame with columns [ticker, secid], one row per input ticker found;
    tickers with no match are omitted (and reported).
    """
    query = f"""
        SELECT secid, ticker, effect_date
        FROM {SECNMD_TABLE}
        WHERE ticker IN ({_sql_str_list(tickers)})
    """
    db = wrds.Connection(wrds_username=wrds_username)
    hits = db.raw_sql(query, date_cols=["effect_date"])
    db.close()

    resolved = []
    for tkr in tickers:
        rows = hits.loc[hits["ticker"] == tkr]
        if rows.empty:
            print(f"[resolve_etf_secids] WARNING: no secid found for {tkr!r}")
            continue
        # Secid whose latest name spell is this ticker == the current holder.
        secid = int(rows.sort_values("effect_date")["secid"].astype("int64").iloc[-1])
        candidates = sorted(rows["secid"].dropna().astype("int64").unique())
        if len(candidates) > 1:
            print(
                f"[resolve_etf_secids] NOTE: {tkr!r} ticker seen on {candidates}; "
                f"using {secid} (most recent name spell)."
            )
        resolved.append((tkr, secid))
    return pd.DataFrame(resolved, columns=["ticker", "secid"])


def assemble_pull_secids(constituent_secids, etf_secids, index_secid=SPX_SECID):
    """Union constituent, index, and ETF secids into one sorted, deduped list.

    Pure helper (no WRDS): the single source of the secid set the surface pull
    iterates over. Kept separate so it can be unit-tested without a connection.
    """
    all_secids = {int(s) for s in constituent_secids}
    all_secids.add(int(index_secid))
    all_secids.update(int(s) for s in etf_secids)
    return sorted(all_secids)


def pull_security_names(secids, wrds_username=WRDS_USERNAME):
    """Pull ``secnmd`` name-history rows for the given secids.

    secnmd is the security NAME history: one row per name spell, with an
    ``effect_date``. Downstream, a ``(secid, date)`` panel row can be labelled with
    the ticker/issuer active in that month via ``merge_asof`` on ``effect_date`` --
    historically correct over the 1996-2025 sample, where tickers change.
    """
    query = f"""
        SELECT secid, ticker, issuer, issue, cusip, class, sic, effect_date
        FROM {SECNMD_TABLE}
        WHERE secid IN ({_sql_int_list(secids)})
        ORDER BY secid, effect_date
    """
    db = wrds.Connection(wrds_username=wrds_username)
    df = db.raw_sql(query, date_cols=["effect_date"])
    db.close()
    return df


def _empty_month_ends(surface, month_ends):
    """Month-ends whose pulled surface is entirely OptionMetrics sentinel.

    OptionMetrics occasionally fails to compute a surface on the month-end
    snapshot: every row comes back with the -99.99 "missing" strike and null vol
    (e.g. 2020-07-31 in our vintage). Such a month-end has no row with a positive
    strike -- those are the ones the last-valid-day fallback handles.
    """
    month_ends = pd.DatetimeIndex(month_ends)
    if surface.empty:
        return list(month_ends)
    have = set(surface.loc[surface["impl_strike"] > 0, "date"].unique())
    return [d for d in month_ends if d not in have]


def _pull_month_last_valid(db, month_end, secid_in, days_in):
    """Surface rows for the last trading day WITH a valid fit in ``month_end``'s
    month, re-stamped to the month-end date.

    Used only for the empty month-ends flagged by ``_empty_month_ends``. Keeping
    the output date at the month-end means every downstream table (rates,
    realized_returns, results) still joins on the standard formation date; only
    the surface itself is a few days stale for that one month.
    """
    month_end = pd.Timestamp(month_end)
    month_start = month_end.replace(day=1)
    table = VSURFD_TABLE_FMT.format(year=month_end.year)
    max_q = f"""
        SELECT MAX(date) AS d
        FROM {table}
        WHERE secid IN ({secid_in})
          AND days IN ({days_in})
          AND date BETWEEN '{month_start:%Y-%m-%d}' AND '{month_end:%Y-%m-%d}'
          AND impl_strike > 0 AND impl_volatility IS NOT NULL
    """
    res = db.raw_sql(max_q, date_cols=["d"])
    if res.empty or pd.isna(res["d"].iloc[0]):
        return pd.DataFrame()
    source_date = pd.Timestamp(res["d"].iloc[0])
    full_q = f"""
        SELECT secid, date, days, cp_flag, delta,
               impl_volatility, impl_strike, dispersion
        FROM {table}
        WHERE secid IN ({secid_in})
          AND days IN ({days_in})
          AND date = '{source_date:%Y-%m-%d}'
    """
    out = db.raw_sql(full_q, date_cols=["date"])
    out["date"] = month_end  # re-stamp to the month-end formation date
    out.attrs["source_date"] = source_date
    return out


def pull_vol_surface(
    secids, month_ends, maturities=MATURITIES_DAYS, wrds_username=WRDS_USERNAME
):
    """Pull raw volatility-surface rows for the given secids and month-ends.

    Restricts server-side to (a) the secids, (b) the four horizon maturities,
    and (c) the month-end trading days, so the daily surface stays a manageable
    pull. Within each maturity slice the FULL smile (all deltas, both cp_flag)
    is kept -- the bounds integrate across strikes. No quality filtering here.

    Month-ends where OptionMetrics has no computed surface (all -99.99 sentinel,
    e.g. 2020-07-31) fall back to that month's last valid trading day, re-stamped
    to the month-end so downstream joins are unaffected.

    Returns a long DataFrame: one row per date x secid x maturity x delta x
    cp_flag, with the raw ``impl_volatility``, ``impl_strike`` and ``dispersion``
    carried through for the cleaning step (#17).
    """
    month_ends = pd.DatetimeIndex(month_ends)
    secid_in = _sql_int_list(secids)
    days_in = _sql_int_list(maturities)

    frames = []
    db = wrds.Connection(wrds_username=wrds_username)
    try:
        for year in range(month_ends.min().year, month_ends.max().year + 1):
            dates_this_year = month_ends[month_ends.year == year]
            if len(dates_this_year) == 0:
                continue
            date_in = _sql_str_list(d.strftime("%Y-%m-%d") for d in dates_this_year)
            query = f"""
                SELECT secid, date, days, cp_flag, delta,
                       impl_volatility, impl_strike, dispersion
                FROM {VSURFD_TABLE_FMT.format(year=year)}
                WHERE secid IN ({secid_in})
                  AND days IN ({days_in})
                  AND date IN ({date_in})
            """
            year_df = db.raw_sql(query, date_cols=["date"])
            frames.append(year_df)
            print(f"[pull_vol_surface] {year}: {len(year_df):,} rows", flush=True)

        surface = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        for month_end in _empty_month_ends(surface, month_ends):
            fb = _pull_month_last_valid(db, month_end, secid_in, days_in)
            if not fb.empty:
                src = pd.Timestamp(fb.attrs["source_date"]).date()
                print(
                    f"[pull_vol_surface] {month_end.date()} month-end empty; "
                    f"used {src} ({len(fb):,} rows)",
                    flush=True,
                )
                frames.append(fb)
    finally:
        db.close()

    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not df.empty:
        df["secid"] = df["secid"].astype("int64")
        df["days"] = df["days"].astype("int64")
    return df


def pull_zero_curve(
    start_date=START_DATE, end_date=END_DATE, wrds_username=WRDS_USERNAME
):
    """Pull the OptionMetrics zero-coupon yield curve (``zerocd``).

    Pulled over the whole sample window (the table is small); per-date maturity
    interpolation to the horizons happens in rates.py (#17).
    """
    if isinstance(start_date, datetime):
        start_date = start_date.strftime("%Y-%m-%d")
    if isinstance(end_date, datetime):
        end_date = end_date.strftime("%Y-%m-%d")
    query = f"""
        SELECT date, days, rate
        FROM {ZEROCD_TABLE}
        WHERE date BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY date, days
    """
    db = wrds.Connection(wrds_username=wrds_username)
    df = db.raw_sql(query, date_cols=["date"])
    db.close()
    return df


def load_vol_surface(data_dir=DATA_DIR):
    """Load the cached raw volatility surface from DATA_DIR."""
    return pd.read_parquet(Path(data_dir) / "optionm_vol_surface.parquet")


def load_zero_curve(data_dir=DATA_DIR):
    """Load the cached zero-coupon curve from DATA_DIR."""
    return pd.read_parquet(Path(data_dir) / "optionm_zero_curve.parquet")


def load_security_names(data_dir=DATA_DIR):
    """Load the cached security-name file from DATA_DIR."""
    return pd.read_parquet(Path(data_dir) / "optionm_security_names.parquet")


def load_option_pull_secids(data_dir=DATA_DIR):
    """Load the cached manifest of pulled secids and their source tag."""
    return pd.read_parquet(Path(data_dir) / "optionm_pull_secids.parquet")


if __name__ == "__main__":
    # 1) Assemble the pull universe: S&P 500 constituent secids (#14) + the
    #    index + the extension ETFs (resolved from tickers via secnmd).
    constituent_secids = get_universe_secids(load_sp500_secid_universe())
    etf_map = resolve_etf_secids()
    all_secids = assemble_pull_secids(constituent_secids, etf_map["secid"])

    # A small manifest tagging each secid's source (index / constituent /
    # sector_etf), so downstream can cleanly separate replication from extension.
    source = {SPX_SECID: "index"}
    for s in constituent_secids:
        source.setdefault(int(s), "constituent")
    ticker_by_secid = dict(zip(etf_map["secid"], etf_map["ticker"]))
    for s in etf_map["secid"]:
        source[int(s)] = "sector_etf"
    manifest = pd.DataFrame(
        {
            "secid": all_secids,
            "source": [source.get(s, "constituent") for s in all_secids],
            "ticker": [ticker_by_secid.get(s) for s in all_secids],
        }
    )
    manifest.to_parquet(DATA_DIR / "optionm_pull_secids.parquet")

    # 2) Cheap pulls FIRST so any schema surprise fails in seconds; the slow
    #    volatility-surface pull (~20-40 min) runs LAST.
    names = pull_security_names(all_secids)
    names.to_parquet(DATA_DIR / "optionm_security_names.parquet")

    zero = pull_zero_curve()
    zero.to_parquet(DATA_DIR / "optionm_zero_curve.parquet")

    month_ends = month_end_trading_days()
    surface = pull_vol_surface(all_secids, month_ends)
    surface.to_parquet(DATA_DIR / "optionm_vol_surface.parquet")
