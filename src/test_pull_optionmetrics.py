"""Unit tests for the OptionMetrics pull's WRDS-free logic.

The pulls themselves need a WRDS connection, but the secid-set assembly (which
governs exactly what gets pulled) is pure and worth pinning: the index and the
extension ETFs must always be included, and the set must be deduped and sorted.
"""

from schema import SPX_SECID
from pull_optionmetrics import assemble_pull_secids


def test_assemble_includes_index_and_etfs():
    """The union always contains the index secid and every ETF secid."""
    out = assemble_pull_secids([5015, 5022], etf_secids=[900001, 900002])
    assert SPX_SECID in out
    assert 900001 in out and 900002 in out
    assert 5015 in out and 5022 in out


def test_assemble_dedupes_and_sorts():
    """Overlaps (e.g. an ETF already among constituents) collapse; result sorts."""
    out = assemble_pull_secids([30, 20, 10, 20], etf_secids=[10, 40])
    assert out == sorted(set(out))
    assert out.count(10) == 1  # deduped despite appearing in both inputs
    assert SPX_SECID in out


def test_assemble_returns_plain_ints():
    """Secids come back as builtin ints (safe for SQL IN-list rendering)."""
    out = assemble_pull_secids([5015], etf_secids=[900001])
    assert all(type(s) is int for s in out)
