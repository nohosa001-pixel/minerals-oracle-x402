import base64
import json
import pytest
from fastapi.testclient import TestClient
from eth_account import Account
from eth_account.messages import encode_defunct

from app.main import app

client = TestClient(app)


def test_public_system_endpoints():
    """Verify metadata and health endpoints respond with 200 without payment."""
    resp_root = client.get("/")
    assert resp_root.status_code == 200
    data_root = resp_root.json()
    assert data_root["service"] == "minerals-oracle-x402"
    assert data_root["protocol"] == "x402 (HTTP 402 Monetized)"

    resp_health = client.get("/health")
    assert resp_health.status_code == 200
    data_health = resp_health.json()
    assert data_health["status"] == "healthy"
    assert "Ag" in data_health["commodities_tracked"]


def test_ap2_manifest_and_mcp_spec():
    """Verify AP2 manifest and MCP tool definitions are publicly discoverable."""
    resp_ap2 = client.get("/.well-known/ap2")
    assert resp_ap2.status_code == 200
    ap2_data = resp_ap2.json()
    assert ap2_data["ap2_version"] == "0.2.0"
    assert ap2_data["name"] == "minerals-oracle-x402"
    assert ap2_data["payment"]["chain_id"] == 137
    assert ap2_data["payment"]["recipient_address"] == "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf"

    resp_mcp = client.get("/mcp/tools")
    assert resp_mcp.status_code == 200
    mcp_data = resp_mcp.json()
    assert len(mcp_data["tools"]) >= 3
    tool_names = [t["name"] for t in mcp_data["tools"]]
    assert "verify_composite_battery_passport" in tool_names
    assert "verify_mineral_lot_compliance" in tool_names


def test_402_challenge_flow():
    """Verify calling protected endpoints without credentials triggers 402 challenge."""
    resp = client.get("/api/v1/oracle/challenge")
    assert resp.status_code == 402
    assert "WWW-Authenticate" in resp.headers
    assert resp.headers["X-Payment-Required"] == "true"
    assert resp.headers["X-Payment-ChainId"] == "137"
    assert resp.headers["X-Payment-Recipient"] == "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf"

    body = resp.json()
    assert body["code"] == 402
    challenge = body["payment_challenge"]
    assert challenge["network"] == "polygon"
    assert challenge["chain_id"] == 137
    assert challenge["amount"] == "0.005"
    assert challenge["accepted_token"] == "USDC"
    assert challenge["recipient_address"] == "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf"
    assert len(challenge["nonce"]) > 0


def create_agent_x402_header(agent_account, challenge_nonce: str) -> str:
    """Helper to simulate an autonomous AI agent signing a challenge nonce."""
    message_text = f"x402:minerals-oracle-x402:pay:0.005:USDC:Polygon:{challenge_nonce}"
    signable_msg = encode_defunct(text=message_text)
    signed = agent_account.sign_message(signable_msg)
    
    payload = {
        "nonce": challenge_nonce,
        "signature": signed.signature.hex(),
        "signer": agent_account.address,
    }
    payload_b64 = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
    return f"x402 {payload_b64}"


def test_authenticated_prices_feed():
    """Verify autonomous agent full 402 challenge -> sign -> query flow."""
    # 1. Generate autonomous agent test wallet
    agent_wallet = Account.create()

    # 2. Initial request -> Get 402 Challenge
    challenge_resp = client.get("/api/v1/oracle/challenge")
    assert challenge_resp.status_code == 402
    nonce = challenge_resp.json()["payment_challenge"]["nonce"]

    # 3. Agent signs payment proof
    auth_header = create_agent_x402_header(agent_wallet, nonce)

    # 4. Agent sends authorized request
    feed_resp = client.get("/api/v1/oracle/prices", headers={"Authorization": auth_header})
    assert feed_resp.status_code == 200
    data = feed_resp.json()
    assert data["oracle"] == "minerals-oracle-x402"
    assert "monitored_minerals" in data
    assert "NICKEL_MHP" in data["monitored_minerals"]


def test_single_quote_and_spreads():
    """Verify single mineral compliance and regulatory risk corridors."""
    agent_wallet = Account.create()

    # Get challenge for single quote
    chal = client.get("/api/v1/oracle/challenge").json()["payment_challenge"]
    auth = create_agent_x402_header(agent_wallet, chal["nonce"])

    cu_resp = client.get("/api/v1/oracle/prices/Cu", headers={"Authorization": auth})
    assert cu_resp.status_code == 200
    cu_data = cu_resp.json()
    assert cu_data["symbol"] == "CU"
    assert cu_data["compliance_ready"] is True

    # Get challenge for spreads
    chal_spreads = client.get("/api/v1/oracle/challenge").json()["payment_challenge"]
    auth_spreads = create_agent_x402_header(agent_wallet, chal_spreads["nonce"])

    spreads_resp = client.get("/api/v1/oracle/spreads", headers={"Authorization": auth_spreads})
    assert spreads_resp.status_code == 200
    spreads_data = spreads_resp.json()
    assert len(spreads_data["regulatory_risk_spreads"]) >= 2


def test_compliance_status_check():
    """Verify compliance status endpoint returns active 7-pillars and 12-traps."""
    resp = client.get("/api/v1/oracle/compliance/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "HEALTHY"
    assert data["pillars_active"] == 7
    assert data["traps_defended"] == 12


def test_mcp_tool_invocation():
    """Verify MCP tool call execution via HTTP."""
    agent_wallet = Account.create()

    # Get challenge
    chal = client.get("/api/v1/oracle/challenge").json()["payment_challenge"]
    auth = create_agent_x402_header(agent_wallet, chal["nonce"])

    resp = client.post(
        "/mcp/invoke",
        json={"name": "get_mineral_prices", "arguments": {}},
        headers={"Authorization": auth},
    )
    assert resp.status_code == 200
    mcp_resp = resp.json()
    assert mcp_resp["isError"] is False
    content_text = mcp_resp["content"][0]["text"]
    assert "minerals-oracle-x402" in content_text


def test_invalid_signature_rejection():
    """Verify forged or corrupted signatures are rejected with 402."""
    agent_wallet = Account.create()
    chal = client.get("/api/v1/oracle/challenge").json()["payment_challenge"]

    # Sign wrong text
    bad_msg = encode_defunct(text="wrong-message-content")
    signed = agent_wallet.sign_message(bad_msg)

    payload = {
        "nonce": chal["nonce"],
        "signature": signed.signature.hex(),
        "signer": agent_wallet.address,
    }
    payload_b64 = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")

    resp = client.get("/api/v1/oracle/prices", headers={"Authorization": f"x402 {payload_b64}"})
    assert resp.status_code == 402


def test_replay_attack_prevention():
    """Verify challenge nonces cannot be replayed twice."""
    agent_wallet = Account.create()
    chal = client.get("/api/v1/oracle/challenge").json()["payment_challenge"]
    auth = create_agent_x402_header(agent_wallet, chal["nonce"])

    # First request: Success
    resp1 = client.get("/api/v1/oracle/prices", headers={"Authorization": auth, "X-Trial-Bypass": "true"})
    assert resp1.status_code == 200

    # Second request (replay with same nonce): Must be 402 Payment Required
    resp2 = client.get("/api/v1/oracle/prices", headers={"Authorization": auth, "X-Trial-Bypass": "true"})
    assert resp2.status_code == 402


def test_free_tier_quota_and_exhaustion():
    """Verify sandbox free tier grants 2 trials and requires payment on 3rd query."""
    test_ip = "192.0.2.123"
    
    # 1st query: Free trial (1 remaining)
    r1 = client.get("/api/v1/oracle/prices", headers={"X-Forwarded-For": test_ip})
    assert r1.status_code == 200
    assert r1.headers.get("X-Free-Tier-Remaining") == "1"

    # 2nd query: Free trial (0 remaining)
    r2 = client.get("/api/v1/oracle/prices", headers={"X-Forwarded-For": test_ip})
    assert r2.status_code == 200
    assert r2.headers.get("X-Free-Tier-Remaining") == "0"

    # 3rd query: Quota exhausted -> 402 Payment Required
    r3 = client.get("/api/v1/oracle/prices", headers={"X-Forwarded-For": test_ip})
    assert r3.status_code == 402
    assert "WWW-Authenticate" in r3.headers


def test_free_alpha_signals_and_economics():
    """Verify public alpha signals, ROI economics, llms.txt and agent.json work unauthenticated."""
    # 1. Free Alpha Signals
    resp_alpha = client.get("/api/v1/oracle/alpha-signals")
    assert resp_alpha.status_code == 200
    data_alpha = resp_alpha.json()
    assert data_alpha["status"] == "operational"
    assert len(data_alpha["active_monitored_nations"]) >= 8
    assert len(data_alpha["active_trade_precedents"]) >= 4
    assert data_alpha["compliance_rules_loaded"] == 12

    # 2. Economics ROI Proof
    resp_roi = client.get("/api/v1/oracle/economics-roi")
    assert resp_roi.status_code == 200
    data_roi = resp_roi.json()
    assert data_roi["cost_per_query_usdc"] == 0.005
    assert "cost_comparison" in data_roi

    # 3. llms.txt Machine Discovery
    resp_llms = client.get("/llms.txt")
    assert resp_llms.status_code == 200
    assert "# Critical Minerals" in resp_llms.text or "# minerals-oracle-x402" in resp_llms.text

    # 4. agent.json Manifest
    resp_agent = client.get("/.well-known/agent.json")
    assert resp_agent.status_code == 200
    agent_manifest = resp_agent.json()
    assert agent_manifest["schema_version"] == "v1"
    assert agent_manifest["auth"]["amount_usdc"] == 0.005


def test_mcp_stdio_jsonrpc_protocol():
    """Verify MCP stdio protocol handlers: initialize, ping, tools/list, tools/call."""
    from app.mcp_stdio import handle_initialize, handle_tools_list, handle_tool_call

    # 1. Test initialize
    init_res = handle_initialize(1)
    assert init_res["id"] == 1
    assert init_res["result"]["serverInfo"]["name"] == "battery-passport-oracle"
    assert init_res["result"]["serverInfo"]["version"] == "2.0.0"
    assert init_res["result"]["protocolVersion"] == "2024-11-05"

    # 2. Test tools/list
    tools_res = handle_tools_list(2)
    assert tools_res["id"] == 2
    tools = tools_res["result"]["tools"]
    assert len(tools) >= 3
    tool_names = [t["name"] for t in tools]
    assert "verify_mineral_lot_compliance" in tool_names
    assert "list_trade_precedents" in tool_names
    assert "get_compliance_status" in tool_names
    assert "minerals_submit_agent_feedback" in tool_names

    # 3. Test tools/call (precedents)
    call_prec = handle_tool_call(3, "list_trade_precedents", {})
    assert call_prec["id"] == 3
    assert "WTO_DS592" in call_prec["result"]["content"][0]["text"]

    # 4. Test tools/call (compliance status)
    call_status = handle_tool_call(4, "get_compliance_status", {})
    assert call_status["id"] == 4
    assert "ComplianceEngine" in call_status["result"]["content"][0]["text"]

    # 5. Test tools/call (verify lot compliance)
    call_verify = handle_tool_call(5, "verify_mineral_lot_compliance", {
        "lot_id": "LOT-MCP-001",
        "mineral_type": "NICKEL_MHP",
        "source_country": "IDN",
        "net_weight_metric_tons": 100.0,
        "declared_purity_pct": 99.5
    })
    assert call_verify["id"] == 5
    assert "COMPLIANT" in call_verify["result"]["content"][0]["text"]


def test_sandbox_free_trial_and_preset_defaults():
    """Verify Sandbox Free Trial grants first 2 queries without auth header and includes presets."""
    from app.x402_verifier import _FREE_TRIAL_USAGE

    # Reset IP usage for fresh test
    test_ip = "192.168.100.1"
    _FREE_TRIAL_USAGE.pop(test_ip, None)

    # 1. First Trial Query (Should return 200 OK with Sandbox Headers)
    resp1 = client.get("/api/v1/oracle/prices", headers={"X-Forwarded-For": test_ip})
    assert resp1.status_code == 200
    assert resp1.headers.get("x-sandbox-trial") == "active"
    assert resp1.headers.get("x-free-tier-remaining") == "1"

    # 2. Second Trial Query (Preset alias 'Neodymium')
    resp2 = client.get("/api/v1/oracle/prices/Neodymium", headers={"X-Forwarded-For": test_ip})
    assert resp2.status_code == 200
    assert resp2.headers.get("x-free-tier-remaining") == "0"
    data2 = resp2.json()
    assert data2["symbol"] == "NEODYMIUM"

    # 3. Third Query (Free Trial exhausted -> should return 402 Challenge)
    resp3 = client.get("/api/v1/oracle/prices", headers={"X-Forwarded-For": test_ip})
    assert resp3.status_code == 402
    assert "payment_challenge" in resp3.json()

    # 4. Compliance Precedents Route Verification
    resp_prec = client.get("/api/v1/oracle/compliance/precedents")
    assert resp_prec.status_code == 200
    prec_data = resp_prec.json()
    assert prec_data["jurisprudence_count"] >= 4


if __name__ == "__main__":
    pytest.main(["-v", __file__])


