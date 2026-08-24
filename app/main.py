import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, Depends, HTTPException, status, Query, Path as FPath
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import (
    CommoditySymbol,
    PriceFeedResponse,
    MineralQuote,
    SpreadsResponse,
    UrbanMiningRequest,
    UrbanMiningResponse,
    MCPToolCallRequest,
    MCPToolCallResponse,
)
from app.feed_engine import feed_engine
from app.x402_verifier import x402_verifier

app = FastAPI(
    title="Critical Raw Minerals & Urban Mining Oracle (x402)",
    description=(
        "High-performance deterministic micro-oracle service for autonomous trading, supply chain, "
        "and RWA agents. Features real-time spot pricing, COMEX/LME arbitrage spreads, and urban mining "
        "scrap yield analytics (EV Battery Black Mass, Auto Catalysts, E-waste PCBs, Permanent Magnets). "
        "Monetized via HTTP 402 + x402 protocol on Base (0.005 USDC per query)."
    ),
    version="1.0.0",
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

AP2_FILE_PATH = Path(__file__).parent.parent / ".well-known" / "ap2.json"
MCP_SPEC_FILE_PATH = Path(__file__).parent.parent / "mcp_tool_spec.json"


# Dependency for 402 Payment verification
async def require_x402_payment(request: Request):
    """Enforces x402 payment authorization before accessing protected oracle endpoints."""
    is_authorized, reason = x402_verifier.verify_request_payment(request)
    if not is_authorized:
        return x402_verifier.build_402_response()
    request.state.authorized_payer = reason
    return None


@app.get("/", tags=["System"])
async def root():
    """Service metadata & introductory details."""
    return {
        "service": "minerals-oracle-x402",
        "description": "Critical Raw Minerals & Urban Mining Oracle",
        "version": "1.0.0",
        "protocol": "x402 (HTTP 402 Monetized)",
        "network": "Base (Chain ID 8453)",
        "price_per_query": "0.005 USDC",
        "endpoints": {
            "all_prices": "/api/v1/oracle/prices",
            "single_price": "/api/v1/oracle/prices/{symbol}",
            "arbitrage_spreads": "/api/v1/oracle/spreads",
            "urban_mining_calculator": "/api/v1/oracle/urban-mining/calculate",
            "ap2_manifest": "/.well-known/ap2",
            "mcp_tools": "/mcp/tools",
            "docs": "/docs",
        },
    }


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
# Oracle Protected Endpoints (HTTP 402)
# ==========================================
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
    return feed_engine.get_all_quotes()


@app.get(
    "/api/v1/oracle/prices/{symbol}",
    response_model=MineralQuote,
    tags=["Oracle Feed"],
    summary="Get single mineral price quote",
    responses={402: {"description": "Payment Required (0.005 USDC on Base)"}},
)
async def get_single_price(
    request: Request,
    symbol: CommoditySymbol = FPath(..., description="Commodity symbol (Ag, Pt, Cu, Li, NdDy)"),
):
    """
    Returns normalized spot quote and unit conversions for a specific critical mineral symbol.
    """
    resp_402 = await require_x402_payment(request)
    if resp_402:
        return resp_402
    try:
        return feed_engine.get_single_quote(symbol)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commodity symbol '{symbol}' not found in active benchmarks.",
        )


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
    return feed_engine.get_arbitrage_spreads()


@app.post(
    "/api/v1/oracle/urban-mining/calculate",
    response_model=UrbanMiningResponse,
    tags=["Urban Mining Valuation"],
    summary="Evaluate urban mining scrap batch yield & recoverable value",
    responses={402: {"description": "Payment Required (0.005 USDC on Base)"}},
)
async def calculate_urban_mining(request: Request, body: UrbanMiningRequest):
    """
    Evaluates gross payable mineral value and net settlement value after treatment/refining charges (TC/RC)
    for urban mining scrap feedstocks:
    - `EV_BATTERY_BLACK_MASS`: Recovers Li, Ni, Co, Mn
    - `AUTO_CATALYST_CERAMIC`: Recovers Pt, Pd, Rh
    - `E_WASTE_HIGH_GRADE_PCB`: Recovers Au, Ag, Cu
    - `WIND_EV_PERMANENT_MAGNETS`: Recovers Nd, Dy, Pr
    """
    resp_402 = await require_x402_payment(request)
    if resp_402:
        return resp_402
    return feed_engine.calculate_urban_mining(body)


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
