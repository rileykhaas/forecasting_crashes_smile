"""Tests for the Fama-French 12-industry mapping (ff_industry.py)."""

import pandas as pd

from ff_industry import assign_ff12, build_secid_sic, ff12_industry


def test_ff12_known_sics():
    assert ff12_industry(6021) == "Money"   # national commercial bank
    assert ff12_industry(1311) == "Enrgy"   # crude petroleum & natural gas
    assert ff12_industry(4911) == "Utils"   # electric services
    assert ff12_industry(2834) == "Hlth"    # pharmaceutical preparations
    assert ff12_industry(7372) == "BusEq"   # prepackaged software
    assert ff12_industry(2080) == "NoDur"   # beverages


def test_ff12_unmatched_is_other():
    assert ff12_industry(9995) == "Other"   # non-classifiable
    assert ff12_industry(None) == "Other"
    assert ff12_industry(float("nan")) == "Other"
    assert ff12_industry("not a number") == "Other"


def test_assign_ff12_one_row_per_secid():
    secid_sic = pd.DataFrame({"secid": [10, 20, 20, 30], "sic": [6021, 1311, 1311, 9995]})
    out = assign_ff12(secid_sic)
    assert len(out) == 3  # deduped per secid
    by = dict(zip(out["secid"], out["ff_industry"]))
    assert by == {10: "Money", 20: "Enrgy", 30: "Other"}


def test_build_secid_sic_uses_modal_crsp_sic():
    universe = pd.DataFrame({
        "date": pd.to_datetime(["2010-01-31", "2010-02-28"]),
        "permno": [111, 111], "secid": [7, 7],
    })
    # permno 111's SIC is 6021 in two months, 6022 in one -> mode is 6021.
    crsp = pd.DataFrame({
        "permno": [111, 111, 111],
        "date": pd.to_datetime(["2010-01-31", "2010-02-28", "2010-03-31"]),
        "siccd": [6021, 6021, 6022],
    })
    ss = build_secid_sic(universe, crsp)
    assert dict(zip(ss["secid"], ss["sic"])) == {7: 6021}
    assert ff12_industry(ss["sic"].iloc[0]) == "Money"
