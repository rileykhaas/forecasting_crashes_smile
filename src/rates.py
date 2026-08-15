"""Clean the OptionMetrics zero curve into rates.parquet (Slice 1).

Produces the index-level (not per-secid) risk-free curve the bound computation
uses. Following Martin & Shi (2025), Appendix D, rates for maturities not directly
observed are linearly interpolated from the OptionMetrics zero curve. We emit the
curve at the four surface maturities that match the paper's 1/3/6/12-month
horizons ({30, 91, 182, 365} days), so it joins cleanly onto clean_surface.

``zero_rate`` is carried through exactly as OptionMetrics reports it (annualized,
continuously compounded, in percentage points); the conversion to a discount
factor happens in the engine (#18), not here.

Output columns are defined by schema.SCHEMAS["rates"].
"""

from pathlib import Path

import numpy as np
import pandas as pd

from settings import config
import schema

DATA_DIR = Path(config("DATA_DIR"))


def build_rates(raw_zero_curve, month_ends=None, maturities=schema.MATURITIES_DAYS):
    """Interpolate the raw zero curve onto the horizon maturities.

    Parameters
    ----------
    raw_zero_curve : DataFrame
        Output of ``pull_optionmetrics.pull_zero_curve`` (columns date, days, rate).
    month_ends : DatetimeIndex, optional
        If given, restrict to these dates (the surface's month-end formation
        days) so ``rates`` is monthly and aligns with clean_surface. The pipeline
        passes ``month_end_trading_days()``; leaving it None keeps every date in
        the curve (used by the unit tests).
    maturities : list of int
        Target maturities in days; defaults to schema.MATURITIES_DAYS.

    Returns
    -------
    DataFrame conforming to schema.SCHEMAS["rates"]:
    columns [date, days_to_maturity, zero_rate], one row per (date, maturity).
    ``numpy.interp`` interpolates linearly within the observed tenors and holds
    the curve flat beyond them (its endpoint-clamping) -- a benign choice, since
    the four target maturities sit inside the OptionMetrics curve's range.
    """
    maturities = sorted(int(m) for m in maturities)
    zc = raw_zero_curve.copy()
    zc["date"] = pd.to_datetime(zc["date"])
    if month_ends is not None:
        zc = zc[zc["date"].isin(pd.DatetimeIndex(month_ends))]

    rows = []
    for date, g in zc.sort_values("days").groupby("date"):
        days = g["days"].to_numpy(dtype=float)
        rate = g["rate"].to_numpy(dtype=float)
        for m in maturities:
            rows.append((date, m, float(np.interp(m, days, rate))))

    out = pd.DataFrame(rows, columns=["date", "days_to_maturity", "zero_rate"])
    out["date"] = pd.to_datetime(out["date"])
    out["days_to_maturity"] = out["days_to_maturity"].astype("int64")
    return out.sort_values(["date", "days_to_maturity"]).reset_index(drop=True)


def load_rates(data_dir=DATA_DIR):
    """Read the cached rates.parquet back from DATA_DIR."""
    return pd.read_parquet(Path(data_dir) / "rates.parquet")


if __name__ == "__main__":
    from pull_optionmetrics import load_zero_curve
    from sp500_secid_universe import month_end_trading_days

    df = build_rates(load_zero_curve(), month_ends=month_end_trading_days())
    schema.validate_schema(df, "rates")
    df.to_parquet(DATA_DIR / "rates.parquet")
