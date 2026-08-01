"""A2: Risk-neutral crash probability.

Given the risk-neutral CDF from rnd.py (A1), the risk-neutral crash probability
is simply P*[R_i <= q] = Q_i(q). This is the P^* column and also the naive
"crying wolf" forecaster the paper argues overstates crash risk in crises.
"""


def risk_neutral_crash_prob(cdf_i, threshold_q):
    """Return P*[R_i <= q] by evaluating the individual-name CDF at q."""
    raise NotImplementedError
