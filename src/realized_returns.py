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

from settings import config
import schema


def build_realized_returns(crsp_monthly, link_table):
    """Compute gross forward returns and key them by secid.

    Returns a DataFrame conforming to schema.SCHEMAS["realized_returns"]:
    columns [date, secid, horizon_months, realized_gross_return].
    """
    raise NotImplementedError


if __name__ == "__main__":
    df = build_realized_returns(...)
    schema.validate_schema(df, "realized_returns")
    df.to_parquet(config("DATA_DIR") / "realized_returns.parquet")
