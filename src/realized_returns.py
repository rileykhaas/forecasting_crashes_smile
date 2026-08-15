"""Build realized_returns.parquet (Slice 2).

Constructs gross forward returns R_{i, t -> t+tau} for each name and horizon,
from the CRSP monthly file (with delisting returns integrated). This table is
threshold-INDEPENDENT: it stores the realized gross return itself, not a crash
flag. The flag is derived later, per threshold, in results (task A5), so that
re-thresholding never requires recomputing returns.

Returns are GROSS (0.80 = down 20%), matching the paper's q convention.
The CRSP-OptionMetrics link (pull_link.py) is applied here to key returns by
secid rather than permno.

Output columns are defined by schema.SCHEMAS["realized_returns"].
"""

from pathlib import Path

import numpy as np
import pandas as pd

import schema
from settings import config
from sp500_secid_universe import month_end_trading_days

DATA_DIR = Path(config("DATA_DIR"))


def build_realized_returns(crsp_monthly, link_table, universe_secids=None):
    """Compute gross forward returns and key them by secid.

    Parameters
    ----------
    crsp_monthly : DataFrame
        Output of ``pull_CRSP_stock.pull_CRSP_monthly_file`` (must have
        permno, date, ret; ret already has delisting returns folded in via
        the CIZ mthret field).
    link_table : DataFrame
        Output of ``pull_link.pull_crsp_optionm_link``
        (secid, permno, score, sdate, edate).
    universe_secids : iterable of int, optional
        If given, restrict to these secids (the analysis universe, e.g.
        optionm_pull_secids). The link is pre-filtered to them and CRSP to the
        permnos they map to, so the expensive rolling products run only over the
        names actually studied (~1.2k) rather than all of CRSP (~20k). Leaving it
        None keeps every linked secid.

    Returns a DataFrame conforming to schema.SCHEMAS["realized_returns"]:
    columns [date, secid, horizon_months, realized_gross_return].
    """
    # 0) Optionally scope to the analysis universe up front.
    if universe_secids is not None:
        keep = {int(s) for s in universe_secids}
        link_table = link_table[link_table["secid"].isin(keep)]
        keep_permnos = set(link_table["permno"].unique())
        crsp_monthly = crsp_monthly[crsp_monthly["permno"].isin(keep_permnos)]

    # 1) One row per (permno, month) with the gross monthly return.
    monthly = crsp_monthly[["permno", "date", "ret"]].dropna(subset=["ret"]).copy()
    monthly["date"] = pd.to_datetime(monthly["date"])
    monthly["period"] = monthly["date"].dt.to_period("M")

    trading_days = month_end_trading_days(monthly["date"].min(), monthly["date"].max())
    period_to_date = pd.Series(trading_days, index=trading_days.to_period("M"))

    monthly = monthly.drop_duplicates(["permno", "period"]).sort_values(
        ["permno", "period"]
    )
    monthly["gross_ret"] = 1.0 + monthly["ret"]

    # 2) Wide matrix (month x permno) on a *complete* monthly grid, so that a
    #    positional rolling window of length h always spans exactly h calendar
    #    months, even for permnos whose history has gaps.
    wide = monthly.pivot(index="period", columns="permno", values="gross_ret")
    full_index = pd.period_range(wide.index.min(), wide.index.max(), freq="M")
    full_index.name = "period"
    wide = wide.reindex(full_index)

    # 3) For each horizon h, the forward gross return from t is
    #    prod_{k=1}^{h} gross_ret[t+k]. A rolling(h) product ending at row j
    #    covers rows [j-h+1, j]; shifting that back by h rows aligns it to
    #    row t = j - h. min_periods=h means any month gap inside the window
    #    (not just at the edges) yields NaN, so an incomplete horizon is
    #    dropped rather than silently bridged.
    #
    #    A log-sum (instead of a direct rolling product) would be the faster
    #    route, but pandas' rolling .sum() returns NaN -- not -inf -- for a
    #    window containing log(0), silently dropping exactly the rows where a
    #    name was wiped out (gross_ret == 0). A direct product handles that
    #    case correctly, so it's used despite being slower.
    frames = []
    for h in schema.HORIZONS_MONTHS:
        rolled = wide.rolling(window=h, min_periods=h).apply(np.prod, raw=True)
        fwd = rolled.shift(-h)
        long = (
            fwd.reset_index()
            .melt(
                id_vars="period", var_name="permno", value_name="realized_gross_return"
            )
            .dropna(subset=["realized_gross_return"])
        )
        long["horizon_months"] = h
        frames.append(long)

    out = pd.concat(frames, ignore_index=True)
    # Map back to the real trading date
    out["date"] = out["period"].map(period_to_date)
    out = out.dropna(subset=["date"]).drop(columns="period")

    # 4) Attach secid via a date-valid link, preferring the best (lowest)
    #    score -- same rule used in sp500_secid_universe.py. Rows for permnos
    #    with no valid OptionMetrics link on that date are dropped, since
    #    realized_returns is keyed on secid (unlinked names have no crash
    #    bound to compare against).
    cand = out.merge(link_table, on="permno", how="inner")
    valid = (cand["sdate"] <= cand["date"]) & (cand["date"] <= cand["edate"])
    best = (
        cand.loc[valid]
        .sort_values(["date", "permno", "horizon_months", "score", "secid"])
        .drop_duplicates(["date", "permno", "horizon_months"], keep="first")
    )

    result = best[["date", "secid", "horizon_months", "realized_gross_return"]].copy()
    result["secid"] = result["secid"].astype("int64")
    result["horizon_months"] = result["horizon_months"].astype("int64")
    result = result.sort_values(["date", "secid", "horizon_months"]).reset_index(
        drop=True
    )
    return result


if __name__ == "__main__":
    from pull_CRSP_stock import load_CRSP_monthly_file
    from pull_link import load_crsp_optionm_link
    from pull_optionmetrics import load_option_pull_secids

    crsp_monthly = load_CRSP_monthly_file()
    link_table = load_crsp_optionm_link()
    universe = load_option_pull_secids()["secid"]
    df = build_realized_returns(crsp_monthly, link_table, universe_secids=universe)
    schema.validate_schema(df, "realized_returns")
    df.to_parquet(DATA_DIR / "realized_returns.parquet")
