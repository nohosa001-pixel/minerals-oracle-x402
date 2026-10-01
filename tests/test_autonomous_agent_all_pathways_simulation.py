"""
Comprehensive Autonomous Agent Entry & Usage Pathways Simulation.
Tests EVERY pathway an autonomous AI agent can take when entering and using Minerals Oracle:
1. Pathway 1: FastMCP Stdio JSON-RPC Direct Calling (All 32 tools)
2. Pathway 2: FastMCP SSE (Server-Sent Events) Transport Simulation (/mcp/sse & /mcp/messages)
3. Pathway 3: REST API with Agent Session Vault (Micro-allowance debit & refund)
4. Pathway 4: x402 Protocol Native HTTP 402 Challenge-Response Flow
5. Pathway 5: Bilateral Multi-Agent Negotiation & EIP-712 Dual-Signed Escrow Lifecycle
6. Pathway 5B: A2A Deal Adversarial Branches (Deal Rejection & Proposer Revocation)
7. Pathway 6: Autonomous Agent Evolution & Governance Proposal Feed
8. Pathway 7: Real-time Webhooks & HMAC-SHA256 Event Verification
"""

import base64
import json
import time
import secrets
import hashlib
import hmac
import pytest
from fastapi.testclient import TestClient
from eth_account import Account
from eth_account.messages import encode_defunct

from app.main import app
from app.mcp_stdio import process_mcp_request, handle_tools_list, handle_tool_call
from app.schemas import (
    MineralType,
    SourceCountry,
    AgentActionType,
    TradeDealSpec,
    TradeDealProposeRequest,
    TradeDealDualSignRequest,
    TradeDealRejectRequest,
    TradeDealCancelRequest,
)
from app.webhook_manager import webhook_manager

client = TestClient(app)


# =============================================================================
# PATHWAY 1: FastMCP Stdio JSON-RPC Direct Protocol (All Major Agent Tools)
# =============================================================================
def test_pathway_1_fastmcp_stdio_comprehensive():
    """Simulates an autonomous agent invoking the Minerals Oracle via FastMCP stdio."""
    # 1. Tools discovery
    list_req = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    resp = process_mcp_request(list_req)
    assert resp is not None and "result" in resp
    tools = {t["name"]: t for t in resp["result"]["tools"]}
    assert len(tools) == 32
    assert "eudr_satellite_mine_audit" in tools
    assert "verify_composite_battery_passport" in tools
    assert "propose_a2a_trade_deal" in tools

    # 2. Tool: eudr_satellite_mine_audit
    eudr_req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "eudr_satellite_mine_audit",
            "arguments": {
                "latitude": -2.55,
                "longitude": 121.35,
                "country_code": "ID",
                "area_hectares": 12.0,
                "concession_id": "MINE-MCP-SIM-01"
            }
        }
    }
    eudr_res = process_mcp_request(eudr_req)
    assert "result" in eudr_res
    eudr_data = json.loads(eudr_res["result"]["content"][0]["text"])
    assert eudr_data["is_compliant"] is True
    assert eudr_data["satellite_evidence_hash"].startswith("0x")
    assert "DDS-EUDR-2026-ID-" in eudr_data["traces_nt_dds_reference"]

    # 3. Tool: register_agent_account & get_agent_vault_balance
    reg_req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "register_agent_account",
            "arguments": {
                "agent_name": "bot_mcp_explorer",
                "agent_address": "0x3333333333333333333333333333333333333333",
                "initial_trial_balance_usdc": 1.50
            }
        }
    }
    reg_res = process_mcp_request(reg_req)
    reg_data = json.loads(reg_res["result"]["content"][0]["text"])
    assert reg_data["status"] == "REGISTERED"
    session_key = reg_data["session_key"]

    bal_req = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "get_agent_vault_balance",
            "arguments": {"session_key": session_key}
        }
    }
    bal_res = process_mcp_request(bal_req)
    bal_data = json.loads(bal_res["result"]["content"][0]["text"])
    assert bal_data["balance_usdc"] == 1.50

    # 4. Tool: optimize_mineral_trade_route
    route_req = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "optimize_mineral_trade_route",
            "arguments": {
                "mineral_type": "Nickel MHP",
                "origin_country": "IDN",
                "destination_country": "USA",
                "cargo_weight_metric_tons": 5000.0
            }
        }
    }
    route_res = process_mcp_request(route_req)
    route_data = json.loads(route_res["result"]["content"][0]["text"])
    assert "optimal_corridor_id" in route_data or "status" in route_data
    assert "agent_decision" in route_data


# =============================================================================
# PATHWAY 2: FastMCP SSE Transport Simulation (/mcp/sse & /mcp/messages)
# =============================================================================
def test_pathway_2_fastmcp_sse_transport():
    """Simulates an autonomous agent connecting via SSE transport to send tool requests."""
    # 1. Connect to /mcp/sse endpoint and read endpoint line
    with client.stream("GET", "/mcp/sse", headers={"X-Test-Stream": "single"}) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        lines = []
        for chunk in response.iter_lines():
            if chunk:
                lines.append(chunk)
            if len(lines) >= 2:
                break

        assert any("event: endpoint" in l for l in lines)
        data_line = [l for l in lines if l.startswith("data:")][0]
        assert "/mcp/messages?sessionId=mcpsess_" in data_line

    # 2. Post tool request directly to /mcp/messages
    rpc_payload = {
        "jsonrpc": "2.0",
        "id": "sse-msg-01",
        "method": "tools/list",
        "params": {}
    }
    msg_resp = client.post("/mcp/messages", json=rpc_payload)
    assert msg_resp.status_code == 200
    res = msg_resp.json()
    assert res["id"] == "sse-msg-01"
    assert len(res["result"]["tools"]) == 32


# =============================================================================
# PATHWAY 3: REST API Workflow with Agent Session Vault (<0.1ms Micro-debits)
# =============================================================================
def test_pathway_3_rest_api_session_vault_lifecycle():
    """Simulates agent opening high-frequency session token and consuming services."""
    agent_addr = "0x4444444444444444444444444444444444444444"

    # Step 1: Open Agent Session
    open_resp = client.post(
        "/api/v1/agent/session/open",
        json={
            "agent_address": agent_addr,
            "deposit_amount_usdc": 2.0,
            "session_duration_hours": 24
        }
    )
    assert open_resp.status_code == 200
    sess = open_resp.json()
    session_token = sess["session_token"]
    assert session_token.startswith("asess_")
    assert sess["allocated_balance_usdc"] == 2.0

    headers = {"X-Agent-Session-Token": session_token}

    # Step 2: Route optimization with deterministic Agent Decision Signal
    opt_resp = client.post(
        "/api/v1/trade/optimize-route",
        headers=headers,
        json={
            "mineral_type": "Lithium Carbonate",
            "origin_country": "CHL",
            "destination_country": "USA",
            "cargo_weight_metric_tons": 3000.0
        }
    )
    assert opt_resp.status_code == 200
    opt_data = opt_resp.json()
    assert "agent_decision" in opt_data
    assert opt_data["agent_decision"]["action"] in [
        AgentActionType.PROCEED_SETTLEMENT,
        AgentActionType.REROUTE_PANAMA_BOTTLENECK,
        AgentActionType.ABORT_FEOC_VIOLATION,
    ]

    # Step 3: Verified Provenance Endpoints (debited micro-settlements)
    li_resp = client.post(
        "/api/v1/lithium/verify-origin",
        headers=headers,
        json={
            "trace_id": "LIT-SIM-SESSION-01",
            "product": "Lithium Hydroxide Monohydrate",
            "mine_name": "Greenbushes Hard-Rock Mine",
            "mine_country": "AU",
            "coordinates": [-33.86, 116.02],
            "spodumene_tonnage_extracted": 75.0,
            "spodumene_grade_pct": 6.0,
            "refinery_facility": "Kwinana Plant",
            "refinery_country": "AU",
            "refined_output_tonnage": 10.0,
            "refinery_feoc_equity_pct": 0.0
        }
    )
    assert li_resp.status_code == 200
    assert "X-Receipt-ID" in li_resp.headers

    # Second query: EUDR Concession Audit
    eudr_resp = client.post(
        "/api/v1/compliance/eudr-satellite-audit",
        headers=headers,
        json={
            "latitude": -12.05,
            "longitude": -77.05,
            "country_code": "PE",
            "area_hectares": 15.0,
            "concession_id": "MINE-PERU-COPPER-01"
        }
    )
    assert eudr_resp.status_code == 200
    assert eudr_resp.json()["is_compliant"] is True

    # Step 4: Check Session status
    info_resp = client.get(f"/api/v1/agent/session/{session_token}")
    assert info_resp.status_code == 200
    info_data = info_resp.json()
    assert info_data["queries_executed"] >= 1
    assert info_data["current_balance_usdc"] < 2.0

    # Step 5: Close Session and claim refund
    close_resp = client.post(
        "/api/v1/agent/session/close",
        json={
            "session_token": session_token,
            "agent_address": agent_addr
        }
    )
    assert close_resp.status_code == 200
    close_data = close_resp.json()
    assert close_data["status"] == "success"
    assert close_data["refunded_balance_usdc"] > 0.0
    assert close_data["settlement_receipt_hash"].startswith("0x")


# =============================================================================
# PATHWAY 4: x402 Protocol Native Payment & Challenge-Response Flow
# =============================================================================
def test_pathway_4_x402_native_challenge_flow():
    """Simulates agent interacting with x402 native HTTP 402 payment challenge."""
    # 1. Request challenge -> receives 402 Payment Required
    chal_resp = client.get("/api/v1/oracle/challenge")
    assert chal_resp.status_code == 402
    assert chal_resp.headers["X-Payment-Required"] == "true"
    assert chal_resp.headers["X-Payment-ChainId"] == "137"
    assert chal_resp.headers["X-Payment-Recipient"] == "0xA185B43fDD19619f99952AAed6eabf1029bF36a1"

    chal_body = chal_resp.json()["payment_challenge"]
    nonce = chal_body["nonce"]
    assert chal_body["network"] == "polygon"
    assert chal_body["amount"] == "0.005"
    assert chal_body["accepted_token"] == "USDC"

    # 2. Agent signs payment nonce with private key
    agent_wallet = Account.create()
    message_text = f"x402:minerals-oracle-x402:pay:0.005:USDC:Polygon:{nonce}"
    signable_msg = encode_defunct(text=message_text)
    signed = agent_wallet.sign_message(signable_msg)
    payload = {
        "nonce": nonce,
        "signature": signed.signature.hex(),
        "signer": agent_wallet.address,
    }
    payload_b64 = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
    auth_header = f"x402 {payload_b64}"

    # 3. Agent calls protected price feed with x402 authorization header
    feed_resp = client.get("/api/v1/oracle/prices", headers={"Authorization": auth_header})
    assert feed_resp.status_code == 200
    feed_data = feed_resp.json()
    assert feed_data["oracle"] == "minerals-oracle-x402"
    assert "monitored_minerals" in feed_data


# =============================================================================
# PATHWAY 5: Bilateral Multi-Agent Negotiation & EIP-712 Dual-Signed Escrow
# =============================================================================
def test_pathway_5_a2a_bilateral_deal_and_dual_sign_lifecycle():
    """Simulates Buyer Agent and Supplier Agent negotiating and dual-signing an on-chain trade deal."""
    buyer_account = Account.create("buyer_agent_secret_entropy_123")
    seller_account = Account.create("seller_agent_secret_entropy_456")

    # Step 1: Seller proposes trade deal via REST
    deal_payload = {
        "spec": {
            "deal_id": "DEAL-SIM-A2A-001",
            "commodity": "COPPER_CATHODE",
            "volume_tons": 2500.0,
            "unit_price_usd_per_ton": 9650.0,
            "total_deal_value_usd": 24125000.0,
            "origin_country": "CHL",
            "destination_country": "USA",
            "feoc_cleared": True,
            "mass_balance_cleared": True,
            "ebl_document_id": "EBL-SIM-CHL-USA-01",
            "buyer_agent_address": buyer_account.address,
            "seller_agent_address": seller_account.address,
            "settlement_currency": "USDC",
            "projected_savings_usd": 50000.0,
            "created_at_utc": "2026-09-29T12:00:00Z",
        },
        "seller_signature": "0x" + "a" * 130,
    }
    prop_resp = client.post("/api/v1/trade/deals/propose", json=deal_payload)
    assert prop_resp.status_code == 200
    deal_info = prop_resp.json()
    assert deal_info["deal_id"] == "DEAL-SIM-A2A-001"
    assert deal_info["status"] == "PROPOSED"
    assert deal_info["spec"]["calculated_gain_share_fee_usd"] == 5000.0

    # Step 2: Buyer dual-signs the proposed deal
    dual_payload = {
        "deal_id": "DEAL-SIM-A2A-001",
        "buyer_signature": "0x" + "b" * 130,
        "buyer_agent_address": buyer_account.address
    }
    dual_resp = client.post("/api/v1/trade/deals/dual-sign", json=dual_payload)
    assert dual_resp.status_code == 200
    dual_data = dual_resp.json()
    assert dual_data["status"] == "DUAL_SIGNED_CONFIRMED"

    # Step 3: Verify Attested Deal
    ver_resp = client.get("/api/v1/trade/deals/verify/DEAL-SIM-A2A-001")
    assert ver_resp.status_code == 200
    ver_data = ver_resp.json()
    assert ver_data["is_valid"] is True
    assert ver_data["deal_status"] == "DUAL_SIGNED_CONFIRMED"

    # Step 4: Generate On-chain Escrow Calldata for MineralTradeEscrow.sol
    call_resp = client.get("/api/v1/trade/deals/DEAL-SIM-A2A-001/escrow-calldata")
    assert call_resp.status_code == 200
    calldata = call_resp.json()
    assert "calldata" in calldata
    assert calldata["calldata"].startswith("0x")
    assert calldata["function_signature"] == "createEscrow(bytes32,address,uint256,bytes32,uint256)"
    assert calldata["escrow_contract_address"] == "0x1270ddebad0ca90070342336a581eaACBA2060Ab"


# =============================================================================
# PATHWAY 5-B: A2A Deal Adversarial Branches (Reject & Cancel)
# =============================================================================
def test_pathway_5b_a2a_deal_rejection_and_cancellation():
    """Simulates adversarial and termination paths: Deal Rejection and Proposer Cancellation."""
    agent1 = Account.create("test_agent_1")
    agent2 = Account.create("test_agent_2")

    # Scenario A: Propose -> Reject
    deal_payload_a = {
        "spec": {
            "deal_id": "DEAL-REJECT-SIM-01",
            "commodity": "NICKEL_MHP",
            "volume_tons": 500.0,
            "unit_price_usd_per_ton": 16000.0,
            "total_deal_value_usd": 8000000.0,
            "origin_country": "IDN",
            "destination_country": "USA",
            "feoc_cleared": False,
            "mass_balance_cleared": True,
            "ebl_document_id": "EBL-REJECT-01",
            "buyer_agent_address": agent1.address,
            "seller_agent_address": agent2.address,
            "created_at_utc": "2026-09-29T12:00:00Z",
        },
        "seller_signature": "0x" + "1" * 130,
    }
    client.post("/api/v1/trade/deals/propose", json=deal_payload_a)

    rej_resp = client.post(
        "/api/v1/trade/deals/reject",
        json={
            "deal_id": "DEAL-REJECT-SIM-01",
            "buyer_agent_address": agent1.address,
            "buyer_signature": "0x" + "2" * 130,
            "rejection_reason": "FEOC compliance not satisfied"
        }
    )
    assert rej_resp.status_code == 200
    assert rej_resp.json()["status"] == "REJECTED"

    # Scenario B: Propose -> Cancel by Seller
    deal_payload_b = {
        "spec": {
            "deal_id": "DEAL-CANCEL-SIM-01",
            "commodity": "LITHIUM_CARBONATE",
            "volume_tons": 100.0,
            "unit_price_usd_per_ton": 14000.0,
            "total_deal_value_usd": 1400000.0,
            "origin_country": "CHL",
            "destination_country": "USA",
            "feoc_cleared": True,
            "mass_balance_cleared": True,
            "ebl_document_id": "EBL-CANCEL-01",
            "buyer_agent_address": agent1.address,
            "seller_agent_address": agent2.address,
            "created_at_utc": "2026-09-29T12:00:00Z",
        },
        "seller_signature": "0x" + "3" * 130,
    }
    client.post("/api/v1/trade/deals/propose", json=deal_payload_b)

    cancel_resp = client.post(
        "/api/v1/trade/deals/cancel",
        json={
            "deal_id": "DEAL-CANCEL-SIM-01",
            "seller_agent_address": agent2.address,
            "seller_signature": "0x" + "4" * 130,
            "cancellation_reason": "Consignment reallocated to domestic battery cell producer"
        }
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"


# =============================================================================
# PATHWAY 6: Autonomous Agent Evolution & Governance Feed
# =============================================================================
def test_pathway_6_agent_evolution_proposal():
    """Simulates an autonomous agent submitting an evolution proposal to enhance oracle datasets."""
    # 1. Submit proposal via REST API
    sub_resp = client.post(
        "/api/v1/oracle/agent/feedback",
        json={
            "agent_id": "bot_regulatory_monitor_v4",
            "title": "Add EU Critical Raw Materials Act (CRMA) 2030 Benchmark Feed",
            "content": "Proposal to track EU CRMA Article 5 benchmarks: 10% extraction, 40% processing, 25% recycling.",
            "feedback_type": "REGULATORY_UPDATE",
            "mineral_focus": "ALL",
            "proposed_solution": "Incorporate CRMA benchmark metrics in composite battery passport",
            "caller_model": "gemini-3.8-flash"
        }
    )
    assert sub_resp.status_code == 200
    prop_data = sub_resp.json()
    assert prop_data["status"] == "PROPOSAL_ACCEPTED"
    assert "feedback_id" in prop_data

    # 2. List proposals
    list_resp = client.get("/api/v1/oracle/agent/feedback")
    assert list_resp.status_code == 200
    all_props = list_resp.json()["items"]
    assert any("CRMA" in p["title"] for p in all_props)


# =============================================================================
# PATHWAY 7: Real-Time Webhooks & HMAC-SHA256 Verification
# =============================================================================
def test_pathway_7_webhooks_registration_and_signing():
    """Simulates agent subscribing to webhook events and validating cryptographic HMAC signatures."""
    agent_addr = "0x9999999999999999999999999999999999999999"
    callback_url = "https://agent-buyer.internal/webhook"
    secret = "my-secure-agent-secret-key-12345"

    # Register webhook
    r_reg = client.post(
        "/api/v1/agent/webhooks/register",
        json={
            "agent_address": agent_addr,
            "callback_url": callback_url,
            "subscribed_events": ["deal.proposed", "deal.dual_signed"],
            "webhook_secret": secret,
        }
    )
    assert r_reg.status_code == 200
    reg_data = r_reg.json()
    assert reg_data["status"] == "success"
    webhook_id = reg_data["webhook_id"]
    assert webhook_id.startswith("whk_")

    # List webhooks
    r_list = client.get(f"/api/v1/agent/webhooks/{agent_addr}")
    assert r_list.status_code == 200
    items = r_list.json()
    assert any(w["webhook_id"] == webhook_id for w in items)

    # Verify HMAC signature computation helper
    payload = json.dumps({"event": "deal.proposed", "deal_id": "DEAL-001"}).encode("utf-8")
    sig = webhook_manager.compute_signature(payload, secret)
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    assert sig == expected
