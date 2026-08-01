"""Pull raw OptionMetrics data from WRDS (Slice 1).

Fetches, for the last trading day of each month over [START_DATE, END_DATE]:
  - the IvyDB volatility surface (optionm_all.vsurfd{year}) for the S&P 500
    index (SPX_SECID) and for S&P 500 constituent names;
  - the zero-coupon yield curve (optionm_all.zerocd);
  - secid lookups (optionm_all.securd / secnmd) as needed.

Writes raw pulls to DATA_DIR (gitignored). Cleaning happens in clean_surface.py
and rates.py; this file only fetches. "pull_" = hits the network; a matching
"load_" reads the cached pull back from DATA_DIR.
"""


def pull_vol_surface(wrds_username, secids, start_date, end_date):
    """Pull raw volatility-surface rows for the given secids and date range.

    Returns a long DataFrame of raw surface observations (one row per
    date x secid x maturity x moneyness grid point) prior to filtering.
    """
    raise NotImplementedError


def pull_zero_curve(wrds_username, start_date, end_date):
    """Pull the raw OptionMetrics zero-coupon yield curve (zerocd)."""
    raise NotImplementedError
