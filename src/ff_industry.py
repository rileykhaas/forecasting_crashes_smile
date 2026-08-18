"""Fama-French 49-industry classification (SIC -> industry).

Martin & Shi (2025) define their industry crash-probability measures (Figure 10) using
the **Fama-French 49 industry classification** ("Figure 10 shows the average
probabilities of 20% crashes in one year for various industries, defined using the
Fama-French 49 industry classification"). We reproduce that classification exactly,
from Kenneth French's data library, and assign each S&P 500 constituent to an FF49
industry from its CRSP SIC code.

For the proxy-vs-direct comparison (exhibit_industry_compare) we then roll the FF49
industries up to the eleven Select Sector SPDR ETFs (the GICS sectors) via
``FF49_TO_ETF``. Five sectors map cleanly (``CLEAN_SECTORS``: Financials, Technology,
Health Care, Energy, Utilities); the other six are best-fit approximations because
FF49's manufacturing/consumer industries straddle GICS lines. REITs (SIC 6798), which
FF49 files under "Trading", are routed to Real Estate so XLRE has a representative proxy.

``ff49_industry(sic)`` returns the industry code; ``assign_ff49(secid_sic)`` maps a
[secid, sic] table to [secid, ff_industry]; ``assign_sector(secid_sic)`` adds the
rolled-up [sector, ticker]. Ranges are inclusive; anything unmatched falls in "Other".
"""

import pandas as pd

# FF49: (code, description, inclusive SIC ranges). Kenneth French "Siccodes49".
FF49_DEFS = [
    (
        "Agric",
        "Agriculture",
        [(100, 199), (200, 299), (700, 799), (910, 919), (2048, 2048)],
    ),
    (
        "Food",
        "Food Products",
        [
            (2000, 2009),
            (2010, 2019),
            (2020, 2029),
            (2030, 2039),
            (2040, 2046),
            (2050, 2059),
            (2060, 2063),
            (2070, 2079),
            (2090, 2092),
            (2095, 2095),
            (2098, 2099),
        ],
    ),
    ("Soda", "Candy & Soda", [(2064, 2068), (2086, 2086), (2087, 2087), (2096, 2097)]),
    ("Beer", "Beer & Liquor", [(2080, 2080), (2082, 2085)]),
    ("Smoke", "Tobacco Products", [(2100, 2199)]),
    (
        "Toys",
        "Recreation",
        [
            (920, 999),
            (3650, 3651),
            (3652, 3652),
            (3732, 3732),
            (3930, 3931),
            (3940, 3949),
        ],
    ),
    (
        "Fun",
        "Entertainment",
        [
            (7800, 7833),
            (7840, 7841),
            (7900, 7900),
            (7910, 7911),
            (7920, 7933),
            (7940, 7949),
            (7980, 7980),
            (7990, 7999),
        ],
    ),
    ("Books", "Printing and Publishing", [(2700, 2749), (2770, 2771), (2780, 2799)]),
    (
        "Hshld",
        "Consumer Goods",
        [
            (2047, 2047),
            (2391, 2392),
            (2510, 2519),
            (2590, 2599),
            (2840, 2844),
            (3160, 3172),
            (3190, 3199),
            (3229, 3231),
            (3260, 3260),
            (3262, 3263),
            (3269, 3269),
            (3630, 3639),
            (3750, 3751),
            (3800, 3800),
            (3860, 3861),
            (3870, 3873),
            (3910, 3911),
            (3914, 3915),
            (3960, 3962),
            (3991, 3991),
            (3995, 3995),
        ],
    ),
    (
        "Clths",
        "Apparel",
        [
            (2300, 2390),
            (3020, 3021),
            (3100, 3111),
            (3130, 3131),
            (3140, 3151),
            (3963, 3965),
        ],
    ),
    ("Hlth", "Healthcare", [(8000, 8099)]),
    ("MedEq", "Medical Equipment", [(3693, 3693), (3840, 3851)]),
    ("Drugs", "Pharmaceutical Products", [(2830, 2831), (2833, 2836)]),
    (
        "Chems",
        "Chemicals",
        [
            (2800, 2809),
            (2810, 2819),
            (2820, 2829),
            (2850, 2859),
            (2860, 2879),
            (2890, 2899),
        ],
    ),
    (
        "Rubbr",
        "Rubber and Plastic Products",
        [(3031, 3031), (3041, 3041), (3050, 3053), (3060, 3099)],
    ),
    (
        "Txtls",
        "Textiles",
        [(2200, 2284), (2290, 2295), (2297, 2299), (2393, 2395), (2397, 2399)],
    ),
    (
        "BldMt",
        "Construction Materials",
        [
            (800, 899),
            (2400, 2439),
            (2450, 2459),
            (2490, 2499),
            (2660, 2661),
            (2950, 2952),
            (3200, 3200),
            (3210, 3211),
            (3240, 3241),
            (3250, 3259),
            (3261, 3261),
            (3264, 3264),
            (3270, 3275),
            (3280, 3281),
            (3290, 3293),
            (3295, 3299),
            (3420, 3433),
            (3440, 3442),
            (3446, 3452),
            (3490, 3499),
            (3996, 3996),
        ],
    ),
    ("Cnstr", "Construction", [(1500, 1511), (1520, 1549), (1600, 1799)]),
    (
        "Steel",
        "Steel Works Etc",
        [
            (3300, 3300),
            (3310, 3317),
            (3320, 3325),
            (3330, 3341),
            (3350, 3357),
            (3360, 3379),
            (3390, 3399),
        ],
    ),
    ("FabPr", "Fabricated Products", [(3400, 3400), (3443, 3444), (3460, 3479)]),
    (
        "Mach",
        "Machinery",
        [
            (3510, 3536),
            (3538, 3538),
            (3540, 3569),
            (3580, 3582),
            (3585, 3586),
            (3589, 3599),
        ],
    ),
    (
        "ElcEq",
        "Electrical Equipment",
        [
            (3600, 3600),
            (3610, 3613),
            (3620, 3621),
            (3623, 3629),
            (3640, 3646),
            (3648, 3649),
            (3660, 3660),
            (3690, 3692),
            (3699, 3699),
        ],
    ),
    (
        "Autos",
        "Automobiles and Trucks",
        [
            (2296, 2296),
            (2396, 2396),
            (3010, 3011),
            (3537, 3537),
            (3647, 3647),
            (3694, 3694),
            (3700, 3700),
            (3710, 3711),
            (3713, 3716),
            (3790, 3792),
            (3799, 3799),
        ],
    ),
    ("Aero", "Aircraft", [(3720, 3721), (3723, 3725), (3728, 3729)]),
    ("Ships", "Shipbuilding, Railroad Equipment", [(3730, 3731), (3740, 3743)]),
    ("Guns", "Defense", [(3480, 3489), (3760, 3769), (3795, 3795)]),
    ("Gold", "Precious Metals", [(1040, 1049)]),
    (
        "Mines",
        "Non-Metallic and Industrial Metal Mining",
        [(1000, 1039), (1050, 1119), (1400, 1499)],
    ),
    ("Coal", "Coal", [(1200, 1299)]),
    (
        "Oil",
        "Petroleum and Natural Gas",
        [(1300, 1300), (1310, 1339), (1370, 1389), (2900, 2912), (2990, 2999)],
    ),
    (
        "Util",
        "Utilities",
        [(4900, 4900), (4910, 4911), (4920, 4925), (4930, 4932), (4939, 4942)],
    ),
    (
        "Telcm",
        "Communication",
        [
            (4800, 4800),
            (4810, 4813),
            (4820, 4822),
            (4830, 4841),
            (4880, 4892),
            (4899, 4899),
        ],
    ),
    (
        "PerSv",
        "Personal Services",
        [
            (7020, 7021),
            (7030, 7033),
            (7200, 7212),
            (7214, 7217),
            (7219, 7221),
            (7230, 7231),
            (7240, 7241),
            (7250, 7251),
            (7260, 7299),
            (7395, 7395),
            (7500, 7500),
            (7510, 7549),
            (7600, 7600),
            (7620, 7620),
            (7622, 7623),
            (7629, 7631),
            (7640, 7641),
            (7690, 7699),
            (8100, 8499),
            (8600, 8699),
            (8800, 8899),
        ],
    ),
    (
        "BusSv",
        "Business Services",
        [
            (2750, 2759),
            (3993, 3993),
            (7218, 7218),
            (7300, 7342),
            (7349, 7353),
            (7359, 7369),
            (7374, 7374),
            (7376, 7385),
            (7389, 7394),
            (7396, 7397),
            (7399, 7399),
            (7519, 7519),
            (8700, 8748),
            (8900, 8911),
            (8920, 8999),
            (4220, 4229),
        ],
    ),
    ("Hardw", "Computers", [(3570, 3579), (3680, 3689), (3695, 3695)]),
    ("Softw", "Computer Software", [(7370, 7373), (7375, 7375)]),
    (
        "Chips",
        "Electronic Equipment",
        [(3622, 3622), (3661, 3666), (3669, 3679), (3810, 3810), (3812, 3812)],
    ),
    (
        "LabEq",
        "Measuring and Control Equipment",
        [(3811, 3811), (3820, 3827), (3829, 3839)],
    ),
    (
        "Paper",
        "Business Supplies",
        [
            (2440, 2449),
            (2520, 2549),
            (2600, 2639),
            (2670, 2699),
            (2760, 2761),
            (3950, 3955),
        ],
    ),
    (
        "Boxes",
        "Shipping Containers",
        [(2440, 2449), (2640, 2659), (3220, 3221), (3410, 3412)],
    ),
    (
        "Trans",
        "Transportation",
        [
            (4000, 4013),
            (4040, 4049),
            (4100, 4100),
            (4110, 4121),
            (4130, 4131),
            (4140, 4142),
            (4150, 4151),
            (4170, 4173),
            (4190, 4200),
            (4210, 4231),
            (4240, 4249),
            (4400, 4700),
            (4710, 4712),
            (4720, 4749),
            (4780, 4780),
            (4782, 4785),
            (4789, 4789),
        ],
    ),
    (
        "Whlsl",
        "Wholesale",
        [
            (5000, 5000),
            (5010, 5015),
            (5020, 5023),
            (5030, 5060),
            (5063, 5065),
            (5070, 5078),
            (5080, 5088),
            (5090, 5094),
            (5099, 5100),
            (5110, 5113),
            (5120, 5122),
            (5130, 5172),
            (5180, 5182),
            (5190, 5199),
        ],
    ),
    (
        "Rtail",
        "Retail",
        [
            (5200, 5200),
            (5210, 5231),
            (5250, 5251),
            (5260, 5271),
            (5300, 5300),
            (5310, 5311),
            (5320, 5320),
            (5330, 5331),
            (5334, 5334),
            (5340, 5349),
            (5390, 5400),
            (5410, 5412),
            (5420, 5469),
            (5490, 5500),
            (5510, 5579),
            (5590, 5700),
            (5710, 5722),
            (5730, 5736),
            (5750, 5799),
            (5900, 5900),
            (5910, 5912),
            (5920, 5921),
            (5930, 5932),
            (5940, 5990),
            (5992, 5995),
            (5999, 5999),
        ],
    ),
    (
        "Meals",
        "Restaurants, Hotels, Motels",
        [
            (5800, 5829),
            (5890, 5899),
            (7000, 7000),
            (7010, 7019),
            (7040, 7049),
            (7213, 7213),
        ],
    ),
    (
        "Banks",
        "Banking",
        [
            (6000, 6000),
            (6010, 6036),
            (6040, 6062),
            (6080, 6082),
            (6090, 6100),
            (6110, 6113),
            (6120, 6179),
            (6190, 6199),
        ],
    ),
    (
        "Insur",
        "Insurance",
        [
            (6300, 6300),
            (6310, 6331),
            (6350, 6351),
            (6360, 6361),
            (6370, 6379),
            (6390, 6411),
        ],
    ),
    (
        "RlEst",
        "Real Estate",
        [
            (6500, 6500),
            (6510, 6510),
            (6512, 6515),
            (6517, 6532),
            (6540, 6541),
            (6550, 6553),
            (6590, 6599),
            (6610, 6611),
        ],
    ),
    (
        "Fin",
        "Trading",
        [
            (6200, 6299),
            (6700, 6700),
            (6710, 6726),
            (6730, 6733),
            (6740, 6779),
            (6790, 6795),
            (6798, 6799),
        ],
    ),
    # "Other" (SIC 4950-4961, 4970-4971, 4990-4991, and anything unmatched) is the fallback.
]

FF49_LABELS = {code: desc for code, desc, _ in FF49_DEFS}

# Crosswalk from FF49 industries to the eleven Select Sector SPDR ETFs (the GICS
# sectors). Sector label -> (ETF, [FF49 codes]). Five of these sectors map cleanly --
# every FF49 industry in them clearly belongs to that one GICS sector:
#     Financials, Technology, Energy, Health Care, Utilities.
# The other six are approximate: FF49's manufacturing/consumer industries straddle the
# GICS Materials / Industrials / Discretionary / Staples / Communication lines, so a few
# member industries could defensibly sit elsewhere (e.g. FF49 "Hshld" spans household
# products and consumer durables). We assign each FF49 industry to the single best-fit
# SPDR sector and flag the split in the report.
FF49_TO_ETF = {
    "Financials": ("XLF", ["Banks", "Insur", "Fin"]),
    "Technology": ("XLK", ["Hardw", "Softw", "Chips"]),
    "Health Care": ("XLV", ["Hlth", "MedEq", "Drugs"]),
    "Energy": ("XLE", ["Oil", "Coal"]),
    "Utilities": ("XLU", ["Util"]),
    "Real Estate": ("XLRE", ["RlEst"]),  # + REITs, via the SIC carve-out below
    "Consumer Discretionary": (
        "XLY",
        ["Autos", "Toys", "Clths", "Txtls", "Rtail", "Meals", "PerSv", "Whlsl"],
    ),
    "Consumer Staples": ("XLP", ["Food", "Soda", "Beer", "Smoke", "Agric", "Hshld"]),
    "Industrials": (
        "XLI",
        [
            "Mach",
            "ElcEq",
            "Aero",
            "Ships",
            "Guns",
            "Cnstr",
            "FabPr",
            "Trans",
            "BusSv",
            "LabEq",
        ],
    ),
    "Materials": (
        "XLB",
        ["Chems", "Steel", "Gold", "Mines", "Paper", "Boxes", "BldMt", "Rubbr"],
    ),
    "Communication Services": ("XLC", ["Telcm", "Fun", "Books"]),
}
# The five sectors whose FF49 composition is unambiguous (used to flag the rest).
CLEAN_SECTORS = {"Financials", "Technology", "Health Care", "Energy", "Utilities"}

# FF49 code -> (sector label, ETF ticker).
FF49_CODE_TO_SECTOR = {
    code: (sector, etf)
    for sector, (etf, codes) in FF49_TO_ETF.items()
    for code in codes
}

# REITs (SIC 6798-6799) are filed under FF49 "Fin" (Trading), but they *are* the GICS
# Real Estate sector and the bulk of XLRE, so we route them to Real Estate for the
# sector rollup. This also de-contaminates Financials (post-2016 XLF excludes REITs).
REIT_SIC_RANGES = [(6798, 6799)]


def _is_reit(sic):
    try:
        s = int(sic)
    except (TypeError, ValueError):
        return False
    return any(lo <= s <= hi for lo, hi in REIT_SIC_RANGES)


def ff49_industry(sic):
    """FF49 industry code for a SIC code (``"Other"`` if unmatched/missing)."""
    if sic is None or (isinstance(sic, float) and pd.isna(sic)):
        return "Other"
    try:
        s = int(sic)
    except (TypeError, ValueError):
        return "Other"
    for code, _desc, ranges in FF49_DEFS:
        if any(lo <= s <= hi for lo, hi in ranges):
            return code
    return "Other"


def assign_ff49(secid_sic):
    """Map a [secid, sic] frame to [secid, ff_industry] (one row per secid)."""
    out = secid_sic.dropna(subset=["secid"]).drop_duplicates("secid").copy()
    out["secid"] = out["secid"].astype("int64")
    out["ff_industry"] = out["sic"].map(ff49_industry)
    return out[["secid", "ff_industry"]].reset_index(drop=True)


def assign_sector(secid_sic):
    """Map a [secid, sic] frame to [secid, ff_industry, sector, ticker] (one row per
    secid): the FF49 industry (the paper's classification), rolled up to its Select
    Sector SPDR via ``FF49_TO_ETF``, with REITs routed to Real Estate. Names in FF49
    "Other" (no SPDR sector) get ``sector``/``ticker`` = None."""
    out = assign_ff49(secid_sic).merge(
        secid_sic.drop_duplicates("secid")[["secid", "sic"]].astype({"secid": "int64"}),
        on="secid",
        how="left",
    )
    mapped = out["ff_industry"].map(lambda c: FF49_CODE_TO_SECTOR.get(c, (None, None)))
    out["sector"] = [s for s, _ in mapped]
    out["ticker"] = [t for _, t in mapped]
    reit = out["sic"].map(_is_reit)
    out.loc[reit, ["sector", "ticker"]] = ["Real Estate", "XLRE"]
    return out[["secid", "ff_industry", "sector", "ticker"]].reset_index(drop=True)


def build_secid_sic(universe, crsp_monthly):
    """[secid, sic] for constituents: the modal CRSP ``siccd`` per permno, mapped to
    secid via the universe's secid<->permno pairs."""
    sic = (
        crsp_monthly.dropna(subset=["siccd"])
        .groupby("permno")["siccd"]
        .agg(lambda s: s.mode().iloc[0])
    )
    uni = universe.dropna(subset=["secid", "permno"])[["secid", "permno"]].copy()
    uni["secid"] = uni["secid"].astype("int64")
    uni["permno"] = uni["permno"].astype("int64")
    m = uni.drop_duplicates().merge(sic.rename("sic"), on="permno", how="left")
    return m[["secid", "sic"]].drop_duplicates("secid").reset_index(drop=True)
