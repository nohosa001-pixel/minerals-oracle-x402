import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

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
)
from app.feed_engine import feed_engine
from app.x402_verifier import x402_verifier
from app.twitter_bot import twitter_bot
from app.telegram_bot import telegram_bot

app = FastAPI(
    title="Critical Raw Minerals & Urban Mining Oracle",
    description=(
        "Real-time physical spot market benchmark pricing, cross-exchange arbitrage spreads, "
        "and metallurgical urban mining scrap yield valuations on Base Network. "
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


# Dependency for 402 Payment verification
async def require_x402_payment(request: Request):
    """Enforces x402 payment authorization or grants Sandbox Free Tier before accessing protected oracle endpoints."""
    is_authorized, reason, extra_headers = x402_verifier.verify_request_payment(request)
    if not is_authorized:
        return x402_verifier.build_402_response()
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
        "network": "Base (Chain ID 8453)",
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
        "network": "base-mainnet",
        "chain_id": 8453,
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
    unlock full EIP-712 certified quotes via x402 on Base (0.005 USDC).
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
        "> Web3 x402 Critical Raw Minerals & Urban Mining Oracle on Base (Chain ID 8453).\n"
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
            "E-Waste PCBs, Permanent Magnets). Monetized via HTTP 402 with 0.005 USDC on Base."
        ),
        "description_for_human": "Autonomous Base x402 Oracle for Physical Commodities & Urban Mining.",
        "auth": {
            "type": "x402",
            "chain_id": 8453,
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
            "network": "base",
            "chain_id": 8453,
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
        except Exception:
            pass
    return manifest


# ==========================================
# Oracle 402 Challenge & Protected Endpoints
# ==========================================
@app.get(
    "/api/v1/oracle/challenge",
    tags=["Oracle Payment"],
    summary="Get fresh x402 payment challenge nonce and parameters",
)
async def get_payment_challenge():
    """
    Directly request a fresh HTTP 402 challenge payload for autonomous agent signing.
    Returns 402 Payment Required with WWW-Authenticate header and JSON challenge body.
    """
    return x402_verifier.build_402_response()
@app.get(
    "/api/v1/oracle/prices",
    response_model=PriceFeedResponse,
    tags=["Oracle Feed"],
    summary="Get all critical mineral prices",
    responses={402: {"description": "Payment Required (0.005 USDC on Base)"}},
)
async def get_all_prices(request: Request):
    """
    Returns normalized, deterministic real-time spot prices for all supported critical commodities:
    - Silver (Ag), Platinum (Pt), Copper (Cu), Lithium (Li), Neodymium/Dysprosium (NdDy).
    """
    resp_402 = await require_x402_payment(request)
    if resp_402:
        return resp_402
    data = feed_engine.get_all_quotes().model_dump()
    headers = getattr(request.state, "extra_headers", {}) or {}
    return JSONResponse(content=data, headers=headers)


@app.get(
    "/api/v1/oracle/prices/{symbol}",
    response_model=MineralQuote,
    tags=["Oracle Feed"],
    summary="Get single mineral price quote",
    responses={402: {"description": "Payment Required (0.005 USDC on Base)"}},
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
    Returns normalized spot quote and unit conversions for a specific critical mineral symbol.
    """
    resp_402 = await require_x402_payment(request)
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
    summary="Get cross-exchange arbitrage spreads",
    responses={402: {"description": "Payment Required (0.005 USDC on Base)"}},
)
async def get_spreads(request: Request):
    """
    Calculates active locational basis spreads across major exchange venues:
    - Copper: COMEX (US) vs LME (UK)
    - Silver: COMEX vs LBMA Loco London Spot
    - Lithium: Fastmarkets CIF Europe vs SMM China Domestic
    - Platinum: NYMEX vs LPPM London
    """
    resp_402 = await require_x402_payment(request)
    if resp_402:
        return resp_402
    data = feed_engine.get_arbitrage_spreads().model_dump()
    headers = getattr(request.state, "extra_headers", {}) or {}
    return JSONResponse(content=data, headers=headers)


@app.post(
    "/api/v1/oracle/urban-mining/calculate",
    response_model=UrbanMiningResponse,
    tags=["Urban Mining Valuation"],
    summary="Evaluate urban mining scrap batch yield & recoverable value",
    responses={402: {"description": "Payment Required (0.005 USDC on Base)"}},
)
async def calculate_urban_mining(request: Request, body: UrbanMiningRequest):
    """
    Evaluates gross payable mineral value, element-wise recovery tensor, and net settlement value in USDC after TC/RC:
    - `E_WASTE_HIGH_GRADE_PCB`: Recovers Au, Ag, Cu (Default Benchmark)
    - `EV_BATTERY_BLACK_MASS`: Recovers Li, Ni, Co, Mn
    - `AUTO_CATALYST_CERAMIC`: Recovers Pt, Pd, Rh
    - `WIND_EV_PERMANENT_MAGNETS`: Recovers Nd, Dy, Pr
    """
    resp_402 = await require_x402_payment(request)
    if resp_402:
        return resp_402
    data = feed_engine.calculate_urban_mining(body).model_dump()
    headers = getattr(request.state, "extra_headers", {}) or {}
    return JSONResponse(content=data, headers=headers)


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

    else:
        return MCPToolCallResponse(
            content=[{"type": "text", "text": f"Unknown tool name: {name}"}],
            isError=True,
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)

