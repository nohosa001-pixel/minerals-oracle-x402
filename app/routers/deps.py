"""
Shared dependencies and metadata helpers for Domain Routers.
"""
import asyncio
from typing import Optional
from fastapi import Request
from app.schemas import PricingTier, ResponseMeta
from app.x402_verifier import x402_verifier

STANDARD_DISCLAIMER_META = ResponseMeta().model_dump()


async def require_x402_payment(request: Request, tier: PricingTier = PricingTier.STANDARD):
    """Enforces x402 payment authorization, pre-funded vault balance, or Sandbox Free Tier."""
    req_chain = (
        request.headers.get("X-Payment-Chain")
        or request.headers.get("X-402-Chain")
        or request.headers.get("X-Chain-ID")
        or request.query_params.get("chain")
        or "polygon"
    )
    is_authorized, reason, extra_headers = await asyncio.to_thread(
        x402_verifier.verify_request_payment, request, tier=tier
    )
    if not is_authorized:
        detail_msg = reason if (reason and ("Insufficient" in str(reason) or "not found" in str(reason))) else None
        return x402_verifier.build_402_response(tier=tier, chain_name=req_chain, custom_detail=detail_msg)
    request.state.authorized_payer = reason
    request.state.extra_headers = extra_headers or {}
    return None
