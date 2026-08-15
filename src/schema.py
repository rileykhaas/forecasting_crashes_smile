"""Project constants and cleaned-data table schemas.

This module is the single source of truth for the fixed parameters of
Martin & Shi (2025), "Forecasting Crashes with a Smile," and for the column
layout of every cleaned parquet that flows between the project's stages.

Every pull, cleaning, analysis, and exhibit script imports its column lists
and constants from here, so that a mismatch surfaces as an ``ImportError`` or
a failing schema test rather than as a silent join failure downstream.

The four cleaned tables and who owns them:

    clean_surface.parquet      (Slice 1)  filtered OptionMetrics vol surface
    rates.parquet              (Slice 1)  OptionMetrics zero-coupon curve
    realized_returns.parquet   (Slice 2)  CRSP forward returns (gross)
    results.parquet            (task A5)   P^L, P^*, P^U + realized outcome

Analysis-facing tables join on JOIN_KEYS. Note that the raw surface and rates
tables are keyed on ``days_to_maturity`` (an option's time to expiry), whereas
the realized-returns and results tables are keyed on ``horizon_months`` (a
return window). These are different axes: the bound computation *consumes* the
surface at the maturity matching a horizon and *emits* results indexed by
horizon. Do not force ``horizon_months`` onto the surface table.
"""

import pandas as pd
from pandas.api import types as ptypes

########################################################
## Fixed parameters from Martin & Shi (2025)
########################################################

# Risk aversion, calibrated on market returns (Appendix C); gamma = 2 is used
# throughout the paper's empirical work.
GAMMA = 2

# Forecasting horizons in months (Section 3.1, Tables 1-2).
HORIZONS_MONTHS = [1, 3, 6, 12]

# Each horizon maps to exactly one OptionMetrics standardized-surface maturity,
# in calendar days. The IvyDB volatility surface is standardized at fixed tenors,
# so a horizon is a single maturity slice -- no cross-maturity interpolation is
# needed. This is what a faithful replication pulls (and nothing else).
HORIZON_TO_MATURITY_DAYS = {1: 30, 3: 91, 6: 182, 12: 365}
MATURITIES_DAYS = [30, 91, 182, 365]

# Crash thresholds q, expressed as GROSS return levels below 1: q = 0.80 means
# a gross return at or below 0.80, i.e. a drop of 20% or more (Table 1).
# q = 0.80 (the "down 20%" case) is the paper's workhorse.
# NOTE: a rally extension (Appendix E), if added later, would instead use
# q = 1.10, 1.20, 1.30 -- thresholds ABOVE 1. The crash project uses q < 1.
THRESHOLDS_Q = [0.70, 0.80, 0.90]

# OptionMetrics secid for the S&P 500 index (the "market"). Individual names
# are S&P 500 constituents, resolved via the security-name history file.
SPX_SECID = 108105

# Extension universe (BEYOND the paper): the 11 Select Sector SPDR ETFs, plus
# KRE (SPDR S&P Regional Banking) for the SVB case study. These are NOT S&P 500
# constituents and never flow through crsp.msp500list; their secids are resolved
# from tickers via the OptionMetrics security file (securd) and added to the
# OptionMetrics pull set alongside SPX_SECID. They are kept OUT of the
# replication constituent panel so Tables 1-2 remain exactly the paper's.
SECTOR_ETF_TICKERS = [
    "XLB",  # Materials
    "XLC",  # Communication Services (options only from ~2018-06)
    "XLE",  # Energy
    "XLF",  # Financials
    "XLI",  # Industrials
    "XLK",  # Technology
    "XLP",  # Consumer Staples
    "XLRE",  # Real Estate (options only from ~2015-10)
    "XLU",  # Utilities
    "XLV",  # Health Care
    "XLY",  # Consumer Discretionary
]
EXTENSION_ETF_TICKERS = SECTOR_ETF_TICKERS + ["KRE"]  # + regional banks (SVB, #31)

# Keys on which the analysis-facing tables (realized_returns, results) join.
JOIN_KEYS = ["date", "secid", "horizon_months", "threshold_q"]


########################################################
## Table schemas: column -> pandas dtype "kind"
########################################################
# dtype kinds are checked loosely (see validate_schema) so that, e.g., either
# int64 or the nullable Int64 satisfies an "integer" requirement.

SCHEMAS = {
    "clean_surface": {
        "date": "datetime",
        "secid": "integer",
        "days_to_maturity": "integer",
        "moneyness": "float",
        "implied_vol": "float",
        "spot_price": "float",
        "cp_flag": "string",
    },
    "rates": {
        "date": "datetime",
        "days_to_maturity": "integer",
        "zero_rate": "float",
    },
    "realized_returns": {
        "date": "datetime",
        "secid": "integer",
        "horizon_months": "integer",
        "realized_gross_return": "float",
    },
    "results": {
        "date": "datetime",
        "secid": "integer",
        "horizon_months": "integer",
        "threshold_q": "float",
        "bound_lower": "float",
        "prob_riskneutral": "float",
        "bound_upper": "float",
        "realized_gross_return": "float",
        "realized_flag": "integer",
    },
}


def columns(table):
    """Return the ordered list of column names for a named table schema."""
    return list(SCHEMAS[table].keys())


def _kind_ok(series, kind):
    """Check whether a pandas Series matches a loose dtype kind."""
    if kind == "datetime":
        return ptypes.is_datetime64_any_dtype(series)
    if kind == "integer":
        return ptypes.is_integer_dtype(series)
    if kind == "float":
        return ptypes.is_float_dtype(series)
    if kind == "string":
        return ptypes.is_string_dtype(series) or ptypes.is_object_dtype(series)
    raise ValueError(f"Unknown dtype kind: {kind}")


def validate_schema(df, table, check_dtypes=True):
    """Validate that a DataFrame matches the agreed schema for ``table``.

    Checks that the column set matches exactly (no missing, no extra columns)
    and, optionally, that each column's dtype matches the loose kind declared
    in SCHEMAS. Raises ValueError on any mismatch; returns True on success.

    Parameters
    ----------
    df : pandas.DataFrame
        The frame to validate (typically just read from a parquet file).
    table : str
        One of the keys in SCHEMAS.
    check_dtypes : bool
        If True, also verify column dtypes, not just their names.
    """
    if table not in SCHEMAS:
        raise ValueError(f"Unknown table '{table}'. Known: {sorted(SCHEMAS)}")

    expected = SCHEMAS[table]
    actual_cols = set(df.columns)
    expected_cols = set(expected)

    missing = expected_cols - actual_cols
    extra = actual_cols - expected_cols
    if missing or extra:
        raise ValueError(
            f"Schema mismatch for '{table}'. "
            f"Missing columns: {sorted(missing)}. "
            f"Unexpected columns: {sorted(extra)}."
        )

    if check_dtypes:
        for col, kind in expected.items():
            if not _kind_ok(df[col], kind):
                raise ValueError(
                    f"Column '{col}' in '{table}' should be {kind}, "
                    f"got dtype {df[col].dtype}."
                )
    return True


def check_bound_ordering(df):
    """Verify the theoretical invariant P^L <= P^* <= P^U on a results frame.

    Result 3 of Martin & Shi (2025) guarantees the risk-neutral probability
    lies between the lower and upper bounds. Raises ValueError if any row
    violates the ordering; returns True otherwise.
    """
    lower_ok = (df["bound_lower"] <= df["prob_riskneutral"]).all()
    upper_ok = (df["prob_riskneutral"] <= df["bound_upper"]).all()
    if not (lower_ok and upper_ok):
        raise ValueError(
            "Bound ordering violated: require "
            "bound_lower <= prob_riskneutral <= bound_upper for every row."
        )
    return True
