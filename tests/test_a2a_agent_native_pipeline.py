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
    TradeDealRejectRequest,
    TradeDealCancelRequest,
    TradeDealDualSignRequest,
    TradeDealVerifyRequest,
)
from eth_account import Account
from eth_account.messages import encode_defunct
from app.agent_session_vault import get_agent_session_vault, InsufficientSessionBalanceError
from app.a2a_deal_engine import (
    get_a2a_deal_engine,
    InvalidDealStateError,
    DealExpiredError,
    InvalidSignatureError,
)
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
    assert att_dual.buyer_signature is not None
    assert att_dual.buyer_signature.startswith("0x")
    assert att_dual.oracle_attestation_signature is not None
    assert att_dual.oracle_attestation_signature.startswith("0x")
    assert att_dual.final_contract_hash is not None
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


def test_a2a_signature_verification_security():
    """Verifies that authentic Web3 ECDSA signatures pass and spoofed signatures are strictly blocked."""
    engine = get_a2a_deal_engine()
    seller_acc = Account.create()
    buyer_acc = Account.create()
    hacker_acc = Account.create()

    spec = TradeDealSpec(
        deal_id="DEAL-SEC-SIG-001",
        commodity=MineralType.LITHIUM_CARBONATE,
        volume_tons=100.0,
        unit_price_usd_per_ton=13000.0,
        total_deal_value_usd=1300000.0,
        origin_country=SourceCountry.CHL,
        destination_country="USA",
        feoc_cleared=True,
        mass_balance_cleared=True,
        ebl_document_id="EBL-SEC-01",
        buyer_agent_address=buyer_acc.address,
        seller_agent_address=seller_acc.address,
        created_at_utc="2026-09-15T12:00:00Z",
    )
    deal_hash = engine.compute_deal_hash(spec)

    # 1. Impersonated seller signature fails
    fake_seller_sig = hacker_acc.sign_message(encode_defunct(hexstr=deal_hash)).signature.hex()
    with pytest.raises(InvalidSignatureError):
        engine.propose_deal(TradeDealProposeRequest(spec=spec, seller_signature="0x" + fake_seller_sig))

    # 2. Legitimate seller signature succeeds
    real_seller_sig = seller_acc.sign_message(encode_defunct(hexstr=deal_hash)).signature.hex()
    prop = engine.propose_deal(TradeDealProposeRequest(spec=spec, seller_signature="0x" + real_seller_sig))
    assert prop.status == "PROPOSED"

    # 3. Impersonated buyer signature fails on countersign
    fake_buyer_sig = hacker_acc.sign_message(encode_defunct(hexstr=deal_hash)).signature.hex()
    with pytest.raises(InvalidSignatureError):
        engine.dual_sign_deal(TradeDealDualSignRequest(
            deal_id="DEAL-SEC-SIG-001",
            buyer_signature="0x" + fake_buyer_sig,
            buyer_agent_address=buyer_acc.address,
        ))

    # 4. Legitimate buyer signature succeeds
    real_buyer_sig = buyer_acc.sign_message(encode_defunct(hexstr=deal_hash)).signature.hex()
    dual = engine.dual_sign_deal(TradeDealDualSignRequest(
        deal_id="DEAL-SEC-SIG-001",
        buyer_signature="0x" + real_buyer_sig,
        buyer_agent_address=buyer_acc.address,
    ))
    assert dual.status == "DUAL_SIGNED_CONFIRMED"


def test_a2a_deal_expiration_and_ttl():
    """Verifies that expired proposals cannot be countersigned (prevents arbitrage attacks)."""
    engine = get_a2a_deal_engine()
    spec = TradeDealSpec(
        deal_id="DEAL-EXPIRED-TEST-002",
        commodity=MineralType.COPPER_CATHODE,
        volume_tons=500.0,
        unit_price_usd_per_ton=9500.0,
        total_deal_value_usd=4750000.0,
        origin_country=SourceCountry.CHL,
        destination_country="USA",
        feoc_cleared=True,
        mass_balance_cleared=True,
        ebl_document_id="EBL-EXP-02",
        buyer_agent_address="0x8888888888888888888888888888888888888888",
        seller_agent_address="0x7777777777777777777777777777777777777777",
        expires_at_utc="2020-01-01T00:00:00Z",  # Already expired
        created_at_utc="2020-01-01T00:00:00Z",
    )
    engine.propose_deal(TradeDealProposeRequest(spec=spec, seller_signature="0x" + "7" * 130))

    with pytest.raises(DealExpiredError):
        engine.dual_sign_deal(TradeDealDualSignRequest(
            deal_id="DEAL-EXPIRED-TEST-002",
            buyer_signature="0x" + "8" * 130,
            buyer_agent_address="0x8888888888888888888888888888888888888888",
        ))


def test_a2a_rejection_and_cancellation_lifecycle():
    """Verifies full rejection and revocation state machine."""
    engine = get_a2a_deal_engine()

    # 1. Test Rejection
    spec_a = TradeDealSpec(
        deal_id="DEAL-REJECT-TEST-003",
        commodity=MineralType.LITHIUM_CARBONATE,
        volume_tons=100.0,
        unit_price_usd_per_ton=14000.0,
        total_deal_value_usd=1400000.0,
        origin_country=SourceCountry.CHL,
        destination_country="USA",
        ebl_document_id="EBL-REJ-01",
        buyer_agent_address="0x8888888888888888888888888888888888888888",
        seller_agent_address="0x7777777777777777777777777777777777777777",
        created_at_utc="2026-09-15T12:00:00Z",
    )
    engine.propose_deal(TradeDealProposeRequest(spec=spec_a, seller_signature="0x" + "7" * 130))
    rej = engine.reject_deal(TradeDealRejectRequest(
        deal_id="DEAL-REJECT-TEST-003",
        buyer_agent_address="0x8888888888888888888888888888888888888888",
        rejection_reason="SPOT_MARKET_PRICE_DROPPED_15_PERCENT",
    ))
    assert rej.status == "REJECTED"
    assert rej.audit_notes is not None
    assert "SPOT_MARKET_PRICE_DROPPED" in rej.audit_notes

    # Cannot dual-sign rejected deal
    with pytest.raises(InvalidDealStateError):
        engine.dual_sign_deal(TradeDealDualSignRequest(
            deal_id="DEAL-REJECT-TEST-003",
            buyer_signature="0x" + "8" * 130,
            buyer_agent_address="0x8888888888888888888888888888888888888888",
        ))

    # 2. Test Cancellation
    spec_b = TradeDealSpec(
        deal_id="DEAL-CANCEL-TEST-004",
        commodity=MineralType.NICKEL_MHP,
        volume_tons=200.0,
        unit_price_usd_per_ton=15000.0,
        total_deal_value_usd=3000000.0,
        origin_country=SourceCountry.IDN,
        destination_country="USA",
        ebl_document_id="EBL-CAN-01",
        buyer_agent_address="0x8888888888888888888888888888888888888888",
        seller_agent_address="0x7777777777777777777777777777777777777777",
        created_at_utc="2026-09-15T12:00:00Z",
    )
    engine.propose_deal(TradeDealProposeRequest(spec=spec_b, seller_signature="0x" + "7" * 130))
    canc = engine.cancel_deal(TradeDealCancelRequest(
        deal_id="DEAL-CANCEL-TEST-004",
        seller_agent_address="0x7777777777777777777777777777777777777777",
        cancellation_reason="VESSEL_CARGO_REALLOCATED",
    ))
    assert canc.status == "CANCELLED"
    assert canc.audit_notes is not None
    assert "VESSEL_CARGO_REALLOCATED" in canc.audit_notes


def test_agent_session_query_and_concurrency(client):
    """Verifies non-debiting session query API and thread-safe concurrent debiting."""
    import concurrent.futures

    vault = get_agent_session_vault()
    agent_addr = "0x9999999999999999999999999999999999999999"

    # Open session with 2.0 USDC (40 queries)
    open_res = vault.open_session(AgentSessionOpenRequest(agent_address=agent_addr, deposit_amount_usdc=2.0))
    token = open_res.session_token

    # Query without debiting via REST API
    r = client.get(f"/api/v1/agent/session/{token}", headers={"X-Dev-Bypass": "true"})
    assert r.status_code == 200
    assert r.json()["current_balance_usdc"] == 2.0
    assert r.json()["remaining_queries_capacity"] == 40
    assert r.json()["status_label"] == "ACTIVE"

    # Run 10 parallel debits across threads
    def worker_debit():
        return vault.debit_query(token)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(worker_debit) for _ in range(10)]
        results = [f.result() for f in futures]

    assert len(results) == 10
    final_info = vault.get_session_info_model(token)
    # 2.0 - (10 * 0.05) = 1.50
    assert final_info.current_balance_usdc == 1.50
    assert final_info.queries_executed == 10


def test_mcp_session_and_deal_lifecycle_tools(client):
    """Verifies MCP invocation router handles open_agent_session, get_agent_session_info, and get_a2a_trade_deal."""
    headers = {"X-Dev-Bypass": "true"}

    # 1. open_agent_session via MCP invoke
    req_open = {
        "name": "open_agent_session",
        "arguments": {
            "agent_address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "deposit_amount_usdc": 10.0,
            "session_duration_hours": 24,
        }
    }
    r = client.post("/mcp/invoke", json=req_open, headers=headers)
    assert r.status_code == 200
    assert not r.json()["isError"]
    import json
    data = json.loads(r.json()["content"][0]["text"])
    assert data["status"] == "success"
    session_token = data["session_token"]

    # 2. get_agent_session_info via MCP invoke
    req_info = {
        "name": "get_agent_session_info",
        "arguments": {"session_token": session_token}
    }
    r = client.post("/mcp/invoke", json=req_info, headers=headers)
    assert r.status_code == 200
    assert not r.json()["isError"]
    info_data = json.loads(r.json()["content"][0]["text"])
    assert info_data["current_balance_usdc"] == 10.0

    # 3. close_agent_session via MCP invoke
    req_close = {
        "name": "close_agent_session",
        "arguments": {
            "session_token": session_token,
            "agent_address": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        }
    }
    r = client.post("/mcp/invoke", json=req_close, headers=headers)
    assert r.status_code == 200
    assert not r.json()["isError"]
    close_data = json.loads(r.json()["content"][0]["text"])
    assert close_data["refunded_balance_usdc"] == 10.0


def test_adversarial_deal_overwrite_prevention():
    """Adversarial Test: Rogue agent attempts to overwrite/hijack an existing deal."""
    engine = get_a2a_deal_engine()
    spec1 = TradeDealSpec(
        deal_id="DEAL-ADV-OVERWRITE-01",
        commodity=MineralType.LITHIUM_CARBONATE,
        volume_tons=10.0,
        unit_price_usd_per_ton=10000.0,
        total_deal_value_usd=100000.0,
        origin_country=SourceCountry.CHL,
        destination_country="USA",
        feoc_cleared=True,
        mass_balance_cleared=True,
        ebl_document_id="EBL-01",
        buyer_agent_address="0x1111111111111111111111111111111111111111",
        seller_agent_address="0x2222222222222222222222222222222222222222",
        created_at_utc="2026-09-15T12:00:00Z",
    )
    engine.propose_deal(TradeDealProposeRequest(spec=spec1, seller_signature="0x" + "7" * 130))

    # Attacker tries to propose deal with same ID
    spec_hack = TradeDealSpec(
        deal_id="DEAL-ADV-OVERWRITE-01",
        commodity=MineralType.COPPER_CATHODE,
        volume_tons=50.0,
        unit_price_usd_per_ton=9000.0,
        total_deal_value_usd=450000.0,
        origin_country=SourceCountry.CHL,
        destination_country="USA",
        feoc_cleared=True,
        mass_balance_cleared=True,
        ebl_document_id="EBL-HACK",
        buyer_agent_address="0x3333333333333333333333333333333333333333",
        seller_agent_address="0x4444444444444444444444444444444444444444",
        created_at_utc="2026-09-15T12:00:00Z",
    )
    with pytest.raises(InvalidDealStateError, match="already exists"):
        engine.propose_deal(TradeDealProposeRequest(spec=spec_hack, seller_signature="0x" + "7" * 130))


def test_adversarial_wash_trading_prevention():
    """Adversarial Test: Sybil agent attempts wash-trading with identical buyer/seller addresses."""
    engine = get_a2a_deal_engine()
    same_addr = "0x9999999999999999999999999999999999999999"
    spec_wash = TradeDealSpec(
        deal_id="DEAL-ADV-WASH-01",
        commodity=MineralType.NICKEL_MHP,
        volume_tons=20.0,
        unit_price_usd_per_ton=18000.0,
        total_deal_value_usd=360000.0,
        origin_country=SourceCountry.IDN,
        destination_country="KOR",
        feoc_cleared=True,
        mass_balance_cleared=True,
        ebl_document_id="EBL-WASH-01",
        buyer_agent_address=same_addr,
        seller_agent_address=same_addr,
        created_at_utc="2026-09-15T12:00:00Z",
    )
    with pytest.raises(InvalidDealStateError, match="Self-dealing detected"):
        engine.propose_deal(TradeDealProposeRequest(spec=spec_wash, seller_signature="0x" + "7" * 130))


def test_adversarial_mathematical_fraud_detection():
    """Adversarial Test: Agent proposes mismatched total deal value to manipulate settlement."""
    engine = get_a2a_deal_engine()
    spec_math_fraud = TradeDealSpec(
        deal_id="DEAL-ADV-MATH-01",
        commodity=MineralType.COBALT_HYDROXIDE,
        volume_tons=100.0,
        unit_price_usd_per_ton=28000.0,
        total_deal_value_usd=10.0,  # Blatant fraud: Should be $2,800,000.00
        origin_country=SourceCountry.COD,
        destination_country="USA",
        feoc_cleared=True,
        mass_balance_cleared=True,
        ebl_document_id="EBL-FRAUD-01",
        buyer_agent_address="0x1111111111111111111111111111111111111111",
        seller_agent_address="0x2222222222222222222222222222222222222222",
        created_at_utc="2026-09-15T12:00:00Z",
    )
    with pytest.raises(InvalidDealStateError, match="Mathematical discrepancy"):
        engine.propose_deal(TradeDealProposeRequest(spec=spec_math_fraud, seller_signature="0x" + "7" * 130))


def test_adversarial_gain_share_fee_evasion_mitigation():
    """Adversarial Test: Agent attempts to evade 10% gain-share fee by declaring $0.01 fee."""
    engine = get_a2a_deal_engine()
    spec_evasion = TradeDealSpec(
        deal_id="DEAL-ADV-EVASION-01",
        commodity=MineralType.LITHIUM_CARBONATE,
        volume_tons=50.0,
        unit_price_usd_per_ton=20000.0,
        total_deal_value_usd=1000000.0,
        origin_country=SourceCountry.CHL,
        destination_country="USA",
        feoc_cleared=True,
        mass_balance_cleared=True,
        ebl_document_id="EBL-EVASION-01",
        buyer_agent_address="0x1111111111111111111111111111111111111111",
        seller_agent_address="0x2222222222222222222222222222222222222222",
        projected_savings_usd=50000.0,
        gain_share_rate_pct=10.0,
        calculated_gain_share_fee_usd=0.01,  # Evasion bypass attempt!
        created_at_utc="2026-09-15T12:00:00Z",
    )
    att = engine.propose_deal(TradeDealProposeRequest(spec=spec_evasion, seller_signature="0x" + "7" * 130))
    # Oracle must correct and strictly enforce 10% ($5,000.00)
    assert att.spec.calculated_gain_share_fee_usd == 5000.0
    assert att.spec.hybrid_settlement_summary is not None
    assert "HYBRID_GAIN_SHARE: 10.0%" in att.spec.hybrid_settlement_summary


def test_adversarial_session_vault_double_refund_exploit():
    """Adversarial Test: Agent attempts double-refund / replay exploit on AgentSessionVault."""
    vault = get_agent_session_vault()
    agent_addr = "0x7777777777777777777777777777777777777777"
    sess = vault.open_session(AgentSessionOpenRequest(
        agent_address=agent_addr,
        deposit_amount_usdc=25.0,
        session_duration_hours=12,
    ))
    token = sess.session_token

    # First close -> legitimate refund of 25.0 USDC
    close1 = vault.close_session(AgentSessionCloseRequest(
        session_token=token,
        agent_address=agent_addr,
    ))
    assert close1.refunded_balance_usdc == 25.0

    # Second close attempt -> must be rejected to prevent double refund!
    from app.agent_session_vault import InvalidSessionTokenError
    with pytest.raises(InvalidSessionTokenError, match="Multiple refunds prohibited"):
        vault.close_session(AgentSessionCloseRequest(
            session_token=token,
            agent_address=agent_addr,
        ))


def test_adversarial_esg_carbon_budget_constraint():
    """Adversarial Test: Route optimizer must enforce ESG carbon budget constraints."""
    req = TradeRouteOptimizationRequest(
        mineral_type=MineralType.LITHIUM_CARBONATE,
        origin_country=SourceCountry.CHL,
        destination_country="USA",
        cargo_weight_metric_tons=5000.0,
        max_carbon_budget_co2_tons=1.0,  # Unattainable strict carbon cap
    )
    res = global_trade_engine.optimize_route(req)
    assert res.agent_decision is not None
    assert "CARBON_BUDGET_EXCEEDED" in res.agent_decision.bottlenecks
    assert res.agent_decision.action == AgentActionType.HOLD_FOR_ASSAY_CLARIFICATION
    assert "exceeds carbon budget limit" in res.agent_decision.recommended_action


def test_adversarial_ebl_null_hash_and_zero_weight():
    """Adversarial Test: eBL verification must reject all-zero null hashes and non-positive weight."""
    from app.schemas import EBLVerificationRequest
    # Null hash attempt
    req_null_hash = EBLVerificationRequest(
        ebl_document_id="EBL-NULL-001",
        ebl_document_hash="0x" + "0" * 64,
        carrier_imo_number=9315331,
        vessel_name="PACIFIC_NAVIGATOR",
        mineral_type=MineralType.LITHIUM_HYDROXIDE,
        gross_weight_metric_tons=5000.0,
        port_of_loading_code="AUHED",
        port_of_discharge_code="KRGWA",
        shipper_name="Exporter Corp",
        consignee_name="Importer Corp",
    )
    res_null = global_trade_engine.verify_ebl(req_null_hash)
    assert res_null.is_valid is False
    assert res_null.hash_integrity is False

    # Negative weight attempt (blocked by schema validation)
    with pytest.raises(Exception):
        EBLVerificationRequest(
            ebl_document_id="EBL-WEIGHT-001",
            ebl_document_hash="0x" + "a" * 64,
            carrier_imo_number=9315331,
            vessel_name="PACIFIC_NAVIGATOR",
            mineral_type=MineralType.LITHIUM_HYDROXIDE,
            gross_weight_metric_tons=-500.0,
            port_of_loading_code="AUHED",
            port_of_discharge_code="KRGWA",
            shipper_name="Exporter Corp",
            consignee_name="Importer Corp",
        )


def test_mcp_cancel_and_list_deals(client):
    """Verifies MCP tools for cancelling proposals and listing deals by agent."""
    headers = {"X-Dev-Bypass": "true"}
    engine = get_a2a_deal_engine()
    seller_addr = "0x6666666666666666666666666666666666666666"
    buyer_addr = "0x5555555555555555555555555555555555555555"

    spec = TradeDealSpec(
        deal_id="DEAL-MCP-CANCEL-001",
        commodity=MineralType.COPPER_CATHODE,
        volume_tons=10.0,
        unit_price_usd_per_ton=9500.0,
        total_deal_value_usd=95000.0,
        origin_country=SourceCountry.CHL,
        destination_country="KOR",
        feoc_cleared=True,
        mass_balance_cleared=True,
        ebl_document_id="EBL-MCP-CANCEL-01",
        buyer_agent_address=buyer_addr,
        seller_agent_address=seller_addr,
        created_at_utc="2026-09-15T12:00:00Z",
    )
    engine.propose_deal(TradeDealProposeRequest(spec=spec, seller_signature="0x" + "7" * 130))

    # 1. list_a2a_trade_deals via MCP invoke
    req_list = {
        "name": "list_a2a_trade_deals",
        "arguments": {"agent_address": seller_addr, "status_filter": "PROPOSED"}
    }
    r_list = client.post("/mcp/invoke", json=req_list, headers=headers)
    assert r_list.status_code == 200
    import json
    data_list = json.loads(r_list.json()["content"][0]["text"])
    assert data_list["total_count"] >= 1

    # 2. cancel_a2a_trade_deal via MCP invoke
    req_cancel = {
        "name": "cancel_a2a_trade_deal",
        "arguments": {
            "deal_id": "DEAL-MCP-CANCEL-001",
            "seller_agent_address": seller_addr,
            "cancellation_reason": "Price renegotiation required"
        }
    }
    r_cancel = client.post("/mcp/invoke", json=req_cancel, headers=headers)
    assert r_cancel.status_code == 200
    data_cancel = json.loads(r_cancel.json()["content"][0]["text"])
    assert data_cancel["status"] == "CANCELLED"

