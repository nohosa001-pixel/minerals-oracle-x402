"""
X (Twitter) Market & Arbitrage Alert Bot for minerals-oracle-x402.

Monitors real-time commodity spot feeds, COMEX/LME cross-exchange spreads,
and urban mining scrap yield valuations to format and dispatch high-engagement
alpha tweets to X (Twitter). Supports both live OAuth 1.0a / v2 API dispatch
and simulation / dry-run mode for automated background runs.
"""

import argparse
import asyncio
import base64
import hashlib
import hmac
import logging
import os
import random
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple

# Enable UTF-8 for Windows console output
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from dotenv import load_dotenv
load_dotenv()

import httpx
from app.feed_engine import feed_engine
from app.schemas import CommoditySymbol, ScrapCategory, UrbanMiningRequest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [TwitterBot] %(message)s"
)
logger = logging.getLogger("TwitterBot")

ORACLE_URL = os.getenv("ORACLE_PUBLIC_URL", "https://minerals-oracle-x402-7qxtp3324q-du.a.run.app")
LIVE_DASHBOARD_URL = f"{ORACLE_URL}/dashboard"


class TwitterAlertBot:
    def __init__(self):
        self.api_key = os.getenv("TWITTER_API_KEY", "").strip()
        self.api_secret = os.getenv("TWITTER_API_SECRET", "").strip()
        self.access_token = os.getenv("TWITTER_ACCESS_TOKEN", "").strip()
        self.access_token_secret = os.getenv("TWITTER_ACCESS_SECRET", "").strip()
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN", "").strip()
        self.has_credentials = bool(
            (self.api_key and self.api_secret and self.access_token and self.access_token_secret)
            or self.bearer_token
        )

    def _generate_oauth1_header(self, method: str, url: str, params: Dict[str, Any] = None) -> str:
        """Generates standard OAuth 1.0a HMAC-SHA1 Authorization header for Twitter API v2."""
        oauth_params = {
            "oauth_consumer_key": self.api_key,
            "oauth_nonce": hashlib.sha256(f"{time.time()}_{random.random()}".encode()).hexdigest()[:32],
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": self.access_token,
            "oauth_version": "1.0",
        }
        if params:
            oauth_params.update(params)

        sorted_params = sorted(oauth_params.items())
        param_str = "&".join([f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(str(v), safe='')}" for k, v in sorted_params])
        base_signature_str = f"{method.upper()}&{urllib.parse.quote(url, safe='')}&{urllib.parse.quote(param_str, safe='')}"
        signing_key = f"{urllib.parse.quote(self.api_secret, safe='')}&{urllib.parse.quote(self.access_token_secret, safe='')}"

        signature = hmac.new(signing_key.encode(), base_signature_str.encode(), hashlib.sha1).digest()
        oauth_params["oauth_signature"] = base64.b64encode(signature).decode()

        auth_header = "OAuth " + ", ".join([
            f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(str(v), safe="")}"'
            for k, v in sorted(oauth_params.items()) if k.startswith("oauth_")
        ])
        return auth_header

    def generate_arbitrage_tweet(self) -> str:
        """Generates a clear, professional cross-market arbitrage spread alert tweet."""
        spreads_data = feed_engine.get_arbitrage_spreads()
        spreads = spreads_data.spreads
        if not spreads:
            return self.generate_market_summary_tweet()

        top_spread = max(spreads, key=lambda s: s.spread_basis_points)
        gross_margin = f"${top_spread.net_arbitrage_margin_usd:,.2f}"

        lines = [
            f"📡 [MARKET SPREAD] Cross-Exchange Price Difference Detected",
            f"",
            f"📊 Commodity: {top_spread.symbol.value}",
            f"⚡ Spread: +{top_spread.spread_basis_points:.1f} bps ({(top_spread.spread_basis_points / 100.0):.2f}%)",
            f"🏛️ Venues: {top_spread.primary_exchange} vs {top_spread.secondary_exchange}",
            f"📈 Trade Direction: {top_spread.arbitrage_direction}",
            f"💵 Net Margin: {gross_margin}/MT",
            f"",
            f"🖥️ View Live Interactive Market Dashboard:",
            f"🔗 {LIVE_DASHBOARD_URL}",
            f"",
            f"#Commodities #Metals #RawMaterials #Arbitrage #Base #Recycling"
        ]
        return "\n".join(lines)

    def generate_urban_mining_tweet(self) -> str:
        """Generates an urban mining scrap recovery yield valuation tweet."""
        feedstocks = [
            (ScrapCategory.EV_BATTERY_BLACK_MASS, 5.0, "🔋 EV Battery Black Mass"),
            (ScrapCategory.AUTO_CATALYST_CERAMIC, 2.0, "🚗 Auto Catalyst Ceramic"),
            (ScrapCategory.E_WASTE_HIGH_GRADE_PCB, 10.0, "💻 High-Grade E-Waste PCB"),
            (ScrapCategory.WIND_EV_PERMANENT_MAGNETS, 3.0, "💨 Wind & EV Permanent Magnets"),
        ]
        category, tons, title = random.choice(feedstocks)
        calc_res = feed_engine.calculate_urban_mining(
            UrbanMiningRequest(
                scrap_category=category,
                quantity_metric_tons=tons,
                target_yield_currency="USDC"
            )
        )

        elements_summary = ", ".join([f"{e.mineral_symbol}: {e.payable_weight_kg:,.1f}kg" for e in calc_res.mineral_breakdown[:3]])
        margin_pct = ((calc_res.net_settlement_value_usd / calc_res.total_gross_payable_usd) * 100) if calc_res.total_gross_payable_usd > 0 else 0

        lines = [
            f"♻️ [SCRAP YIELD] Urban Mining Recycling Benchmark Valuation",
            f"",
            f"📦 Material: {title} ({tons} MT Batch)",
            f"💎 Gross Recoverable Value: ${calc_res.total_gross_payable_usd:,.2f}",
            f"⚙️ Smelter TC/RC Charges: ${calc_res.total_treatment_and_refining_charges_usd:,.2f}",
            f"💵 Net Settlement Value: ${calc_res.net_settlement_value_usd:,.2f} USDC (Margin {margin_pct:.1f}%)",
            f"🔬 Recoverable Metals: {elements_summary}",
            f"",
            f"🖥️ Calculate Your Scrap Batches on Live Dashboard:",
            f"🔗 {LIVE_DASHBOARD_URL}",
            f"",
            f"#UrbanMining #Recycling #CircularEconomy #Metals #Lithium #Platinum"
        ]
        return "\n".join(lines)

    def generate_market_summary_tweet(self) -> str:
        """Generates a spot market overview ticker tweet with accurate physical spot prices."""
        quotes_resp = feed_engine.get_all_quotes()
        p_map = quotes_resp.quotes

        ag_q = p_map.get(CommoditySymbol.AG)
        pt_q = p_map.get(CommoditySymbol.PT)
        cu_q = p_map.get(CommoditySymbol.CU)
        li_q = p_map.get(CommoditySymbol.LI)
        nd_q = p_map.get(CommoditySymbol.NDDY)

        ag_str = f"${ag_q.spot_price_usd:.2f}/oz (${ag_q.secondary_prices.get('USD/kg', 1008):,.1f}/kg)" if ag_q else "$31.35/oz"
        pt_str = f"${pt_q.spot_price_usd:.2f}/oz" if pt_q else "$968.00/oz"
        cu_str = f"${cu_q.spot_price_usd:,.0f}/MT (${cu_q.secondary_prices.get('USD/lb', 4.30):.2f}/lb)" if cu_q else "$9,480/MT"
        li_str = f"${li_q.spot_price_usd:,.0f}/MT (${li_q.secondary_prices.get('USD/kg', 11.45):.2f}/kg)" if li_q else "$11,450/MT"
        nd_str = f"${nd_q.spot_price_usd:.2f}/kg (${nd_q.secondary_prices.get('USD/mt', 72500):,.0f}/MT)" if nd_q else "$72.50/kg"

        lines = [
            f"🌐 [SPOT BENCHMARK] Critical Physical Commodities Live Feeds",
            f"",
            f"🥈 Silver (LBMA Ag): {ag_str}",
            f"⚪ Platinum (LPPM Pt): {pt_str}",
            f"🥉 Copper (LME Grade A Cu): {cu_str}",
            f"🔋 Lithium Carbonate (SMM 99.5% Li): {li_str}",
            f"🧲 Neodymium Magnet (Asian Metal NdPr): {nd_str}",
            f"",
            f"🖥️ View Live Interactive Price & Yield Dashboard:",
            f"🔗 {LIVE_DASHBOARD_URL}",
            f"",
            f"#Commodities #Metals #RawMaterials #SupplyChain #Base #DeFi"
        ]
        return "\n".join(lines)

    def generate_random_alert(self) -> Tuple[str, str]:
        """Chooses and builds one of the alert formats."""
        choices = [
            ("arbitrage", self.generate_arbitrage_tweet),
            ("urban_mining", self.generate_urban_mining_tweet),
            ("market_summary", self.generate_market_summary_tweet),
        ]
        alert_type, generator = random.choice(choices)
        return alert_type, generator()

    async def post_tweet(self, text: str, dry_run: bool = False) -> Dict[str, Any]:
        """Dispatches tweet to Twitter API v2 or performs dry-run simulation."""
        timestamp = datetime.now(timezone.utc).isoformat()

        if dry_run or not self.has_credentials:
            logger.info("=== [DRY-RUN / SIMULATION TWEET DISPATCH] ===")
            logger.info(f"\n{text}\n")
            logger.info(f"Length: {len(text)} chars | Credentials configured: {self.has_credentials}")
            return {
                "status": "simulated",
                "mode": "dry_run" if dry_run else "no_credentials_fallback",
                "tweet_text": text,
                "length": len(text),
                "timestamp_utc": timestamp,
                "message": "Tweet successfully simulated and logged. Set TWITTER_API_KEY & TWITTER_ACCESS_TOKEN for live dispatch."
            }

        url = "https://api.twitter.com/2/tweets"
        payload = {"text": text}
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "MineralsOracleBot/1.1.0"
        }

        if self.api_key and self.access_token:
            auth_header = self._generate_oauth1_header("POST", url)
            headers["Authorization"] = auth_header
        elif self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code in (200, 201):
                    res_data = resp.json()
                    logger.info(f"Successfully posted live tweet! Tweet ID: {res_data.get('data', {}).get('id')}")
                    return {
                        "status": "success",
                        "mode": "live",
                        "tweet_id": res_data.get("data", {}).get("id"),
                        "tweet_text": text,
                        "timestamp_utc": timestamp,
                    }
                else:
                    logger.error(f"Twitter API v2 error: {resp.status_code} - {resp.text}")
                    return {
                        "status": "error",
                        "status_code": resp.status_code,
                        "error_details": resp.text,
                        "tweet_text": text,
                        "timestamp_utc": timestamp,
                    }
        except Exception as e:
            logger.error(f"Failed to post tweet via HTTP: {e}")
            return {
                "status": "exception",
                "error": str(e),
                "tweet_text": text,
                "timestamp_utc": timestamp,
            }

    async def run_loop(self, interval_seconds: int = 300, dry_run: bool = False):
        """Continuous execution loop for periodic broadcasting."""
        logger.info(f"Starting Twitter Alert Bot loop (Interval: {interval_seconds}s, Dry-run: {dry_run})")
        while True:
            try:
                alert_type, tweet_content = self.generate_random_alert()
                logger.info(f"Dispatching [{alert_type.upper()}] alert...")
                result = await self.post_tweet(tweet_content, dry_run=dry_run)
                logger.info(f"Dispatch result: {result.get('status')}")
            except Exception as e:
                logger.error(f"Unexpected error in bot iteration: {e}")
            await asyncio.sleep(interval_seconds)


twitter_bot = TwitterAlertBot()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Minerals Oracle X (Twitter) Alert Bot Runner")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Run in simulation mode without calling Twitter API")
    parser.add_argument("--once", action="store_true", default=False, help="Dispatch a single alert and exit")
    parser.add_argument("--interval", type=int, default=300, help="Interval in seconds between tweets in daemon mode")
    parser.add_argument("--type", type=str, choices=["arbitrage", "urban_mining", "market_summary", "random"], default="random", help="Specific alert type")

    args = parser.parse_args()

    async def main():
        if args.type == "arbitrage":
            text = twitter_bot.generate_arbitrage_tweet()
        elif args.type == "urban_mining":
            text = twitter_bot.generate_urban_mining_tweet()
        elif args.type == "market_summary":
            text = twitter_bot.generate_market_summary_tweet()
        else:
            _, text = twitter_bot.generate_random_alert()

        if args.once:
            result = await twitter_bot.post_tweet(text, dry_run=args.dry_run)
            print("\nResult:", result)
        else:
            await twitter_bot.run_loop(interval_seconds=args.interval, dry_run=args.dry_run)

    asyncio.run(main())
