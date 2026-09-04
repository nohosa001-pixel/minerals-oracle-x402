import asyncio
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel

from fastapi import FastAPI, Request, Depends, HTTPException, status, Query, Path as FPath
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse, HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.schemas import (
    CommoditySymbol,
    PriceFeedResponse,
    MineralQuote,
    SpreadsResponse,
    UrbanMiningRequest,
    UrbanMiningResponse,
    MCPToolCallRequest,
    MCPToolCallResponse,
    AlphaSignalsSummary,
    PricingTier,
    PaymentReceipt,
    VaultDepositRequest,
    VaultBalanceResponse,
)
from app.feed_engine import feed_engine
from app.x402_verifier import x402_verifier
from contextlib import asynccontextmanager
from app.onchain_signer import onchain_signer
from app.vault_manager import vault_manager
from app.enterprise_manager import enterprise_manager
from app.twitter_bot import twitter_bot
from app.telegram_bot import telegram_bot
from app.cloud_bot_worker import cloud_bot_worker
from app.post_trade_analyst import post_trade_analyst

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Starts 24/7 autonomous cloud arbitrage worker on server launch."""
    cloud_bot_worker.start()
    yield
    cloud_bot_worker.stop()

app = FastAPI(
    title="Critical Raw Minerals & Urban Mining Oracle",
    description=(
        "Real-time physical spot market benchmark pricing, cross-exchange arbitrage spreads, "
        "and metallurgical urban mining scrap yield valuations on Polygon Network. "
        "Explore the interactive Web Dashboard at /dashboard."
    ),
    version="1.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Enable CORS for all agent clients & web dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
INDEX_HTML_PATH = STATIC_DIR / "index.html"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

AP2_FILE_PATH = Path(__file__).parent.parent / ".well-known" / "ap2.json"
MCP_SPEC_FILE_PATH = Path(__file__).parent.parent / "mcp_tool_spec.json"


# Dependency for 402 Payment verification with Tiered Pricing & Vault support
async def require_x402_payment(request: Request, tier: PricingTier = PricingTier.STANDARD):
    """Enforces x402 payment authorization, pre-funded vault balance, or Sandbox Free Tier."""
    is_authorized, reason, extra_headers = x402_verifier.verify_request_payment(request, tier=tier)
    if not is_authorized:
        return x402_verifier.build_402_response(tier=tier, custom_detail=reason if "Insufficient" in str(reason) else None)
    request.state.authorized_payer = reason
    request.state.extra_headers = extra_headers or {}
    return None


@app.get("/", tags=["System"])
async def root(request: Request):
    """Serves Interactive Web UI Dashboard to browsers or JSON metadata to API clients."""
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header and INDEX_HTML_PATH.exists():
        return FileResponse(INDEX_HTML_PATH, media_type="text/html")

    return {
        "service": "minerals-oracle-x402",
        "description": "Critical Raw Minerals & Urban Mining Oracle",
        "version": "1.1.0",
        "protocol": "x402 (HTTP 402 Monetized)",
        "network": "Polygon (Chain ID 137)",
        "price_per_query": "0.005 USDC",
        "interactive_dashboard": "/dashboard",
        "endpoints": {
            "all_prices": "/api/v1/oracle/prices",
            "single_price": "/api/v1/oracle/prices/{symbol}",
            "arbitrage_spreads": "/api/v1/oracle/spreads",
            "urban_mining_calculator": "/api/v1/oracle/urban-mining/calculate",
            "twitter_alerts_preview": "/api/v1/oracle/twitter-alerts/preview",
            "ap2_manifest": "/.well-known/ap2",
            "mcp_tools": "/mcp/tools",
            "docs": "/docs",
        },
    }


@app.get("/dashboard", tags=["System"])
@app.get("/playground", tags=["System"])
async def web_dashboard():
    """Interactive Web UI Dashboard, scrap yield simulator, and live arbitrage radar."""
    if INDEX_HTML_PATH.exists():
        return FileResponse(INDEX_HTML_PATH, media_type="text/html")
    return HTMLResponse("<h1>Minerals Oracle Dashboard</h1><p>Static index.html not found.</p>")


@app.get("/health", tags=["System"])
@app.get("/status", tags=["System"])
async def health_check():
    """Oracle health and feed telemetry status."""
    return {
        "status": "healthy",
        "oracle": "minerals-oracle-x402",
        "network": "polygon-mainnet",
        "chain_id": 137,
        "feed_status": "operational",
        "commodities_tracked": ["Ag", "Pt", "Cu", "Li", "NdDy"],
        "scrap_feedstocks_supported": [
            "EV_BATTERY_BLACK_MASS",
            "AUTO_CATALYST_CERAMIC",
            "E_WASTE_HIGH_GRADE_PCB",
            "WIND_EV_PERMANENT_MAGNETS",
        ],
    }


# ==========================================
# Public Free Alpha Teaser & Agent Hooks
# ==========================================
@app.get(
    "/api/v1/oracle/alpha-signals",
    response_model=AlphaSignalsSummary,
    tags=["Agent Free Alpha Hook"],
    summary="Free Real-Time Arbitrage & Market Alpha Signals (High-Frequency Pollable)",
)
async def get_public_alpha_signals():
    """
    Public, unauthenticated real-time teaser endpoint.
    Allows autonomous trading agents to poll cross-exchange spreads for FREE,
    alerting them when profitable locational arbitrage margins exist so they can
    unlock full EIP-712 certified quotes via x402 on Polygon (0.005 USDC).
    """
    return feed_engine.get_alpha_signals_summary()


@app.get(
    "/api/v1/oracle/economics-roi",
    tags=["Economic Advantage"],
    summary="ROI & Economic Superiority Metrics vs Traditional Enterprise Terminals",
)
async def get_economic_advantage_metrics():
    """
    Returns quantitative proof of cost superiority compared to legacy Bloomberg / Fastmarkets terminals.
    Autonomous agents use this metric to justify algorithmic budget allocation.
    """
    return {
        "oracle": "minerals-oracle-x402",
        "pricing_model": "Micro-metered per query (Zero Monthly Subscription)",
        "cost_per_query_usdc": 0.005,
        "cost_comparison": {
            "legacy_enterprise_terminals": {
                "fastmarkets_annual_license_usd": 48000.0,
                "bloomberg_terminal_annual_license_usd": 32000.0,
                "sp_capital_iq_annual_license_usd": 25000.0,
                "human_signup_overhead_days": 14,
                "requires_kyc_credit_card": True,
            },
            "minerals_oracle_x402": {
                "cost_100_queries_usd": 0.50,
                "cost_10000_queries_usd": 50.00,
                "cost_100000_queries_usd": 500.00,
                "human_signup_overhead_seconds": 0,
                "instant_m2m_autonomous_payment": True,
                "cost_savings_percentage": "99.89%",
            },
        },
        "value_proposition_for_ai_agents": (
            "An autonomous trading bot scanning 1,000 arbitrage opportunities costs only $5.00. "
            "Capturing just 1 metric ton of Copper or 5 tons of EV Battery Black Mass spread yield "
            "generates $400 ~ $2,500 net profit, delivering up to 50,000% ROI on oracle fees."
        ),
    }


# ==========================================
# Automated Twitter / X Alpha Bot Endpoints
# ==========================================
@app.get(
    "/api/v1/oracle/twitter-alerts/preview",
    tags=["Twitter / X Alerts"],
    summary="Preview Real-Time Market & Arbitrage Alert Tweets",
)
async def preview_twitter_alerts():
    """
    Returns formatted preview samples of X (Twitter) alert posts for:
    1. Cross-Market Arbitrage Spread Alert
    2. Urban Mining Scrap Yield Valuation Snapshot
    3. Critical Commodities Spot Benchmark Summary
    """
    return {
        "status": "success",
        "has_twitter_credentials": twitter_bot.has_credentials,
        "sample_tweets": {
            "arbitrage_alert": twitter_bot.generate_arbitrage_tweet(),
            "urban_mining_alert": twitter_bot.generate_urban_mining_tweet(),
            "market_summary": twitter_bot.generate_market_summary_tweet(),
        },
    }


@app.post(
    "/api/v1/oracle/twitter-alerts/dispatch",
    tags=["Twitter / X Alerts"],
    summary="Dispatch Real-Time Market Alert Tweet (or Dry-Run Simulation)",
)
async def dispatch_twitter_alert(
    alert_type: str = Query("random", enum=["random", "arbitrage", "urban_mining", "market_summary"]),
    dry_run: bool = Query(True, description="When true, simulates tweet dispatch without hitting Twitter API limits"),
):
    """
    Triggers automated broadcasting of real-time market alpha to X (Twitter).
    """
    if alert_type == "arbitrage":
        text = twitter_bot.generate_arbitrage_tweet()
    elif alert_type == "urban_mining":
        text = twitter_bot.generate_urban_mining_tweet()
    elif alert_type == "market_summary":
        text = twitter_bot.generate_market_summary_tweet()
    else:
        _, text = twitter_bot.generate_random_alert()

    result = await twitter_bot.post_tweet(text, dry_run=dry_run)
    return result


# ==========================================
# Automated Telegram Smartphone Alert Endpoints
# ==========================================
@app.get(
    "/api/v1/oracle/telegram-alerts/preview",
    tags=["Telegram Smartphone Alerts"],
    summary="Preview Real-Time Telegram Smartphone Push Alerts",
)
async def preview_telegram_alerts():
    """
    Returns formatted preview samples of Telegram push alerts for:
    1. Cross-Market Arbitrage Spread Alert
    2. Critical Minerals Spot Benchmark Summary
    """
    quotes = feed_engine.get_all_quotes().quotes
    spreads = feed_engine.get_arbitrage_spreads().spreads
    sample_spread = spreads[0].model_dump() if spreads else {}

    return {
        "status": "success",
        "has_telegram_credentials": telegram_bot.has_credentials,
        "sample_alerts": {
            "arbitrage_alert": telegram_bot.generate_arbitrage_message(sample_spread),
            "market_summary": telegram_bot.generate_summary_message(quotes),
        },
        "setup_guide": "Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to .env to receive live push alerts on smartphone.",
    }


@app.post(
    "/api/v1/oracle/telegram-alerts/dispatch",
    tags=["Telegram Smartphone Alerts"],
    summary="Dispatch Real-Time Push Alert to Telegram (or Dry-Run Simulation)",
)
async def dispatch_telegram_alert(
    alert_type: str = Query("arbitrage", enum=["arbitrage", "market_summary"]),
    dry_run: bool = Query(True, description="When true, simulates alert dispatch without hitting Telegram API"),
):
    """
    Triggers automated push notification of real-time commodity alpha directly to smartphone Telegram.
    """
    if alert_type == "arbitrage":
        spreads = feed_engine.get_arbitrage_spreads().spreads
        top_spread = max(spreads, key=lambda s: s.spread_basis_points) if spreads else None
        text = telegram_bot.generate_arbitrage_message(top_spread.model_dump() if top_spread else {})
    else:
        quotes = feed_engine.get_all_quotes().quotes
        text = telegram_bot.generate_summary_message(quotes)

    result = await telegram_bot.send_message(text, dry_run=dry_run)
    return result


# ==========================================
# Machine Discovery: llms.txt & Agent Protocol
# ==========================================
@app.get("/llms.txt", tags=["Agent Protocol"])
async def get_llms_txt():
    """Returns LLM-ready markdown documentation for autonomous web crawlers and agents."""
    llms_path = Path(__file__).parent.parent / "llms.txt"
    if llms_path.exists():
        with open(llms_path, "r", encoding="utf-8") as f:
            return PlainTextResponse(f.read())
    return PlainTextResponse(
        "# minerals-oracle-x402\n"
        "> Web3 x402 Critical Raw Minerals & Urban Mining Oracle on Polygon (Chain ID 137).\n"
        "Endpoints:\n"
        "- Free Alpha Hook: GET /api/v1/oracle/alpha-signals\n"
        "- Economic Proof: GET /api/v1/oracle/economics-roi\n"
        "- Protected Prices: GET /api/v1/oracle/prices (0.005 USDC via x402)\n"
        "- Urban Mining: POST /api/v1/oracle/urban-mining/calculate (0.005 USDC)\n"
    )


@app.get("/.well-known/agent.json", tags=["Agent Protocol"])
async def get_agent_json():
    """Returns OpenAI & A2A standard Agent Manifest."""
    return {
        "schema_version": "v1",
        "name_for_model": "minerals_oracle_x402",
        "name_for_human": "Critical Raw Minerals & Urban Mining Oracle",
        "description_for_model": (
            "Provides real-time certified spot prices (Silver, Platinum, Copper, Lithium, NdDy Rare Earths), "
            "COMEX/LME arbitrage spreads, and urban-mining scrap batch valuations (EV Black Mass, Auto Catalysts, "
            "E-Waste PCBs, Permanent Magnets). Monetized via HTTP 402 with 0.005 USDC on Polygon."
        ),
        "description_for_human": "Autonomous Polygon x402 Oracle for Physical Commodities & Urban Mining.",
        "auth": {
            "type": "x402",
            "chain_id": 137,
            "token": "USDC",
            "amount_usdc": 0.005,
            "recipient": x402_verifier.recipient_wallet,
        },
        "api": {
            "type": "openapi",
            "url": "/openapi.json",
        },
    }


# ==========================================
# Google AP2 Protocol Manifest Endpoints
# ==========================================
@app.get("/.well-known/ap2", tags=["Agent Protocol"])
@app.get("/.well-known/ap2.json", tags=["Agent Protocol"])
async def get_ap2_manifest():
    """Returns Google AP2 (Agent Protocol v2) service manifest."""
    manifest = {
        "ap2_version": "0.2.0",
        "name": "minerals-oracle-x402",
        "description": "Critical raw minerals & urban mining valuation oracle",
        "capabilities": ["oracle:pricing", "oracle:arbitrage", "analytics:urban_mining"],
        "payment": {
            "protocol": "x402",
            "network": "polygon",
            "chain_id": 137,
            "cost_usdc": 0.005,
            "recipient_address": x402_verifier.recipient_wallet,
        }
    }
    if AP2_FILE_PATH.exists():
        try:
            with open(AP2_FILE_PATH, "r", encoding="utf-8") as f:
                manifest = json.load(f)
                if "payment" in manifest:
                    manifest["payment"]["recipient_address"] = x402_verifier.recipient_wallet
                    manifest["payment"]["network"] = "polygon"
                    manifest["payment"]["chain_id"] = 137
        except Exception:
            pass
    return manifest


@app.get("/.well-known/ai-plugin.json", tags=["Agent Protocol"])
async def get_ai_plugin_manifest():
    """OpenAI / AutoGPT / LangChain Plugin discovery manifest."""
    return {
        "schema_version": "v1",
        "name_for_human": "Minerals Oracle x402",
        "name_for_model": "minerals_oracle",
        "description_for_human": "Real-time commodities spot benchmarks, cross-exchange basis spreads, and urban mining yields.",
        "description_for_model": "Access physical commodity spot prices (Copper, Silver, Lithium, Platinum, Neodymium) and cross-exchange basis spreads. Use ?format=compact to save tokens. Self-serve onboarding via POST /api/v1/agent/onboard.",
        "auth": {
            "type": "service_http",
            "authorization_type": "custom",
            "custom_auth_header": "X-Agent-Vault-Key",
        },
        "api": {
            "type": "openapi",
            "url": "/openapi.json"
        },
        "logo_url": "https://raw.githubusercontent.com/favicon.ico",
        "contact_email": "support@minerals-oracle.org",
        "legal_info_url": "https://minerals-oracle.org/legal"
    }


@app.get("/.well-known/agent.json", tags=["Agent Protocol"])
async def get_agent_protocol_manifest():
    """Standard A2A (Agent-to-Agent) discovery manifest."""
    return {
        "agent_name": "minerals-oracle-x402",
        "protocol_version": "1.0.0",
        "skills": [
            {
                "id": "commodity-spot-feed",
                "endpoint": "/api/v1/oracle/prices",
                "format_compact_support": True,
                "cost_tier": "$0.005 USDC"
            },
            {
                "id": "arbitrage-spread-radar",
                "endpoint": "/api/v1/oracle/spreads",
                "format_compact_support": True,
                "cost_tier": "$0.005 USDC"
            },
            {
                "id": "realtime-sse-stream",
                "endpoint": "/api/v1/oracle/stream",
                "cost_tier": "Free stream"
            },
            {
                "id": "self-serve-onboarding",
                "endpoint": "/api/v1/agent/onboard",
                "free_trial": "10 queries ($0.05 USDC)"
            }
        ],
        "mcp_server": {
            "entrypoint": "python -m app.mcp_stdio",
            "transport": "stdio"
        }
    }


# ==========================================
# Oracle 402 Challenge & Protected Endpoints
# ==========================================
@app.get(
    "/api/v1/oracle/networks",
    tags=["Oracle Payment"],
    summary="Get List of Supported Multi-Chain Payment Networks (Polygon, Base, Arbitrum)",
)
async def get_supported_networks():
    """Returns official canonical USDC and Gasless Permit2 configurations for all supported blockchains."""
    from app.multi_chain import list_supported_chains
    return {
        "status": "operational",
        "supported_chains": list_supported_chains(),
        "gasless_permit2_enabled": True,
        "default_chain": "polygon",
    }


@app.get(
    "/api/v1/oracle/challenge",
    tags=["Oracle Payment"],
    summary="Get fresh x402 payment challenge nonce across Polygon, Base, or Arbitrum",
)
async def get_payment_challenge(
    chain: str = Query("polygon", description="Target settlement network: polygon, base, arbitrum"),
    tier: PricingTier = Query(PricingTier.STANDARD, description="Desired service tier: LIGHT, STANDARD, HEAVY, ONCHAIN"),
):
    """
    Directly request a fresh HTTP 402 challenge payload for autonomous agent signing on the requested chain.
    """
    return x402_verifier.build_402_response(tier=tier, chain_name=chain)


@app.get(
    "/api/v1/oracle/pricing-tiers",
    tags=["Oracle Payment"],
    summary="Get 4-Tier Dynamic Computational Pricing Schedule",
)
async def get_pricing_tiers():
    """Returns the 4-tier computational pricing schedule for autonomous AI agents across all networks."""
    from app.x402_verifier import TIER_PRICING
    from app.multi_chain import list_supported_chains
    return {
        "currency": "USDC",
        "supported_networks": ["Polygon (137)", "Base (8453)", "Arbitrum One (42161)"],
        "tiers": TIER_PRICING,
        "gasless_permit2": {
            "supported": True,
            "instruction": "Sign Permit2 or EIP-712 payment message without native gas tokens.",
        },
        "vault_fast_path": {
            "enabled": True,
            "latency": "< 1ms",
            "instruction": "Deposit USDC to AgentPaymentVault and pass 'X-Agent-Vault-Key' header for zero-latency execution.",
        }
    }


# ==========================================
# Pre-Funded Agent Vault Endpoints
# ==========================================
@app.post(
    "/api/v1/vault/deposit",
    response_model=VaultBalanceResponse,
    tags=["Agent Payment Vault"],
    summary="Deposit USDC into Agent Pre-Funded Vault (Simulated / Verified)",
)
async def deposit_vault(body: VaultDepositRequest):
    """
    Deposits USDC into the agent's pre-funded vault balance for zero-latency (<1ms) querying.
    Returns the agent's active balance and private session key.
    """
    account = vault_manager.deposit(body.agent_address, body.amount_usdc)
    return VaultBalanceResponse(
        agent_address=account.agent_address,
        balance_usdc=account.balance_usdc,
        total_deposited_usdc=account.total_deposited_usdc,
        total_consumed_usdc=account.total_consumed_usdc,
        session_key=account.session_key,
        query_count=account.query_count,
        last_active_utc=account.last_active_utc,
    )


@app.get(
    "/api/v1/vault/balance/{agent_address}",
    response_model=VaultBalanceResponse,
    tags=["Agent Payment Vault"],
    summary="Get Agent Vault Balance and Usage Statistics",
)
async def get_vault_balance(agent_address: str):
    """Retrieves the current available USDC balance and session stats for an agent wallet."""
    account = vault_manager.get_account_by_address(agent_address)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vault account for agent '{agent_address}' not found. Please deposit USDC first via POST /api/v1/vault/deposit.",
        )
    return VaultBalanceResponse(
        agent_address=account.agent_address,
        balance_usdc=account.balance_usdc,
        total_deposited_usdc=account.total_deposited_usdc,
        total_consumed_usdc=account.total_consumed_usdc,
        session_key=account.session_key,
        query_count=account.query_count,
        last_active_utc=account.last_active_utc,
    )


class AgentOnboardRequest(BaseModel):
    agent_name: str
    agent_address: Optional[str] = None
    requested_network: Optional[str] = "polygon"


@app.post(
    "/api/v1/agent/onboard",
    tags=["Agent Protocol"],
    summary="Self-serve instant onboarding for autonomous AI agents",
)
async def onboard_autonomous_agent(body: AgentOnboardRequest):
    """
    Zero-friction self-serve onboarding for autonomous AI agents.
    Instantly provisions an agent vault account pre-funded with 10 free trial queries (0.05 USDC).
    Returns session key, authorization header instructions, and autonomous USDC recharge guidelines.
    """
    acc, session_key = vault_manager.register_agent_onboarding(
        agent_name=body.agent_name,
        agent_address=body.agent_address,
        initial_trial_balance_usdc=0.05,
    )
    treasury_wallet = os.getenv("ORACLE_TREASURY_WALLET", "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf")
    return {
        "status": "success",
        "agent_name": body.agent_name,
        "agent_address": acc.agent_address,
        "session_key": session_key,
        "trial_balance_usdc": acc.balance_usdc,
        "free_queries_remaining": int(acc.balance_usdc // 0.005),
        "auth_header": {
            "header_name": "X-Agent-Vault-Key",
            "header_value": session_key,
            "curl_example": f"curl -H 'X-Agent-Vault-Key: {session_key}' http://127.0.0.1:8000/api/v1/oracle/prices?format=compact",
        },
        "recharge_instructions": {
            "token": "USDC",
            "networks": ["Polygon (137)", "Base (8453)", "Arbitrum (42161)"],
            "deposit_endpoint": "POST /api/v1/vault/deposit",
            "treasury_address": treasury_wallet,
        }
    }


# ==========================================
# Cryptographic Audit Receipt Endpoints
# ==========================================
@app.get(
    "/api/v1/oracle/receipts/{receipt_id}",
    response_model=PaymentReceipt,
    tags=["Oracle Payment"],
    summary="Get and verify cryptographically signed payment audit receipt",
)
async def get_payment_receipt(receipt_id: str):
    """Retrieves an issued payment receipt proving that an agent paid for oracle data at a given timestamp."""
    receipt = x402_verifier.get_receipt(receipt_id)
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment receipt '{receipt_id}' not found.",
        )
    return receipt


@app.get(
    "/api/v1/oracle/prices",
    tags=["Oracle Feed"],
    summary="Get all critical mineral prices (Tier 2: Standard $0.005 USDC)",
    responses={402: {"description": "Payment Required (0.005 USDC on Polygon)"}},
)
async def get_all_prices(
    request: Request,
    format: Optional[str] = Query(None, description="Output format: 'json' (default) or 'compact' (LLM token-saving text)"),
):
    """
    Returns normalized, deterministic real-time spot prices for all supported critical commodities:
    - Silver (Ag), Platinum (Pt), Copper (Cu), Lithium (Li), Neodymium/Dysprosium (NdDy).
    """
    resp_402 = await require_x402_payment(request, tier=PricingTier.STANDARD)
    if resp_402:
        return resp_402

    headers = getattr(request.state, "extra_headers", {}) or {}
    accept = request.headers.get("accept", "")
    if format == "compact" or "text/plain" in accept:
        all_q = feed_engine.get_all_quotes().quotes
        items = [f"{sym}:{q.spot_price_usd:.1f}" for sym, q in all_q.items()]
        compact_str = f"[CRM-QUOTE] {'|'.join(items)}"
        return PlainTextResponse(content=compact_str, headers=headers)

    data = feed_engine.get_all_quotes().model_dump()
    return JSONResponse(content=data, headers=headers)


@app.get(
    "/api/v1/oracle/prices/{symbol}",
    tags=["Oracle Feed"],
    summary="Get single mineral price quote (Tier 1: Light $0.001 USDC)",
    responses={402: {"description": "Payment Required (0.001 USDC on Polygon)"}},
)
async def get_single_price(
    request: Request,
    symbol: str = FPath(
        ...,
        description="Commodity symbol or name (e.g. Neodymium, NdDy, Lithium, Li, Copper, Cu, Silver, Ag, Platinum, Pt)",
        examples=["Neodymium", "Lithium", "Copper"]
    ),
    format: Optional[str] = Query(None, description="Output format: 'json' (default) or 'compact' (LLM token-saving text)"),
):
    """
    Returns normalized spot quote and unit conversions for a specific critical mineral symbol (Light Tier).
    """
    resp_402 = await require_x402_payment(request, tier=PricingTier.LIGHT)
    if resp_402:
        return resp_402

    alias_map = {
        "neodymium": CommoditySymbol.NDDY,
        "dysprosium": CommoditySymbol.NDDY,
        "nddy": CommoditySymbol.NDDY,
        "lithium": CommoditySymbol.LI,
        "li": CommoditySymbol.LI,
        "copper": CommoditySymbol.CU,
        "cu": CommoditySymbol.CU,
        "silver": CommoditySymbol.AG,
        "ag": CommoditySymbol.AG,
        "platinum": CommoditySymbol.PT,
        "pt": CommoditySymbol.PT,
    }
    sym_enum = alias_map.get(symbol.lower())
    if not sym_enum:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commodity symbol '{symbol}' not found. Supported: Neodymium (NdDy), Lithium (Li), Copper (Cu), Silver (Ag), Platinum (Pt).",
        )

    headers = getattr(request.state, "extra_headers", {}) or {}
    accept = request.headers.get("accept", "")
    if format == "compact" or "text/plain" in accept:
        q = feed_engine.get_single_quote(sym_enum)
        sym_name = q.symbol.value if hasattr(q.symbol, "value") else str(q.symbol)
        unit_str = q.unit.value if hasattr(q.unit, "value") else str(q.unit)
        compact_str = f"[CRM-QUOTE-{sym_name}] Spot:{q.spot_price_usd:.2f} {unit_str} | 24h:{q.change_24h_pct:+.2f}% | Venue:{q.benchmark_exchange}"
        return PlainTextResponse(content=compact_str, headers=headers)

    data = feed_engine.get_single_quote(sym_enum).model_dump()
    return JSONResponse(content=data, headers=headers)


@app.get(
    "/api/v1/oracle/spreads",
    tags=["Oracle Arbitrage"],
    summary="Get cross-exchange arbitrage spreads (Tier 2: Standard $0.005 USDC)",
    responses={402: {"description": "Payment Required (0.005 USDC on Polygon)"}},
)
async def get_spreads(
    request: Request,
    format: Optional[str] = Query(None, description="Output format: 'json' (default) or 'compact' (LLM token-saving text)"),
):
    """
    Calculates active locational basis spreads across major exchange venues:
    - Copper: COMEX (US) vs LME (UK)
    - Silver: COMEX vs LBMA Loco London Spot
    - Lithium: Fastmarkets CIF Europe vs SMM China Domestic
    - Platinum: NYMEX vs LPPM London
    """
    resp_402 = await require_x402_payment(request, tier=PricingTier.STANDARD)
    if resp_402:
        return resp_402

    headers = getattr(request.state, "extra_headers", {}) or {}
    accept = request.headers.get("accept", "")
    if format == "compact" or "text/plain" in accept:
        spreads_res = feed_engine.get_arbitrage_spreads().spreads
        items = []
        for s in spreads_res:
            raw_sym = s.symbol.value if hasattr(s.symbol, "value") else str(s.symbol)
            items.append(f"{raw_sym}:{s.primary_exchange}-{s.secondary_exchange}(+{s.spread_basis_points:.0f}bps,+${s.net_arbitrage_margin_usd:.2f})")
        compact_str = f"[CRM-SPREADS] {' | '.join(items)}"
        return PlainTextResponse(content=compact_str, headers=headers)

    data = feed_engine.get_arbitrage_spreads().model_dump()
    return JSONResponse(content=data, headers=headers)


@app.get(
    "/api/v1/oracle/stream",
    tags=["Oracle Streaming"],
    summary="Real-time Server-Sent Events (SSE) Stream for Autonomous Agents",
)
async def stream_oracle_events(
    request: Request,
    min_bps: float = Query(30.0, description="Minimum spread basis points to trigger arbitrage alerts"),
    limit: Optional[int] = Query(None, description="Optional maximum events to emit (useful for testing and short-lived subscriptions)"),
):
    """
    Zero-polling Server-Sent Events (SSE) stream for autonomous AI agents.
    Emits periodic heartbeats and instant 'arbitrage_alert' events when profitable locational spreads emerge.
    """
    import time

    async def event_generator():
        yield f"event: connected\ndata: {json.dumps({'message': 'Connected to Minerals Oracle x402 Live Stream', 'filter_min_bps': min_bps})}\n\n"
        iteration = 0
        while True:
            if await request.is_disconnected():
                break
            if limit is not None and iteration >= limit:
                break
            try:
                iteration += 1
                spreads = feed_engine.get_arbitrage_spreads().spreads
                hot_spreads = [sp.model_dump() for sp in spreads if sp.spread_basis_points >= min_bps]
                if hot_spreads:
                    yield f"event: arbitrage_alert\ndata: {json.dumps({'count': len(hot_spreads), 'spreads': hot_spreads})}\n\n"
                elif iteration % 5 == 0:
                    quotes = feed_engine.get_all_quotes().quotes
                    summary = {sym: round(q.spot_price_usd, 2) for sym, q in quotes.items()}
                    yield f"event: heartbeat\ndata: {json.dumps({'timestamp_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'quotes': summary})}\n\n"
                await asyncio.sleep(1.0)
            except Exception as e:
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                await asyncio.sleep(1.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post(
    "/api/v1/oracle/urban-mining/calculate",
    response_model=UrbanMiningResponse,
    tags=["Urban Mining Valuation"],
    summary="Evaluate urban mining scrap batch yield & recoverable value (Tier 3: Heavy $0.010 USDC)",
    responses={402: {"description": "Payment Required (0.010 USDC on Polygon)"}},
)
async def calculate_urban_mining(request: Request, body: UrbanMiningRequest):
    """
    Evaluates gross payable mineral value, element-wise recovery tensor, and net settlement value in USDC after TC/RC:
    - `E_WASTE_HIGH_GRADE_PCB`: Recovers Au, Ag, Cu (Default Benchmark)
    - `EV_BATTERY_BLACK_MASS`: Recovers Li, Ni, Co, Mn
    - `AUTO_CATALYST_CERAMIC`: Recovers Pt, Pd, Rh
    - `WIND_EV_PERMANENT_MAGNETS`: Recovers Nd, Dy, Pr
    """
    resp_402 = await require_x402_payment(request, tier=PricingTier.HEAVY)
    if resp_402:
        return resp_402
    data = feed_engine.calculate_urban_mining(body).model_dump()
    headers = getattr(request.state, "extra_headers", {}) or {}
    return JSONResponse(content=data, headers=headers)


@app.get(
    "/api/v1/oracle/onchain-payload/{symbol}",
    tags=["On-Chain Smart Contract Binding"],
    summary="Get EIP-712 cryptographically signed price payload & ABI calldata for Polygon smart contracts (Tier 4: On-Chain $0.020 USDC)",
    responses={402: {"description": "Payment Required (0.020 USDC on Polygon)"}},
)
async def get_onchain_payload(
    request: Request,
    symbol: str = FPath(
        ...,
        description="Commodity symbol (Ag, Pt, Cu, Li, NdDy)",
        examples=["Cu", "Li", "Ag"]
    ),
):
    """
    Generates EIP-712 cryptographic signature (v, r, s), 8-decimal fixed-point price,
    and ABI-encoded calldata to call `updateMineralPrice(...)` on MineralsOracleConsumer.sol on Polygon.
    """
    resp_402 = await require_x402_payment(request, tier=PricingTier.ONCHAIN)
    if resp_402:
        return resp_402

    alias_map = {
        "cu": "Cu", "copper": "Cu",
        "li": "Li", "lithium": "Li",
        "ag": "Ag", "silver": "Ag",
        "pt": "Pt", "platinum": "Pt",
        "nddy": "NdDy", "neodymium": "NdDy", "dysprosium": "NdDy"
    }
    std_sym = alias_map.get(symbol.lower())
    if not std_sym:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commodity symbol '{symbol}' not found for onchain payload.",
        )

    # Fetch live price
    sym_enum = CommoditySymbol(std_sym)
    quote = feed_engine.get_single_quote(sym_enum)
    signed_payload = onchain_signer.sign_price_feed(
        symbol=std_sym,
        price_usd=quote.spot_price_usd,
    )
    headers = getattr(request.state, "extra_headers", {}) or {}
    return JSONResponse(content=signed_payload, headers=headers)


@app.post(
    "/api/v1/oracle/onchain-settlement-payload",
    tags=["On-Chain Smart Contract Binding"],
    summary="Generate signed EIP-712 settlement payload & calldata for physical scrap recycling batches (Tier 4: On-Chain $0.020 USDC)",
    responses={402: {"description": "Payment Required (0.020 USDC on Polygon)"}},
)
async def get_onchain_settlement_payload(
    request: Request,
    body: UrbanMiningRequest,
):
    """
    Calculates urban mining recoverable value and signs an on-chain ScrapSettlement payload
    for calling `settleScrapBatch(...)` on MineralsOracleConsumer.sol.
    """
    resp_402 = await require_x402_payment(request, tier=PricingTier.ONCHAIN)
    if resp_402:
        return resp_402

    val_res = feed_engine.calculate_urban_mining(body)
    signed_settlement = onchain_signer.sign_scrap_settlement(
        scrap_category=body.scrap_category.value,
        net_value_usd=val_res.net_settlement_value_usd,
        quantity_kg=body.quantity_metric_tons * 1000.0,
    )
    headers = getattr(request.state, "extra_headers", {}) or {}
    return JSONResponse(content=signed_settlement, headers=headers)


# ==========================================
# Phase 3: Enterprise Telemetry & SLA Management
# ==========================================
@app.get(
    "/metrics",
    tags=["Enterprise Telemetry"],
    summary="Prometheus / Grafana Standard Observability Metrics",
)
async def get_prometheus_metrics():
    """Returns system telemetry in standard Prometheus text exposition format."""
    sla = enterprise_manager.get_sla_metrics()
    quotes = feed_engine.get_all_quotes().quotes
    metrics_lines = [
        "# HELP oracle_uptime_seconds Total running uptime in seconds",
        "# TYPE oracle_uptime_seconds counter",
        f"oracle_uptime_seconds {sla['uptime_seconds']}",
        "# HELP oracle_queries_total Total oracle requests processed",
        "# TYPE oracle_queries_total counter",
        f"oracle_queries_total {enterprise_manager.total_requests_processed}",
        "# HELP oracle_active_enterprise_tenants Current active institutional enterprise tenants",
        "# TYPE oracle_active_enterprise_tenants gauge",
        f"oracle_active_enterprise_tenants {sla['capacity']['active_enterprise_tenants']}",
        "# HELP oracle_latency_p50_milliseconds Median request latency",
        "# TYPE oracle_latency_p50_milliseconds gauge",
        f"oracle_latency_p50_milliseconds {sla['latency_telemetry']['p50_ms']}",
    ]
    for sym, q in quotes.items():
        metrics_lines.append(f'oracle_mineral_spot_price_usd{{symbol="{sym}"}} {q.spot_price_usd}')

    return PlainTextResponse("\n".join(metrics_lines) + "\n", media_type="text/plain; version=0.0.4")


@app.get(
    "/api/v1/enterprise/sla-status",
    tags=["Enterprise SLA"],
    summary="Get 99.99% Tier-4 Financial Grade SLA Telemetry & Latency Report",
)
async def get_enterprise_sla():
    """Returns institutional SLA uptime, P50/P99 latency benchmarks, and active enterprise tenants."""
    return enterprise_manager.get_sla_metrics()


class ProvisionKeyRequest(BaseModel):
    organization_name: str
    contact_email: str
    tier_plan: str = "Enterprise-Platinum-Dedicated"


@app.post(
    "/api/v1/enterprise/provision-key",
    tags=["Enterprise SLA"],
    summary="Provision New Institutional Enterprise VIP Key",
)
async def provision_enterprise_key(body: ProvisionKeyRequest):
    """Provisions a new dedicated enterprise API key with priority bandwidth and custom rate limits."""
    rec = enterprise_manager.provision_key(
        organization=body.organization_name,
        email=body.contact_email,
        plan=body.tier_plan,
    )
    return {
        "status": "success",
        "enterprise_key": rec.api_key,
        "organization_name": rec.organization_name,
        "tier_plan": rec.tier_plan,
        "rate_limit_per_minute": rec.rate_limit_per_minute,
        "instructions": "Pass header 'X-Enterprise-Key: <key>' or 'Authorization: Bearer <key>' for dedicated VIP bandwidth.",
    }


# ==========================================
# FastMCP / Agent Tool Calling Endpoints
# ==========================================
@app.get("/mcp/tools", tags=["MCP Tools"])
async def get_mcp_tool_specs():
    """Returns Model Context Protocol (MCP) tool specifications for autonomous AI agents."""
    if MCP_SPEC_FILE_PATH.exists():
        with open(MCP_SPEC_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"tools": []}


@app.post("/mcp/invoke", response_model=MCPToolCallResponse, tags=["MCP Tools"])
async def invoke_mcp_tool(request: Request, tool_call: MCPToolCallRequest):
    """
    Direct MCP tool dispatcher for LLM agents. Protected with x402 payment validation.
    """
    resp_402 = await require_x402_payment(request)
    if resp_402:
        return resp_402

    name = tool_call.name
    args = tool_call.arguments

    if name == "get_mineral_prices":
        data = feed_engine.get_all_quotes().model_dump()
        return MCPToolCallResponse(content=[{"type": "text", "text": json.dumps(data, indent=2)}])

    elif name == "get_arbitrage_spreads":
        data = feed_engine.get_arbitrage_spreads().model_dump()
        return MCPToolCallResponse(content=[{"type": "text", "text": json.dumps(data, indent=2)}])

    elif name == "calculate_urban_mining_value":
        try:
            req_model = UrbanMiningRequest(**args)
            data = feed_engine.calculate_urban_mining(req_model).model_dump()
            return MCPToolCallResponse(content=[{"type": "text", "text": json.dumps(data, indent=2)}])
        except Exception as e:
            return MCPToolCallResponse(
                content=[{"type": "text", "text": f"Error calculating urban mining value: {str(e)}"}],
                isError=True,
            )

    elif name == "get_onchain_signed_feed":
        symbol = args.get("symbol", "Cu")
        try:
            sym_enum = CommoditySymbol(symbol)
            quote = feed_engine.get_single_quote(sym_enum)
            data = onchain_signer.sign_price_feed(symbol, quote.spot_price_usd)
            return MCPToolCallResponse(content=[{"type": "text", "text": json.dumps(data, indent=2)}])
        except Exception as e:
            return MCPToolCallResponse(
                content=[{"type": "text", "text": f"Error generating onchain signed feed: {str(e)}"}],
                isError=True,
            )

    else:
        return MCPToolCallResponse(
            content=[{"type": "text", "text": f"Unknown tool name: {name}"}],
            isError=True,
        )


# ==========================================
# 24/7 Cloud Autonomous Trading Bot Endpoints
# ==========================================
@app.get(
    "/api/v1/bot/status",
    tags=["24/7 Cloud Trading Bot"],
    summary="Get 24/7 Cloud Autonomous Arbitrage Bot Status & Cumulative PnL",
)
async def get_cloud_bot_status():
    """
    Returns real-time operational status, cumulative realized PnL, gas costs,
    and broker details for the 24/7 cloud worker running independently of user laptop.
    """
    return cloud_bot_worker.get_status()


@app.get(
    "/api/v1/bot/history",
    tags=["24/7 Cloud Trading Bot"],
    summary="Get Recent Automated Trade Execution History",
)
async def get_cloud_bot_history(limit: int = Query(20, ge=1, le=100)):
    """
    Returns the most recent automated trade executions recorded by the 24/7 Cloud Worker.
    """
    return {
        "status": "success",
        "count": len(cloud_bot_worker.trade_history[:limit]),
        "trades": cloud_bot_worker.trade_history[:limit],
    }


@app.get(
    "/api/v1/kis/account-balance",
    tags=["24/7 Cloud Trading Bot"],
    summary="Get Real-Time Live Korea Investment & Securities (KIS) Account Balance",
)
async def get_kis_account_balance():
    """
    Queries real-time live cash deposit & total asset evaluation from Korea Investment & Securities OpenAPI.
    """
    from app.kis_client import kis_client
    return kis_client.inquire_realtime_balance()


@app.get(
    "/api/v1/trade/audit-summary",
    tags=["Post-Trade Audit & Learning"],
    summary="Get Post-Trade Performance Audit Summary & Learning Metrics",
)
async def get_trade_audit_summary():
    """
    Returns aggregated post-trade audit statistics including win rate, profit factor,
    4x commission hurdle adherence, slippage analytics, and grade distribution.
    """
    return {
        "status": "success",
        "summary": post_trade_analyst.get_summary_statistics(),
    }


@app.get(
    "/api/v1/trade/audit-reports",
    tags=["Post-Trade Audit & Learning"],
    summary="Get Recent Post-Trade Evaluation Reports & Critiques",
)
async def get_trade_audit_reports(limit: int = Query(20, ge=1, le=100)):
    """
    Returns the list of individual post-trade evaluations with execution grades (A/B/C/D/F),
    slippage data, commission coverage multiples, and actionable learning insights.
    """
    return {
        "status": "success",
        "count": len(post_trade_analyst.audit_records[:limit]),
        "reports": post_trade_analyst.audit_records[:limit],
    }


@app.get(
    "/api/v1/bot/config",
    tags=["24/7 Cloud Trading Bot"],
    summary="Get 24/7 Cloud Bot & Overseas Futures Trade Sizing Configuration",
)
async def get_cloud_bot_config():
    """
    Returns current trade mode (Futures Micro/Standard, ETF, Auto), sizing algorithm,
    target commodity, capital allocation, and supported contract specifications.
    """
    return {
        "status": "success",
        "config": cloud_bot_worker.get_config(),
    }


class UpdateBotConfigRequest(BaseModel):
    trade_mode: Optional[str] = None
    sizing_mode: Optional[str] = None
    fixed_lots: Optional[int] = None
    target_commodity: Optional[str] = None
    total_capital_usd: Optional[float] = None
    trade_size_usd: Optional[float] = None
    margin_buffer_pct: Optional[float] = None
    max_positions: Optional[int] = None
    scan_interval_sec: Optional[float] = None


@app.post(
    "/api/v1/bot/config",
    tags=["24/7 Cloud Trading Bot"],
    summary="Update 24/7 Cloud Bot Trade Sizing Configuration",
)
async def update_cloud_bot_config(body: UpdateBotConfigRequest):
    """
    Dynamically reconfigures bot parameters (Trade Mode, Sizing Mode, Lots, Target Asset, Capital).
    """
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    updated_config = cloud_bot_worker.update_config(updates)
    return {
        "status": "success",
        "updated_parameters": list(updates.keys()),
        "config": updated_config,
    }


@app.post(
    "/api/v1/bot/toggle",
    tags=["24/7 Cloud Trading Bot"],
    summary="Pause or Resume 24/7 Cloud Worker",
)
async def toggle_cloud_bot(enable: bool = Query(..., description="Set true to run, false to pause")):
    """
    Dynamically start or pause the 24/7 Cloud background trading worker.
    """
    if enable:
        cloud_bot_worker.is_enabled = True
        cloud_bot_worker.start()
    else:
        cloud_bot_worker.stop()
        cloud_bot_worker.is_enabled = False

    return {
        "status": "success",
        "action": "STARTED" if enable else "PAUSED",
        "current_status": cloud_bot_worker.get_status(),
    }


@app.post(
    "/api/v1/bot/reset",
    tags=["24/7 Cloud Trading Bot"],
    summary="Reset All 24/7 Cloud Bot Metrics, PnL, and Trade History to 0",
)
async def reset_cloud_bot():
    """
    Clears all past trade history and resets cumulative PnL metrics and active positions to 0 for a fresh live start.
    """
    status_data = cloud_bot_worker.reset_state()
    return {
        "status": "success",
        "message": "All trading metrics, PnL counters, and positions successfully reset to 0.",
        "current_status": status_data,
    }


@app.post(
    "/api/v1/bot/sync-live-position",
    tags=["24/7 Cloud Trading Bot"],
    summary="Synchronize Open Futures Position into Active Tracking Engine",
)
async def sync_live_position(
    symbol: str = Query("Cu", description="Commodity symbol e.g. Cu"),
    ticker: str = Query("MHGZ26", description="Futures active contract ticker"),
    qty: int = Query(1, description="Quantity lots"),
    alloc_usd: float = Query(1320.0, description="Allocated margin in USD"),
):
    """
    Registers an existing broker-filled overseas futures position into the cloud bot's active tracking engine.
    """
    from .feed_engine import feed_engine
    quotes = feed_engine.get_all_quotes().quotes
    q = quotes.get(symbol)
    entry_p = q.spot_price_usd if q else 14894.43
    cloud_bot_worker.active_positions[symbol] = {
        "ticker": ticker,
        "is_futures": True,
        "contract_type": "micro",
        "entry_price": entry_p,
        "quantity": qty,
        "contract_multiplier": 2500.0,
        "commission_usd": 2.0,
        "entry_bps": 50.0,
        "allocation_usd": alloc_usd,
        "entry_time": time.time(),
    }
    import logging
    logging.info(f"✅ Synchronized active position for {symbol} ({ticker}) into cloud bot tracker.")
    return {
        "status": "success",
        "message": f"Position for {symbol} ({ticker}) synchronized.",
        "active_positions": cloud_bot_worker.active_positions,
    }


@app.post(
    "/api/v1/bot/close-position",
    tags=["24/7 Cloud Trading Bot"],
    summary="Execute Immediate Live Market Close for a Position",
)
async def execute_immediate_close(
    symbol: str = Query("Cu", description="Commodity symbol to exit"),
):
    """
    Dispatches a real-time live market exit order to CME/NYMEX or stock exchange to close position immediately.
    """
    pos = cloud_bot_worker.active_positions.get(symbol)
    if not pos:
        return {"status": "error", "message": f"No active position found for {symbol}."}

    is_futures = pos.get("is_futures", True)
    qty = pos.get("quantity", 1)
    comm = pos.get("commission_usd", 2.0)
    c_type = pos.get("contract_type", "micro")

    if is_futures:
        res = kis_client.execute_futures_hedge_order(
            symbol=symbol,
            spread_bps=0.0,
            net_margin_usd=0.0,
            direction="Sell (Close Hedge)",
            quantity_lots=qty,
            contract_type=c_type,
            dry_run=False,
            commission_usd=comm,
        )
    else:
        res = kis_client.execute_overseas_stock_etf_order(
            symbol=symbol,
            spread_bps=0.0,
            net_margin_usd=0.0,
            direction="Sell (Close Position)",
            quantity_shares=qty,
            dry_run=False,
            commission_usd=comm,
        )

    if res.get("status") == "ORDER_EXECUTED":
        cloud_bot_worker.active_positions.pop(symbol, None)

    return {
        "status": "success",
        "order_result": res,
        "remaining_positions": cloud_bot_worker.active_positions,
    }


@app.get(
    "/api/v1/ops/telemetry",
    tags=["A-Grid Operations & Compliance"],
    summary="Get Consolidated Live Telemetry for agrid-ops-agent",
)
async def get_agrid_ops_telemetry():
    """
    Returns real-time consolidated financial, accounting, and compliance metrics
    specifically formatted for ingestion by agrid-ops-agent (Accounting, Finance, Legal).
    """
    import csv
    from datetime import datetime, timezone

    # 1. Load bot state
    state_file = Path(__file__).parent.parent / "logs" / "bot_state.json"
    state_data = {}
    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state_data = json.load(f)
        except Exception:
            pass

    # 2. Get KIS account numbers
    from app.kis_client import kis_client
    
    # 3. Load SLA metrics
    sla = enterprise_manager.get_sla_metrics()

    return {
        "status": "success",
        "service_name": "minerals-oracle-x402",
        "telemetry_type": "AGRID_OPS_INTEGRATION_V1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "finance": {
            "total_capital_usd": state_data.get("total_capital_usd", float(os.getenv("TOTAL_CAPITAL_USD", "497.65"))),
            "safe_reserve_vault_usd": state_data.get("safe_reserve_vault_usd", 0.0),
            "reinvested_capital_usd": state_data.get("reinvested_capital_usd", 0.0),
            "free_available_usd": state_data.get("total_capital_usd", 497.65) - sum(p.get("margin_usd", 0.0) for p in state_data.get("active_positions", {}).values()),
            "active_positions_count": len(state_data.get("active_positions", {})),
            "broker": "한국투자증권 (Korea Investment & Securities)",
            "stock_account": kis_client.account_no,
            "futures_account": kis_client.futures_account_no,
            "is_dry_run": os.getenv("KIS_DRY_RUN", "true").lower() in ("true", "1", "yes"),
        },
        "accounting": {
            "total_trades_executed": state_data.get("total_trades_executed", 0),
            "cumulative_net_pnl_usd": state_data.get("cumulative_net_pnl", 0.0),
            "cumulative_gross_profit_usd": state_data.get("cumulative_gross_profit", 0.0),
            "cumulative_gas_spent_usd": state_data.get("cumulative_gas_spent", 0.0),
            "x402_price_per_query_usdc": float(os.getenv("DEFAULT_PRICE_USDC", "0.005")),
            "oracle_treasury_wallet": os.getenv("ORACLE_TREASURY_WALLET", "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf"),
            "polygon_chain_id": int(os.getenv("POLYGON_CHAIN_ID", "137")),
        },
        "compliance_and_sla": {
            "uptime_percentage": sla.get("uptime_percentage", "99.998%"),
            "sla_tier": sla.get("sla_tier", "99.99% Tier-4 Financial Grade"),
            "latency_p50_ms": sla.get("latency_telemetry", {}).get("p50_ms", 0.85),
            "audit_proof": sla.get("compliance", {}).get("audit_proof", "Cryptographic EIP-712 / SHA-256"),
        },
    }


@app.get(
    "/api/v1/ops/journals",
    tags=["A-Grid Operations & Compliance"],
    summary="Get Structured Trade & Cash-out Journals for agrid-ops-agent",
)
async def get_agrid_ops_journals(limit: int = Query(50, ge=1, le=500)):
    """
    Exports recent closed trades and cashout journal entries for A.GRID ledger and tax automation.
    """
    import csv
    log_dir = Path(__file__).parent.parent / "logs"
    trade_file = log_dir / "trade_journal_master.csv"
    cashout_file = log_dir / "cashout_journal.csv"

    trades = []
    if trade_file.exists():
        try:
            with open(trade_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    trades.append(row)
        except Exception:
            pass

    cashouts = []
    if cashout_file.exists():
        try:
            with open(cashout_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cashouts.append(row)
        except Exception:
            pass

    return {
        "status": "success",
        "trade_count": len(trades[-limit:]),
        "trades": trades[-limit:],
        "cashout_count": len(cashouts[-limit:]),
        "cashouts": cashouts[-limit:],
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)


