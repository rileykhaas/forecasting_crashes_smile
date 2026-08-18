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
CRSP index file); the extension sector ETFs (#34) get CRSP ``|prc|`` for their
own permno via ``etf_link`` (their permnos are force-pulled into the CRSP file by
``pull_CRSP_stock.sector_etf_permnos``). Passing no ``etf_link`` reproduces the
paper's constituents-plus-index scope exactly.

Output columns are defined by schema.SCHEMAS["clean_surface"].
"""

from pathlib import Path

import pandas as pd

import schema
from schema import SPX_SECID
from settings import config

DATA_DIR = Path(config("DATA_DIR"))


def build_spot_by_month(universe, crsp_monthly, crsp_index, etf_link=None):
    """Assemble month-end CRSP spot per (secid, month) for names + the index.

    Keyed on a monthly period rather than the exact date so the surface's
    NYSE month-end and CRSP's month-end always line up.

    ``etf_link`` (sector-ETF extension, #34): an optional [secid, permno] map for
    the extension ETFs. Given it, each ETF gets a CRSP ``|prc|`` spot for every
    month it traded (the same |prc| source and moneyness = strike/spot convention
    as the constituents), so its surface survives the spot inner-join in
    ``clean_surface``. Left None, the output is constituents + index only (the
    paper's scope).

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

    parts = [cons_spot, spx_spot[["secid", "ym", "spot_price"]]]

    # Extension ETFs: CRSP |prc| for each ETF's permno, every month it traded.
    if etf_link is not None and len(etf_link) > 0:
        el = etf_link.dropna(subset=["permno"]).copy()
        el["secid"] = el["secid"].astype("int64")
        el["permno"] = el["permno"].astype("int64")
        el = el.drop_duplicates(["secid", "permno"])
        etf_spot = (
            crsp[["permno", "ym", "altprc"]]
            .merge(el[["secid", "permno"]], on="permno", how="inner")
            .rename(columns={"altprc": "spot_price"})[["secid", "ym", "spot_price"]]
            .dropna(subset=["spot_price"])
            .drop_duplicates(["secid", "ym"])
        )
        parts.append(etf_spot)

    return pd.concat(parts, ignore_index=True)


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
    from pull_CRSP_stock import load_CRSP_index_files, load_CRSP_monthly_file
    from pull_link import load_crsp_optionm_link
    from pull_optionmetrics import load_option_pull_secids, load_vol_surface
    from sp500_secid_universe import load_sp500_secid_universe

    # Extension ETFs (#34): [secid, permno] map for the sector_etf secids.
    manifest = load_option_pull_secids()
    etf_secids = set(
        manifest.loc[manifest["source"] == "sector_etf", "secid"].astype(int)
    )
    link = load_crsp_optionm_link()
    etf_link = link.loc[
        link["secid"].isin(etf_secids), ["secid", "permno"]
    ].drop_duplicates()

    spot = build_spot_by_month(
        load_sp500_secid_universe(),
        load_CRSP_monthly_file(),
        load_CRSP_index_files(),
        etf_link=etf_link,
    )
    df = clean_surface(load_vol_surface(), spot)
    schema.validate_schema(df, "clean_surface")
    df.to_parquet(DATA_DIR / "clean_surface.parquet")
