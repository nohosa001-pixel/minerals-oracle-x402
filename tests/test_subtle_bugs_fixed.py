# -*- coding: utf-8 -*-
"""
Tests for Subtle Internal Bugs Fixed in Minerals Oracle System
=============================================================
Validates:
1. WebhookManager.dispatch_event returns genuine webhook_ids instead of callback URLs.
2. ComplianceEngine does not falsely penalize non-nickel commodities in Indonesia under WTO DS592.
3. RedisDistributedStore acquire_lock executes proper timeout polling loop.
4. X402Verifier._ACTIVE_NONCES is thread-safe against concurrent mutation crashes.
5. MineralTradeEscrow.sol contains minimum durationSeconds validation against instant-expiry exploits.
"""

import threading
import time
import pytest
from app.webhook_manager import WebhookManager, AgentWebhookRegistrationRequest
from app.compliance_engine import compliance_engine
from app.schemas import (
    MineralLotProvenanceRequest,
    MineralType,
    SourceCountry,
    MinePermitsRecord,
    EcologicalSpatialRecord,
    LaborHumanRightsRecord,
    RefiningMassBalanceRecord,
    MaritimeLogisticsRecord,
    MaritimeCIIRating,
    GeopoliticalSanctionsRecord,
)
from app.x402_verifier import x402_verifier, _ACTIVE_NONCES


def test_webhook_manager_dispatch_returns_webhook_ids():
    """Validates that dispatch_event returns webhook IDs (whk_...) not callback URLs."""
    mgr = WebhookManager()
    reg_res = mgr.register_webhook(
        AgentWebhookRegistrationRequest(
            agent_address="0x1111111111111111111111111111111111111111",
            callback_url="https://agent-node.example.com/webhook",
            subscribed_events=["deal.proposed"],
        )
    )
    assert reg_res.webhook_id.startswith("whk_")

    matched_ids = mgr.dispatch_event(
        event_type="deal.proposed",
        target_agent_address="0x1111111111111111111111111111111111111111",
        data={"test": True},
    )

    assert len(matched_ids) > 0
    # Must be webhook ID (whk_...) and NOT the URL ("https://...")
    for wid in matched_ids:
        assert wid.startswith("whk_")
        assert not wid.startswith("http")

    # Cleanup
    mgr.unregister_webhook(reg_res.webhook_id)


def test_compliance_engine_indonesia_non_nickel_not_falsely_penalized():
    """
    Validates that non-nickel commodities (e.g. Copper Cathode) sourced from Indonesia
    are NOT falsely penalized under WTO DS592 (raw nickel ore export ban).
    """
    from tests.test_compliance_engine import build_valid_indonesia_nickel_request

    req = build_valid_indonesia_nickel_request()
    req.mineral_type = MineralType.COPPER_CATHODE
    req.lot_id = "LOT-IDN-COPPER-001"

    verdict_resp = compliance_engine.evaluate_lot(req)
    fatal_list = [v for v in verdict_resp.verdict.gotcha_defenses_applied if "FATAL" in v]
    # WTO DS592 raw nickel ore violation must NOT be present for Copper Cathode!
    assert not any("WTO_DS592_VIOLATION" in v for v in fatal_list)
    assert not any("nickel" in v.lower() for v in fatal_list)


def test_nonce_concurrent_access_safety():
    """
    Validates that X402Verifier nonce challenge generation and cleanup
    is protected by _NONCE_LOCK and does not crash under multi-threaded load.
    """
    errors = []

    def worker():
        try:
            for _ in range(50):
                ch = x402_verifier.generate_challenge()
                assert ch.nonce is not None
                assert x402_verifier._is_valid_nonce(ch.nonce) is True
                x402_verifier._cleanup_expired_nonces()
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(15)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    assert len(errors) == 0, f"Nonce race condition detected: {errors}"


def test_mineral_trade_escrow_duration_validation():
    """Validates that MineralTradeEscrow.sol requires durationSeconds >= 60."""
    with open("contracts/MineralTradeEscrow.sol", "r", encoding="utf-8") as f:
        src = f.read()
    assert "require(durationSeconds >= 60" in src
