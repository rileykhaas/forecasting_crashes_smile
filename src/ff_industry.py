"""Fama-French 12-industry classification (SIC -> industry), for the industry
proxy that replicates the paper's Figure 10 methodology (issue #34 / #35).

The paper builds an industry crash-probability series as the equal-weighted average
of single-stock lower bounds within each Fama-French industry. We reuse the standard
FF12 definition (Kenneth French's data library, "Industry Definitions") to assign
each S&P 500 constituent to an industry from its CRSP SIC code, so that average --
the paper's *proxy* -- can be compared against our *direct* sector-ETF bound.

``ff12_industry(sic)`` returns the industry label; ``assign_ff12(secid_sic)`` maps a
[secid, sic] table to [secid, ff_industry]. Ranges are inclusive and mutually
exclusive by construction; anything unmatched falls in "Other".
"""

import pandas as pd

# FF12: (label, description, list of inclusive SIC ranges). Order is irrelevant
# (ranges do not overlap); "Other" is the fallback.
FF12_DEFS = [
    ("NoDur", "Consumer NonDurables",
     [(100, 999), (2000, 2399), (2700, 2749), (2770, 2799), (3100, 3199), (3940, 3989)]),
    ("Durbl", "Consumer Durables",
     [(2500, 2519), (2590, 2599), (3630, 3659), (3710, 3711), (3714, 3714),
      (3716, 3716), (3750, 3751), (3792, 3792), (3900, 3939), (3990, 3999)]),
    ("Manuf", "Manufacturing",
     [(2520, 2589), (2600, 2699), (2750, 2769), (3000, 3099), (3200, 3569),
      (3580, 3629), (3700, 3709), (3712, 3713), (3715, 3715), (3717, 3749),
      (3752, 3791), (3793, 3799), (3830, 3839), (3860, 3899)]),
    ("Enrgy", "Oil, Gas, and Coal Extraction and Products",
     [(1200, 1399), (2900, 2999)]),
    ("Chems", "Chemicals and Allied Products",
     [(2800, 2829), (2840, 2899)]),
    ("BusEq", "Business Equipment",
     [(3570, 3579), (3660, 3692), (3694, 3699), (3810, 3829), (7370, 7379)]),
    ("Telcm", "Telephone and Television Transmission", [(4800, 4899)]),
    ("Utils", "Utilities", [(4900, 4949)]),
    ("Shops", "Wholesale, Retail, and Some Services",
     [(5000, 5999), (7200, 7299), (7600, 7699)]),
    ("Hlth", "Healthcare, Medical Equipment, and Drugs",
     [(2830, 2839), (3693, 3693), (3840, 3859), (8000, 8099)]),
    ("Money", "Finance", [(6000, 6999)]),
]

FF12_LABELS = {code: desc for code, desc, _ in FF12_DEFS}

# Short labels for figure titles and table rows (the full descriptions are long).
FF12_SHORT = {
    "NoDur": "Consumer NonDur.", "Durbl": "Consumer Dur.", "Manuf": "Manufacturing",
    "Enrgy": "Energy", "Chems": "Chemicals", "BusEq": "Business Equip.",
    "Telcm": "Telecom", "Utils": "Utilities", "Shops": "Shops",
    "Hlth": "Health", "Money": "Finance", "Other": "Other",
}

# Cleanest FF12 <-> Select Sector SPDR correspondences, for the proxy-vs-direct
# comparison. The FF/GICS mappings are approximate; these are the six where the
# correspondence is tight enough to compare like with like.
FF12_TO_ETF = {
    "Money": "XLF",   # Finance          -> Financials
    "Enrgy": "XLE",   # Oil & Gas        -> Energy
    "Utils": "XLU",   # Utilities        -> Utilities
    "Hlth": "XLV",    # Healthcare       -> Health Care
    "BusEq": "XLK",   # Business Equip.  -> Technology
    "Manuf": "XLI",   # Manufacturing    -> Industrials
}


def ff12_industry(sic):
    """FF12 industry label for a SIC code (``"Other"`` if unmatched/missing)."""
    if sic is None or (isinstance(sic, float) and pd.isna(sic)):
        return "Other"
    try:
        s = int(sic)
    except (TypeError, ValueError):
        return "Other"
    for code, _desc, ranges in FF12_DEFS:
        if any(lo <= s <= hi for lo, hi in ranges):
            return code
    return "Other"


def assign_ff12(secid_sic):
    """Map a [secid, sic] frame to [secid, ff_industry] (one row per secid)."""
    out = secid_sic.dropna(subset=["secid"]).drop_duplicates("secid").copy()
    out["secid"] = out["secid"].astype("int64")
    out["ff_industry"] = out["sic"].map(ff12_industry)
    return out[["secid", "ff_industry"]].reset_index(drop=True)


def build_secid_sic(universe, crsp_monthly):
    """[secid, sic] for constituents: the modal CRSP ``siccd`` per permno, mapped to
    secid via the universe's secid<->permno pairs."""
    sic = (crsp_monthly.dropna(subset=["siccd"])
           .groupby("permno")["siccd"]
           .agg(lambda s: s.mode().iloc[0]))
    uni = universe.dropna(subset=["secid", "permno"])[["secid", "permno"]].copy()
    uni["secid"] = uni["secid"].astype("int64")
    uni["permno"] = uni["permno"].astype("int64")
    m = uni.drop_duplicates().merge(sic.rename("sic"), on="permno", how="left")
    return m[["secid", "sic"]].drop_duplicates("secid").reset_index(drop=True)
