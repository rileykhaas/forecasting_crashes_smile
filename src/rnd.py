"""A1: Risk-neutral density via Breeden-Litzenberger.

Builds the risk-neutral CDF of a name's gross return from its cleaned vol
surface (Appendix D): pick the out-of-the-money side of each strike, price
it with Black-Scholes on a fine grid, differentiate to get the CDF, then fit
an isotonic regression and clip to [0, 1] so it's a valid CDF.

Strikes are handled in moneyness terms (k = K / S_0), so a strike and a
gross-return level are the same number and no spot conversion is needed.
"""

import numpy as np
from scipy.stats import norm
from sklearn.isotonic import IsotonicRegression

N_GRID = 2000  # steps in the fine moneyness grid, per Appendix D


def _grid_half_width(days_to_maturity):
    """Grid spans K/S in [1/L, L]. Appendix D: L=3 up to 6 months, L=5 at 12."""
    return 5.0 if days_to_maturity >= 365 else 3.0


class RiskNeutralCDF:
    """A monotone risk-neutral CDF Q(.) of the gross return R = S_T / S_0.

    Stored on a fixed grid of gross-return levels with matching CDF values.
    Call it like a function to evaluate Q(q); use ``inverse`` for Q^-1(p).

    Also keeps ``call_grid`` (the priced call curve) and ``maturity_years``,
    which utility_correction.py needs to compute Result 5's moments directly
    from option prices instead of the CDF.
    """

    def __init__(self, grid, values, call_grid=None, maturity_years=None):
        self.grid = np.asarray(grid, dtype=float)
        self.values = np.asarray(values, dtype=float)
        self.call_grid = None if call_grid is None else np.asarray(call_grid, dtype=float)
        self.maturity_years = maturity_years

    def __call__(self, q):
        return np.interp(q, self.grid, self.values)

    def inverse(self, p):
        """Q^-1(p): the gross-return level where the CDF equals p."""
        values, first_idx = np.unique(self.values, return_index=True)
        grid = self.grid[first_idx]
        return np.interp(p, values, grid)


def _black_scholes_call(moneyness, vol, maturity_years, rate):
    """Black-Scholes call price with spot normalized to 1."""
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
        Rows of schema.SCHEMAS['clean_surface'] for one smile, both put and
        call quotes. Needs a ``cp_flag`` column ('P'/'C').
    rate : float
        Zero rate for this maturity, as a decimal (0.03 = 3%). rates.parquet
        stores it in percent, so divide by 100 before calling this.

    Returns a RiskNeutralCDF: monotone, non-decreasing, in [0, 1].
    """
    if abs(rate) >= 1.0:
        raise ValueError(
            f"rate must be a decimal fraction (e.g. 0.03 for 3%), got {rate!r}; "
            "rates.parquet stores zero_rate in percent -- divide by 100 first."
        )

    days = int(surface_slice["days_to_maturity"].iloc[0])
    maturity_years = days / 365.0

    # Keep only the OTM side of each strike (puts below the forward, calls
    # above it). clean_surface.parquet has both sides on the same moneyness
    # axis, and put/call vol at similar moneyness can differ sharply, so
    # without this the "smile" isn't even single-valued.
    forward = np.exp(rate * maturity_years)
    is_otm = (
        (surface_slice["cp_flag"] == "P") & (surface_slice["moneyness"] <= forward)
    ) | ((surface_slice["cp_flag"] == "C") & (surface_slice["moneyness"] > forward))
    slice_ = surface_slice.loc[is_otm].sort_values("moneyness")

    moneyness = slice_["moneyness"].to_numpy(dtype=float)
    implied_vol = slice_["implied_vol"].to_numpy(dtype=float)

    L = _grid_half_width(days)
    grid = np.linspace(1.0 / L, L, n_grid)

    # Linear interpolation between observed strikes, flat outside the range.
    vol_grid = np.interp(grid, moneyness, implied_vol)

    call_grid = _black_scholes_call(grid, vol_grid, maturity_years, rate)

    # Breeden-Litzenberger: Q(k) = 1 + e^{rT} * dC/dk
    dC_dk = np.gradient(call_grid, grid)
    q_raw = 1.0 + np.exp(rate * maturity_years) * dC_dk

    isotonic = IsotonicRegression(
        y_min=0.0, y_max=1.0, increasing=True, out_of_bounds="clip"
    )
    q_fit = np.clip(isotonic.fit_transform(grid, q_raw), 0.0, 1.0)

    return RiskNeutralCDF(grid, q_fit, call_grid=call_grid, maturity_years=maturity_years)
