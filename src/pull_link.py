"""Pull the CRSP-OptionMetrics link table from WRDS (Slice 2).

Fetches wrdsapps_link_crsp_optionm, which maps CRSP permno <-> OptionMetrics
secid. This is the ONLY place the two data worlds meet: it is applied in
realized_returns.py to attach each secid's CRSP forward return.

Writes raw pulls to DATA_DIR (gitignored).
"""


def pull_crsp_optionm_link(wrds_username):
    """Return the CRSP-OptionMetrics link table (permno <-> secid with dates)."""
    raise NotImplementedError
