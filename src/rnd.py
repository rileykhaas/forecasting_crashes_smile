"""A1: Risk-neutral density via Breeden-Litzenberger.

Turns a cleaned volatility surface (for one date x secid x maturity) into the
risk-neutral CDF Q(.) of the gross return, following Breeden & Litzenberger
(1978) and the construction in Appendix D: build Black-Scholes OTM option
prices on a fine strike grid, take the relevant gradients to recover the
marginal CDF, fit an isotonic regression to enforce monotonicity, and winsorize
into [0, 1].

Consumes clean_surface + rates. Produces the marginals Q_m (index) and Q_i
(individual name) used everywhere downstream.

Strikes are handled entirely in moneyness terms, k = K / S_0 (schema's
``moneyness`` column), so the gross return R = S_T / S_0 and a strike are the
same variable and no dollar-denominated spot conversion is ever needed here:
a call priced with spot normalized to 1 has price C(k) = e^{-rT} E*[(R-k)^+],
and Breeden-Litzenberger gives Q(k) = P*[R <= k] = 1 + e^{rT} dC/dk.
"""

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.stats import norm
from sklearn.isotonic import IsotonicRegression

# Fine strike grid used to numerically differentiate the call-price curve.
N_GRID = 2000
# How far past the quoted smile (in log-moneyness units) the fine grid
# extends before Breeden-Litzenberger is evaluated. The smile itself is held
# flat (nearest observed vol) past the quoted strikes -- it isn't identified
# out there -- but the *grid* still needs to extend well past any threshold
# q of interest so the numerical derivative near q isn't an edge effect.
GRID_LOG_PAD = 1.5


class RiskNeutralCDF:
    """A monotone risk-neutral CDF Q(.) of the gross return R = S_T / S_0.

    Represented on a fixed grid of gross-return levels (``grid``, increasing)
    with corresponding CDF values (``values``, non-decreasing, in [0, 1]).
    Callable at any gross-return level(s) via linear interpolation between
    grid points; ``inverse`` does the same on the swapped axes to recover
    Q^{-1}(p), which the Frechet-Hoeffding bounds (A4) apply to the index CDF.
    """

    def __init__(self, grid, values):
        self.grid = np.asarray(grid, dtype=float)
        self.values = np.asarray(values, dtype=float)

    def __call__(self, q):
        """Evaluate Q(q) for scalar or array-like gross-return level(s) q."""
        return np.interp(q, self.grid, self.values)

    def inverse(self, p):
        """Return Q^{-1}(p): the gross-return level where the CDF equals p.

        Flat regions in ``values`` (from clipping/isotonic ties) are not
        invertible pointwise, so only the first grid point attaining each
        CDF level is kept before interpolating.
        """
        values, first_idx = np.unique(self.values, return_index=True)
        grid = self.grid[first_idx]
        return np.interp(p, values, grid)


def _black_scholes_call(moneyness, vol, maturity_years, rate):
    """Black-Scholes call price with spot normalized to 1, i.e. C(k)/S_0."""
    k = np.asarray(moneyness, dtype=float)
    sqrt_t = np.sqrt(maturity_years)
    d1 = (-np.log(k) + (rate + 0.5 * vol**2) * maturity_years) / (vol * sqrt_t)
    d2 = d1 - vol * sqrt_t
    return norm.cdf(d1) - k * np.exp(-rate * maturity_years) * norm.cdf(d2)


def risk_neutral_cdf(surface_slice, rate, n_grid=N_GRID, log_pad=GRID_LOG_PAD):
    """Return the risk-neutral CDF Q(.) for one date x secid x maturity.

    Parameters
    ----------
    surface_slice : DataFrame
        Rows of schema.SCHEMAS['clean_surface'] for a single (date, secid,
        days_to_maturity) -- i.e. one smile. Must have at least two distinct
        ``moneyness`` points.
    rate : float
        Continuously-compounded annualized zero rate for this maturity
        (schema.SCHEMAS['rates']['zero_rate']), as a decimal (0.03 = 3%).

    Returns
    -------
    RiskNeutralCDF
        Evaluable on a gross-return grid; monotone non-decreasing, in [0, 1].
    """
    slice_ = surface_slice.sort_values("moneyness")
    moneyness = slice_["moneyness"].to_numpy(dtype=float)
    implied_vol = slice_["implied_vol"].to_numpy(dtype=float)
    maturity_years = slice_["days_to_maturity"].iloc[0] / 365.0

    # Smooth (monotonicity-agnostic) smile interpolant; extrapolation is
    # handled separately below by clipping to the quoted range (flat vol),
    # since the smile shape isn't identified past the data.
    smile = PchipInterpolator(moneyness, implied_vol, extrapolate=False)
    log_k = np.log(moneyness)
    grid = np.exp(np.linspace(log_k.min() - log_pad, log_k.max() + log_pad, n_grid))
    vol_grid = smile(np.clip(grid, moneyness.min(), moneyness.max()))

    call_grid = _black_scholes_call(grid, vol_grid, maturity_years, rate)

    # Breeden-Litzenberger (Appendix D): C(k) = e^{-rT} E*[(R-k)^+], so
    # dC/dk = -e^{-rT}(1 - Q(k))  =>  Q(k) = 1 + e^{rT} dC/dk.
    dC_dk = np.gradient(call_grid, grid)
    q_raw = 1.0 + np.exp(rate * maturity_years) * dC_dk

    isotonic = IsotonicRegression(
        y_min=0.0, y_max=1.0, increasing=True, out_of_bounds="clip"
    )
    q_fit = np.clip(isotonic.fit_transform(grid, q_raw), 0.0, 1.0)

    return RiskNeutralCDF(grid, q_fit)
