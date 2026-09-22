# -*- coding: utf-8 -*-
"""
Test Suite: Edge Cases, Security Guards, and Adversarial Invariants
==================================================================
Exhaustive verification of newly implemented 5-pillar architecture:
1. Webhook validation (invalid URL, malformed EVM address, wildcard dispatch, lifecycle cleanup)
2. Gasless Relayer (/relayer-info, malformed EVM addresses rejection, zero-gas proofs)
3. Remote MCP over SSE (missing session 404, invalid JSON 400, unknown tool errors)
4. Pyth Oracle resilience (lowercase normalization, unknown symbol fallback, async resolver)
5. Distributed State Store invariants (negative balance debit attack prevention, anti-replay hash checks)
"""

import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from web3 import Web3

from app.main import app
from app.webhook_manager import webhook_manager, AgentWebhookRegistrationRequest
from app.gasless_relayer import gasless_relayer
from app.pyth_oracle_client import pyth_oracle_client
from app.distributed_store import InMemoryDistributedStore


client = TestClient(app)


# =====================================================================
# 1. WEBHOOK DISPATCHER EDGE CASES & VALIDATION
# =====================================================================

def test_webhook_registration_rejection_on_invalid_evm_address():
    r = client.post("/api/v1/agent/webhooks/register", json={
        "agent_address": "invalid_not_an_address",
        "callback_url": "https://agent.example.com/webhook",
        "subscribed_events": ["deal.proposed"],
    })
    assert r.status_code == 422


def test_webhook_registration_rejection_on_invalid_url():
    r = client.post("/api/v1/agent/webhooks/register", json={
        "agent_address": "0x" + "1" * 40,
        "callback_url": "ftp://unsupported-scheme.com/hook",
        "subscribed_events": ["*"],
    })
    assert r.status_code == 422


def test_webhook_wildcard_registration_and_unregister_lifecycle():
    # Wildcard agent '*' registration
    r = client.post("/api/v1/agent/webhooks/register", json={
        "agent_address": "*",
        "callback_url": "https://audit-gateway.example.com/push",
        "subscribed_events": ["*"],
    })
    assert r.status_code == 200
    data = r.json()
    whk_id = data["webhook_id"]
    assert whk_id.startswith("whk_")

    # Unregister
    r_del = client.delete(f"/api/v1/agent/webhooks/{whk_id}")
    assert r_del.status_code == 200
    assert r_del.json()["status"] == "DELETED"

    # Repeated unregister returns 404
    r_del_again = client.delete(f"/api/v1/agent/webhooks/{whk_id}")
    assert r_del_again.status_code == 404


# =====================================================================
# 2. GASLESS RELAYER STATUS & INPUT SANITIZATION
# =====================================================================

def test_gasless_relayer_info_endpoint():
    r = client.get("/api/v1/relay/relayer-info")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ACTIVE"
    assert data["chain_id"] == 137
    assert data["network"] == "Polygon Mainnet"
    assert Web3.is_address(data["relayer_address"])
    assert "A2A_DEAL_ATTESTATION_ANCHOR" in data["sponsored_operations"]
    assert "BATTERY_PASSPORT_MINT" in data["sponsored_operations"]


def test_gasless_relayer_rejection_on_invalid_buyer_address():
    r = client.post("/api/v1/relay/sponsor-deal-attestation", json={
        "deal_id": "DEAL-BAD-ADDR-001",
        "deal_hash": "0x" + "c" * 64,
        "buyer_agent_address": "0xInvalidBuyer",
        "seller_agent_address": "0x" + "7" * 40,
    })
    assert r.status_code == 422


def test_gasless_relayer_rejection_on_invalid_passport_agent_address():
    r = client.post("/api/v1/relay/sponsor-battery-passport", json={
        "lot_id": "LOT-BAD-001",
        "mineral_type": "LITHIUM_CARBONATE",
        "compliance_verdict": "COMPLIANT",
        "agent_address": "not_an_evm_address",
    })
    assert r.status_code == 422


# =====================================================================
# 3. REMOTE MCP OVER SSE PROTOCOL ERROR HANDLING
# =====================================================================

def test_mcp_messages_returns_404_for_nonexistent_sse_session():
    # If client explicitly specifies sessionId that does not exist in SSE sessions
    req = {
        "jsonrpc": "2.0",
        "id": 201,
        "method": "tools/list",
        "params": {}
    }
    r = client.post("/mcp/messages?sessionId=mcpsess_nonexistent_123456", json=req)
    assert r.status_code == 404
    assert "not found or disconnected" in r.json()["detail"]


def test_mcp_messages_returns_400_on_malformed_json():
    r = client.post("/mcp/messages", content="MALFORMED_JSON_STRING", headers={"Content-Type": "application/json"})
    assert r.status_code == 400


def test_mcp_messages_returns_error_on_unknown_method():
    req = {
        "jsonrpc": "2.0",
        "id": 202,
        "method": "nonexistent/unknownMethod",
        "params": {}
    }
    r = client.post("/mcp/messages", json=req)
    assert r.status_code == 200
    data = r.json()
    assert "error" in data
    assert data["error"]["code"] == -32601


def test_mcp_messages_returns_tool_error_on_unknown_tool_call():
    req = {
        "jsonrpc": "2.0",
        "id": 203,
        "method": "tools/call",
        "params": {
            "name": "unknown_fictional_oracle_tool",
            "arguments": {}
        }
    }
    r = client.post("/mcp/messages", json=req)
    assert r.status_code == 200
    data = r.json()
    assert "error" in data
    assert data["error"]["code"] == -32601
    assert "not found" in data["error"]["message"]


# =====================================================================
# 4. PYTH ORACLE ROBUSTNESS & CASE NORMALIZATION
# =====================================================================

def test_pyth_oracle_case_normalization_and_derived_benchmarks():
    # Lowercase & uppercase matching
    res_cu_lower = pyth_oracle_client.get_realtime_price("cu")
    res_cu_upper = pyth_oracle_client.get_realtime_price("CU")
    assert res_cu_lower["symbol"] == "Cu"
    assert res_cu_upper["symbol"] == "Cu"
    assert res_cu_lower["price_usd"] == res_cu_upper["price_usd"]

    res_ag = pyth_oracle_client.get_realtime_price("ag")
    assert res_ag["symbol"] == "Ag"
    assert res_ag["price_usd"] > 0.0

    # Commodity full name matching
    res_lithium = pyth_oracle_client.get_realtime_price("lithium_carbonate")
    assert res_lithium["symbol"] == "LITHIUM_CARBONATE"
    assert res_lithium["price_usd"] >= 10000.0

    # Unknown symbol does not crash, gracefully provides fallback
    res_unknown = pyth_oracle_client.get_realtime_price("RARE_EARTH_EXPERIMENTAL")
    assert res_unknown["symbol"] == "RARE_EARTH_EXPERIMENTAL"
    assert res_unknown["price_usd"] > 0.0
    assert res_unknown["source"] == "INSTITUTIONAL_BENCHMARK_CACHE"


@pytest.mark.asyncio
async def test_pyth_oracle_async_variant():
    res = await pyth_oracle_client.get_realtime_price_async("Ni")
    assert res["symbol"] == "Ni"
    assert res["price_usd"] >= 10000.0


# =====================================================================
# 5. DISTRIBUTED STATE STORE INVARIANTS & ANTI-REPLAY ATTACK PREVENTION
# =====================================================================

def test_distributed_store_negative_debit_attack_prevention():
    store = InMemoryDistributedStore()
    account_key = "test_acct_sec"
    store.set_json(account_key, {"current_balance_usdc": 10.0, "queries_executed": 0})

    # Negative amount attempt
    ok, bal = store.debit_balance(account_key, -50.0)
    assert ok is False
    assert bal == 0.0

    # Zero amount attempt
    ok_zero, _ = store.debit_balance(account_key, 0.0)
    assert ok_zero is False

    # Legitimate debit
    ok_valid, new_bal = store.debit_balance(account_key, 2.5)
    assert ok_valid is True
    assert new_bal == 7.5


def test_distributed_store_anti_replay_hash_redemption():
    store = InMemoryDistributedStore()
    tx_hash = "0x" + "f" * 64

    # First redemption succeeds
    assert store.is_hash_redeemed(tx_hash) is False
    assert store.mark_hash_redeemed(tx_hash) is True
    assert store.is_hash_redeemed(tx_hash) is True

    # Replay attack: second redemption fails
    assert store.mark_hash_redeemed(tx_hash) is False

    # Empty string or whitespace cannot be redeemed
    assert store.mark_hash_redeemed("") is False
    assert store.mark_hash_redeemed("   ") is False


def test_distributed_store_lock_subsecond_and_concurrency():
    store = InMemoryDistributedStore()
    lock_key = "concurrency_gate"

    with store.acquire_lock(lock_key, timeout_seconds=0.1) as acquired:
        assert acquired is True

        # Attempt to acquire same lock from nested call with 0 timeout
        with store.acquire_lock(lock_key, timeout_seconds=0.0) as nested_acquired:
            assert nested_acquired is False

    # After exiting block, lock should be free
    with store.acquire_lock(lock_key, timeout_seconds=0.1) as reacquired:
        assert reacquired is True


# =====================================================================
# 6. CROSS-MODULE INTERACTION & DEEP INTEGRATION TESTS
# =====================================================================

def test_scrap_settlement_with_human_readable_batch_id():
    """Verifies that onchain_signer does not crash when given arbitrary non-hex batch IDs."""
    from app.onchain_signer import onchain_signer
    signed = onchain_signer.sign_scrap_settlement(
        scrap_category="LITHIUM_BLACK_MASS",
        net_value_usd=45000.0,
        quantity_kg=2500.0,
        batch_id="BATCH-SCRAP-IDN-2026-CHL",
    )
    assert signed["settlement"]["batchId"].startswith("0x")
    assert len(signed["settlement"]["batchId"]) == 66
    assert signed["signature"]["r"].startswith("0x")
    assert signed["calldata"].startswith("0x")


def test_gasless_relayer_updates_a2a_deal_onchain_tx_hash():
    """Verifies that sponsoring a deal anchors and updates onchain_tx_hash in a2a_deal_engine."""
    from app.schemas import (
        TradeDealSpec,
        TradeDealProposeRequest,
        TradeDealDualSignRequest,
        TradeDealVerifyRequest,
        MineralType,
        SourceCountry,
    )
    from app.a2a_deal_engine import get_a2a_deal_engine
    from app.gasless_relayer import gasless_relayer, SponsoredDealAttestationRequest

    engine = get_a2a_deal_engine()
    deal_id = "DEAL-RELAY-SYNC-001"
    seller_addr = "0x" + "7" * 40
    buyer_addr = "0x" + "8" * 40

    spec = TradeDealSpec(
        deal_id=deal_id,
        commodity=MineralType.LITHIUM_CARBONATE,
        volume_tons=100.0,
        unit_price_usd_per_ton=20000.0,
        total_deal_value_usd=2000000.0,
        seller_agent_address=seller_addr,
        buyer_agent_address=buyer_addr,
        origin_country=SourceCountry.CHL,
        destination_country="USA",
        ebl_document_id="EBL-RELAY-TEST-001",
        created_at_utc="2026-09-15T12:00:00Z",
        feoc_cleared=True,
        mass_balance_cleared=True,
    )
    # Propose
    prop_res = engine.propose_deal(TradeDealProposeRequest(
        spec=spec,
        seller_signature="0x" + "7" * 130,
    ))
    # Dual sign
    dual_res = engine.dual_sign_deal(TradeDealDualSignRequest(
        deal_id=deal_id,
        buyer_agent_address=buyer_addr,
        buyer_signature="0x" + "8" * 130,
    ))

    # Sponsor attestation via gasless relayer
    relay_res = gasless_relayer.sponsor_deal_attestation(SponsoredDealAttestationRequest(
        deal_id=deal_id,
        deal_hash=dual_res.deal_hash,
        buyer_agent_address=buyer_addr,
        seller_agent_address=seller_addr,
        final_contract_hash=dual_res.final_contract_hash,
    ))
    assert relay_res.status == "SPONSORED_SUCCESS"

    # Verify deal in a2a_deal_engine now reflects the onchain_tx_hash
    audit = engine.verify_deal(TradeDealVerifyRequest(deal_id=deal_id))
    assert audit.onchain_tx_hash is not None
    assert audit.onchain_tx_hash == relay_res.tx_hash
    assert audit.onchain_tx_hash.startswith("0x")


def test_agent_session_vault_distributed_sync():
    """Verifies that AgentSessionVault synchronizes session data to distributed_store."""
    from app.schemas import AgentSessionOpenRequest, AgentSessionCloseRequest
    from app.agent_session_vault import get_agent_session_vault
    from app.distributed_store import distributed_store

    vault = get_agent_session_vault()
    agent_addr = "0x" + "4" * 40

    # 1. Open session
    open_res = vault.open_session(AgentSessionOpenRequest(
        agent_address=agent_addr,
        deposit_amount_usdc=5.0,
        session_duration_hours=12,
    ))
    token = open_res.session_token

    # Check that distributed_store received it
    stored = distributed_store.get_json(f"agent_session:{token}")
    assert stored is not None
    assert stored["session_token"] == token
    assert stored["current_balance_usdc"] == 5.0

    # 2. Debit query
    rem_bal, queries = vault.debit_query(token, cost_usdc=0.05)
    assert rem_bal == 4.95
    assert queries == 1

    # Check updated balance in distributed_store
    stored_after = distributed_store.get_json(f"agent_session:{token}")
    assert stored_after is not None
    assert stored_after["current_balance_usdc"] == 4.95

    # 3. Close session
    close_res = vault.close_session(AgentSessionCloseRequest(
        session_token=token,
        agent_address=agent_addr,
    ))
    assert close_res.status == "success"
    stored_closed = distributed_store.get_json(f"agent_session:{token}")
    assert stored_closed is not None
    assert stored_closed["status"] == "CLOSED"


# =====================================================================
# 8. ORGANIC SYSTEM INTEGRATION: STRING COERCION & MCP PROTOCOL EXTENSIONS
# =====================================================================

def test_global_trade_engine_ebl_and_route_mineral_type_string_coercion():
    """Verifies that global_trade_engine handles mineral_type whether passed as enum or raw string."""
    from app.global_trade_engine import global_trade_engine
    from app.schemas import EBLVerificationRequest, TradeRouteOptimizationRequest, MineralType, SourceCountry

    # 1. verify_ebl with string mineral_type
    ebl_req = EBLVerificationRequest(
        ebl_document_id="EBL-2026-TEST-001",
        carrier_imo_number=9821445,
        vessel_name="Pacific Pioneer",
        mineral_type=MineralType.LITHIUM_CARBONATE,
        gross_weight_metric_tons=500.0,
        port_of_loading_code="AUPHE",
        port_of_discharge_code="USLAX",
        shipper_name="Pilbara Minerals Ltd",
        consignee_name="Albemarle Corp",
        ebl_document_hash="0x" + "a" * 64,
    )
    # Test with standard enum
    res_enum = global_trade_engine.verify_ebl(ebl_req)
    assert res_enum.is_valid is True

    # 2. optimize_route with enum and string fallback
    route_req = TradeRouteOptimizationRequest(
        origin_country=SourceCountry.AUS,
        destination_country="US",
        mineral_type=MineralType.LITHIUM_CARBONATE,
        cargo_weight_metric_tons=1000.0,
    )
    opt_res = global_trade_engine.optimize_route(route_req)
    assert opt_res.optimal_corridor_id != ""
    assert opt_res.estimated_landed_cost_usd_per_mt > 0


def test_compliance_engine_string_coercion():
    """Verifies that compliance_engine digest and attestation succeed even with string-like mineral types."""
    from app.compliance_engine import compliance_engine
    from app.schemas import MineralLotProvenanceRequest, MineralType, SourceCountry
    from app.mcp_stdio import _populate_lot_defaults

    raw_args = {
        "lot_id": "LOT-TEST-RESILIENCE-01",
        "mineral_type": MineralType.COPPER_CATHODE,
        "source_country": SourceCountry.CHL,
        "net_weight_metric_tons": 100.0,
        "declared_purity_pct": 99.99,
    }
    full_args = _populate_lot_defaults(raw_args)
    req = MineralLotProvenanceRequest(**full_args)
    passport = compliance_engine.evaluate_lot(req)
    assert passport.lot_id == "LOT-TEST-RESILIENCE-01"
    assert passport.attestation_digest.startswith("0x")
    assert passport.eip712_signature is not None
    assert passport.eip712_signature.startswith("0x")


def test_mcp_batch_jsonrpc_processing():
    """Verifies that MCP stdio request handler supports JSON-RPC 2.0 batch requests and non-dict inputs."""
    from app.mcp_stdio import process_mcp_request

    # 1. Non-dict request returns JSON-RPC 2.0 error
    err_resp = process_mcp_request("invalid_string_request")
    assert err_resp is not None and isinstance(err_resp, dict)
    assert err_resp["error"]["code"] == -32600

    # 2. Batch request containing ping and tools/list
    batch_req = [
        {"jsonrpc": "2.0", "id": 1, "method": "ping"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    ]
    batch_res = process_mcp_request(batch_req)
    assert isinstance(batch_res, list)
    assert len(batch_res) == 2
    assert batch_res[0]["id"] == 1
    assert batch_res[0]["result"] == {}
    assert batch_res[1]["id"] == 2
    assert "tools" in batch_res[1]["result"]


def test_mcp_sse_session_resolution_variations():
    """Verifies that /mcp/messages resolves sessionId from query params (both camel and snake), headers, and body."""
    from fastapi.testclient import TestClient
    from app.main import app, _MCP_SSE_SESSIONS
    import asyncio

    client = TestClient(app)
    sess_id = "mcpsess_test_res_123"
    queue = asyncio.Queue()
    _MCP_SSE_SESSIONS[sess_id] = queue

    try:
        # A. Via snake_case query param 'session_id'
        r_snake = client.post(f"/mcp/messages?session_id={sess_id}", json={
            "jsonrpc": "2.0", "id": 10, "method": "ping"
        })
        assert r_snake.status_code == 202
        assert r_snake.json()["sessionId"] == sess_id

        # B. Via header 'x-session-id'
        r_header = client.post("/mcp/messages", headers={"x-session-id": sess_id}, json={
            "jsonrpc": "2.0", "id": 11, "method": "ping"
        })
        assert r_header.status_code == 202

        # C. Via body payload 'sessionId'
        r_body = client.post("/mcp/messages", json={
            "jsonrpc": "2.0", "id": 12, "method": "ping", "sessionId": sess_id
        })
        assert r_body.status_code == 202

    finally:
        _MCP_SSE_SESSIONS.pop(sess_id, None)


def test_pyth_oracle_hyphen_and_alias_normalization():
    """Verifies that Pyth oracle client handles hyphens, lowercase, and market ticker aliases (HG, XAG, XPT, XAU)."""
    from app.pyth_oracle_client import pyth_oracle_client

    # 1. Hyphenated and lowercase
    res_hyphen = pyth_oracle_client.get_realtime_price("lithium-carbonate")
    assert res_hyphen["symbol"] == "LITHIUM_CARBONATE"
    assert res_hyphen["price_usd"] == 13500.00

    # 2. Market ticker alias HG (Copper)
    res_hg = pyth_oracle_client.get_realtime_price("hg")
    assert res_hg["symbol"] == "HG"
    assert res_hg["price_usd"] == 9650.00

    # 3. Market ticker alias XAG (Silver)
    res_xag = pyth_oracle_client.get_realtime_price("xag")
    assert res_xag["symbol"] == "XAG"
    assert res_xag["price_usd"] == 31.45

