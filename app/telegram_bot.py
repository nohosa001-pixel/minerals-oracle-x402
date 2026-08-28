"""
Telegram Market & Arbitrage Alert Bot for minerals-oracle-x402.
Sends real-time high-priority alerts for profitable commodity basis spreads,
market summaries, and scrap yield valuations directly to Telegram channels/chat.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("TelegramBot")

class TelegramAlertBot:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        self.has_credentials = bool(self.bot_token and self.chat_id)

    def generate_arbitrage_message(self, spread_info: Dict[str, Any]) -> str:
        """Formats a high-priority telegram alert for detected arbitrage spreads."""
        symbol = spread_info.get("symbol", "Commodity")
        bps = spread_info.get("spread_basis_points", 0.0)
        net_margin = spread_info.get("net_arbitrage_margin_usd", 0.0)
        direction = spread_info.get("arbitrage_direction", "")
        primary_ex = spread_info.get("primary_exchange", "")
        sec_ex = spread_info.get("secondary_exchange", "")
        spread_usd = spread_info.get("spread_usd", 0.0)

        return (
            f"🚨 <b>[ARBITRAGE ALERT] +{bps:.1f} bps Opportunity Detected!</b>\n\n"
            f"💎 <b>Commodity:</b> {symbol}\n"
            f"🏛️ <b>Venues:</b> {primary_ex} vs {sec_ex}\n"
            f"📊 <b>Gross Spread:</b> ${spread_usd:,.2f} ({bps:.1f} bps)\n"
            f"💵 <b>Net Margin:</b> <b>+${net_margin:,.2f}/MT</b> (After Freight/Tariff)\n"
            f"⚡ <b>Strategy:</b> <code>{direction}</code>\n\n"
            f"🔗 <a href='https://minerals-oracle-x402-7qxtp3324q-du.a.run.app/dashboard'>Live Market Dashboard</a>\n"
            f"#MineralsOracle #Arbitrage #Polygon"
        )

    def generate_summary_message(self, quotes: Dict[str, Any]) -> str:
        """Formats a comprehensive market overview message."""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        
        lines = [
            f"🌐 <b>[MARKET SUMMARY] Critical Minerals Live Benchmark</b>",
            f"⏱ <i>{now_str}</i>\n"
        ]

        def get_field(obj, key, default=0):
            if hasattr(obj, key):
                return getattr(obj, key)
            if isinstance(obj, dict):
                return obj.get(key, default)
            return default

        # Normalize keys (handle both CommoditySymbol enum and string keys)
        normalized = {}
        for k, v in quotes.items():
            sym_key = k.value if hasattr(k, "value") else str(k)
            normalized[sym_key] = v

        if "Ag" in normalized:
            q = normalized["Ag"]
            lines.append(f"🥈 <b>Silver (Ag):</b> ${get_field(q, 'spot_price_usd'):,.2f}/oz ({get_field(q, 'change_24h_pct'):+.2f}%)")
        if "Pt" in normalized:
            q = normalized["Pt"]
            lines.append(f"⚪ <b>Platinum (Pt):</b> ${get_field(q, 'spot_price_usd'):,.2f}/oz ({get_field(q, 'change_24h_pct'):+.2f}%)")
        if "Cu" in normalized:
            q = normalized["Cu"]
            lines.append(f"🥉 <b>Copper (Cu):</b> ${get_field(q, 'spot_price_usd'):,.2f}/mt ({get_field(q, 'change_24h_pct'):+.2f}%)")
        if "Li" in normalized:
            q = normalized["Li"]
            lines.append(f"🔋 <b>Lithium (Li):</b> ${get_field(q, 'spot_price_usd'):,.2f}/mt ({get_field(q, 'change_24h_pct'):+.2f}%)")
        if "NdDy" in normalized:
            q = normalized["NdDy"]
            lines.append(f"🧲 <b>Neodymium (NdDy):</b> ${get_field(q, 'spot_price_usd'):,.2f}/kg ({get_field(q, 'change_24h_pct'):+.2f}%)")

        lines.append(f"\n🖥️ <a href='https://minerals-oracle-x402-212942243360.asia-northeast3.run.app/dashboard'>Open Oracle Dashboard</a>")
        return "\n".join(lines)

    async def send_message(self, text: str, parse_mode: str = "HTML", dry_run: bool = False) -> Dict[str, Any]:
        """Dispatches HTML-formatted message to Telegram or performs dry-run simulation."""
        timestamp = datetime.now(timezone.utc).isoformat()

        if dry_run or not self.has_credentials:
            logger.info("=== [TELEGRAM ALERT SIMULATION / DRY-RUN] ===")
            logger.info(f"\n{text}\n")
            return {
                "status": "simulated",
                "mode": "dry_run" if dry_run else "no_credentials_fallback",
                "message_text": text,
                "timestamp_utc": timestamp,
                "detail": "Alert successfully simulated. Set TELEGRAM_BOT_TOKEN & TELEGRAM_CHAT_ID in .env for live smartphone push."
            }

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": False,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    return {
                        "status": "success",
                        "telegram_message_id": resp.json().get("result", {}).get("message_id"),
                        "timestamp_utc": timestamp,
                    }
                else:
                    return {
                        "status": "error",
                        "code": resp.status_code,
                        "error": resp.text,
                        "timestamp_utc": timestamp,
                    }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp_utc": timestamp,
            }


# Singleton Telegram alert bot instance
telegram_bot = TelegramAlertBot()
