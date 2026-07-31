"""Pull S&P 500 constituent membership from WRDS/CRSP (Slice 2).

Fetches the historical S&P 500 constituent list (crsp.msp500list) so that,
for each month, we know which names were index members. Used to scope the
firm-month panel and to attach index membership to the realized-returns table.

Writes raw pulls to DATA_DIR (gitignored).
"""


def pull_sp500_constituents(wrds_username, start_date, end_date):
    """Return the S&P 500 constituent membership panel (permno x date range)."""
    raise NotImplementedError
