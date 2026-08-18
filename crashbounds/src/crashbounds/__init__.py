"""crashbounds: option-implied crash-probability bounds (Martin & Shi, 2025).

This package does NOT reimplement the A1-A4 engine -- it imports it directly
from the parent repo's ``src/``, which stays the single source of truth (so a
fix to the math only ever needs to happen in one place). That only works
inside a checkout of this repo (crashbounds/ is a subfolder of it, not a
standalone package meant to be published on its own); the path below is
resolved relative to this file, not hardcoded.

Two ways to use this package (see api.py):

Step by step (more control, e.g. reusing one market fetch across names)::

    name = fetch_data("AAPL")
    market = fetch_data("SPX")
    bound_lower, prob_riskneutral, bound_upper = bounds(name, market, threshold_q=0.80)

End to end (one call)::

    result = crash_probability("AAPL", horizon_months=1, threshold_q=0.80)
    print(report(result))
"""

import sys
from pathlib import Path

_crashbounds_pkg_dir = (
    Path(__file__).resolve().parent
)  # .../crashbounds/src/crashbounds
_crashbounds_dir = _crashbounds_pkg_dir.parent.parent  # .../crashbounds
_repo_root = _crashbounds_dir.parent  # the main repo
_engine_src = _repo_root / "src"

if not (_engine_src / "rnd.py").exists():
    raise ImportError(
        f"crashbounds could not find the engine at {_engine_src}. "
        "This package only works from inside a checkout of the "
        "forecasting_crashes_smile repo (crashbounds/ as a subfolder of it)."
    )

if str(_engine_src) not in sys.path:
    sys.path.insert(0, str(_engine_src))

from bounds import crash_bounds
from crash_prob import risk_neutral_crash_prob
from crashbounds.api import (
    CrashBoundsResult,
    MarketData,
    bounds,
    crash_probability,
    fetch_data,
    plot,
    report,
    risk_neutral_prob,
)
from rnd import RiskNeutralCDF, risk_neutral_cdf
from utility_correction import market_moment, weighted_tail_expectation

__all__ = [
    # engine (A1-A4), re-exported as-is
    "RiskNeutralCDF",
    "risk_neutral_cdf",
    "risk_neutral_crash_prob",
    "market_moment",
    "weighted_tail_expectation",
    "crash_bounds",
    # public API (#28)
    "MarketData",
    "CrashBoundsResult",
    "fetch_data",
    "risk_neutral_prob",
    "bounds",
    "crash_probability",
    "report",
    "plot",
]
