"""A1: Risk-neutral density via Breeden-Litzenberger.

Turns a cleaned volatility surface (for one date x secid x maturity) into the
risk-neutral CDF Q(.) of the gross return, following Breeden & Litzenberger
(1978) and the construction in Appendix D: select the out-of-the-money side of
each put/call pair (K <= S*Rf uses puts, K > S*Rf uses calls, Rf = e^{r tau}),
build Black-Scholes prices on a fine strike grid, take the relevant gradients
to recover the marginal CDF, fit an isotonic regression to enforce
monotonicity, and winsorize into [0, 1].

Consumes clean_surface + rates. Produces the marginals Q_m (index) and Q_i
(individual name) used everywhere downstream.

Strikes are handled entirely in moneyness terms, k = K / S_0 (schema's
``moneyness`` column), so the gross return R = S_T / S_0 and a strike are the
same variable and no dollar-denominated spot conversion is ever needed here:
a call priced with spot normalized to 1 has price C(k) = e^{-rT} E*[(R-k)^+],
and Breeden-Litzenberger gives Q(k) = P*[R <= k] = 1 + e^{rT} dC/dk.
"""

import numpy as np
from scipy.stats import norm
from sklearn.isotonic import IsotonicRegression

# Number of uniform steps in the fine moneyness grid used to numerically
# differentiate the call-price curve (Appendix D uses 2000).
N_GRID = 2000


def _grid_half_width(days_to_maturity):
    """Moneyness grid half-width L; the grid spans K/S in [1/L, L].

    Appendix D uses L = 3 for the 1/3/6-month horizons and L = 5 for 12 months.
    """
    return 5.0 if days_to_maturity >= 365 else 3.0


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


def risk_neutral_cdf(surface_slice, rate, n_grid=N_GRID):
    """Return the risk-neutral CDF Q(.) for one date x secid x maturity.

    Parameters
    ----------
    surface_slice : DataFrame
        Rows of schema.SCHEMAS['clean_surface'] for a single (date, secid,
        days_to_maturity) -- i.e. one smile, BOTH put and call quotes. Must
        have a ``cp_flag`` column ('P'/'C') and at least two distinct OTM
        ``moneyness`` points after the filter below.
    rate : float
        Continuously-compounded annualized zero rate for this maturity, as a
        DECIMAL (0.03 = 3%). NOTE: rates.parquet's ``zero_rate`` is in percentage
        points, so the pipeline must divide it by 100 before calling this.

    Returns
    -------
    RiskNeutralCDF
        Evaluable on a gross-return grid; monotone non-decreasing, in [0, 1].
    """
    # Guard the rate-unit contract: fail loud rather than silently pricing with
    # r = 300% if a percent value slips through from rates.parquet.
    if abs(rate) >= 1.0:
        raise ValueError(
            f"rate must be a decimal fraction (e.g. 0.03 for 3%), got {rate!r}; "
            "rates.parquet stores zero_rate in percent -- divide by 100 first."
        )

    days = int(surface_slice["days_to_maturity"].iloc[0])
    maturity_years = days / 365.0

    # Only out-of-the-money options are used (Appendix D): puts for K <= S*Rf,
    # calls for K > S*Rf, where Rf = e^{r tau} is the forward growth factor.
    # clean_surface.parquet carries BOTH sides' quotes on the same moneyness
    # axis -- put and call implied vol at similar moneyness are NOT
    # interchangeable (they can differ sharply, especially in stress), so
    # without this filter the two curves interleave into a single
    # non-monotonic, effectively two-valued "smile."
    forward = np.exp(rate * maturity_years)
    is_otm = (
        (surface_slice["cp_flag"] == "P") & (surface_slice["moneyness"] <= forward)
    ) | ((surface_slice["cp_flag"] == "C") & (surface_slice["moneyness"] > forward))
    slice_ = surface_slice.loc[is_otm].sort_values("moneyness")

    moneyness = slice_["moneyness"].to_numpy(dtype=float)
    implied_vol = slice_["implied_vol"].to_numpy(dtype=float)

    # Fine strike grid over the paper's fixed moneyness range K/S in [1/L, L]
    # (Appendix D: L=3 for 1/3/6-month, L=5 for 12-month), with N_GRID uniform
    # steps for the midpoint-rule integrals downstream.
    L = _grid_half_width(days)
    grid = np.linspace(1.0 / L, L, n_grid)

    # Linear interpolation of implied vol between observed strikes; held flat
    # outside the quoted range (np.interp clamps to the endpoints) -- Appendix D.
    vol_grid = np.interp(grid, moneyness, implied_vol)

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
