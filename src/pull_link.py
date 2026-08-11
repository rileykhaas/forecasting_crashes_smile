"""Pull the CRSP-OptionMetrics link table from WRDS (Slice 2).

Fetches ``wrdsapps_link_crsp_optionm``, the WRDS-maintained bridge that maps a
CRSP ``permno`` to an OptionMetrics ``secid`` over a validity window. This is
the ONLY place the two data worlds meet: it is applied in
``sp500_secid_universe.py`` to turn the S&P 500 permno universe into a secid
universe, and in ``realized_returns.py`` to attach each secid's CRSP forward
return.

Each row is a (secid, permno) linkage valid over ``[sdate, edate]`` with a
``score`` (1 = best, higher = weaker match). A permno can map to more than one
secid over time (e.g. re-listings), so consumers must both range-test on the
date and prefer the lowest score.

Writes raw pulls to DATA_DIR (gitignored). "pull_" = hits the network; a
matching "load_" reads the cached pull back from DATA_DIR.
"""

from pathlib import Path

import pandas as pd
import wrds

from settings import config

DATA_DIR = Path(config("DATA_DIR"))
WRDS_USERNAME = config("WRDS_USERNAME")


def pull_crsp_optionm_link(wrds_username=WRDS_USERNAME):
    """Return the CRSP-OptionMetrics link table (permno <-> secid with dates).

    The full table is small (one row per linkage spell), so it is pulled whole
    and filtered downstream. No date argument: linkage validity windows, not the
    sample window, govern which rows apply.

    Columns
    -------
    secid  : int      OptionMetrics security id
    permno : int      CRSP permanent security identifier
    score  : int      match quality (1 = best)
    sdate  : datetime first date this linkage is valid
    edate  : datetime last date this linkage is valid
    """
    # opcrsphist is OptionMetrics-centric: every row has a secid, but permno
    # (and thus score) is null for secids that never matched a CRSP security.
    # Such rows link nothing, so drop them server-side.
    query = """
        SELECT secid, permno, score, sdate, edate
        FROM wrdsapps_link_crsp_optionm.opcrsphist
        WHERE permno IS NOT NULL
        ORDER BY permno, secid, sdate
    """

    db = wrds.Connection(wrds_username=wrds_username)
    df = db.raw_sql(query, date_cols=["sdate", "edate"])
    db.close()

    # Belt-and-suspenders: guarantee the id/score columns are NA-free before
    # casting, so a stray null can never crash the pull.
    df = df.dropna(subset=["secid", "permno", "score"])
    df["secid"] = df["secid"].astype("int64")
    df["permno"] = df["permno"].astype("int64")
    df["score"] = df["score"].astype("int64")
    return df


def load_crsp_optionm_link(data_dir=DATA_DIR):
    """Load the cached CRSP-OptionMetrics link table from DATA_DIR."""
    path = Path(data_dir) / "crsp_optionm_link.parquet"
    return pd.read_parquet(path)


if __name__ == "__main__":
    df = pull_crsp_optionm_link(wrds_username=WRDS_USERNAME)
    df.to_parquet(Path(DATA_DIR) / "crsp_optionm_link.parquet")
