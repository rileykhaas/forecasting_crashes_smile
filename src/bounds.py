"""A4: Frechet-Hoeffding bounds on the physical crash probability.

Core of the crashbounds package. Implements Result 3: with q fixed,
    q_l = Q_m^{-1}(Q_i(q)),   q_u = Q_m^{-1}(1 - Q_i(q)),
the lower and upper bounds are
    P^L = E*[R_m^gamma I(R_m <= q_l)] / E*[R_m^gamma],
    P^U = E*[R_m^gamma I(R_m >= q_u)] / E*[R_m^gamma],
and the risk-neutral probability P* lies between them. The lower bound is
attained under (lower) comonotonicity of the stock and market, which the paper
argues a priori is close to the truth.

Consumes the marginals from A1 and the weighted expectations from A3.
"""


def crash_bounds(cdf_i, cdf_m, rate, threshold_q):
    """Return (bound_lower, prob_riskneutral, bound_upper) for one observation.

    Guaranteed to satisfy bound_lower <= prob_riskneutral <= bound_upper
    (Result 3); schema.check_bound_ordering enforces this on the assembled table.
    """
    raise NotImplementedError
