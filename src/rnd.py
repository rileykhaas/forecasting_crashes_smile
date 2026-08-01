"""A1: Risk-neutral density via Breeden-Litzenberger.

Turns a cleaned volatility surface (for one date x secid x maturity) into the
risk-neutral CDF Q(.) of the gross return, following Breeden & Litzenberger
(1978) and the construction in Appendix D: build Black-Scholes OTM option
prices on a fine strike grid, take the relevant gradients to recover the
marginal CDF, fit an isotonic regression to enforce monotonicity, and winsorize
into [0, 1].

Consumes clean_surface + rates. Produces the marginals Q_m (index) and Q_i
(individual name) used everywhere downstream.
"""


def risk_neutral_cdf(surface_slice, rate):
    """Return the risk-neutral CDF Q(.) for one date x secid x maturity.

    The returned object should be evaluable on a gross-return grid and be
    monotone non-decreasing with values in [0, 1].
    """
    raise NotImplementedError
