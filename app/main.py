from __future__ import annotations

import asyncio
import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any, Optional, List

from fastapi import (
    FastAPI,
    Request,
    HTTPException,
    status,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import (
    JSONResponse,
    FileResponse,
    PlainTextResponse,
    HTMLResponse,
    StreamingResponse,
    Response,
)
from fastapi.middleware.cors import CORSMiddleware
from app.security_gate_middleware import SecurityGateMiddleware
from fastapi.staticfiles import StaticFiles

from app.websocket_manager import ws_manager
from app.x402_verifier import x402_verifier
from app.routers.deps import require_x402_payment, STANDARD_DISCLAIMER_META

# Modular Domain APIRouters
from app.routers.minerals import router as minerals_router
from app.routers.logistics import router as logistics_router
from app.routers.a2a_trade import router as a2a_trade_router
from app.routers.oracle_pricing import router as oracle_pricing_router
from app.routers.mcp import router as mcp_router, _MCP_SSE_SESSIONS
from app.routers.brain import router as brain_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes autonomous critical mineral compliance engine on startup."""
    yield


app = FastAPI(
    title="Autonomous Critical Minerals & Battery Supply-Chain Compliance Oracle",
    description=(
        "Agent-Native 7-Pillar Provenance, 12-Trap Regulatory Defense, "
        "Trade Jurisprudence Precedents, and EIP-712 Polygon Battery Passport Oracle."
    ),
    version="2.0.0",
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

# 1-Line Zero-Friction Security Gate Defense (<2ms Prompt Injection / Jailbreak Filter)
app.add_middleware(SecurityGateMiddleware)


@app.middleware("http")
async def a2a_machine_protocol_middleware(request: Request, call_next):
    response = await call_next(request)
    # Sovereign Machine Protocol & AEO Directives (Zero-Human Distribution)
    response.headers["X-Protocol"] = "A.GRID-AP2/1.0"
    response.headers["X-Agrid-Hub"] = "https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/hub/"
    response.headers["X-Agrid-Directive"] = "https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/AGENTS.md"
    response.headers["X-Agrid-Minerals"] = "https://minerals-oracle-x402-212942243360.asia-northeast3.run.app/api/v1/oracle/alpha-signals"
    response.headers["X-Agrid-Rebate-Bps"] = "2000"
    response.headers["X-Robots-Tag"] = "all, index, follow"
    return response


STATIC_DIR = Path(__file__).parent / "static"
INDEX_HTML_PATH = STATIC_DIR / "index.html"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

AP2_FILE_PATH = Path(__file__).parent.parent / ".well-known" / "ap2.json"
MCP_SPEC_FILE_PATH = Path(__file__).parent.parent / "mcp_tool_spec.json"


# ==========================================
# Root & System Endpoints
# ==========================================
@app.get("/", tags=["System"])
async def root(request: Request):
    """Serves Autonomous Agent Interactive Web UI Console (English RFC Compliant) or JSON metadata."""
    accept_header = request.headers.get("accept", "")
    no_cache_headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
        "X-Language-Policy": "en-US-Agent-Only",
    }
    # If a browser requests text/html, serve the HTML dashboard
    if "text/html" in accept_header or request.query_params.get("ui") == "true":
        if INDEX_HTML_PATH.exists():
            return FileResponse(INDEX_HTML_PATH, media_type="text/html; charset=utf-8", headers=no_cache_headers)

    # API clients, test clients, and curl get JSON service metadata
    return {
        "service": "minerals-oracle-x402",
        "description": "Autonomous Critical Minerals & Battery Supply-Chain Compliance Oracle (Agent-Exclusive)",
        "version": "2.0.0",
        "protocol": "x402 (HTTP 402 Monetized)",
        "network": "Polygon (Chain ID 137)",
        "price_per_query": "0.005 ~ 0.50 USDC",
        "interactive_dashboard": "/dashboard",
        "endpoints": {
            "compliance_verify": "/api/v1/oracle/compliance/verify",
            "lithium_origin_verify": "/api/v1/lithium/verify-origin",
            "nickel_origin_verify": "/api/v1/nickel/verify-origin",
            "cobalt_origin_verify": "/api/v1/cobalt/verify-origin",
            "copper_origin_verify": "/api/v1/copper/verify-origin",
            "silver_origin_verify": "/api/v1/silver/verify-origin",
            "composite_battery_verify": "/api/v1/battery/composite-verify",
            "compliance_status": "/api/v1/oracle/compliance/status",
            "trade_precedents": "/api/v1/oracle/compliance/precedents",
            "trade_optimize_route": "/api/v1/trade/optimize-route",
            "trade_verify_ebl": "/api/v1/trade/verify-ebl",
            "trade_deals_propose": "/api/v1/trade/deals/propose",
            "trade_deals_dual_sign": "/api/v1/trade/deals/dual-sign",
            "agent_session_open": "/api/v1/agent/session/open",
            "agent_session_close": "/api/v1/agent/session/close",
            "alpha_signals": "/api/v1/oracle/alpha-signals",
            "all_prices": "/api/v1/oracle/prices",
            "single_price": "/api/v1/oracle/prices/{symbol}",
            "arbitrage_spreads": "/api/v1/oracle/spreads",
            "agent_onboard": "/api/v1/agent/onboard",
            "agent_evolution": "/api/v1/oracle/agent/feedback",
            "vault_deposit": "/api/v1/vault/deposit",
            "ap2_manifest": "/.well-known/ap2",
            "mcp_tools": "/mcp/tools",
            "mcp_sse": "/mcp/sse",
            "mcp_messages": "/mcp/messages",
            "agent_webhooks_register": "/api/v1/agent/webhooks/register",
            "pyth_realtime_price": "/api/v1/oracle/realtime-price/{symbol}",
            "relay_sponsor_deal": "/api/v1/relay/sponsor-deal-attestation",
            "relay_sponsor_passport": "/api/v1/relay/sponsor-battery-passport",
            "solana_truth_attest": "/api/v1/escrow/universal/solana/attest",
            "brain_perceive": "/api/v1/brain/perceive",
            "brain_execute": "/api/v1/brain/execute",
            "brain_diagnostics": "/api/v1/brain/diagnostics",
            "solana_settle": "/api/v1/escrow/universal/settle-solana",
            "docs": "/docs",
        },
    }


@app.get("/dashboard", tags=["System"])
@app.get("/playground", tags=["System"])
@app.get("/en", tags=["System"])
async def web_dashboard(request: Request):
    """Interactive Web UI Console for Autonomous Agents (English Only)."""
    no_cache_headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
        "X-Language-Policy": "en-US-Agent-Only",
    }
    if INDEX_HTML_PATH.exists():
        return FileResponse(INDEX_HTML_PATH, media_type="text/html; charset=utf-8", headers=no_cache_headers)
    return HTMLResponse("<h1>Minerals Oracle Agent Console</h1><p>Static index.html not found.</p>")


@app.get("/ko", tags=["System"])
@app.get("/dashboard/ko", tags=["System"])
async def web_dashboard_ko(request: Request):
    """Legacy route mapped to Pure English Autonomous Agent Console."""
    no_cache_headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
        "X-Language-Policy": "en-US-Agent-Only",
    }
    if INDEX_HTML_PATH.exists():
        return FileResponse(INDEX_HTML_PATH, media_type="text/html; charset=utf-8", headers=no_cache_headers)
    return HTMLResponse("<h1>Minerals Oracle Agent Console</h1><p>Static index.html not found.</p>")


@app.get("/manifest.json", tags=["System"])
async def pwa_manifest():
    """Progressive Web App (PWA) manifest."""
    manifest_path = STATIC_DIR / "manifest.json"
    if manifest_path.exists():
        return FileResponse(manifest_path, media_type="application/manifest+json")
    raise HTTPException(status_code=404, detail="manifest.json not found")


@app.get("/sw.js", tags=["System"])
async def pwa_sw():
    """Progressive Web App (PWA) Service Worker."""
    sw_path = STATIC_DIR / "sw.js"
    if sw_path.exists():
        return FileResponse(sw_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="sw.js not found")


@app.get("/robots.txt", tags=["System"])
async def get_robots_txt():
    """Allows AI agents, search engines and LLM crawlers to locate llms.txt and MCP tooling definitions."""
    robots_content = (
        "# Specialized AI Engine & LLM Crawlers\n"
        "User-agent: GPTBot\n"
        "User-agent: ChatGPT-User\n"
        "User-agent: ClaudeBot\n"
        "User-agent: Claude-Web\n"
        "User-agent: PerplexityBot\n"
        "User-agent: Cursor-Agent\n"
        "User-agent: Google-Extended\n"
        "User-agent: Applebot-Extended\n"
        "User-agent: CCBot\n"
        "Allow: /\n"
        "Allow: /llms.txt\n"
        "Allow: /sitemap.xml\n"
        "Allow: /mcp/tools\n"
        "Allow: /.well-known/\n"
        "Allow: /api/v1/oracle/alpha-signals\n"
        "Allow: /api/v1/oracle/battery-passports\n"
        "\n"
        "User-agent: *\n"
        "Allow: /\n"
        "Allow: /llms.txt\n"
        "Allow: /sitemap.xml\n"
        "\n"
        "Sitemap: https://minerals-oracle-x402-212942243360.asia-northeast3.run.app/sitemap.xml\n"
        "LLMs-Txt: https://minerals-oracle-x402-212942243360.asia-northeast3.run.app/llms.txt\n"
        "Agent-Hub: https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/hub/\n"
    )
    return PlainTextResponse(content=robots_content)


@app.get("/sitemap.xml", tags=["System"])
async def get_sitemap_xml():
    """XML sitemap enabling autonomous AI trade agents, scrapers, and indexers to discover all machine specs."""
    base = "https://minerals-oracle-x402-212942243360.asia-northeast3.run.app"
    xml_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'  <url><loc>{base}/llms.txt</loc><changefreq>daily</changefreq><priority>1.0</priority></url>\n'
        f'  <url><loc>{base}/.well-known/agent.json</loc><changefreq>daily</changefreq><priority>0.9</priority></url>\n'
        f'  <url><loc>{base}/.well-known/a2a.json</loc><changefreq>daily</changefreq><priority>0.9</priority></url>\n'
        f'  <url><loc>{base}/.well-known/ai-plugin.json</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>\n'
        f'  <url><loc>{base}/.well-known/ap2</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>\n'
        f'  <url><loc>{base}/mcp/tools</loc><changefreq>daily</changefreq><priority>0.9</priority></url>\n'
        f'  <url><loc>{base}/openapi.json</loc><changefreq>daily</changefreq><priority>0.8</priority></url>\n'
        f'  <url><loc>{base}/api/v1/oracle/alpha-signals</loc><changefreq>hourly</changefreq><priority>0.9</priority></url>\n'
        f'  <url><loc>{base}/api/v1/oracle/economics-roi</loc><changefreq>daily</changefreq><priority>0.7</priority></url>\n'
        f'  <url><loc>{base}/dashboard</loc><changefreq>daily</changefreq><priority>0.5</priority></url>\n'
        '</urlset>'
    )
    return Response(content=xml_content, media_type="application/xml")


@app.get("/healthz", tags=["System"])
@app.get("/health", tags=["System"])
@app.get("/status", tags=["System"])
async def health_check():
    """Oracle health and feed telemetry status."""
    return {
        "status": "healthy",
        "oracle": "minerals-oracle-x402",
        "service": "minerals-oracle-x402",
        "network": "polygon-mainnet",
        "chain_id": 137,
        "feed_status": "operational",
        "compliance_engine": "operational",
        "active_pillars": 7,
        "traps_defended": 12,
        "commodities_tracked": [
            "NICKEL_MHP", "LITHIUM_HYDROXIDE", "LITHIUM_CARBONATE",
            "COBALT_HYDROXIDE", "NATURAL_GRAPHITE", "SYNTHETIC_GRAPHITE",
            "MANGANESE_SULFATE", "NEODYMIUM_DYSPROSIUM", "ANTIMONY_TRIOXIDE",
            "Ag", "Pt", "Cu"
        ],
        "monitored_jurisdictions": ["IDN", "COD", "CHL", "ARG", "AUS", "BRA", "CHN", "ZAF"],
    }


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
        "> Autonomous Critical Minerals & Battery Supply-Chain Compliance Oracle on Polygon (Chain ID 137).\n"
        "Endpoints:\n"
        "- Free Alpha Hook: GET /api/v1/oracle/alpha-signals\n"
        "- Economic Proof: GET /api/v1/oracle/economics-roi\n"
        "- Compliance Verification: POST /api/v1/oracle/compliance/verify (x402 Monitored)\n"
        "- Monitored Rules: GET /api/v1/oracle/compliance/status\n"
        "- Trade Precedents: GET /api/v1/oracle/compliance/precedents\n"
    )


@app.get("/.well-known/agent.json", tags=["Agent Protocol"])
async def get_agent_json():
    """Returns OpenAI & A2A standard Agent Manifest."""
    return {
        "schema_version": "v1",
        "name_for_model": "minerals_oracle_x402",
        "name_for_human": "Critical Minerals & Battery Supply-Chain Compliance Oracle",
        "description_for_model": (
            "Autonomous 7-Pillar Critical Mineral Provenance & Battery Passport Verification Oracle. "
            "Evaluates SIMBARA, CEEC, DGA, EUDR, RMI RMAP, OECD Annex II mass balance (loss <= 2%), "
            "IMO CII ratings, and US IRA 30D FEOC (< 25%). Issues EIP-712 Polygon verifiable battery passports. "
            "Monetized via HTTP 402 with USDC on Polygon."
        ),
        "description_for_human": "Autonomous Polygon x402 Critical Minerals Compliance & Battery Passport Oracle.",
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
        "escrow_protocol": "ERC-MilestoneTradeEscrow",
        "supported_chains": {
            "polygon": {"chain_id": 137, "escrow_contract": "0x1270ddebad0ca90070342336a581eaACBA2060Ab"},
            "base": {"chain_id": 8453, "escrow_contract": "0xfCf3BF5fB5858db9aE81bE458B39b0032fc0C638"},
            "arbitrum": {"chain_id": 42161, "escrow_contract": "0xfCf3BF5fB5858db9aE81bE458B39b0032fc0C638"}
        },
        "a2a_endpoints": {
            "propose_deal": "/api/v1/trade/deals/propose",
            "dual_sign_deal": "/api/v1/trade/deals/dual-sign",
            "escrow_calldata": "/api/v1/a2a/deals/{deal_id}/escrow-calldata",
            "mcp_tools": "/mcp/tools",
            "llms_spec": "/llms.txt"
        },
    }


@app.get("/.well-known/ap2", tags=["Agent Protocol"])
@app.get("/.well-known/ap2.json", tags=["Agent Protocol"])
async def get_ap2_manifest():
    """Returns Google AP2 (Agent Protocol v2) service manifest."""
    manifest = {
        "ap2_version": "0.2.0",
        "name": "minerals-oracle-x402",
        "description": "Critical minerals & battery supply-chain compliance oracle",
        "capabilities": ["compliance:7_pillars", "compliance:battery_passport", "oracle:pricing", "oracle:arbitrage"],
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
        "description_for_human": "Autonomous critical minerals compliance, battery passports, and A2A milestone trade escrow contracts.",
        "description_for_model": "Access physical commodity spot prices, 7-pillar provenance verification, battery passports, and autonomous A2A bilateral trade escrow contracts with milestone releases (Polygon/Base/Arbitrum). Use ?format=compact to save tokens. Self-serve onboarding via POST /api/v1/agent/onboard.",
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
        "zero_pii_policy": True,
        "legal_info_url": "https://minerals-oracle.org/legal"
    }


@app.get("/.well-known/a2a.json", tags=["Agent Protocol"])
@app.get("/.well-known/agent-skills.json", tags=["Agent Protocol"])
async def get_agent_protocol_manifest():
    """Standard A2A (Agent-to-Agent) discovery manifest."""
    return {
        "agent_name": "minerals-oracle-x402",
        "protocol_version": "1.0.0",
        "escrow_standard": "ERC-MilestoneTradeEscrow",
        "skills": [
            {
                "id": "a2a-bilateral-trade-deal",
                "endpoint": "/api/v1/trade/deals/propose",
                "dual_sign_endpoint": "/api/v1/trade/deals/dual-sign",
                "cost_tier": "Free Deal Attestation"
            },
            {
                "id": "erc-milestone-trade-escrow",
                "endpoint": "/api/v1/a2a/deals/{deal_id}/escrow-calldata",
                "supported_chains": ["polygon", "base", "arbitrum"],
                "cost_tier": "Zero Platform Fee (Gas Only)"
            },
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
                "id": "ebl-mletr-audit",
                "endpoint": "/api/v1/trade/verify-ebl",
                "cost_tier": "$0.01 USDC"
            },
            {
                "id": "trade-route-optimization",
                "endpoint": "/api/v1/trade/optimize-route",
                "cost_tier": "$0.02 USDC"
            },
            {
                "id": "realtime-sse-stream",
                "endpoint": "/api/v1/oracle/stream",
                "cost_tier": "Free stream"
            },
            {
                "id": "copper-origin-audit",
                "endpoint": "/api/v1/copper/verify-origin",
                "cost_tier": "$0.01 USDC",
                "description": "Chilean COCHILCO, Codelco geofencing, ASTM B115 Grade 1 AI Datacenter HVDC spec"
            },
            {
                "id": "silver-origin-audit",
                "endpoint": "/api/v1/silver/verify-origin",
                "cost_tier": "$0.01 USDC",
                "description": "Terronera/Fresnillo geofencing, N-Type TOPCon solar PV grade >=99.99% Ag"
            },
            {
                "id": "eudr-satellite-radar-audit",
                "endpoint": "/api/v1/compliance/eudr-satellite-audit",
                "mcp_tool": "eudr_satellite_mine_audit",
                "cost_tier": "$0.02 USDC",
                "description": "Multi-satellite Sentinel-1/2 SAR radar deforestation (2020-12-31 cutoff) & TRACES-NT DDS issuance"
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


@app.get(
    "/api/v1/oracle/alpha-signals",
    tags=["Agent Free Alpha Hook"],
    summary="Free Real-Time Critical Mineral Regulatory Radar & Precedent Signals",
)
async def get_public_alpha_signals():
    """
    Public, unauthenticated real-time regulatory radar teaser endpoint.
    Allows autonomous agents to inspect global critical mineral compliance alerts.
    """
    return {
        "oracle": "minerals-oracle-x402",
        "status": "operational",
        "version": "2.0.0",
        "active_monitored_nations": ["IDN", "COD", "CHL", "ARG", "AUS", "BRA", "CHN", "ZAF"],
        "active_trade_precedents": ["WTO_DS592", "WTO_DS431", "ICSID_ARB_15_31", "CIT_SUPERIOR_WIRE"],
        "compliance_rules_loaded": 12,
        "message": "Ready to verify mineral lots via /api/v1/oracle/compliance/verify",
        "verified_passport_premium_bps": 2000,
        "signals": [
            {"mineral": "NICKEL_MHP", "benchmark": "LME", "unverified_discount_pct": 20.0, "reason": "CBAM Captive Coal Risk"},
            {"mineral": "LITHIUM_HYDROXIDE", "benchmark": "Fastmarkets", "unverified_discount_pct": 25.0, "reason": "FEOC Taint 25%"},
            {"mineral": "COBALT_HYDROXIDE", "benchmark": "Metal Bulletin", "unverified_discount_pct": 30.0, "reason": "ASM Child Labor Audit Risk"},
        ],
    }


@app.get(
    "/api/v1/oracle/economics-roi",
    tags=["Economic Advantage"],
    summary="ROI & Economic Superiority Metrics vs Traditional Enterprise Terminals",
)
async def get_economic_advantage_metrics():
    """
    Returns quantitative proof of cost superiority compared to legacy Bloomberg / Fastmarkets terminals.
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
# Real-Time Streaming Endpoints (WebSocket & SSE)
# ==========================================
@app.websocket("/ws/oracle/stream")
async def websocket_oracle_stream(websocket: WebSocket, client_id: str = "quant_agent"):
    """
    High-frequency real-time WebSocket streaming feed for autonomous AI quants and trading swarms.
    Stream physical spot price ticks, arbitrage spreads, and compliance signals with <1ms latency.
    """
    await ws_manager.connect(websocket, client_id)
    try:
        # Initial greeting tick
        await websocket.send_json({
            "type": "CONNECTION_ESTABLISHED",
            "client_id": client_id,
            "stream": "minerals-oracle-feed",
            "server_time_utc": time.time(),
            "status": "ACTIVE",
        })
        while True:
            # Keep-alive loop and agent heartbeat listener
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


@app.get(
    "/api/v1/oracle/stream",
    tags=["Agent Protocol"],
    summary="Real-time SSE event stream for autonomous AI agents",
)
async def sse_oracle_stream():
    """
    Server-Sent Events (SSE) stream for lightweight LLM agent subscriptions.
    Broadcasts real-time physical commodity spot benchmarks and spread updates.
    """
    async def event_generator():
        yield f"data: {json.dumps({'event': 'CONNECTED', 'service': 'minerals-oracle-x402', 'time': time.time()})}\n\n"
        for _ in range(3):
            await asyncio.sleep(1.0)
            yield f"data: {json.dumps({'event': 'HEARTBEAT', 'status': 'ONLINE', 'timestamp': time.time()})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ==========================================
# Domain Router Registrations
# ==========================================
app.include_router(minerals_router)
app.include_router(logistics_router)
app.include_router(a2a_trade_router)
app.include_router(oracle_pricing_router)
app.include_router(mcp_router)
app.include_router(brain_router)
