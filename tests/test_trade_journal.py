"""
Unit Tests for TradeJournal CSV recording and persistence.
"""

import csv
import os
import shutil
import tempfile
from app.trade_journal import TradeJournal, CSV_HEADER


def test_trade_journal_creation_and_recording():
    temp_dir = tempfile.mkdtemp()
    try:
        journal = TradeJournal(log_dir=temp_dir)
        
        test_trade = {
            "trade_id": "EXIT-Cu-0001",
            "timestamp_utc": "2026-09-01 06:00:00 UTC",
            "symbol": "Cu",
            "action": "SPREAD_CONVERGED",
            "direction": "Sell (Close Position)",
            "instrument_type": "OVERSEAS_FUTURES",
            "quantity": 1,
            "entry_price": 15000.0,
            "exit_price": 15150.0,
            "gain_pct": 1.0,
            "spread_bps": 85.0,
            "entry_bps": 120.0,
            "holding_sec": 120.0,
            "initial_margin_usd": 950.0,
            "gross_profit_usd": 75.0,
            "commission_fee_usd": 1.50,
            "gas_fee_usd": 0.02,
            "net_pnl_usd": 73.48,
            "kis_account": "10061681-08",
            "kis_order_id": "ORD-12345",
            "kis_ticker": "MHG",
            "tx_hash": "0x123abc456def",
        }

        success = journal.record_trade(test_trade)
        assert success is True

        master_path = journal.master_csv_path
        assert os.path.exists(master_path)

        with open(master_path, "r", encoding="utf-8-sig") as f:
            reader = list(csv.reader(f))
            assert len(reader) == 2  # Header + 1 record
            assert reader[0] == CSV_HEADER
            assert reader[1][1] == "EXIT-Cu-0001"
            assert reader[1][2] == "Cu"
            assert float(reader[1][17]) == 73.48  # net_pnl_usd
    finally:
        shutil.rmtree(temp_dir)
