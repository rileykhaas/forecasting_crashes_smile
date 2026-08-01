"""A3: Power-utility (fear) correction via R_m^gamma weighting.

Implements the E*[R_m^gamma * .] / E*[R_m^gamma] reweighting of equation (2)
that converts risk-neutral into physical expectations for the power-utility
investor holding the market. With gamma = 2 (schema.GAMMA), the R_m^2 weighting
pulls probability mass OUT of the crash tail -- the fear correction -- because
in crash states R_m is small, so R_m^2 is small.

Provides E*[R_m^gamma] (the denominator, Result 5) and the R_m^gamma-weighted
risk-neutral expectation of an indicator, which the bounds in A4 build on.
"""

from schema import GAMMA


def market_moment(index_cdf, rate, gamma=GAMMA):
    """Return E*[R_m^gamma], the denominator of the correction (Result 5)."""
    raise NotImplementedError


def weighted_tail_expectation(index_cdf, rate, k_level, tail, gamma=GAMMA):
    """Return E*[R_m^gamma * I(R_m <= k)] (lower) or E*[R_m^gamma * I(R_m >= k)] (upper)."""
    raise NotImplementedError
