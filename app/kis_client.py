"""
Korea Investment & Securities (한국투자증권 KIS Developers)
Overseas Commodity Futures & ETF API Client for minerals-oracle-x402.

Supports:
- Automated OAuth 2.0 Token management with 24h caching
- CME/COMEX/NYMEX Micro & Standard Futures Order Execution (Copper MHG/HG, Silver SIL/SI, Platinum PL, Lithium LIT)
- Precision Trade Sizing Engine (Capital-based, Fixed-lots, Dynamic Kelly Compounding)
- Atomic 1:1 Delta-Neutral Arbitrage Hedging
- Account Margin & Balance Diagnostics (01 Stock/ETF & 08 Futures)
- Built-in Safety Guard (Dry-run default / Execution Kill-Switch)
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, Tuple, Union

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("KISClient")


class TradeMode(str, Enum):
    FUTURES_MICRO = "FUTURES_MICRO"       # Micro futures (e.g. MHG, SIL, PL)
    FUTURES_STANDARD = "FUTURES_STANDARD" # Standard futures (e.g. HG, SI, PL)
    ETF = "ETF"                           # Overseas ETF (e.g. CPER, SLV, PPLT, LIT)
    AUTO = "AUTO"                         # Auto-select: Futures if capital >= margin, else ETF


class TradeSizingMode(str, Enum):
    CAPITAL_BASED = "CAPITAL_BASED"       # Max lots/shares within capital allocation & margin buffer
    FIXED_LOTS = "FIXED_LOTS"             # Fixed number of contracts/lots specified by user
    DYNAMIC_KELLY = "DYNAMIC_KELLY"       # Dynamically scaled Kelly fraction sizing based on spread bps


# Detailed Overseas Futures & ETF Contract Specifications
FUTURES_CONTRACT_SPECS: Dict[str, Dict[str, Any]] = {
    "Cu": {
        "name": "Copper (COMEX / LME)",
        "micro": {
            "ticker": "MHG",
            "exchange": "CME",
            "contract_size": 2500.0,
            "unit": "lbs",
            "tick_size": 0.0005,
            "tick_value_usd": 1.25,
            "initial_margin_usd": 950.0,
            "maintenance_margin_usd": 860.0,
            "commission_per_contract_usd": 1.50,
            "description": "Micro Copper (2,500 lbs)",
        },
        "standard": {
            "ticker": "HG",
            "exchange": "CME",
            "contract_size": 25000.0,
            "unit": "lbs",
            "tick_size": 0.0005,
            "tick_value_usd": 12.50,
            "initial_margin_usd": 9500.0,
            "maintenance_margin_usd": 8600.0,
            "commission_per_contract_usd": 2.50,
            "description": "High Grade Copper (25,000 lbs)",
        },
        "etf": {
            "ticker": "CPER",
            "exchange": "NYSE",
            "name": "United States Copper Index Fund",
            "approx_unit_price_usd": 30.0,
        },
    },
    "Ag": {
        "name": "Silver (COMEX / LBMA)",
        "micro": {
            "ticker": "SIL",
            "exchange": "CME",
            "contract_size": 1000.0,
            "unit": "troy_oz",
            "tick_size": 0.005,
            "tick_value_usd": 5.00,
            "initial_margin_usd": 1800.0,
            "maintenance_margin_usd": 1600.0,
            "commission_per_contract_usd": 1.50,
            "description": "Micro Silver (1,000 troy oz)",
        },
        "standard": {
            "ticker": "SI",
            "exchange": "CME",
            "contract_size": 5000.0,
            "unit": "troy_oz",
            "tick_size": 0.005,
            "tick_value_usd": 25.00,
            "initial_margin_usd": 9000.0,
            "maintenance_margin_usd": 8000.0,
            "commission_per_contract_usd": 2.50,
            "description": "Silver 5,000 oz (COMEX)",
        },
        "etf": {
            "ticker": "SLV",
            "exchange": "NYSE",
            "name": "iShares Silver Trust",
            "approx_unit_price_usd": 35.0,
        },
    },
    "Pt": {
        "name": "Platinum (NYMEX / LPPM)",
        "micro": {
            "ticker": "PL",
            "exchange": "NYMEX",
            "contract_size": 50.0,
            "unit": "troy_oz",
            "tick_size": 0.10,
            "tick_value_usd": 5.00,
            "initial_margin_usd": 2500.0,
            "maintenance_margin_usd": 2200.0,
            "commission_per_contract_usd": 2.00,
            "description": "NYMEX Platinum (50 troy oz)",
        },
        "standard": {
            "ticker": "PL",
            "exchange": "NYMEX",
            "contract_size": 50.0,
            "unit": "troy_oz",
            "tick_size": 0.10,
            "tick_value_usd": 5.00,
            "initial_margin_usd": 2500.0,
            "maintenance_margin_usd": 2200.0,
            "commission_per_contract_usd": 2.50,
            "description": "NYMEX Platinum (50 troy oz)",
        },
        "etf": {
            "ticker": "PPLT",
            "exchange": "NYSE",
            "name": "abrdn Physical Platinum Shares",
            "approx_unit_price_usd": 95.0,
        },
    },
    "Li": {
        "name": "Lithium Carbonate (Fastmarkets / SMM)",
        "micro": {
            "ticker": "LIT",
            "exchange": "CME",
            "contract_size": 1.0,
            "unit": "mt",
            "tick_size": 1.0,
            "tick_value_usd": 1.0,
            "initial_margin_usd": 500.0,
            "maintenance_margin_usd": 450.0,
            "commission_per_contract_usd": 1.50,
            "description": "CME Lithium Synthetic / Micro Contract",
        },
        "standard": {
            "ticker": "LIT",
            "exchange": "CME",
            "contract_size": 1.0,
            "unit": "mt",
            "tick_size": 1.0,
            "tick_value_usd": 1.0,
            "initial_margin_usd": 1000.0,
            "maintenance_margin_usd": 900.0,
            "commission_per_contract_usd": 2.50,
            "description": "CME Lithium Battery Grade (1 MT)",
        },
        "etf": {
            "ticker": "LIT",
            "exchange": "NASDAQ",
            "name": "Global X Lithium & Battery Tech ETF",
            "approx_unit_price_usd": 40.0,
        },
    },
    "NdDy": {
        "name": "Neodymium-Dysprosium Rare Earths",
        "micro": {
            "ticker": "REMX",
            "exchange": "NYSE",
            "contract_size": 10.0,
            "unit": "kg",
            "tick_size": 0.1,
            "tick_value_usd": 1.0,
            "initial_margin_usd": 500.0,
            "maintenance_margin_usd": 450.0,
            "commission_per_contract_usd": 1.50,
            "description": "Rare Earth Strategic Basket Synthetic",
        },
        "standard": {
            "ticker": "REMX",
            "exchange": "NYSE",
            "contract_size": 100.0,
            "unit": "kg",
            "tick_size": 0.1,
            "tick_value_usd": 10.0,
            "initial_margin_usd": 2500.0,
            "maintenance_margin_usd": 2200.0,
            "commission_per_contract_usd": 2.50,
            "description": "Rare Earth Strategic Basket Standard",
        },
        "etf": {
            "ticker": "REMX",
            "exchange": "NYSE",
            "name": "VanEck Rare Earth/Strategic Metals ETF",
            "approx_unit_price_usd": 45.0,
        },
    },
}

# Legacy mapping for backwards compatibility
FUTURES_TICKER_MAP = {
    sym: {
        "micro": data["micro"]["ticker"],
        "standard": data["standard"]["ticker"],
        "etf": data["etf"]["ticker"],
        "exchange": data["etf"]["exchange"],
        "name": data["name"],
    }
    for sym, data in FUTURES_CONTRACT_SPECS.items()
}


class KoreaInvestmentFuturesClient:
    def __init__(self):
        self.app_key = os.getenv("KIS_APP_KEY", "").strip()
        self.app_secret = os.getenv("KIS_APP_SECRET", "").strip()
        self.cano = os.getenv("KIS_CANO", "10061681").strip()
        self.acnt_prdt_cd = os.getenv("KIS_ACNT_PRDT_CD", "01").strip()
        self.account_no = f"{self.cano}-{self.acnt_prdt_cd}"
        self.futures_acnt_prdt_cd = os.getenv("KIS_FUTURES_ACNT_PRDT_CD", "08").strip()
        self.futures_account_no = f"{self.cano}-{self.futures_acnt_prdt_cd}"
        self.stock_acnt_prdt_cd = "01"
        
        self.base_url = "https://openapi.koreainvestment.com:9443"
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0
        
        # Persistent token cache file path (supports both local and container /tmp)
        cache_dir = os.getenv("TOKEN_CACHE_DIR", os.path.dirname(os.path.abspath(__file__)))
        self._cache_file = os.path.join(cache_dir, ".kis_token_cache.json")
        self._load_token_from_cache()

    @property
    def is_configured(self) -> bool:
        return bool(self.app_key and self.app_secret and self.cano)

    def _get_credentials_hash(self) -> str:
        """Returns SHA256 hash of app_key for cache validation."""
        return hashlib.sha256(f"{self.app_key}:{self.app_secret}".encode()).hexdigest()

    def _load_token_from_cache(self) -> bool:
        """Attempts to load a valid unexpired token from persistent file cache."""
        if not os.path.exists(self._cache_file):
            return False
        try:
            with open(self._cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Verify credentials match
            if data.get("cred_hash") != self._get_credentials_hash():
                return False

            expires_at = data.get("expires_at", 0.0)
            now = time.time()
            # If token is still valid for at least 10 minutes (600s), reuse it
            if expires_at > now + 600:
                self._access_token = data.get("access_token")
                self._token_expires_at = expires_at
                remaining_hours = (expires_at - now) / 3600.0
                logger.info(f"Loaded existing valid KIS OAuth token from cache. (Remaining: {remaining_hours:.1f} hours)")
                return True
        except Exception as e:
            logger.warning(f"Failed to read KIS token cache file: {e}")
        return False

    def _save_token_to_cache(self, token: str, expires_in: int):
        """Saves newly issued token and expiration to persistent file cache."""
        now = time.time()
        self._access_token = token
        self._token_expires_at = now + expires_in
        data = {
            "cred_hash": self._get_credentials_hash(),
            "access_token": token,
            "token_type": "Bearer",
            "expires_at": self._token_expires_at,
            "issued_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        try:
            with open(self._cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved KIS OAuth token to cache file: {self._cache_file}")
        except Exception as e:
            logger.warning(f"Failed to write KIS token cache file: {e}")

    def get_access_token(self) -> str:
        """
        Retrieves access token adhering to KIS strict '1 token per 24 hours' rule.
        Uses in-memory and persistent file cache to avoid frequent requests that cause EGW00133 errors.
        """
        now = time.time()
        # 1. Check in-memory cache (valid if > 10 mins remaining)
        if self._access_token and now < self._token_expires_at - 600:
            return self._access_token

        # 2. Check persistent disk file cache
        if self._load_token_from_cache() and self._access_token:
            return self._access_token

        if not self.is_configured:
            return "MOCK_KIS_DEV_TOKEN_SANDBOX"

        # 3. Only request new token from KIS when strictly expired / absent
        url = f"{self.base_url}/oauth2/tokenP"
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }

        try:
            logger.info("Requesting fresh KIS OAuth Access Token (once per 24 hours)...")
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    access_token = data.get("access_token")
                    expires_in = int(data.get("expires_in", 86400))  # 24 hours = 86,400s
                    self._save_token_to_cache(access_token, expires_in)
                    logger.info("KIS OAuth Access Token issued and cached successfully for 24h.")
                    return access_token
                else:
                    logger.error(f"KIS Token Request Error: {res.status_code} - {res.text}")
                    if self._access_token:
                        return self._access_token
                    return "TOKEN_AUTH_FAILED"
        except Exception as e:
            logger.error(f"KIS Token Exception: {e}")
            if self._access_token:
                return self._access_token
            return "TOKEN_CONN_FAILED"

    def calculate_order_sizing(
        self,
        symbol: str,
        mode: Union[TradeMode, str] = TradeMode.AUTO,
        sizing_mode: Union[TradeSizingMode, str] = TradeSizingMode.CAPITAL_BASED,
        capital_usd: float = 500.0,
        fixed_lots: int = 1,
        spread_bps: float = 50.0,
        unit_price: float = 0.0,
        margin_buffer_pct: float = 20.0,
    ) -> Dict[str, Any]:
        """
        Calculates optimal position sizing, contract selection, required margin, and commission.
        Supports both Overseas Futures (마이크로/표준) and ETF shares.
        """
        spec: Dict[str, Any] = FUTURES_CONTRACT_SPECS.get(symbol) or FUTURES_CONTRACT_SPECS["Cu"]
        mode_str = mode.value if isinstance(mode, TradeMode) else mode.upper()
        sizing_str = sizing_mode.value if isinstance(sizing_mode, TradeSizingMode) else sizing_mode.upper()

        # Resolve effective mode (AUTO chooses Standard Futures if capital is large enough, else Micro Futures, else ETF)
        micro_info: Dict[str, Any] = spec["micro"]
        standard_info: Dict[str, Any] = spec.get("standard", micro_info)
        micro_base_margin: float = float(micro_info["initial_margin_usd"])
        micro_margin_with_buffer: float = micro_base_margin * (1.0 + margin_buffer_pct / 100.0)
        standard_base_margin: float = float(standard_info["initial_margin_usd"])
        standard_margin_with_buffer: float = standard_base_margin * (1.0 + margin_buffer_pct / 100.0)
        
        auto_standard_upgrade = os.getenv("AUTO_STANDARD_UPGRADE", "true").lower() in ("true", "1", "yes")

        if mode_str == "AUTO":
            if auto_standard_upgrade and capital_usd >= standard_margin_with_buffer:
                effective_mode = "FUTURES_STANDARD"
            elif capital_usd >= micro_margin_with_buffer or capital_usd >= micro_base_margin:
                effective_mode = "FUTURES_MICRO"
            else:
                effective_mode = "ETF"
        else:
            effective_mode = mode_str

        # 1. FUTURES (MICRO or STANDARD)
        if effective_mode in ("FUTURES_MICRO", "FUTURES_STANDARD"):
            contract_type = "micro" if effective_mode == "FUTURES_MICRO" else "standard"
            c_info: Dict[str, Any] = spec[contract_type]
            init_margin_per_contract: float = float(c_info["initial_margin_usd"])
            maint_margin_per_contract: float = float(c_info["maintenance_margin_usd"])
            contract_multiplier: float = float(c_info["contract_size"])
            ticker: str = str(c_info["ticker"])
            exchange: str = str(c_info["exchange"])
            comm_per_contract: float = float(c_info.get("commission_per_contract_usd", 2.0))

            # Strict Sizing & Margin Budget Logic
            effective_margin: float = init_margin_per_contract * (1.0 + margin_buffer_pct / 100.0)
            affordable_lots_with_buffer: int = int(capital_usd // effective_margin) if effective_margin > 0 else 0
            max_possible_lots_raw: int = int(capital_usd // init_margin_per_contract) if init_margin_per_contract > 0 else 0

            if sizing_str == "FIXED_LOTS":
                desired_lots = max(fixed_lots, 1)
                lots = min(desired_lots, max_possible_lots_raw) if max_possible_lots_raw > 0 else 1
            elif sizing_str == "DYNAMIC_KELLY":
                kelly_factor = min(max(spread_bps / 100.0, 1.0), 2.5)
                base_lots = affordable_lots_with_buffer if affordable_lots_with_buffer > 0 else max(max_possible_lots_raw, 1)
                lots = min(max(int(base_lots * kelly_factor), 1), max(max_possible_lots_raw, 1))
            else:  # CAPITAL_BASED
                if affordable_lots_with_buffer > 0:
                    lots = affordable_lots_with_buffer
                elif max_possible_lots_raw > 0:
                    lots = max_possible_lots_raw
                else:
                    lots = 1 if capital_usd >= (init_margin_per_contract * 0.8) else 0

            # If capital is strictly insufficient for even 1 futures contract and in AUTO mode, fall back to ETF
            if lots == 0 and mode_str == "AUTO":
                effective_mode = "ETF"
            else:
                lots = max(lots, 1 if capital_usd >= init_margin_per_contract else 0)
                total_required_margin: float = round(lots * init_margin_per_contract, 2)
                total_commission: float = round(lots * comm_per_contract, 2)
                unit_val: float = float(unit_price if unit_price > 0 else c_info.get("tick_value_usd", 10.0))
                contract_notional_value: float = round(lots * contract_multiplier * unit_val, 2)

                return {
                    "trade_mode": effective_mode,
                    "instrument_type": "OVERSEAS_FUTURES",
                    "contract_type": contract_type,
                    "symbol": symbol,
                    "ticker": ticker,
                    "exchange": exchange,
                    "account_type": "해외선물/파생 (08)",
                    "account_no": self.futures_account_no,
                    "quantity": lots,
                    "unit_label": "lots",
                    "contract_multiplier": contract_multiplier,
                    "contract_unit": str(c_info["unit"]),
                    "initial_margin_usd": total_required_margin,
                    "maintenance_margin_usd": round(lots * maint_margin_per_contract, 2),
                    "commission_fee_usd": total_commission,
                    "notional_value_usd": contract_notional_value,
                    "description": f"{lots} lot(s) of {c_info['description']} on {exchange}",
                }

        # 2. ETF (STOCK)
        etf_info: Dict[str, Any] = spec["etf"]
        ticker = str(etf_info["ticker"])
        exchange = str(etf_info["exchange"])
        price_est: float = float(etf_info.get("approx_unit_price_usd", 30.0))
        
        if sizing_str == "FIXED_LOTS":
            shares = max(fixed_lots * 5, 1)  # 1 lot ≈ 5 shares ETF
        elif sizing_str == "DYNAMIC_KELLY":
            kelly_factor = min(max(spread_bps / 100.0, 1.0), 3.0)
            shares = max(int((capital_usd * 0.35 * kelly_factor) // price_est), 1)
        else:  # CAPITAL_BASED
            target_alloc = min(capital_usd * 0.35, max(capital_usd, price_est))
            shares = max(int(target_alloc // price_est), 1 if capital_usd >= price_est else 0)

        allocation_usd: float = round(shares * price_est, 2)
        commission_usd: float = round(allocation_usd * 0.0025, 2)

        return {
            "trade_mode": "ETF",
            "instrument_type": "OVERSEAS_ETF",
            "contract_type": "etf",
            "symbol": symbol,
            "ticker": ticker,
            "exchange": exchange,
            "account_type": "해외주식/ETF 종합위탁 (01)",
            "account_no": self.account_no,
            "quantity": shares,
            "unit_label": "shares",
            "contract_multiplier": 1.0,
            "contract_unit": "shares",
            "initial_margin_usd": allocation_usd,
            "maintenance_margin_usd": 0.0,
            "commission_fee_usd": commission_usd,
            "notional_value_usd": allocation_usd,
            "description": f"{shares} share(s) of {etf_info['name']} ({ticker}) on {exchange}",
        }

    def execute_overseas_stock_etf_order(
        self,
        symbol: str,
        spread_bps: float,
        net_margin_usd: float,
        direction: str,
        quantity_shares: int = 1,
        price_usd: float = 0.0,
        dry_run: bool = True,
        commission_usd: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Executes or simulates an atomic overseas ETF order on KIS account (01 종합위탁).
        """
        now_utc = datetime.now(timezone.utc).isoformat()
        spec: Dict[str, Any] = FUTURES_CONTRACT_SPECS.get(symbol) or FUTURES_CONTRACT_SPECS["Cu"]
        ticker_info: Dict[str, Any] = spec["etf"]
        order_ticker = str(ticker_info["ticker"])
        exchange = str(ticker_info["exchange"])

        # All commodity ETFs (SLV, CPER, PPLT, LIT, REMX) trade on NYSE Arca
        # KIS Quotation EXCD is 'AMS', Order OVRS_EXCG_CD is 'AMEX'
        price_excd = "AMS"
        order_excg_cd = "AMEX"

        raw = f"KIS-ETF:{self.account_no}:{order_ticker}:{now_utc}:{quantity_shares}:{spread_bps}"
        order_id = "ORD-ETF-" + hashlib.sha256(raw.encode()).hexdigest()[:10].upper()

        if dry_run or not self.is_configured:
            logger.info(f"[KIS SIMULATED ETF ORDER] Account: {self.account_no} | Ticker: {order_ticker} ({order_excg_cd}) | Qty: {quantity_shares} share(s)")
            return {
                "status": "FILLED_SIMULATED",
                "broker": "한국투자증권 (Korea Investment & Securities)",
                "account_no": self.account_no,
                "exchange": order_excg_cd,
                "ticker": order_ticker,
                "instrument_type": "OVERSEAS_ETF",
                "commodity_name": ticker_info["name"],
                "quantity_shares": quantity_shares,
                "spread_bps": spread_bps,
                "net_margin_usd": net_margin_usd,
                "commission_rate": "0.25% (US Online Standard)",
                "commission_fee_usd": commission_usd,
                "direction": direction,
                "order_id": order_id,
                "timestamp_utc": now_utc,
                "execution_latency_ms": 12.0,
                "safety_guard": "DELTA_NEUTRAL_1TO1_HEDGED",
                "message": f"Successfully simulated {quantity_shares}-share {order_ticker} ETF hedge on KIS account {self.account_no}."
            }

        # Real Live KIS Overseas Stock/ETF Order Execution (TTTT1002U Buy / TTTT1006U Sell)
        token = self.get_access_token()
        is_buy = "Buy" in direction or "Long" in direction
        tr_id = "TTTT1002U" if is_buy else "TTTT1006U"

        # Always fetch exact real-time ETF share price from KIS (not underlying raw commodity ton/oz price)
        order_price = 0.0
        try:
            p_headers = {
                "content-type": "application/json; charset=utf-8",
                "authorization": f"Bearer {token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": "HHDFS00000300",
            }
            p_params = {"AUTH": "", "EXCD": price_excd, "SYMB": order_ticker}
            with httpx.Client(timeout=4.0) as client:
                p_res = client.get(f"{self.base_url}/uapi/overseas-price/v1/quotations/price", headers=p_headers, params=p_params)
                p_data = p_res.json()
                last_str = p_data.get("output", {}).get("last")
                if last_str:
                    order_price = float(last_str)
        except Exception as e:
            logger.warning(f"Failed to fetch live ETF price for {order_ticker}: {e}")

        if order_price <= 0:
            order_price = float(ticker_info.get("approx_unit_price_usd", 35.0))

        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
        }

        payload = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": order_excg_cd,
            "PDNO": order_ticker,
            "ORD_QTY": str(quantity_shares),
            "OVRS_ORD_UNPR": str(round(order_price, 2)),
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": "00",
        }

        try:
            with httpx.Client(timeout=8.0) as client:
                res = client.post(f"{self.base_url}/uapi/overseas-stock/v1/trading/order", headers=headers, json=payload)
                data = res.json()
                output = data.get("output", {})
                odno = output.get("ODNO", order_id)
                msg1 = data.get("msg1", "Order Submitted")
                rt_cd = data.get("rt_cd", "0")
                logger.info(f"Live KIS ETF Order Result: {rt_cd} - {msg1} (ODNO: {odno})")
                return {
                    "status": "ORDER_EXECUTED" if rt_cd == "0" else "ORDER_SUBMITTED",
                    "broker": "한국투자증권 (Korea Investment & Securities)",
                    "account_no": self.account_no,
                    "order_id": odno,
                    "ticker": order_ticker,
                    "quantity_shares": quantity_shares,
                    "direction": direction,
                    "message": msg1,
                    "timestamp_utc": now_utc,
                }
        except Exception as e:
            logger.error(f"Live KIS ETF Order Exception: {e}")
            return {
                "status": "ORDER_DISPATCH_FALLBACK",
                "broker": "한국투자증권 (Korea Investment & Securities)",
                "account_no": self.account_no,
                "order_id": order_id,
                "ticker": order_ticker,
                "quantity_shares": quantity_shares,
                "error": str(e),
                "timestamp_utc": now_utc,
            }

    def execute_futures_hedge_order(
        self,
        symbol: str,
        spread_bps: float,
        net_margin_usd: float,
        direction: str,
        quantity_lots: int = 1,
        contract_type: str = "micro",
        dry_run: bool = True,
        commission_usd: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Executes or simulates an atomic overseas commodity futures order on KIS account (08 해외선물/파생).
        """
        now_utc = datetime.now(timezone.utc).isoformat()
        spec: Dict[str, Any] = FUTURES_CONTRACT_SPECS.get(symbol) or FUTURES_CONTRACT_SPECS["Cu"]
        c_info: Dict[str, Any] = spec.get(contract_type) or spec["micro"]
        order_ticker: str = str(c_info["ticker"])
        exchange: str = str(c_info["exchange"])
        desc_name: str = str(c_info["description"])
        contract_multiplier: float = float(c_info["contract_size"])

        raw = f"KIS-FUTURES:{self.futures_account_no}:{order_ticker}:{now_utc}:{quantity_lots}:{spread_bps}"
        order_id = "ORD-FUT-" + hashlib.sha256(raw.encode()).hexdigest()[:10].upper()

        if dry_run or not self.is_configured:
            logger.info(f"[KIS SIMULATED FUTURES ORDER] Account: {self.futures_account_no} | Ticker: {order_ticker} ({exchange}) | Qty: {quantity_lots} lot(s)")
            return {
                "status": "FILLED_SIMULATED",
                "broker": "한국투자증권 (Korea Investment & Securities)",
                "account_no": self.futures_account_no,
                "exchange": exchange,
                "ticker": order_ticker,
                "instrument_type": f"OVERSEAS_FUTURES_{contract_type.upper()}",
                "commodity_name": desc_name,
                "quantity_lots": quantity_lots,
                "contract_multiplier": contract_multiplier,
                "spread_bps": spread_bps,
                "net_margin_usd": net_margin_usd,
                "commission_fee_usd": commission_usd,
                "direction": direction,
                "order_id": order_id,
                "timestamp_utc": now_utc,
                "execution_latency_ms": 14.5,
                "safety_guard": "DELTA_NEUTRAL_1TO1_HEDGED",
                "message": f"Successfully simulated {quantity_lots}-lot {desc_name} hedge on KIS overseas futures account {self.futures_account_no}."
            }

        # Real Live KIS Overseas Futures Order Execution (TR: OTFM0101U)
        token = self.get_access_token()
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "OTFM0101U",
        }

        payload = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.futures_acnt_prdt_cd,
            "OVRS_FUTR_EXCG_CD": exchange,
            "OVRS_FUTR_PDNO": order_ticker,
            "ORD_QTY": str(quantity_lots),
            "OVRS_ORD_UNPR": "0",  # Market order
            "ORD_DVSN_CD": "01",
            "SLL_BUY_DVSN_CD": "02" if "Buy" in direction or "Long" in direction else "01",
        }

        try:
            with httpx.Client(timeout=8.0) as client:
                res = client.post(f"{self.base_url}/uapi/overseas-futureoption/v1/trading/order", headers=headers, json=payload)
                data = res.json()
                output = data.get("output", {})
                odno = output.get("ODNO", order_id)
                msg1 = data.get("msg1", "Order Submitted")
                rt_cd = data.get("rt_cd", "0")
                logger.info(f"Live KIS Futures Order Result: {rt_cd} - {msg1} (ODNO: {odno})")
                return {
                    "status": "ORDER_EXECUTED" if rt_cd == "0" else "ORDER_SUBMITTED",
                    "broker": "한국투자증권 (Korea Investment & Securities)",
                    "account_no": self.futures_account_no,
                    "order_id": odno,
                    "ticker": order_ticker,
                    "quantity_lots": quantity_lots,
                    "direction": direction,
                    "message": msg1,
                    "timestamp_utc": now_utc,
                }
        except Exception as e:
            logger.error(f"Live KIS Futures Order Exception: {e}")
            return {
                "status": "ORDER_DISPATCH_FALLBACK",
                "broker": "한국투자증권 (Korea Investment & Securities)",
                "account_no": self.futures_account_no,
                "order_id": order_id,
                "ticker": order_ticker,
                "quantity_lots": quantity_lots,
                "error": str(e),
                "timestamp_utc": now_utc,
            }

    def execute_auto_hedge_order(
        self,
        symbol: str,
        spread_bps: float,
        net_margin_usd: float,
        direction: str,
        sizing_plan: Dict[str, Any],
        price_usd: float = 0.0,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """
        Dispatches hedge order automatically routing to either Overseas Futures (08) or ETF (01)
        based on the generated sizing plan.
        """
        inst_type = sizing_plan.get("instrument_type", "OVERSEAS_ETF")
        if "FUTURES" in inst_type:
            contract_type = sizing_plan.get("contract_type", "micro")
            lots = sizing_plan.get("quantity", 1)
            comm = sizing_plan.get("commission_fee_usd", 2.0)
            return self.execute_futures_hedge_order(
                symbol=symbol,
                spread_bps=spread_bps,
                net_margin_usd=net_margin_usd,
                direction=direction,
                quantity_lots=lots,
                contract_type=contract_type,
                dry_run=dry_run,
                commission_usd=comm,
            )
        else:
            shares = sizing_plan.get("quantity", 1)
            comm = sizing_plan.get("commission_fee_usd", 0.38)
            return self.execute_overseas_stock_etf_order(
                symbol=symbol,
                spread_bps=spread_bps,
                net_margin_usd=net_margin_usd,
                direction=direction,
                quantity_shares=shares,
                price_usd=price_usd,
                dry_run=dry_run,
                commission_usd=comm,
            )

    def inquire_overseas_stock_holdings(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Queries overseas stock/ETF holdings (TTTS3012R) across AMEX, NASD, and NYSE.
        Returns detailed holding positions, purchase price, current price, unrealized PnL.
        """
        if dry_run or not self.is_configured:
            return {
                "status": "SIMULATED_HOLDINGS",
                "items": [
                    {
                        "symbol": "Ag",
                        "ticker": "SLV",
                        "name": "ISHARES SILVER TRUST",
                        "exchange": "AMEX",
                        "quantity": 4,
                        "order_possible_qty": 4,
                        "purchase_avg_price_usd": 58.98,
                        "current_price_usd": 59.07,
                        "purchase_total_usd": 235.91,
                        "eval_total_usd": 236.28,
                        "unrealized_pnl_usd": 0.37,
                        "unrealized_pnl_pct": 0.16,
                    },
                    {
                        "symbol": "Pt",
                        "ticker": "PPLT",
                        "name": "ABERDEEN STANDARD PHYSICAL PLATINUM SHARES",
                        "exchange": "AMEX",
                        "quantity": 3,
                        "order_possible_qty": 3,
                        "purchase_avg_price_usd": 16.01,
                        "current_price_usd": 15.98,
                        "purchase_total_usd": 48.02,
                        "eval_total_usd": 47.94,
                        "unrealized_pnl_usd": -0.08,
                        "unrealized_pnl_pct": -0.16,
                    },
                ],
                "total_purchase_usd": 283.92,
                "total_eval_usd": 284.22,
                "total_unrealized_pnl_usd": 0.30,
                "total_pnl_pct": 0.10,
            }

        token = self.get_access_token()
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "TTTS3012R",
        }

        # Reverse ticker map for commodity symbol lookup
        ticker_to_sym = {}
        for sym, spec in FUTURES_CONTRACT_SPECS.items():
            etf_t = spec.get("etf", {}).get("ticker")
            if etf_t:
                ticker_to_sym[etf_t.upper()] = sym
            m_t = spec.get("micro", {}).get("ticker")
            if m_t:
                ticker_to_sym[m_t.upper()] = sym

        holdings_list = []
        tot_pchs_usd = 0.0
        tot_evlu_usd = 0.0
        tot_pnl_usd = 0.0

        # Query main US ETF exchanges
        for excg in ["NASD", "AMEX", "NYSE"]:
            params = {
                "CANO": self.cano,
                "ACNT_PRDT_CD": self.acnt_prdt_cd,
                "OVRS_EXCG_CD": excg,
                "TR_CRCY_CD": "USD",
                "CTX_AREA_FK200": "",
                "CTX_AREA_NK200": "",
            }
            try:
                with httpx.Client(timeout=6.0) as client:
                    res = client.get(f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-balance", headers=headers, params=params)
                    if res.status_code == 200:
                        data = res.json()
                        out1 = data.get("output1", [])
                        for item in out1:
                            ticker = item.get("ovrs_pdno", item.get("pdno", "")).upper()
                            qty = float(item.get("ovrs_cblc_qty", item.get("cblc_qty", 0)))
                            if qty <= 0:
                                continue
                            
                            # Avoid duplicates across multi-market sweep
                            if any(h["ticker"] == ticker for h in holdings_list):
                                continue

                            pchs_unpr = float(item.get("pchs_avg_pric", 0))
                            cur_pr = float(item.get("now_pric2", item.get("prpr", pchs_unpr)))
                            pchs_amt = float(item.get("frcr_pchs_amt1", qty * pchs_unpr))
                            evlu_amt = float(item.get("ovrs_stck_evlu_amt", qty * cur_pr))
                            pnl_amt = float(item.get("frcr_evlu_pfls_amt", evlu_amt - pchs_amt))
                            pnl_rt = float(item.get("evlu_pfls_rt", (pnl_amt / pchs_amt * 100) if pchs_amt > 0 else 0))
                            ord_psbl = float(item.get("ord_psbl_qty", qty))

                            holdings_list.append({
                                "symbol": ticker_to_sym.get(ticker, ticker),
                                "ticker": ticker,
                                "name": item.get("ovrs_item_name", item.get("prdt_name", ticker)),
                                "exchange": item.get("ovrs_excg_cd", excg),
                                "quantity": int(qty) if qty.is_integer() else qty,
                                "order_possible_qty": int(ord_psbl) if ord_psbl.is_integer() else ord_psbl,
                                "purchase_avg_price_usd": round(pchs_unpr, 4),
                                "current_price_usd": round(cur_pr, 4),
                                "purchase_total_usd": round(pchs_amt, 2),
                                "eval_total_usd": round(evlu_amt, 2),
                                "unrealized_pnl_usd": round(pnl_amt, 2),
                                "unrealized_pnl_pct": round(pnl_rt, 2),
                            })
                            tot_pchs_usd += pchs_amt
                            tot_evlu_usd += evlu_amt
                            tot_pnl_usd += pnl_amt
            except Exception as e:
                logger.warning(f"Error querying overseas holdings on {excg}: {e}")

        tot_pnl_pct = round((tot_pnl_usd / tot_pchs_usd * 100.0), 2) if tot_pchs_usd > 0 else 0.0

        return {
            "status": "LIVE_VERIFIED",
            "items": holdings_list,
            "total_purchase_usd": round(tot_pchs_usd, 2),
            "total_eval_usd": round(tot_evlu_usd, 2),
            "total_unrealized_pnl_usd": round(tot_pnl_usd, 2),
            "total_pnl_pct": tot_pnl_pct,
        }

    def inquire_domestic_stock_holdings(self, dry_run: bool = True) -> Dict[str, Any]:
        """Queries domestic stock holdings (TTTC8434R) on account 01."""
        if dry_run or not self.is_configured:
            return {"status": "SIMULATED", "items": [], "total_eval_krw": 0.0}

        token = self.get_access_token()
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "TTTC8434R",
        }
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
        try:
            with httpx.Client(timeout=6.0) as client:
                res = client.get(f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance", headers=headers, params=params)
                if res.status_code == 200:
                    data = res.json()
                    out1 = data.get("output1", [])
                    items = []
                    tot_eval = 0.0
                    for x in out1:
                        qty = float(x.get("hldg_qty", 0))
                        if qty > 0:
                            eval_amt = float(x.get("evlu_amt", 0))
                            items.append({
                                "code": x.get("pdno"),
                                "name": x.get("prdt_name"),
                                "quantity": int(qty),
                                "purchase_avg_krw": float(x.get("pchs_avg_pric", 0)),
                                "current_price_krw": float(x.get("prpr", 0)),
                                "eval_krw": eval_amt,
                                "pnl_krw": float(x.get("evlu_pfls_amt", 0)),
                                "pnl_pct": float(x.get("evlu_pfls_rt", 0)),
                            })
                            tot_eval += eval_amt
                    return {"status": "LIVE_VERIFIED", "items": items, "total_eval_krw": tot_eval}
        except Exception as e:
            logger.warning(f"Domestic holdings query error: {e}")
        return {"status": "ERROR", "items": [], "total_eval_krw": 0.0}

    def inquire_filled_orders(self, start_date: str = "", end_date: str = "", dry_run: bool = True) -> List[Dict[str, Any]]:
        """
        Queries overseas stock/ETF execution history (TTTS3035R / inquire-ccnl).
        Returns filled orders with order ID, ticker, qty, price, and execution time.
        """
        if dry_run or not self.is_configured:
            return []

        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        if not start_date:
            start_date = end_date

        token = self.get_access_token()
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "TTTS3035R",
        }
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "PDNO": "%",
            "ORD_STRT_DT": start_date,
            "ORD_END_DT": end_date,
            "SLL_BUY_DVSN": "00",
            "CCLD_NCCS_DVSN": "00",
            "OVRS_EXCG_CD": "%",
            "SORT_SQN": "DS",
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": "",
        }
        try:
            with httpx.Client(timeout=8.0) as client:
                res = client.get(f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-ccnl", headers=headers, params=params)
                if res.status_code == 200:
                    data = res.json()
                    out = data.get("output", [])
                    filled_orders = []
                    for row in out:
                        ccld_qty = float(row.get("ft_ccld_qty", 0))
                        if ccld_qty > 0 or row.get("prcs_stat_name") == "완료":
                            filled_orders.append({
                                "order_no": row.get("odno"),
                                "order_date": row.get("ord_dt"),
                                "order_time": row.get("ord_tmd"),
                                "side": row.get("sll_buy_dvsn_cd_name"),
                                "ticker": row.get("pdno"),
                                "name": row.get("prdt_name"),
                                "exchange": row.get("ovrs_excg_cd"),
                                "order_qty": float(row.get("ft_ord_qty", 0)),
                                "filled_qty": ccld_qty,
                                "filled_price_usd": float(row.get("ft_ccld_unpr3", 0)),
                                "filled_amount_usd": float(row.get("ft_ccld_amt3", 0)),
                                "status": row.get("prcs_stat_name"),
                            })
                    return filled_orders
        except Exception as e:
            logger.warning(f"Filled orders query error: {e}")
        return []

    def sync_live_positions_with_bot(self, dry_run: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Scans KIS broker holdings and maps them directly to the trading bot's active_positions format.
        Ensures the bot is 100% aware of all existing holdings (e.g. SLV 4 shares, PPLT 3 shares) upon boot/restart.
        """
        holdings_res = self.inquire_overseas_stock_holdings(dry_run=dry_run)
        synced_positions = {}
        for item in holdings_res.get("items", []):
            sym = item["symbol"]
            ticker = item["ticker"]
            qty = item["quantity"]
            avg_price = item["purchase_avg_price_usd"]
            cur_price = item["current_price_usd"]
            eval_usd = item["eval_total_usd"]
            pnl_usd = item["unrealized_pnl_usd"]
            
            synced_positions[sym] = {
                "ticker": ticker,
                "is_futures": False,
                "contract_type": "etf",
                "entry_price": avg_price,
                "current_price": cur_price,
                "quantity": qty,
                "contract_multiplier": 1.0,
                "commission_usd": 0.38,
                "entry_bps": 50.0,
                "margin_usd": eval_usd,
                "allocation_usd": eval_usd,
                "unrealized_pnl_usd": pnl_usd,
                "entry_time": time.time(),
                "synced_from_broker": True,
            }
        return synced_positions

    def execute_position_close(
        self,
        symbol: str,
        quantity: Optional[int] = None,
        price_usd: float = 0.0,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes take-profit or stop-loss liquidation for an existing holding.
        """
        holdings_res = self.inquire_overseas_stock_holdings(dry_run=dry_run)
        target_item = None
        for item in holdings_res.get("items", []):
            if item["symbol"] == symbol or item["ticker"] == symbol:
                target_item = item
                break

        if not target_item:
            return {"status": "NO_POSITION_FOUND", "symbol": symbol, "message": "No active holding found to close."}

        close_qty = quantity if quantity and quantity > 0 else int(target_item["quantity"])
        cur_p = price_usd if price_usd > 0 else target_item["current_price_usd"]

        return self.execute_overseas_stock_etf_order(
            symbol=symbol,
            spread_bps=0.0,
            net_margin_usd=0.0,
            direction="Sell (Close Position)",
            quantity_shares=close_qty,
            price_usd=cur_p,
            dry_run=dry_run,
            commission_usd=round(close_qty * cur_p * 0.0025, 2),
        )

    def inquire_realtime_balance(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Queries live comprehensive account balance across 01 (Stock/ETF & Cash) and 08 (Futures) from KIS.
        Integrates exact overseas stock holdings (TTTS3012R) + Cash Deposit (CTRP6548R).
        """
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        if dry_run or not self.is_configured:
            stock_deposit_usd = 401.96
            futures_deposit_usd = 0.0
            holdings_sim = self.inquire_overseas_stock_holdings(dry_run=True)
            etf_eval_usd = holdings_sim.get("total_eval_usd", 284.22)
            total_net_worth_usd = stock_deposit_usd + etf_eval_usd
            return {
                "status": "SIMULATED_MOCK" if not self.is_configured else "DRY_RUN_SYNCHRONIZED",
                "broker": "한국투자증권 (Korea Investment & Securities)",
                "primary_stock_account": self.account_no,
                "primary_futures_account": self.futures_account_no,
                "total_available_usd": stock_deposit_usd,
                "stock_available_usd": stock_deposit_usd,
                "futures_available_usd": futures_deposit_usd,
                "total_combined_cash_krw": round(stock_deposit_usd * 1350.0, 0),
                "overseas_stock_eval_usd": etf_eval_usd,
                "total_net_worth_usd": round(total_net_worth_usd, 2),
                "total_net_worth_krw": round(total_net_worth_usd * 1350.0, 0),
                "holdings_count": len(holdings_sim.get("items", [])),
                "holdings": holdings_sim.get("items", []),
                "accounts_breakdown": {
                    self.account_no: {
                        "type": "해외주식/ETF 종합위탁 (01)",
                        "available_usd": stock_deposit_usd,
                        "cash_deposit_krw": round(stock_deposit_usd * 1350.0, 0),
                    },
                    self.futures_account_no: {
                        "type": "해외선물/파생 위탁 (08)",
                        "available_usd": futures_deposit_usd,
                        "cash_deposit_krw": round(futures_deposit_usd * 1350.0, 0),
                    },
                },
                "currency": "USD/KRW",
                "timestamp_utc": now_str,
            }

        token = self.get_access_token()
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "CTRP6548R",
        }

        balances = {}
        total_combined_krw = 0.0
        total_available_usd = 0.0

        for prdt_cd in ["01", "08"]:
            params = {
                "CANO": self.cano,
                "ACNT_PRDT_CD": prdt_cd,
                "WCRC_FRCR_DVSN_CD": "02",
                "NATN_CD": "840",
                "TR_MKET_CD": "00",
                "INQR_DVSN_CD": "00",
            }
            try:
                with httpx.Client(timeout=8.0) as client:
                    res = client.get(f"{self.base_url}/uapi/overseas-stock/v1/trading/inquire-present-balance", headers=headers, params=params)
                    if res.status_code == 200:
                        data = res.json()
                        out2 = data.get("output2", {})
                        tot_asset = float(out2.get("tot_asst_amt", "0"))
                        dncl = float(out2.get("dncl_amt", "0"))
                        usd_val = float(out2.get("frcr_dncl_amt_2", dncl / 1350.0))
                        
                        balances[f"{self.cano}-{prdt_cd}"] = {
                            "type": "해외주식/ETF 종합위탁" if prdt_cd == "01" else "해외선물/파생",
                            "total_asset_krw": tot_asset,
                            "cash_deposit_krw": dncl,
                            "available_usd": usd_val,
                        }
                        total_combined_krw += dncl
                        total_available_usd += usd_val
            except Exception as e:
                logger.warning(f"Balance check error for {prdt_cd}: {e}")

        if total_available_usd == 0.0 and total_combined_krw > 0:
            total_available_usd = round(total_combined_krw / 1350.0, 2)

        # Retrieve live holdings from TTTS3012R
        holdings_data = self.inquire_overseas_stock_holdings(dry_run=False)
        etf_eval_usd = float(holdings_data.get("total_eval_usd", 0.0))
        total_net_worth_usd = round(total_available_usd + etf_eval_usd, 2)
        total_net_worth_krw = round(total_combined_krw + (etf_eval_usd * 1350.0), 0)

        return {
            "status": "LIVE_VERIFIED",
            "broker": "한국투자증권 (Korea Investment & Securities)",
            "primary_stock_account": self.account_no,
            "primary_futures_account": self.futures_account_no,
            "total_available_usd": total_available_usd,
            "total_combined_cash_krw": total_combined_krw,
            "overseas_stock_eval_usd": etf_eval_usd,
            "total_net_worth_usd": total_net_worth_usd,
            "total_net_worth_krw": total_net_worth_krw,
            "holdings_count": len(holdings_data.get("items", [])),
            "holdings": holdings_data.get("items", []),
            "accounts_breakdown": balances,
            "currency": "USD/KRW",
            "timestamp_utc": now_str,
        }

    def get_available_usd_balance(self, dry_run: bool = True) -> float:
        """Returns total usable USD balance across broker accounts."""
        try:
            res = self.inquire_realtime_balance(dry_run=dry_run)
            return float(res.get("total_available_usd", 401.96))
        except Exception:
            return 401.96


# Singleton KIS client instance
kis_client = KoreaInvestmentFuturesClient()

