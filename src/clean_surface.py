"""Clean the OptionMetrics volatility surface into clean_surface.parquet (Slice 1).

Applies the paper's filtering (Appendix D): CRSP spot must exist; strike > 0;
OptionMetrics dispersion in (0, 0.05); more than 10 distinct strikes per
firm-month-maturity. Interpolates implied vol linearly within observed strikes
and extrapolates a FLAT smile outside them (a conservative choice that refuses
to invent tail probability).

Output columns are defined by schema.SCHEMAS["clean_surface"].
"""

from settings import config
import schema


def clean_surface(raw_surface):
    """Filter and interpolate the raw surface into the tidy clean_surface table.

    Returns a DataFrame conforming to schema.SCHEMAS["clean_surface"]:
    columns [date, secid, days_to_maturity, moneyness, implied_vol, spot_price].
    """
    raise NotImplementedError


def load_clean_surface(data_dir=None):
    """Read the cached clean_surface.parquet back from DATA_DIR."""
    raise NotImplementedError


if __name__ == "__main__":
    df = clean_surface(...)  # wire to pull_optionmetrics in dodo.py
    schema.validate_schema(df, "clean_surface")
    df.to_parquet(config("DATA_DIR") / "clean_surface.parquet")
