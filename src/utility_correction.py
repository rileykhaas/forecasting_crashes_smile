"""A3: Power-utility (fear) correction via R_m^gamma weighting.

Converts risk-neutral expectations into physical ones for a power-utility
investor (gamma = 2). The R_m^2 weighting pulls probability mass out of the
crash tail, since R_m is small in a crash and R_m^2 is even smaller.

Follows Result 5 (Appendix D) directly: these moments come from index
OPTION PRICES on the fine grid, using the midpoint rule -- not from
re-integrating the fitted CDF. Only OTM prices matter (puts below the
forward, calls above it). Since put and call prices built from the same
vol satisfy put-call parity exactly, we get the put curve from rnd.py's
call_grid via parity instead of pricing puts separately.

Result 5, with spot normalized to 1 (K becomes moneyness k, F becomes Rf):

    E*[R_m^gamma] = Rf^gamma + Rf * [
        integral_0^Rf   gamma(gamma-1) k^(gamma-2) put(k)  dk +
        integral_Rf^inf gamma(gamma-1) k^(gamma-2) call(k) dk
    ]

    E*[R_m^gamma I(R_m<=q_l)] = Rf q_l^gamma [put'(q_l) - gamma put(q_l)/q_l]
        + Rf * integral_0^q_l gamma(gamma-1) k^(gamma-2) put(k) dk

    E*[R_m^gamma I(R_m>=q_u)] = Rf q_u^gamma [gamma call(q_u)/q_u - call'(q_u)]
        + Rf * integral_q_u^inf gamma(gamma-1) k^(gamma-2) call(k) dk
"""

import numpy as np

from schema import GAMMA


def _put_call_curves(index_cdf, rate):
    """Call and put price curves on index_cdf.grid, via put-call parity."""
    discount = np.exp(-rate * index_cdf.maturity_years)
    call_grid = index_cdf.call_grid
    put_grid = call_grid - 1.0 + index_cdf.grid * discount
    return call_grid, put_grid


def _midpoint_integral(grid, integrand, mask):
    """Midpoint-rule sum of integrand over grid points where mask is True."""
    dk = grid[1] - grid[0]
    return float(integrand[mask].sum() * dk)


def market_moment(index_cdf, rate, gamma=GAMMA):
    """Return E*[R_m^gamma], the denominator of the correction (Result 5)."""
    grid = index_cdf.grid
    call_grid, put_grid = _put_call_curves(index_cdf, rate)
    forward = np.exp(rate * index_cdf.maturity_years)

    kernel = gamma * (gamma - 1) * grid ** (gamma - 2)
    integrand = np.where(grid <= forward, kernel * put_grid, kernel * call_grid)
    integral = _midpoint_integral(grid, integrand, np.ones_like(grid, dtype=bool))

    return forward**gamma + forward * integral


def weighted_tail_expectation(index_cdf, rate, k_level, tail, gamma=GAMMA):
    """Return E*[R_m^gamma * I(R_m <= k)] (lower) or E*[R_m^gamma * I(R_m >= k)] (upper)."""
    grid = index_cdf.grid
    call_grid, put_grid = _put_call_curves(index_cdf, rate)
    forward = np.exp(rate * index_cdf.maturity_years)
    kernel = gamma * (gamma - 1) * grid ** (gamma - 2)

    if tail == "lower":
        put_at_k = float(np.interp(k_level, grid, put_grid))
        # Result 5's boundary derivative put'(K_l) IS the marginal: Appendix D
        # defines Q_m(K) = Rf * put'(K) on the OTM-put side, and fits isotonic to
        # it. So put'(k) = Q_m(k)/Rf must come from the *fitted* CDF (index_cdf) --
        # using a raw np.gradient of the price curve is the pre-isotonic marginal,
        # which is inconsistent with the q_l that Result 3 derives from the fitted
        # Q_m, and breaks P^L <= P* at short maturities.
        put_prime_at_k = float(index_cdf(k_level)) / forward
        boundary = (
            forward * k_level**gamma * (put_prime_at_k - gamma * put_at_k / k_level)
        )
        integral = _midpoint_integral(grid, kernel * put_grid, grid <= k_level)
        return boundary + forward * integral

    if tail == "upper":
        call_at_k = float(np.interp(k_level, grid, call_grid))
        # Symmetric to the lower tail: Appendix D defines Q_m(K) = Rf * call'(K) + 1
        # on the OTM-call side, so call'(k) = (Q_m(k) - 1)/Rf from the fitted CDF.
        call_prime_at_k = (float(index_cdf(k_level)) - 1.0) / forward
        boundary = (
            forward * k_level**gamma * (gamma * call_at_k / k_level - call_prime_at_k)
        )
        integral = _midpoint_integral(grid, kernel * call_grid, grid >= k_level)
        return boundary + forward * integral

    raise ValueError(f"tail must be 'lower' or 'upper', got {tail!r}")
