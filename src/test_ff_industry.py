"""Tests for the Fama-French 49-industry mapping (ff_industry.py)."""

import pandas as pd

from ff_industry import (
    CLEAN_SECTORS,
    FF49_CODE_TO_SECTOR,
    FF49_TO_ETF,
    assign_ff49,
    assign_sector,
    build_secid_sic,
    ff49_industry,
)


def test_ff49_known_sics():
    assert ff49_industry(6021) == "Banks"  # national commercial bank
    assert ff49_industry(1311) == "Oil"  # crude petroleum & natural gas
    assert ff49_industry(4911) == "Util"  # electric services
    assert ff49_industry(2834) == "Drugs"  # pharmaceutical preparations
    assert ff49_industry(7372) == "Softw"  # prepackaged software
    assert ff49_industry(3571) == "Hardw"  # electronic computers
    assert ff49_industry(6798) == "Fin"  # REITs -> Trading (financials)
    assert ff49_industry(6311) == "Insur"  # life insurance
    assert ff49_industry(2080) == "Beer"  # beverages (not a clean-sector industry)


def test_ff49_unmatched_is_other():
    assert ff49_industry(4955) == "Other"  # sanitary services
    assert ff49_industry(None) == "Other"
    assert ff49_industry(float("nan")) == "Other"
    assert ff49_industry("not a number") == "Other"


def test_sector_crosswalk_covers_eleven_spdrs():
    # All eleven Select Sector SPDR sectors are covered, and the five clean ones are
    # a subset of them.
    assert FF49_CODE_TO_SECTOR["Banks"] == ("Financials", "XLF")
    assert FF49_CODE_TO_SECTOR["Oil"] == ("Energy", "XLE")
    assert FF49_CODE_TO_SECTOR["Chips"] == ("Technology", "XLK")
    assert FF49_CODE_TO_SECTOR["Telcm"] == ("Communication Services", "XLC")
    assert len(FF49_TO_ETF) == 11
    assert CLEAN_SECTORS == {
        "Financials",
        "Technology",
        "Health Care",
        "Energy",
        "Utilities",
    }
    assert CLEAN_SECTORS <= set(FF49_TO_ETF)


def test_assign_sector_routes_reits_to_real_estate():
    # SIC 6798 is FF49 "Fin" (Trading) but belongs to Real Estate / XLRE for the
    # SPDR rollup; a bank (6021) stays in Financials.
    out = assign_sector(pd.DataFrame({"secid": [1, 2], "sic": [6798, 6021]}))
    by = {r.secid: (r.ff_industry, r.sector, r.ticker) for r in out.itertuples()}
    assert by[1] == ("Fin", "Real Estate", "XLRE")
    assert by[2] == ("Banks", "Financials", "XLF")


def test_assign_ff49_one_row_per_secid():
    secid_sic = pd.DataFrame(
        {"secid": [10, 20, 20, 30], "sic": [6021, 1311, 1311, 9995]}
    )
    out = assign_ff49(secid_sic)
    assert len(out) == 3  # deduped per secid
    by = dict(zip(out["secid"], out["ff_industry"]))
    assert by == {10: "Banks", 20: "Oil", 30: "Other"}


def test_build_secid_sic_uses_modal_crsp_sic():
    universe = pd.DataFrame(
        {
            "date": pd.to_datetime(["2010-01-31", "2010-02-28"]),
            "permno": [111, 111],
            "secid": [7, 7],
        }
    )
    # permno 111's SIC is 6021 in two months, 6022 in one -> mode is 6021.
    crsp = pd.DataFrame(
        {
            "permno": [111, 111, 111],
            "date": pd.to_datetime(["2010-01-31", "2010-02-28", "2010-03-31"]),
            "siccd": [6021, 6021, 6022],
        }
    )
    ss = build_secid_sic(universe, crsp)
    assert dict(zip(ss["secid"], ss["sic"])) == {7: 6021}
    assert ff49_industry(ss["sic"].iloc[0]) == "Banks"
