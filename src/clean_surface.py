"""Clean the OptionMetrics volatility surface into clean_surface.parquet (Slice 1).

Applies the paper's four filtering criteria (Martin & Shi 2025, Appendix D):

  1. a CRSP spot price must exist for the firm-month,
  2. strike price > 0,
  3. the OptionMetrics ``dispersion`` (surface goodness-of-fit) lies in (0, 0.05),
  4. more than 10 distinct strikes exist per firm-month-maturity.

and reshapes the surviving observed surface points to ``(moneyness, implied_vol)``
with the CRSP spot attached, where ``moneyness = impl_strike / spot_price``.

Boundary with the engine (#18): this file does NOT interpolate/extrapolate or
price. It emits the *filtered observed* surface. The linear-within / flat-outside
interpolation, the 2000-step Black-Scholes grid, and the Breeden-Litzenberger
marginals all live in the engine (rnd.py, #18), keeping cleaning separate from
analysis. ``cp_flag`` is kept so the engine can select OTM by moneyness-vs-forward
at pricing time, exactly as the paper does.

Spot sourcing: constituents get CRSP ``|prc|`` via the #14 secid<->permno link;
the S&P 500 index (SPX_SECID) gets the CRSP S&P 500 level (``spindx`` from the
CRSP index file). The extension ETFs are out of the paper's scope and are not
spot-matched here (handled with the sector-ETF extension, #34).

Output columns are defined by schema.SCHEMAS["clean_surface"].
"""

from pathlib import Path

import pandas as pd

from settings import config
from schema import SPX_SECID
import schema

DATA_DIR = Path(config("DATA_DIR"))


def build_spot_by_month(universe, crsp_monthly, crsp_index):
    """Assemble month-end CRSP spot per (secid, month) for names + the index.

    Keyed on a monthly period rather than the exact date so the surface's
    NYSE month-end and CRSP's month-end always line up.

    Returns a DataFrame with columns [secid, ym (Period[M]), spot_price].
    """
    # Constituents: link secid <-> permno (#14), then CRSP |prc| for that permno.
    cons = universe.dropna(subset=["secid"]).copy()
    cons["secid"] = cons["secid"].astype("int64")
    cons["ym"] = cons["date"].dt.to_period("M")

    crsp = crsp_monthly[["permno", "date", "altprc"]].copy()
    crsp["ym"] = crsp["date"].dt.to_period("M")

    cons = cons.merge(crsp[["permno", "ym", "altprc"]], on=["permno", "ym"], how="left")
    cons_spot = (
        cons[["secid", "ym", "altprc"]]
        .rename(columns={"altprc": "spot_price"})
        .dropna(subset=["spot_price"])
        .drop_duplicates(["secid", "ym"])
    )

    # S&P 500 index: the CRSP S&P 500 level (spindx).
    idx = crsp_index[["caldt", "spindx"]].copy()
    idx["ym"] = idx["caldt"].dt.to_period("M")
    spx_spot = (
        idx[["ym", "spindx"]]
        .rename(columns={"spindx": "spot_price"})
        .dropna(subset=["spot_price"])
        .drop_duplicates(["ym"])
    )
    spx_spot["secid"] = SPX_SECID

    spot = pd.concat(
        [cons_spot, spx_spot[["secid", "ym", "spot_price"]]], ignore_index=True
    )
    return spot


def clean_surface(raw_surface, spot_by_month):
    """Filter the raw surface and attach CRSP spot -> the tidy clean_surface table.

    Parameters
    ----------
    raw_surface : DataFrame
        Output of ``pull_optionmetrics.pull_vol_surface`` (secid, date, days,
        cp_flag, delta, impl_volatility, impl_strike, dispersion).
    spot_by_month : DataFrame
        Output of ``build_spot_by_month`` ([secid, ym, spot_price]).

    Returns
    -------
    DataFrame conforming to schema.SCHEMAS["clean_surface"]:
    columns [date, secid, days_to_maturity, moneyness, implied_vol, spot_price,
    cp_flag].
    """
    df = raw_surface.copy()
    df["secid"] = df["secid"].astype("int64")

    # Criteria 2 & 3: positive strike; dispersion strictly inside (0, 0.05). The
    # strike test also rejects OptionMetrics' -99.99 "missing" sentinel, which is
    # how a surface snapshot that failed to compute shows up (the entire 2020-07
    # month-end is such a gap in our IvyDB vintage: impl_strike=-99.99, implied
    # vol and dispersion NaN). Those rows carry no usable surface and are dropped.
    df = df[
        (df["impl_strike"] > 0) & (df["dispersion"] > 0) & (df["dispersion"] < 0.05)
    ]

    # Criterion 1: a CRSP spot must exist -> inner join drops firm-months without one.
    df["ym"] = df["date"].dt.to_period("M")
    df = df.merge(spot_by_month, on=["secid", "ym"], how="inner")

    df["moneyness"] = df["impl_strike"] / df["spot_price"]
    df = df.rename(
        columns={"days": "days_to_maturity", "impl_volatility": "implied_vol"}
    )

    # Criterion 4: keep firm-month-maturities with more than 10 distinct strikes.
    n_strikes = df.groupby(["date", "secid", "days_to_maturity"])[
        "impl_strike"
    ].transform("nunique")
    df = df[n_strikes > 10]

    out = df[
        [
            "date",
            "secid",
            "days_to_maturity",
            "moneyness",
            "implied_vol",
            "spot_price",
            "cp_flag",
        ]
    ].copy()
    out["secid"] = out["secid"].astype("int64")
    out["days_to_maturity"] = out["days_to_maturity"].astype("int64")
    return out.sort_values(
        ["date", "secid", "days_to_maturity", "moneyness"]
    ).reset_index(drop=True)


def load_clean_surface(data_dir=DATA_DIR):
    """Read the cached clean_surface.parquet back from DATA_DIR."""
    return pd.read_parquet(Path(data_dir) / "clean_surface.parquet")


if __name__ == "__main__":
    from pull_optionmetrics import load_vol_surface
    from pull_CRSP_stock import load_CRSP_monthly_file, load_CRSP_index_files
    from sp500_secid_universe import load_sp500_secid_universe

    spot = build_spot_by_month(
        load_sp500_secid_universe(),
        load_CRSP_monthly_file(),
        load_CRSP_index_files(),
    )
    df = clean_surface(load_vol_surface(), spot)
    schema.validate_schema(df, "clean_surface")
    df.to_parquet(DATA_DIR / "clean_surface.parquet")
