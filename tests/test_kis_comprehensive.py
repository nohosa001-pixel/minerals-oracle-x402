"""
Unit tests for Comprehensive KIS Client Ecosystem & Position Synchronization.
"""

from app.kis_client import kis_client
from app.cloud_bot_worker import CloudArbitrageWorker


def test_kis_overseas_stock_holdings():
    res = kis_client.inquire_overseas_stock_holdings(dry_run=True)
    assert res["status"] in ("SIMULATED_HOLDINGS", "LIVE_VERIFIED")
    assert "items" in res
    assert len(res["items"]) >= 2
    
    tickers = [x["ticker"] for x in res["items"]]
    assert "SLV" in tickers
    assert "PPLT" in tickers
    assert res["total_eval_usd"] > 0


def test_kis_domestic_stock_holdings():
    res = kis_client.inquire_domestic_stock_holdings(dry_run=True)
    assert res["status"] in ("SIMULATED", "LIVE_VERIFIED")
    assert "items" in res


def test_kis_filled_orders():
    orders = kis_client.inquire_filled_orders(dry_run=True)
    assert isinstance(orders, list)


def test_kis_position_sync_with_bot():
    synced = kis_client.sync_live_positions_with_bot(dry_run=True)
    assert "Ag" in synced or "Pt" in synced
    if "Ag" in synced:
        assert synced["Ag"]["ticker"] == "SLV"
        assert synced["Ag"]["quantity"] == 4
    if "Pt" in synced:
        assert synced["Pt"]["ticker"] == "PPLT"
        assert synced["Pt"]["quantity"] == 3


def test_kis_realtime_balance_integrated():
    bal = kis_client.inquire_realtime_balance(dry_run=True)
    assert bal["broker"] == "한국투자증권 (Korea Investment & Securities)"
    assert bal["total_available_usd"] > 0
    assert "holdings" in bal
    assert bal["holdings_count"] >= 2
    assert bal["overseas_stock_eval_usd"] > 0
    assert bal["total_net_worth_usd"] > bal["total_available_usd"]


def test_kis_execute_position_close():
    res = kis_client.execute_position_close("Ag", quantity=2, price_usd=59.0, dry_run=True)
    assert res["status"] in ("DRY_RUN_UNEXECUTED", "FILLED_SIMULATED")
    assert res["direction"] == "Sell (Close Position)"
    assert res["ticker"] == "SLV"
