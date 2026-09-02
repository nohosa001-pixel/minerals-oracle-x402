"""
Trade Journal & Historical Analytics Logger for Minerals Oracle x402.
Automatically exports every executed/closed round-trip trade into:
1. logs/trade_journal_YYYYMMDD.csv (Daily segmented log for tax & accounting)
2. logs/trade_journal_master.csv (Consolidated cumulative execution log)
"""

import csv
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger("TradeJournal")

CSV_HEADER = [
    "timestamp_utc",
    "trade_id",
    "symbol",
    "action",
    "direction",
    "instrument_type",
    "quantity",
    "entry_price_usd",
    "exit_price_usd",
    "gain_pct",
    "spread_bps",
    "entry_bps",
    "holding_sec",
    "initial_margin_usd",
    "gross_profit_usd",
    "commission_usd",
    "gas_fee_usd",
    "net_pnl_usd",
    "kis_account",
    "kis_order_id",
    "kis_ticker",
    "tx_hash",
]


class TradeJournal:
    def __init__(self, log_dir: Optional[str] = None):
        if log_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.log_dir = os.path.join(base_dir, "logs")
        else:
            self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.master_csv_path = os.path.join(self.log_dir, "trade_journal_master.csv")
        self._ensure_header(self.master_csv_path)

    def _get_daily_csv_path(self, dt: Optional[datetime] = None) -> str:
        if dt is None:
            dt = datetime.now(timezone.utc)
        date_str = dt.strftime("%Y%m%d")
        return os.path.join(self.log_dir, f"trade_journal_{date_str}.csv")

    def _ensure_header(self, filepath: str):
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            try:
                with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow(CSV_HEADER)
            except Exception as e:
                logger.warning("Failed to initialize CSV header in %s: %s", filepath, e)

    def record_trade(self, trade_record: Dict[str, Any]) -> bool:
        """
        Appends a closed trade record into both the daily CSV and master CSV files.
        """
        now = datetime.now(timezone.utc)
        daily_csv_path = self._get_daily_csv_path(now)
        self._ensure_header(daily_csv_path)

        timestamp_utc = trade_record.get("timestamp_utc") or trade_record.get("timestamp") or now.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        row = [
            timestamp_utc,
            trade_record.get("trade_id", ""),
            trade_record.get("symbol", ""),
            trade_record.get("action", "SPREAD_CONVERGED"),
            trade_record.get("direction", "Sell (Close Position)"),
            trade_record.get("instrument_type", trade_record.get("contract_description", "")),
            trade_record.get("quantity", 1),
            f"{float(trade_record.get('entry_price', 0.0)):.2f}",
            f"{float(trade_record.get('exit_price', 0.0)):.2f}",
            f"{float(trade_record.get('gain_pct', 0.0)):+.2f}",
            f"{float(trade_record.get('spread_bps', trade_record.get('entry_bps', 0.0))):.1f}",
            f"{float(trade_record.get('entry_bps', 0.0)):.1f}",
            f"{float(trade_record.get('holding_sec', 0.0)):.1f}",
            f"{float(trade_record.get('initial_margin_usd', 0.0)):.2f}",
            f"{float(trade_record.get('gross_profit_usd', 0.0)):.2f}",
            f"{float(trade_record.get('commission_fee_usd', trade_record.get('commission_usd', 0.0))):.2f}",
            f"{float(trade_record.get('gas_fee_usd', 0.0)):.2f}",
            f"{float(trade_record.get('net_pnl_usd', 0.0)):.2f}",
            trade_record.get("kis_account", ""),
            trade_record.get("kis_order_id", ""),
            trade_record.get("kis_ticker", ""),
            trade_record.get("tx_hash", ""),
        ]

        success = True
        for path in (daily_csv_path, self.master_csv_path):
            try:
                with open(path, "a", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow(row)
            except Exception as e:
                logger.error("Error writing trade to %s: %s", path, e)
                success = False

        if success:
            logger.info("Recorded trade %s to CSV journals", trade_record.get("trade_id"))
        return success


# Global Singleton Instance
trade_journal = TradeJournal()
