"""
Domain Routers Package for minerals-oracle-x402.
Modularized endpoints for Clean Architecture and rapid, decoupled agent interactions.
"""
from app.routers.minerals import router as minerals_router
from app.routers.a2a_trade import router as a2a_trade_router
from app.routers.logistics import router as logistics_router
from app.routers.oracle_pricing import router as oracle_pricing_router
from app.routers.mcp import router as mcp_router

__all__ = [
    "minerals_router",
    "a2a_trade_router",
    "logistics_router",
    "oracle_pricing_router",
    "mcp_router",
]
