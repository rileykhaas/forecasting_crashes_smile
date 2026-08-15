"""Unit tests for the zero-curve cleaning (rates.py).

Pin the two behaviors the paper relies on (Appendix D): linear interpolation to
the horizon maturities, and flat (endpoint) extrapolation beyond the observed
tenors. Run on tiny synthetic curves, no WRDS.
"""

import pandas as pd

import schema
from rates import build_rates


def _curve(days, rate, date="2020-01-31"):
    return pd.DataFrame(
        {"date": [pd.Timestamp(date)] * len(days), "days": days, "rate": rate}
    )


def test_interpolates_to_horizon_maturities():
    """Output lands on {30,91,182,365}; interior points are linearly interpolated."""
    out = build_rates(_curve([30, 365], [1.0, 5.0]))
    assert sorted(out["days_to_maturity"]) == [30, 91, 182, 365]
    by = dict(zip(out["days_to_maturity"], out["zero_rate"]))
    assert by[30] == 1.0 and by[365] == 5.0
    expected_91 = 1.0 + 4.0 * (91 - 30) / (365 - 30)  # linear
    assert abs(by[91] - expected_91) < 1e-9


def test_flat_extrapolation_beyond_range():
    """Maturities outside the observed tenors clamp flat to the nearest endpoint."""
    by = dict(
        zip(
            *[
                build_rates(_curve([100, 200], [2.0, 3.0]))[c]
                for c in ("days_to_maturity", "zero_rate")
            ]
        )
    )
    assert by[30] == 2.0  # below the curve -> first rate
    assert by[365] == 3.0  # above the curve -> last rate


def test_schema_conforms():
    out = build_rates(_curve([30, 182, 365], [1.0, 3.0, 5.0]))
    assert schema.validate_schema(out, "rates")
