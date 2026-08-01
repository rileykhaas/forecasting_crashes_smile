"""A5: Orchestrate A1-A4 into results.parquet.

Iterates over every date x secid x horizon x threshold, computes the marginals
(A1), applies the fear correction (A3) and the Frechet-Hoeffding bounds (A4),
joins the realized gross return from realized_returns.parquet, and derives the
realized_flag = 1{realized_gross_return <= threshold_q}.

Output columns are defined by schema.SCHEMAS["results"]. The bound-ordering
invariant is checked before writing.
"""

from settings import config
import schema


def run_pipeline(clean_surface, rates, realized_returns):
    """Assemble the full results table from cleaned inputs.

    Returns a DataFrame conforming to schema.SCHEMAS["results"].
    """
    raise NotImplementedError


if __name__ == "__main__":
    df = run_pipeline(...)
    schema.validate_schema(df, "results")
    schema.check_bound_ordering(df)
    df.to_parquet(config("OUTPUT_DIR") / "results.parquet")
