import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel

from fastapi import FastAPI, Request, Depends, HTTPException, status, Query, Path as FPath
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse, HTMLResponse
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
from app.onchain_signer import onchain_signer
from app.vault_manager import vault_manager
from app.enterprise_manager import enterprise_manager
from app.twitter_bot import twitter_bot
from app.telegram_bot import telegram_bot

app = FastAPI(
    title="Critical Raw Minerals & Urban Mining Oracle",
    description=(
        "Real-time physical spot market benchmark pricing, cross-exchange arbitrage spreads, "
        "and metallurgical urban mining scrap yield valuations on Polygon Network. "
        "Explore the interactive Web Dashboard at /dashboard."
    ),
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
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
    response_model=PriceFeedResponse,
    tags=["Oracle Feed"],
    summary="Get all critical mineral prices (Tier 2: Standard $0.005 USDC)",
    responses={402: {"description": "Payment Required (0.005 USDC on Polygon)"}},
)
async def get_all_prices(request: Request):
    """
    Returns normalized, deterministic real-time spot prices for all supported critical commodities:
    - Silver (Ag), Platinum (Pt), Copper (Cu), Lithium (Li), Neodymium/Dysprosium (NdDy).
    """
    resp_402 = await require_x402_payment(request, tier=PricingTier.STANDARD)
    if resp_402:
        return resp_402
    data = feed_engine.get_all_quotes().model_dump()
    headers = getattr(request.state, "extra_headers", {}) or {}
    return JSONResponse(content=data, headers=headers)


@app.get(
    "/api/v1/oracle/prices/{symbol}",
    response_model=MineralQuote,
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

    data = feed_engine.get_single_quote(sym_enum).model_dump()
    headers = getattr(request.state, "extra_headers", {}) or {}
    return JSONResponse(content=data, headers=headers)


@app.get(
    "/api/v1/oracle/spreads",
    response_model=SpreadsResponse,
    tags=["Oracle Arbitrage"],
    summary="Get cross-exchange arbitrage spreads (Tier 2: Standard $0.005 USDC)",
    responses={402: {"description": "Payment Required (0.005 USDC on Polygon)"}},
)
async def get_spreads(request: Request):
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
    data = feed_engine.get_arbitrage_spreads().model_dump()
    headers = getattr(request.state, "extra_headers", {}) or {}
    return JSONResponse(content=data, headers=headers)


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


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)

