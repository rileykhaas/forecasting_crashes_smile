"""Public, documented API wrapping the A1-A4 engine (issue #28).

``fetch_data`` pulls whatever WRDS currently has for a ticker; everything
else is a thin wrapper around the engine (rnd.py, crash_prob.py,
utility_correction.py, bounds.py), imported from the parent repo's src/ via
crashbounds/__init__.py -- so the actual math is never duplicated here.

WRDS-lag limitation
--------------------
``fetch_data`` returns the MOST RECENT surface WRDS actually has, not
"today's" surface -- OptionMetrics data through WRDS lags real time
noticeably. As of writing, the current year's volatility-surface table
doesn't exist yet at all, and the prior year's data itself stops months
before the year ends (e.g. fetched on 2026-08-16, the latest available
surface was from 2025-08-29 -- about a year stale). CRSP stock prices lag
far less (weeks, not months) but are still not "today." Always check the
``date`` field on the returned data before treating a result as current.
"""

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

import schema
from bounds import crash_bounds
from crash_prob import risk_neutral_crash_prob
from rates import build_rates
from rnd import risk_neutral_cdf
from settings import config
from utility_correction import market_moment, weighted_tail_expectation

OPTIONM_LIB = "optionm_all"
SECNMD_TABLE = f"{OPTIONM_LIB}.secnmd"
ZEROCD_TABLE = f"{OPTIONM_LIB}.zerocd"
VSURFD_TABLE_FMT = OPTIONM_LIB + ".vsurfd{year}"
SECPRD_TABLE_FMT = OPTIONM_LIB + ".secprd{year}"

# Tickers understood as "the market" -- resolved directly to schema.SPX_SECID
# rather than via secnmd, and priced via secprd (no CRSP permno for an index).
MARKET_TICKERS = {"SPX", "^SPX", "^GSPC", "SPX INDEX"}


@dataclass
class MarketData:
    """Everything risk_neutral_cdf needs for one ticker, as of the most
    recent date WRDS has it (see the WRDS-lag note in this module's docstring).
    """

    ticker: str
    secid: int
    date: pd.Timestamp
    days_to_maturity: int
    spot_price: float
    rate: float  # decimal (already divided by 100)
    surface_slice: pd.DataFrame  # schema.SCHEMAS['clean_surface']-shaped


@dataclass
class CrashBoundsResult:
    """Result of crash_probability(): the full Result-3 bound triple, with
    enough context (ticker, date, horizon, threshold) to be self-describing.
    """

    ticker: str
    market_ticker: str
    date: pd.Timestamp
    horizon_months: int
    threshold_q: float
    bound_lower: float
    prob_riskneutral: float
    bound_upper: float


def _resolve_secid(db, ticker):
    query = f"""
        SELECT secid, effect_date FROM {SECNMD_TABLE}
        WHERE ticker = '{ticker}' ORDER BY effect_date
    """
    hits = db.raw_sql(query, date_cols=["effect_date"])
    if hits.empty:
        raise ValueError(f"No OptionMetrics secid found for ticker {ticker!r}.")
    return int(hits.sort_values("effect_date")["secid"].iloc[-1])


def _resolve_permno(db, ticker):
    query = f"""
        SELECT permno, secinfostartdt FROM crspm.stksecurityinfohist
        WHERE ticker = '{ticker}' AND securitytype = 'EQTY'
        ORDER BY secinfostartdt
    """
    hits = db.raw_sql(query, date_cols=["secinfostartdt"])
    if hits.empty:
        raise ValueError(f"No CRSP permno found for ticker {ticker!r}.")
    return int(hits["permno"].iloc[-1])


def _latest_surface_date(db, secid, days_to_maturity, max_years_back=5):
    """The most recent date with surface data for this secid/maturity.

    Tries the current year's table first (may not exist yet -- see this
    module's WRDS-lag note), then walks backward.
    """
    current_year = datetime.now().year
    for year in range(current_year, current_year - max_years_back, -1):
        try:
            query = f"""
                SELECT MAX(date) as latest FROM {VSURFD_TABLE_FMT.format(year=year)}
                WHERE secid = {secid} AND days = {days_to_maturity}
            """
            result = db.raw_sql(query, date_cols=["latest"])
        except Exception:
            continue
        latest = result.iloc[0, 0]
        if pd.notna(latest):
            return latest
    raise ValueError(
        f"No surface data found for secid={secid}, days={days_to_maturity} "
        f"in the last {max_years_back} years."
    )


def _pull_surface_slice(db, secid, date, days_to_maturity):
    year = date.year
    query = f"""
        SELECT secid, date, days, cp_flag, impl_volatility, impl_strike, dispersion
        FROM {VSURFD_TABLE_FMT.format(year=year)}
        WHERE secid = {secid} AND days = {days_to_maturity}
          AND date = '{date.strftime("%Y-%m-%d")}'
    """
    return db.raw_sql(query, date_cols=["date"])


def _pull_rate(db, date, days_to_maturity):
    query = f"""
        SELECT date, days, rate FROM {ZEROCD_TABLE}
        WHERE date = '{date.strftime("%Y-%m-%d")}'
    """
    raw_zero_curve = db.raw_sql(query, date_cols=["date"])
    rates_df = build_rates(raw_zero_curve, month_ends=[date], maturities=[days_to_maturity])
    return float(rates_df["zero_rate"].iloc[0]) / 100.0


def _pull_crsp_spot(db, permno, date):
    query = f"""
        SELECT mthcaldt, mthprc FROM crspm.msf_v2
        WHERE permno = {permno} AND mthcaldt <= '{date.strftime("%Y-%m-%d")}'
        ORDER BY mthcaldt DESC LIMIT 1
    """
    row = db.raw_sql(query, date_cols=["mthcaldt"])
    if row.empty:
        raise ValueError(f"No CRSP price found for permno={permno} at or before {date}.")
    return abs(float(row["mthprc"].iloc[0]))


def _pull_index_spot(db, secid, date):
    year = date.year
    query = f"""
        SELECT date, close FROM {SECPRD_TABLE_FMT.format(year=year)}
        WHERE secid = {secid} AND date <= '{date.strftime("%Y-%m-%d")}'
        ORDER BY date DESC LIMIT 1
    """
    row = db.raw_sql(query, date_cols=["date"])
    if row.empty:
        raise ValueError(f"No index price found for secid={secid} at or before {date}.")
    return float(row["close"].iloc[0])


def fetch_data(ticker, maturity_days=30, wrds_username=None):
    """Fetch the most recent surface + zero curve + spot WRDS has for ``ticker``.

    Parameters
    ----------
    ticker : str
        A stock ticker (e.g. "AAPL"), or one of MARKET_TICKERS ("SPX", ...)
        for the S&P 500 index.
    maturity_days : int
        One of schema.MATURITIES_DAYS (30/91/182/365).
    wrds_username : str, optional
        Passed to wrds.Connection(); defaults to the project's configured
        WRDS_USERNAME (.env / environment / keyring), same as every pull_*.py
        script. Passing an explicit value never prompts interactively.

    Returns
    -------
    MarketData

    See this module's docstring for the WRDS-lag caveat: check
    ``result.date`` -- it is the latest WRDS has, not "today."
    """
    import wrds

    if wrds_username is None:
        wrds_username = config("WRDS_USERNAME", default="")
    db = wrds.Connection(wrds_username=wrds_username)
    try:
        is_market = ticker.upper() in MARKET_TICKERS
        secid = schema.SPX_SECID if is_market else _resolve_secid(db, ticker)
        date = _latest_surface_date(db, secid, maturity_days)
        raw_surface = _pull_surface_slice(db, secid, date, maturity_days)
        if raw_surface.empty:
            raise ValueError(f"Empty surface for {ticker!r} on {date}.")
        rate = _pull_rate(db, date, maturity_days)
        if is_market:
            spot_price = _pull_index_spot(db, secid, date)
        else:
            spot_price = _pull_crsp_spot(db, _resolve_permno(db, ticker), date)
    finally:
        db.close()

    surface = raw_surface[
        (raw_surface["impl_strike"] > 0)
        & (raw_surface["dispersion"] > 0)
        & (raw_surface["dispersion"] < 0.05)
    ].rename(columns={"days": "days_to_maturity", "impl_volatility": "implied_vol"})
    surface = surface.copy()
    surface["secid"] = int(secid)
    surface["spot_price"] = spot_price
    surface["moneyness"] = surface["impl_strike"] / spot_price
    surface = surface[
        ["date", "secid", "days_to_maturity", "moneyness", "implied_vol", "spot_price", "cp_flag"]
    ]

    return MarketData(
        ticker=ticker,
        secid=int(secid),
        date=pd.Timestamp(date),
        days_to_maturity=maturity_days,
        spot_price=spot_price,
        rate=rate,
        surface_slice=surface,
    )


def risk_neutral_prob(data, threshold_q):
    """P*[R<=q] for a single fetched name -- no market data needed."""
    cdf = risk_neutral_cdf(data.surface_slice, data.rate)
    return risk_neutral_crash_prob(cdf, threshold_q)


def bounds(name_data, market_data, threshold_q, gamma=None):
    """Frechet-Hoeffding bounds (Result 3) for one name against the market.

    ``gamma`` defaults to the paper's calibrated value (schema.GAMMA = 2);
    pass a different value to see how the bounds widen/narrow with risk
    aversion (Result 4). gamma=2 goes through the same crash_bounds() the
    engine's own tests are pinned against; any other gamma composes
    market_moment/weighted_tail_expectation directly (Result 3's own
    assembly, not a new calculation method).
    """
    cdf_i = risk_neutral_cdf(name_data.surface_slice, name_data.rate)
    cdf_m = risk_neutral_cdf(market_data.surface_slice, market_data.rate)

    if gamma is None or gamma == schema.GAMMA:
        return crash_bounds(cdf_i, cdf_m, name_data.rate, threshold_q)

    prob_riskneutral = float(cdf_i(threshold_q))
    q_l = float(cdf_m.inverse(prob_riskneutral))
    q_u = float(cdf_m.inverse(1.0 - prob_riskneutral))
    denom = market_moment(cdf_m, market_data.rate, gamma=gamma)
    bound_lower = weighted_tail_expectation(cdf_m, market_data.rate, q_l, tail="lower", gamma=gamma) / denom
    bound_upper = weighted_tail_expectation(cdf_m, market_data.rate, q_u, tail="upper", gamma=gamma) / denom
    return bound_lower, prob_riskneutral, bound_upper


def crash_probability(
    ticker, horizon_months, threshold_q, market_ticker="SPX", gamma=None, wrds_username=None
):
    """End-to-end: fetch data for ``ticker`` and ``market_ticker``, return
    the full bound triple. For more control (e.g. reusing one market fetch
    across several names), call fetch_data()/bounds() yourself instead.
    """
    maturity_days = schema.HORIZON_TO_MATURITY_DAYS[horizon_months]
    name_data = fetch_data(ticker, maturity_days=maturity_days, wrds_username=wrds_username)
    market_data = fetch_data(market_ticker, maturity_days=maturity_days, wrds_username=wrds_username)
    bound_lower, prob_riskneutral, bound_upper = bounds(
        name_data, market_data, threshold_q, gamma=gamma
    )
    return CrashBoundsResult(
        ticker=ticker,
        market_ticker=market_ticker,
        date=name_data.date,
        horizon_months=horizon_months,
        threshold_q=threshold_q,
        bound_lower=bound_lower,
        prob_riskneutral=prob_riskneutral,
        bound_upper=bound_upper,
    )


def report(result):
    """A short human-readable summary of a CrashBoundsResult.

    Examples
    --------
    >>> import pandas as pd
    >>> result = CrashBoundsResult(
    ...     ticker="AAPL", market_ticker="SPX", date=pd.Timestamp("2025-08-29"),
    ...     horizon_months=1, threshold_q=0.80,
    ...     bound_lower=0.0029, prob_riskneutral=0.0040, bound_upper=0.0047,
    ... )
    >>> print(report(result))
    AAPL vs SPX, 1-month horizon, as of 2025-08-29 (latest WRDS had -- see fetch_data's WRDS-lag note)
    P[AAPL <= 80% of today's price]:
      lower bound:        0.29%
      risk-neutral (P*):  0.40%
      upper bound:        0.47%
    <BLANKLINE>
    """
    return (
        f"{result.ticker} vs {result.market_ticker}, {result.horizon_months}-month horizon, "
        f"as of {result.date.date()} (latest WRDS had -- see fetch_data's WRDS-lag note)\n"
        f"P[{result.ticker} <= {result.threshold_q:.0%} of today's price]:\n"
        f"  lower bound:        {result.bound_lower:.2%}\n"
        f"  risk-neutral (P*):  {result.prob_riskneutral:.2%}\n"
        f"  upper bound:        {result.bound_upper:.2%}\n"
    )


def plot(result, ax=None):
    """A simple [bound_lower, bound_upper] range with P* marked, for one result."""
    import matplotlib.pyplot as plt

    if ax is None:
        _, ax = plt.subplots(figsize=(5, 2.5))
    ax.hlines(0, result.bound_lower, result.bound_upper, colors="#8ecae6", linewidth=8)
    ax.scatter([result.prob_riskneutral], [0], color="#e41a1c", zorder=3, label="P*")
    ax.set_yticks([])
    ax.set_xlabel(f"P[{result.ticker} <= {result.threshold_q:.0%}]")
    ax.set_title(f"{result.ticker}, {result.horizon_months}mo, {result.date.date()}")
    ax.legend()
    return ax
