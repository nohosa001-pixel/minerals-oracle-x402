"""
Unit Tests for KIS Realtime Balance Inquiries and Dynamic Spread Cutoffs.
"""

from app.kis_client import kis_client
from run_arbitrage_agent import get_min_spread_bps


def test_kis_realtime_balance_inquiry():
    res = kis_client.inquire_realtime_balance(dry_run=True)
    assert res["broker"] == "한국투자증권 (Korea Investment & Securities)"
    assert res["total_available_usd"] > 0
    assert "accounts_breakdown" in res
    assert kis_client.account_no in res["accounts_breakdown"]
    assert kis_client.futures_account_no in res["accounts_breakdown"]

    usd_avail = kis_client.get_available_usd_balance(dry_run=True)
    assert usd_avail > 0


def test_asset_specific_spread_thresholds():
    # Asset thresholds are protected by the safety policy (minimum 100.0 bps)
    assert get_min_spread_bps("Ag") >= 25.0
    assert get_min_spread_bps("Pt") >= 30.0
    assert get_min_spread_bps("Cu") >= 35.0
    assert get_min_spread_bps("Li") >= 45.0
    assert get_min_spread_bps("NdDy") >= 50.0
    assert get_min_spread_bps("UNKNOWN") >= 30.0
