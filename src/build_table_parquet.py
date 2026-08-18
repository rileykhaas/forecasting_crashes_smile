"""Write parquet copies of the summary-table CSVs for the chartbook data glimpse.

ChartBook's data-glimpse/load tooling reads parquet (Polars ``scan_parquet``), so the
exhibit tables that are emitted as CSV (for the report) get a parquet twin here, which
the chartbook registers as their ``path``. Run by ``doit table_parquet`` before the
chartbook build.
"""

from pathlib import Path

import pandas as pd

from settings import config

OUTPUT_DIR = Path(config("OUTPUT_DIR"))

TABLES = [
    "table1",
    "table2",
    "eda_coverage",
    "etf_bounds",
    "industry_tightness",
    "svb_realized",
]


def build_all(output_dir=OUTPUT_DIR):
    written = []
    for name in TABLES:
        df = pd.read_csv(output_dir / f"{name}.csv")
        df.to_parquet(output_dir / f"{name}.parquet")
        written.append(f"{name}.parquet")
    return written


if __name__ == "__main__":
    print("wrote table parquet:", ", ".join(build_all()))
