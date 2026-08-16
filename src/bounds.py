"""A4: Frechet-Hoeffding bounds on the physical crash probability.

Implements Result 3: with q fixed,
    q_l = Q_m^{-1}(Q_i(q)),   q_u = Q_m^{-1}(1 - Q_i(q)),
    P^L = E*[R_m^gamma I(R_m <= q_l)] / E*[R_m^gamma],
    P^U = E*[R_m^gamma I(R_m >= q_u)] / E*[R_m^gamma],
and the risk-neutral probability P* always lies between them.
"""

from utility_correction import market_moment, weighted_tail_expectation


def crash_bounds(cdf_i, cdf_m, rate, threshold_q):
    """Return (bound_lower, prob_riskneutral, bound_upper) for one observation.

    Guaranteed to satisfy bound_lower <= prob_riskneutral <= bound_upper
    (Result 3); schema.check_bound_ordering enforces this on the assembled table.
    """
    prob_riskneutral = float(cdf_i(threshold_q))

    q_l = float(cdf_m.inverse(prob_riskneutral))
    q_u = float(cdf_m.inverse(1.0 - prob_riskneutral))

    denom = market_moment(cdf_m, rate)
    bound_lower = weighted_tail_expectation(cdf_m, rate, q_l, tail="lower") / denom
    bound_upper = weighted_tail_expectation(cdf_m, rate, q_u, tail="upper") / denom

    return bound_lower, prob_riskneutral, bound_upper
