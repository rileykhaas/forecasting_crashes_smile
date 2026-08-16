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

    Examples
    --------
    A calmer market (20% vol) and a riskier name (35% vol), both 30 days out:

    >>> import numpy as np
    >>> import pandas as pd
    >>> from rnd import risk_neutral_cdf
    >>> moneyness = np.linspace(0.5, 1.5, 9)
    >>> def _smile(secid, vol):
    ...     return pd.DataFrame({
    ...         "date": pd.Timestamp("2020-01-31"), "secid": secid,
    ...         "days_to_maturity": 30, "moneyness": moneyness,
    ...         "implied_vol": vol, "spot_price": 100.0,
    ...         "cp_flag": np.where(moneyness <= 1.0, "P", "C"),
    ...     })
    >>> cdf_m = risk_neutral_cdf(_smile(108105, 0.20), rate=0.03)
    >>> cdf_i = risk_neutral_cdf(_smile(5001, 0.35), rate=0.03)
    >>> bound_lower, prob_riskneutral, bound_upper = crash_bounds(cdf_i, cdf_m, 0.03, 0.80)
    >>> bound_lower <= prob_riskneutral <= bound_upper
    True
    >>> round(bound_lower, 4), round(prob_riskneutral, 4), round(bound_upper, 4)
    (0.0104, 0.014, 0.0186)
    """
    prob_riskneutral = float(cdf_i(threshold_q))

    q_l = float(cdf_m.inverse(prob_riskneutral))
    q_u = float(cdf_m.inverse(1.0 - prob_riskneutral))

    denom = market_moment(cdf_m, rate)
    bound_lower = weighted_tail_expectation(cdf_m, rate, q_l, tail="lower") / denom
    bound_upper = weighted_tail_expectation(cdf_m, rate, q_u, tail="upper") / denom

    return float(bound_lower), prob_riskneutral, float(bound_upper)
