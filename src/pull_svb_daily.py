"""Pull daily OptionMetrics data for the Silicon Valley Bank case study (#31).

A self-contained DAILY slice -- distinct from the monthly replication pipeline. Over
Feb-Mar 2023 it pulls, for the four case-study securities, the standardized volatility
surface (``vsurfd2023``), the daily spot (``secprd2023`` close), and the zero curve
(``zerocd``). The three assets read one event at three levels:

  * SIVB (secid 110169) -- SVB Financial, the failed name (the crash itself);
  * KRE  (secid 127104) -- the regional-bank ETF (the sector layer);
  * XLF  (secid 110012) -- broad financials (the systemic layer);

plus the S&P 500 (SPX_SECID) as the market, needed for the bound's market CDF.

SIVB's surface ends on 2023-03-09, the day its stock collapsed ~60% and the last day
it traded as a going concern (options were halted with the stock on 2023-03-10). That
truncation is not a data gap to paper over -- it *is* the event.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd
import wrds

from settings import config
from schema import MATURITIES_DAYS, SPX_SECID

DATA_DIR = Path(config("DATA_DIR"))
WRDS_USERNAME = config("WRDS_USERNAME", default="")

SIVB_SECID = 110169
KRE_SECID = 127104
XLF_SECID = 110012
# SIVB, KRE, XLF, and the market (SPX) -- the market CDF is needed for the bounds.
CASE_SECIDS = [SIVB_SECID, KRE_SECID, XLF_SECID, SPX_SECID]
CASE_LABELS = {SIVB_SECID: "SIVB", KRE_SECID: "KRE", XLF_SECID: "XLF", SPX_SECID: "SPX"}

WINDOW_START = "2023-02-01"
WINDOW_END = "2023-03-31"
SURFACE_YEAR = 2023  # the case-study window lies entirely in the 2023 per-year tables


def _int_list(xs):
    return ", ".join(str(int(x)) for x in xs)


def pull_surface(secids=CASE_SECIDS, start=WINDOW_START, end=WINDOW_END,
                 maturities=MATURITIES_DAYS, year=SURFACE_YEAR, wrds_username=WRDS_USERNAME):
    """Daily standardized vol-surface rows for the case-study secids over [start, end].

    Same columns as the monthly ``pull_optionmetrics.pull_vol_surface`` (so the same
    cleaning applies), but every trading day is kept -- and, unlike the monthly pull,
    there is NO last-valid-day fallback: a day with no surface (SIVB after its
    collapse) stays absent."""
    query = f"""
        SELECT secid, date, days, cp_flag, delta,
               impl_volatility, impl_strike, dispersion
        FROM optionm_all.vsurfd{year}
        WHERE secid IN ({_int_list(secids)})
          AND days IN ({_int_list(maturities)})
          AND date BETWEEN '{start}' AND '{end}'
    """
    db = wrds.Connection(wrds_username=wrds_username)
    df = db.raw_sql(query, date_cols=["date"])
    db.close()
    if not df.empty:
        df["secid"] = df["secid"].astype("int64")
        df["days"] = df["days"].astype("int64")
    return df


def pull_spot(secids=CASE_SECIDS, start=WINDOW_START, end=WINDOW_END,
              year=SURFACE_YEAR, wrds_username=WRDS_USERNAME):
    """Daily close price per (secid, date) from OptionMetrics ``secprd`` -- the spot
    for moneyness = impl_strike / spot. Columns [secid, date, spot_price]."""
    query = f"""
        SELECT secid, date, close
        FROM optionm_all.secprd{year}
        WHERE secid IN ({_int_list(secids)})
          AND date BETWEEN '{start}' AND '{end}'
    """
    db = wrds.Connection(wrds_username=wrds_username)
    df = db.raw_sql(query, date_cols=["date"])
    db.close()
    df = df.rename(columns={"close": "spot_price"})
    df["secid"] = df["secid"].astype("int64")
    return df[["secid", "date", "spot_price"]]


def pull_zero(start=WINDOW_START, end=WINDOW_END, wrds_username=WRDS_USERNAME):
    """The OptionMetrics zero curve over the window (columns date, days, rate), for
    ``rates.build_rates`` to interpolate onto the horizon maturities daily."""
    query = f"""
        SELECT date, days, rate
        FROM optionm_all.zerocd
        WHERE date BETWEEN '{start}' AND '{end}'
        ORDER BY date, days
    """
    db = wrds.Connection(wrds_username=wrds_username)
    df = db.raw_sql(query, date_cols=["date"])
    db.close()
    return df


def load_svb_surface(data_dir=DATA_DIR):
    return pd.read_parquet(Path(data_dir) / "svb_daily_surface.parquet")


def load_svb_spot(data_dir=DATA_DIR):
    return pd.read_parquet(Path(data_dir) / "svb_daily_spot.parquet")


def load_svb_zero(data_dir=DATA_DIR):
    return pd.read_parquet(Path(data_dir) / "svb_daily_zero.parquet")


if __name__ == "__main__":
    pull_surface().to_parquet(DATA_DIR / "svb_daily_surface.parquet")
    pull_spot().to_parquet(DATA_DIR / "svb_daily_spot.parquet")
    pull_zero().to_parquet(DATA_DIR / "svb_daily_zero.parquet")
    print("wrote svb_daily_surface / svb_daily_spot / svb_daily_zero .parquet")
