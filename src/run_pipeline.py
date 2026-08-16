"""A5: Orchestrate A1-A4 into results.parquet.

Iterates over every date x secid x horizon x threshold, computes the marginals
(A1), applies the fear correction (A3) and the Frechet-Hoeffding bounds (A4),
joins the realized gross return from realized_returns.parquet, and derives the
realized_flag = 1{realized_gross_return <= threshold_q}.

Output columns are defined by schema.SCHEMAS["results"]. The bound-ordering
invariant is checked before writing.
"""

import pandas as pd

from bounds import crash_bounds
from rnd import risk_neutral_cdf
from settings import config
import schema

DAYS_TO_HORIZON = {days: months for months, days in schema.HORIZON_TO_MATURITY_DAYS.items()}


def run_pipeline(clean_surface, rates, realized_returns):
    """Assemble the full results table from cleaned inputs.

    Returns a DataFrame conforming to schema.SCHEMAS["results"].
    """
    rate_lookup = {
        (row.date, row.days_to_maturity): row.zero_rate / 100.0
        for row in rates.itertuples()
    }

    # One risk-neutral CDF per (secid, date, days_to_maturity), including the
    # market index -- built once and reused for every name/threshold that day.
    # A smile can still fail here even with plenty of raw rows: rnd.py's OTM
    # filter can leave nothing usable for a thin/illiquid name, so we skip
    # those rather than let one bad group crash the whole run.
    cdfs = {}
    n_skipped = 0
    for (secid, date, days), smile in clean_surface.groupby(
        ["secid", "date", "days_to_maturity"]
    ):
        rate = rate_lookup.get((date, days))
        if rate is None:
            continue
        try:
            cdfs[(secid, date, days)] = (risk_neutral_cdf(smile, rate), rate)
        except ValueError:
            n_skipped += 1
    if n_skipped:
        print(f"run_pipeline: skipped {n_skipped} smiles with no usable OTM quotes")

    rows = []
    for (secid, date, days), (cdf_i, rate) in cdfs.items():
        horizon = DAYS_TO_HORIZON.get(days)
        if horizon is None or secid == schema.SPX_SECID:
            continue
        market = cdfs.get((schema.SPX_SECID, date, days))
        if market is None:
            continue
        cdf_m, _ = market
        for threshold_q in schema.THRESHOLDS_Q:
            bound_lower, prob_riskneutral, bound_upper = crash_bounds(
                cdf_i, cdf_m, rate, threshold_q
            )
            rows.append(
                {
                    "date": date,
                    "secid": secid,
                    "horizon_months": horizon,
                    "threshold_q": threshold_q,
                    "bound_lower": bound_lower,
                    "prob_riskneutral": prob_riskneutral,
                    "bound_upper": bound_upper,
                }
            )

    results = pd.DataFrame(rows)
    results = results.merge(
        realized_returns, on=["date", "secid", "horizon_months"], how="left"
    )

    # realized_flag is only defined where a realized return exists (e.g. the
    # most recent formation dates have no completed forward window yet).
    has_realized = results["realized_gross_return"].notna()
    results["realized_flag"] = pd.NA
    results.loc[has_realized, "realized_flag"] = (
        results.loc[has_realized, "realized_gross_return"]
        <= results.loc[has_realized, "threshold_q"]
    ).astype("int64")
    results["realized_flag"] = results["realized_flag"].astype("Int64")

    results["secid"] = results["secid"].astype("int64")
    results["horizon_months"] = results["horizon_months"].astype("int64")

    return results.sort_values(
        ["date", "secid", "horizon_months", "threshold_q"]
    ).reset_index(drop=True)


if __name__ == "__main__":
    from clean_surface import load_clean_surface
    from rates import load_rates
    from realized_returns import load_realized_returns

    df = run_pipeline(load_clean_surface(), load_rates(), load_realized_returns())
    schema.validate_schema(df, "results")
    schema.check_bound_ordering(df)
    df.to_parquet(config("OUTPUT_DIR") / "results.parquet")
