"""Unit tests for the surface cleaning (clean_surface.py).

Each test pins one of the paper's four Appendix-D filter criteria (plus the
spot-join and schema), on tiny synthetic frames -- no WRDS. The strike-count
criterion means every "kept" fixture needs >10 distinct strikes, so the helper
builds that many rows.
"""

import pandas as pd

import schema
from schema import SPX_SECID
from clean_surface import build_spot_by_month, clean_surface


def _raw(secid=1, date="2020-01-31", days=30, n=12, dispersion=0.01, strike0=90.0):
    """n surface rows for one firm-month-maturity, each a distinct strike."""
    return pd.DataFrame(
        {
            "secid": secid,
            "date": pd.Timestamp(date),
            "days": days,
            "cp_flag": "C",
            "delta": 0.5,
            "impl_volatility": 0.2,
            "impl_strike": [strike0 + i for i in range(n)],
            "dispersion": dispersion,
        }
    )


def _spot(secid=1, date="2020-01-31", spot=100.0):
    return pd.DataFrame(
        {
            "secid": [secid],
            "ym": [pd.Timestamp(date).to_period("M")],
            "spot_price": [spot],
        }
    )


def test_dispersion_band_is_exclusive():
    """dispersion must be strictly in (0, 0.05); the 0 and 0.05 edges are dropped."""
    raw = pd.concat(
        [
            _raw(secid=1, dispersion=0.03),   # inside -> kept
            _raw(secid=2, dispersion=0.05),   # upper edge -> dropped
            _raw(secid=3, dispersion=0.0),    # lower edge -> dropped
        ]
    )
    spot = pd.concat([_spot(1), _spot(2), _spot(3)])
    out = clean_surface(raw, spot)
    assert set(out["secid"]) == {1}


def test_positive_strike_required():
    """Non-positive strikes are dropped before anything else."""
    raw = _raw(secid=1, n=12)
    raw.loc[raw.index[0], "impl_strike"] = -5.0
    out = clean_surface(raw, _spot(1))
    assert (out["moneyness"] > 0).all()
    assert len(out) == 11  # the one bad strike removed, 11 (>10) survive


def test_more_than_ten_strikes_required():
    """Exactly 10 distinct strikes is dropped; 11 is kept (strictly > 10)."""
    raw = pd.concat([_raw(secid=1, n=10), _raw(secid=2, n=11)])
    spot = pd.concat([_spot(1), _spot(2)])
    out = clean_surface(raw, spot)
    assert set(out["secid"]) == {2}


def test_spot_required_and_moneyness_computed():
    """No CRSP spot => firm-month dropped; moneyness = strike / spot."""
    out = clean_surface(_raw(secid=1, strike0=90.0), _spot(1, spot=100.0))
    assert out["spot_price"].eq(100.0).all()
    assert abs(out["moneyness"].min() - 0.90) < 1e-9  # strike 90 / spot 100
    # A secid with no spot row is dropped entirely (criterion 1).
    assert clean_surface(_raw(secid=99), _spot(1)).empty


def test_build_spot_names_and_index():
    """Constituents get CRSP |prc|; the index (SPX_SECID) gets spindx."""
    universe = pd.DataFrame(
        {"date": [pd.Timestamp("2020-01-31")], "permno": [111], "secid": [5]}
    )
    crsp = pd.DataFrame(
        {"permno": [111], "date": [pd.Timestamp("2020-01-31")], "altprc": [50.0]}
    )
    idx = pd.DataFrame({"caldt": [pd.Timestamp("2020-01-31")], "spindx": [3200.0]})
    spot = build_spot_by_month(universe, crsp, idx)
    by = dict(zip(spot["secid"], spot["spot_price"]))
    assert by[5] == 50.0
    assert by[SPX_SECID] == 3200.0


def test_schema_conforms():
    out = clean_surface(_raw(secid=1), _spot(1))
    assert schema.validate_schema(out, "clean_surface")
