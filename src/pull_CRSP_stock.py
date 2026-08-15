"""Pull the CRSP monthly stock panel and the S&P 500 index level from WRDS.

This is the CRSP side of the firm-month panel for the Martin & Shi (2025)
replication: monthly prices, returns (with delisting folded in), trading volume,
shares outstanding, and industry codes for each security, plus the S&P 500 index
level used as the index "spot."

Uses the CRSP CIZ format (Flat File Format 2.0):
 - Monthly stock table: crspm.msf_v2 (+ crspm.stksecurityinfohist for security info)
 - Delisting returns are built into mthret (no separate table needed) -- this is
   what lets a bankruptcy/wipeout show up as a crash rather than vanishing.
 - Column renames from SIZ: date->mthcaldt, ret->mthret, prc->mthprc, vol->mthvol.

Resources:
 - CRSP 2.0 update: https://www.tidy-finance.org/blog/crsp-v2-update/
 - CIZ FAQ: https://wrds-www.wharton.upenn.edu/pages/support/manuals-and-overviews/crsp/stocks-and-indices/crsp-stock-and-indexes-version-2/crsp-ciz-faq/

Thank you to Tobias Rodriguez del Pozo for his assistance with the CIZ query.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd
import wrds
from dateutil.relativedelta import relativedelta

from settings import config

DATA_DIR = Path(config("DATA_DIR"))
WRDS_USERNAME = config("WRDS_USERNAME", default="")
START_DATE = config("START_DATE")
END_DATE = config("END_DATE")


def pull_CRSP_monthly_file(
    start_date=START_DATE, end_date=END_DATE, wrds_username=WRDS_USERNAME
):
    """Pull monthly CRSP stock data (CIZ format) over [start_date, end_date].

    Returns one row per (permno, month) with price, return, volume, shares, the
    adjustment factors, and industry codes. ``mthret`` already integrates the
    delisting return, so no separate delisting handling is needed.

    Security filter: ``securitytype = 'EQTY'`` -- a broad equity filter. Per the
    paper we do NOT drop financial firms (or otherwise narrow by industry); the
    firm universe is instead governed by S&P 500 membership downstream.
    """
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
    # Pull one extra lead month: a t-1 market cap is needed for some downstream
    # calculations. Hidden from the caller.
    start_date = (start_date - relativedelta(months=1)).strftime("%Y-%m-%d")
    if isinstance(end_date, datetime):
        end_date = end_date.strftime("%Y-%m-%d")

    # Only the columns the project uses: identifiers, price/return/volume/shares,
    # adjustment factors (for market cap), and industry codes.
    query = f"""
    SELECT
        msf.permno,
        msf.mthcaldt,
        msf.mthret,
        msf.shrout,
        msf.mthprc,
        msf.mthvol,
        msf.mthcumfacshr,
        msf.mthcumfacpr,
        ssih.siccd,
        ssih.naics
    FROM crspm.msf_v2 AS msf
    INNER JOIN crspm.stksecurityinfohist AS ssih
        ON msf.permno = ssih.permno
        AND ssih.secinfostartdt <= msf.mthcaldt
        AND msf.mthcaldt <= ssih.secinfoenddt
    WHERE
        msf.mthcaldt BETWEEN '{start_date}' AND '{end_date}'
        AND ssih.securitytype = 'EQTY'
    """

    db = wrds.Connection(wrds_username=wrds_username)
    df = db.raw_sql(query, date_cols=["mthcaldt"])
    db.close()

    df = df.loc[:, ~df.columns.duplicated()]

    # shrout is in thousands in CRSP; convert to actual shares.
    df["shrout"] = df["shrout"] * 1000

    df = df.rename(
        columns={
            "mthcaldt": "date",
            "mthret": "ret",
            "mthprc": "prc",
            "mthvol": "vol",
            "mthcumfacshr": "cfacshr",
            "mthcumfacpr": "cfacpr",
        }
    )

    # Spot proxy (absolute price; CRSP negates bid/ask-midpoint prices).
    df["altprc"] = df["prc"].abs()

    # Split-adjusted market cap.
    df["market_cap"] = (df["prc"].abs() / df["cfacpr"]) * (df["shrout"] * df["cfacshr"])

    return df


def pull_CRSP_index_files(
    start_date=START_DATE, end_date=END_DATE, wrds_username=WRDS_USERNAME
):
    """Pull the CRSP monthly index file (crsp_a_indexes.msix).

    Used here for the S&P 500 index level (``spindx``), which serves as the index
    "spot" in clean_surface. The index tables were not materially changed in the
    CIZ transition.
    """
    query = f"""
        SELECT *
        FROM crsp_a_indexes.msix
        WHERE caldt BETWEEN '{start_date}' AND '{end_date}'
    """
    db = wrds.Connection(wrds_username=wrds_username)
    df = db.raw_sql(query, date_cols=["caldt"])
    db.close()
    return df


def load_CRSP_monthly_file(data_dir=DATA_DIR):
    return pd.read_parquet(Path(data_dir) / "CRSP_monthly_stock.parquet")


def load_CRSP_index_files(data_dir=DATA_DIR):
    return pd.read_parquet(Path(data_dir) / "CRSP_MSIX.parquet")


if __name__ == "__main__":
    df_msf = pull_CRSP_monthly_file(start_date=START_DATE, end_date=END_DATE)
    df_msf.to_parquet(Path(DATA_DIR) / "CRSP_monthly_stock.parquet")

    df_msix = pull_CRSP_index_files(start_date=START_DATE, end_date=END_DATE)
    df_msix.to_parquet(Path(DATA_DIR) / "CRSP_MSIX.parquet")
