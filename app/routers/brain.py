# -*- coding: utf-8 -*-
"""ElizaOS Brain & Security Gate x402 REST API Router
=====================================================
Exposes 4-tier cognitive perception, episodic immune defense, and sovereign execution endpoints:
- POST /api/v1/brain/perceive: Inbound perception shield & memory poisoning protection.
- POST /api/v1/brain/execute: Outbound hardened execution trace, EU AI Act Art. 50 watermark,
                              ephemeral sub-account air-gap, and RWA USDY yield allocation.
- GET  /api/v1/brain/diagnostics: Multi-tier cognitive memory stats, readiness score & immune memory metrics.
- POST /api/v1/brain/absorb-intelligence: Direct ingestion of daily market/EUDR reports.
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from app.modules.elizaos_brain_security_bridge import (
    ElizaOSBrainSecurityBridge,
    BrainPerceptionRequest,
    BrainExecutionRequest,
)

router = APIRouter(prefix="/api/v1/brain", tags=["ElizaOS Brain & Security Gate"])


@router.post("/perceive", summary="Inbound Perception Shield & Adversarial Defense")
async def perceive_and_filter(req: BrainPerceptionRequest) -> Dict[str, Any]:
    """Inspects inbound prompts, AST syntax, and financial proposals for prompt injection,

    jailbreaks, and memory poisoning before passing them into working episodic memory.
    """
    try:
        verdict = ElizaOSBrainSecurityBridge.perceive_and_filter(req)
        return verdict
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Perception engine error: {str(exc)}")


@router.post("/execute", summary="Outbound Hardened Execution & Capital Air-Gap")
async def evaluate_and_execute(req: BrainExecutionRequest) -> Dict[str, Any]:
    """Evaluates metallurgical plausibility, provisions ephemeral sub-accounts ($1~$5 micro-cap),

    applies EU AI Act Art. 50 watermark, and yields EIP-712 truth attestation for dynamic escrow.
    """
    try:
        result = ElizaOSBrainSecurityBridge.evaluate_and_execute_action(req)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Execution engine error: {str(exc)}")


@router.get("/diagnostics", summary="Brain Cognitive & Immune Diagnostics")
async def get_brain_diagnostics() -> Dict[str, Any]:
    """Returns real-time 4-tier architecture statistics, cognitive readiness score,

    working/episodic memory depth, and neutralized immune fingerprints.
    """
    return ElizaOSBrainSecurityBridge.get_diagnostics()


@router.post("/absorb-intelligence", summary="Absorb Market & Regulatory Intelligence")
async def absorb_intelligence(payload: Dict[str, str]) -> Dict[str, Any]:
    """Ingests daily intelligence report text and updates cognitive baseline."""
    text = payload.get("content", "")
    date_str = payload.get("date", "")
    if not text:
        raise HTTPException(status_code=400, detail="Missing report 'content'")
    return ElizaOSBrainSecurityBridge.absorb_daily_intelligence(text, date_str)

