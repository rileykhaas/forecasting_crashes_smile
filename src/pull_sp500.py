"""Pull S&P 500 constituent membership from WRDS/CRSP (Slice 2).

Fetches the historical S&P 500 constituent list (``crsp.msp500list``) so that,
for each month, we know which names were index members. Martin & Shi (2025)
"focus on firms included in the S&P 500 index, using index constituent
information from CRSP" -- this file is where that universe originates.

Each row of ``crsp.msp500list`` is one spell of index membership for a permno:
``start`` is the first date the permno was an index member and ``ending`` is the
last. A permno that enters, leaves, and re-enters the index appears as multiple
rows. Membership on any given date is therefore a range test:
``start <= date <= ending``.

Writes raw pulls to DATA_DIR (gitignored). "pull_" = hits the network; a
matching "load_" reads the cached pull back from DATA_DIR.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd
import wrds

from settings import config

DATA_DIR = Path(config("DATA_DIR"))
WRDS_USERNAME = config("WRDS_USERNAME", default="")
START_DATE = config("START_DATE")
END_DATE = config("END_DATE")


def pull_sp500_constituents(
    start_date=START_DATE, end_date=END_DATE, wrds_username=WRDS_USERNAME
):
    """Return the S&P 500 constituent membership panel (permno x date range).

    Pulls every membership spell from ``crsp.msp500list`` whose ``[start,
    ending]`` interval overlaps ``[start_date, end_date]``, so that a name that
    was already in the index at the start of the sample (or is still in it at
    the end) is retained. The returned frame is NOT expanded to a monthly grid;
    that is the job of ``sp500_secid_universe.build_sp500_secid_universe``.

    Columns
    -------
    permno : int      CRSP permanent security identifier
    start  : datetime first date of this membership spell
    ending : datetime last date of this membership spell

    Parameters
    ----------
    start_date, end_date : str or datetime
        Sample window; spells that do not overlap it are dropped server-side.
    wrds_username : str
        WRDS login used to open the connection.
    """
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
    start_date = start_date.strftime("%Y-%m-%d")
    end_date = end_date.strftime("%Y-%m-%d")

    # Overlap test: a spell [start, ending] intersects [start_date, end_date]
    # iff start <= end_date AND ending >= start_date. A name still in the index
    # may carry a null "ending"; treat that as open-ended (still a member) so a
    # NULL comparison does not silently drop current constituents.
    query = f"""
        SELECT permno, start, ending
        FROM crsp.msp500list
        WHERE start <= '{end_date}'
          AND (ending IS NULL OR ending >= '{start_date}')
        ORDER BY permno, start
    """

    db = wrds.Connection(wrds_username=wrds_username)
    df = db.raw_sql(query, date_cols=["start", "ending"])
    db.close()

    df["permno"] = df["permno"].astype("int64")
    # Fill any open-ended spell so the downstream range test (date <= ending)
    # keeps current members on every later month-end.
    df["ending"] = df["ending"].fillna(pd.Timestamp("2100-01-01"))
    return df


def load_sp500_constituents(data_dir=DATA_DIR):
    """Load the cached S&P 500 constituent panel from DATA_DIR."""
    path = Path(data_dir) / "sp500_constituents.parquet"
    return pd.read_parquet(path)


if __name__ == "__main__":
    df = pull_sp500_constituents(
        start_date=START_DATE, end_date=END_DATE, wrds_username=WRDS_USERNAME
    )
    df.to_parquet(Path(DATA_DIR) / "sp500_constituents.parquet")
