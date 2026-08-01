"""Clean the OptionMetrics zero curve into rates.parquet (Slice 1).

Produces the index-level (not per-secid) risk-free curve used when evaluating
the integrals in Result 5. Rates for maturities not directly observed are
linearly interpolated from the OptionMetrics yield curve.

Output columns are defined by schema.SCHEMAS["rates"].
"""

from settings import config
import schema


def build_rates(raw_zero_curve):
    """Interpolate the raw zero curve into the tidy rates table.

    Returns a DataFrame conforming to schema.SCHEMAS["rates"]:
    columns [date, days_to_maturity, zero_rate].
    """
    raise NotImplementedError


if __name__ == "__main__":
    df = build_rates(...)
    schema.validate_schema(df, "rates")
    df.to_parquet(config("DATA_DIR") / "rates.parquet")
