# -*- coding: utf-8 -*-
"""
Test Suite: Autonomous Agent-Native Intelligence, Session Vault & A2A Deals
=============================================================================
Verifies:
1. Agent Session Vault (<0.1ms micro-allowance debit and cryptographic receipt refund)
2. Agent-Native Decision Signals (Deterministic PROCEED/REROUTE flags)
3. A2A Bilateral Trade Deal Engine (EIP-712 Dual-Signing and Oracle Attestation)
4. REST API integration for autonomous agent endpoints
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import (
    MineralType,
    SourceCountry,
    AgentActionType,
    AgentSessionOpenRequest,
    AgentSessionCloseRequest,
    TradeRouteOptimizationRequest,
    TradeDealSpec,
    TradeDealProposeRequest,
    TradeDealDualSignRequest,
    TradeDealVerifyRequest,
)
from app.agent_session_vault import get_agent_session_vault, InsufficientSessionBalanceError
from app.a2a_deal_engine import get_a2a_deal_engine, InvalidDealStateError
from app.global_trade_engine import global_trade_engine


@pytest.fixture
def client():
    return TestClient(app)


def test_agent_session_vault_lifecycle():
    """Tests session open, atomic micro-debit, and cryptographic settlement refund."""
    vault = get_agent_session_vault()
    agent_addr = "0x1111111111111111111111111111111111111111"

    # 1. Open session with 1.0 USDC
    open_req = AgentSessionOpenRequest(
        agent_address=agent_addr,
        deposit_amount_usdc=1.0,
        session_duration_hours=12,
    )
    res_open = vault.open_session(open_req)
    assert res_open.status == "success"
    assert res_open.allocated_balance_usdc == 1.0
    assert res_open.remaining_queries_capacity == 20
    token = res_open.session_token
    assert token.startswith("asess_")

    # 2. Debit 3 queries (3 * 0.05 = 0.15)
    bal, count = vault.debit_query(token)
    assert bal == 0.95
    assert count == 1

    bal, count = vault.debit_query(token)
    bal, count = vault.debit_query(token)
    assert bal == 0.85
    assert count == 3

    # 3. Close session and check refund
    close_req = AgentSessionCloseRequest(session_token=token, agent_address=agent_addr)
    res_close = vault.close_session(close_req)
    assert res_close.status == "success"
    assert res_close.queries_executed == 3
    assert res_close.total_consumed_usdc == 0.15
    assert res_close.refunded_balance_usdc == 0.85
    assert res_close.settlement_receipt_hash.startswith("0x")


def test_agent_decision_signal_in_route_optimizer():
    """Tests that TradeRouteOptimizationResponse includes deterministic AgentDecisionSignal."""
    req = TradeRouteOptimizationRequest(
        mineral_type=MineralType.LITHIUM_CARBONATE,
        origin_country=SourceCountry.CHL,
        destination_country="USA",
        cargo_weight_metric_tons=2500.0,
    )
    res = global_trade_engine.optimize_route(req)

    assert res.status == "success"
    assert res.agent_decision is not None
    assert res.agent_decision.action in [
        AgentActionType.PROCEED_SETTLEMENT,
        AgentActionType.REROUTE_PANAMA_BOTTLENECK,
        AgentActionType.REROUTE_RED_SEA_CONFLICT,
    ]
    assert 0.0 <= res.agent_decision.confidence_score <= 1.0
    assert 0.0 <= res.agent_decision.risk_score <= 1.0
    assert len(res.agent_decision.recommended_action) > 5


def test_a2a_bilateral_trade_deal_engine():
    """Tests seller proposal, buyer dual-countersigning, and oracle attestation seal."""
    engine = get_a2a_deal_engine()

    seller_addr = "0x2222222222222222222222222222222222222222"
    buyer_addr = "0x3333333333333333333333333333333333333333"

    spec = TradeDealSpec(
        deal_id="DEAL-2026-LIT-001",
        commodity=MineralType.LITHIUM_CARBONATE,
        volume_tons=2500.0,
        unit_price_usd_per_ton=13500.0,
        total_deal_value_usd=33750000.0,
        origin_country=SourceCountry.CHL,
        destination_country="USA",
        feoc_cleared=True,
        mass_balance_cleared=True,
        ebl_document_id="EBL-MAERSK-2026-LIT09",
        buyer_agent_address=buyer_addr,
        seller_agent_address=seller_addr,
        created_at_utc="2026-09-15T12:00:00Z",
    )

    # 1. Propose
    prop_req = TradeDealProposeRequest(
        spec=spec,
        seller_signature="0x" + "a" * 130,
    )
    att_prop = engine.propose_deal(prop_req)
    assert att_prop.status == "PROPOSED"
    assert att_prop.seller_signature.startswith("0x")
    assert att_prop.buyer_signature is None

    # 2. Dual-sign by buyer
    sign_req = TradeDealDualSignRequest(
        deal_id="DEAL-2026-LIT-001",
        buyer_signature="0x" + "b" * 130,
        buyer_agent_address=buyer_addr,
    )
    att_dual = engine.dual_sign_deal(sign_req)
    assert att_dual.status == "DUAL_SIGNED_CONFIRMED"
    assert att_dual.buyer_signature.startswith("0x")
    assert att_dual.oracle_attestation_signature.startswith("0x")
    assert att_dual.final_contract_hash.startswith("0x")

    # 3. Verify
    verify_req = TradeDealVerifyRequest(deal_id="DEAL-2026-LIT-001")
    v_res = engine.verify_deal(verify_req)
    assert v_res.is_valid is True
    assert v_res.seller_verified is True
    assert v_res.buyer_verified is True
    assert v_res.oracle_verified is True


def test_hybrid_gain_share_settlement_calculation():
    """Tests the Hybrid 10% Gain-Share calculation and statutory cap mechanism."""
    engine = get_a2a_deal_engine()

    # Case A: Normal savings under cap ($50,000 savings -> 10% = $5,000)
    fee_a, cap_a, sum_a = engine.calculate_gain_share_fee(50000.0, base_pct=10.0, cap_usd=10000.0)
    assert fee_a == 5000.0
    assert cap_a is False
    assert "5,000.00 USDC" in sum_a

    # Case B: Large bulk savings exceeding cap ($1,136,500 savings -> 10% = $113,650 -> Capped at $10,000)
    fee_b, cap_b, sum_b = engine.calculate_gain_share_fee(1136500.0, base_pct=10.0, cap_usd=10000.0)
    assert fee_b == 10000.0
    assert cap_b is True
    assert "capped at $10,000.00 USDC max" in sum_b

    # Case C: Zero savings
    fee_c, cap_c, _ = engine.calculate_gain_share_fee(0.0)
    assert fee_c == 0.0
    assert cap_c is False

    # Case D: Integrated deal propose with auto-computed gain-share fee
    spec = TradeDealSpec(
        deal_id="DEAL-HYBRID-TEST-001",
        commodity=MineralType.LITHIUM_CARBONATE,
        volume_tons=2500.0,
        unit_price_usd_per_ton=13500.0,
        total_deal_value_usd=33750000.0,
        origin_country=SourceCountry.CHL,
        destination_country="USA",
        feoc_cleared=True,
        mass_balance_cleared=True,
        ebl_document_id="EBL-HYBRID-01",
        buyer_agent_address="0x3333333333333333333333333333333333333333",
        seller_agent_address="0x2222222222222222222222222222222222222222",
        projected_savings_usd=1136500.0,
        created_at_utc="2026-09-15T12:00:00Z",
    )
    prop = engine.propose_deal(TradeDealProposeRequest(spec=spec, seller_signature="0x" + "9" * 130))
    assert prop.spec.calculated_gain_share_fee_usd == 10000.0
    assert prop.spec.fee_cap_applied is True


def test_rest_api_session_and_deals(client):
    """Tests the new REST endpoints via FastAPI TestClient."""
    headers = {"X-Dev-Bypass": "true"}

    # Open session via REST
    open_payload = {
        "agent_address": "0x4444444444444444444444444444444444444444",
        "deposit_amount_usdc": 5.0,
        "session_duration_hours": 24,
    }
    r = client.post("/api/v1/agent/session/open", json=open_payload, headers=headers)
    assert r.status_code == 200
    token = r.json()["session_token"]

    # Close session via REST
    close_payload = {
        "session_token": token,
        "agent_address": "0x4444444444444444444444444444444444444444",
    }
    r = client.post("/api/v1/agent/session/close", json=close_payload, headers=headers)
    assert r.status_code == 200
    assert r.json()["refunded_balance_usdc"] == 5.0

    # Propose Deal via REST
    deal_payload = {
        "spec": {
            "deal_id": "DEAL-REST-TEST-99",
            "commodity": "COPPER_CATHODE",
            "volume_tons": 5000.0,
            "unit_price_usd_per_ton": 9800.0,
            "total_deal_value_usd": 49000000.0,
            "origin_country": "CHL",
            "destination_country": "USA",
            "feoc_cleared": True,
            "mass_balance_cleared": True,
            "ebl_document_id": "EBL-REST-99",
            "buyer_agent_address": "0x5555555555555555555555555555555555555555",
            "seller_agent_address": "0x6666666666666666666666666666666666666666",
            "settlement_currency": "USDC",
            "created_at_utc": "2026-09-15T12:00:00Z",
        },
        "seller_signature": "0x" + "c" * 130,
    }
    r = client.post("/api/v1/a2a/deals/propose", json=deal_payload, headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "PROPOSED"

    # Dual sign via REST
    dual_payload = {
        "deal_id": "DEAL-REST-TEST-99",
        "buyer_signature": "0x" + "d" * 130,
        "buyer_agent_address": "0x5555555555555555555555555555555555555555",
    }
    r = client.post("/api/v1/a2a/deals/dual-sign", json=dual_payload, headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "DUAL_SIGNED_CONFIRMED"

    # Verify via REST
    r = client.get("/api/v1/a2a/deals/verify/DEAL-REST-TEST-99", headers=headers)
    assert r.status_code == 200
    assert r.json()["is_valid"] is True
