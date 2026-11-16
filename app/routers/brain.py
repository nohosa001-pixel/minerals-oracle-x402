# -*- coding: utf-8 -*-
"""ElizaOS Brain & Security Gate x402 REST API Router
=====================================================
Exposes 4-tier cognitive perception, episodic immune defense, and sovereign execution endpoints:
- GET  /api/v1/brain/status: Real-time server-native daemon & cognitive engine status.
- GET  /api/v1/brain/heartbeat: 30-day continuous learning heartbeat and readiness telemetry.
- POST /api/v1/brain/trigger-cycle: Immediate manual/cron trigger of learning & defense cycle.
- POST /api/v1/brain/perceive: Inbound perception shield & memory poisoning protection.
- POST /api/v1/brain/execute: Outbound hardened execution trace, EU AI Act Art. 50 watermark,
                              ephemeral sub-account air-gap, and RWA USDY yield allocation.
- GET  /api/v1/brain/diagnostics: Multi-tier cognitive memory stats, readiness score & immune memory metrics.
- POST /api/v1/brain/absorb-intelligence: Direct ingestion of daily market/EUDR reports.
"""

import json
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends

from app.modules.elizaos_brain_security_bridge import (
    ElizaOSBrainSecurityBridge,
    BrainPerceptionRequest,
    BrainExecutionRequest,
)
from app.modules.autonomous_brain_daemon import brain_daemon

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HEARTBEAT_FILE = PROJECT_ROOT / "data" / "minerals_brain_30day_heartbeat.json"

router = APIRouter(prefix="/api/v1/brain", tags=["ElizaOS Brain & Security Gate"])


@router.get("/status", summary="Server-Native ElizaOS Brain Status")
async def get_brain_status() -> Dict[str, Any]:
    """Returns the live status of the server-native ElizaOS Brain daemon,
    including current day of 30-day learning, memory telemetry, and readiness.
    """
    return brain_daemon.get_live_status()


@router.get("/heartbeat", summary="Brain 30-Day Learning Heartbeat")
async def get_brain_heartbeat() -> Dict[str, Any]:
    """Returns persistent 30-day learning heartbeat data recorded on server."""
    if HEARTBEAT_FILE.exists():
        try:
            return json.loads(HEARTBEAT_FILE.read_text(encoding="utf-8"))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to read heartbeat: {exc}")
    # Return synthetic live fallback if file not yet written
    return brain_daemon.get_live_status()


@router.post("/trigger-cycle", summary="Trigger Immediate Server Learning Cycle")
async def trigger_learning_cycle() -> Dict[str, Any]:
    """Manually triggers a shadow learning and adversarial hardening cycle on the server."""
    try:
        hb_data = brain_daemon.execute_learning_cycle()
        return {
            "status": "SUCCESS",
            "message": "Learning cycle executed successfully on server.",
            "heartbeat": hb_data,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Cycle execution failed: {str(exc)}")


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
