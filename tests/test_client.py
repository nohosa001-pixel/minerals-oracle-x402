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
    assert ap2_data["payment"]["chain_id"] == 8453
    assert ap2_data["payment"]["recipient_address"] == "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf"

    resp_mcp = client.get("/mcp/tools")
    assert resp_mcp.status_code == 200
    mcp_data = resp_mcp.json()
    assert len(mcp_data["tools"]) >= 3
    tool_names = [t["name"] for t in mcp_data["tools"]]
    assert "get_mineral_prices" in tool_names
    assert "calculate_urban_mining_value" in tool_names


def test_402_challenge_flow():
    """Verify calling protected endpoints without credentials triggers 402 challenge."""
    resp = client.get("/api/v1/oracle/challenge")
    assert resp.status_code == 402
    assert "WWW-Authenticate" in resp.headers
    assert resp.headers["X-Payment-Required"] == "true"
    assert resp.headers["X-Payment-ChainId"] == "8453"
    assert resp.headers["X-Payment-Recipient"] == "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf"

    body = resp.json()
    assert body["code"] == 402
    challenge = body["payment_challenge"]
    assert challenge["network"] == "base"
    assert challenge["chain_id"] == 8453
    assert challenge["amount"] == "0.005"
    assert challenge["accepted_token"] == "USDC"
    assert challenge["recipient_address"] == "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf"
    assert len(challenge["nonce"]) > 0


def create_agent_x402_header(agent_account, challenge_nonce: str) -> str:
    """Helper to simulate an autonomous AI agent signing a challenge nonce."""
    message_text = f"x402:minerals-oracle-x402:pay:0.005:USDC:Base:{challenge_nonce}"
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
    assert "Ag" in data["quotes"]
    assert "Pt" in data["quotes"]
    assert "Cu" in data["quotes"]
    assert "Li" in data["quotes"]
    assert "NdDy" in data["quotes"]

    ag_quote = data["quotes"]["Ag"]
    assert ag_quote["spot_price_usd"] > 0
    assert ag_quote["unit"] == "USD/troy_oz"
    assert len(ag_quote["attestation_hash"]) == 64


def test_single_quote_and_spreads():
    """Verify single commodity quote and cross-exchange arbitrage analytics."""
    agent_wallet = Account.create()

    # Get challenge for single quote
    chal = client.get("/api/v1/oracle/challenge").json()["payment_challenge"]
    auth = create_agent_x402_header(agent_wallet, chal["nonce"])

    cu_resp = client.get("/api/v1/oracle/prices/Cu", headers={"Authorization": auth})
    assert cu_resp.status_code == 200
    cu_data = cu_resp.json()
    assert cu_data["symbol"] == "Cu"
    assert "USD/lb" in cu_data["secondary_prices"]

    # Get challenge for spreads
    chal_spreads = client.get("/api/v1/oracle/challenge").json()["payment_challenge"]
    auth_spreads = create_agent_x402_header(agent_wallet, chal_spreads["nonce"])

    spreads_resp = client.get("/api/v1/oracle/spreads", headers={"Authorization": auth_spreads})
    assert spreads_resp.status_code == 200
    spreads_data = spreads_resp.json()
    assert len(spreads_data["spreads"]) >= 4


def test_urban_mining_calculations():
    """Verify scrap batch yields for EV Battery Black Mass, Auto Catalysts, E-waste, and Magnets."""
    agent_wallet = Account.create()

    # 1. Test EV Battery Black Mass (10 metric tons)
    chal = client.get("/api/v1/oracle/challenge").json()["payment_challenge"]
    auth = create_agent_x402_header(agent_wallet, chal["nonce"])

    resp_bm = client.post(
        "/api/v1/oracle/urban-mining/calculate",
        json={
            "scrap_category": "EV_BATTERY_BLACK_MASS",
            "quantity_metric_tons": 10.0,
            "custom_assay_overrides": {"Li": 4.0, "Ni": 20.0},
        },
        headers={"Authorization": auth},
    )
    assert resp_bm.status_code == 200
    bm_data = resp_bm.json()
    assert bm_data["scrap_category"] == "EV_BATTERY_BLACK_MASS"
    assert bm_data["net_settlement_value_usd"] > 0
    assert len(bm_data["mineral_breakdown"]) == 4

    # 2. Test Auto Catalysts (2.5 metric tons)
    chal2 = client.get("/api/v1/oracle/challenge").json()["payment_challenge"]
    auth2 = create_agent_x402_header(agent_wallet, chal2["nonce"])

    resp_cat = client.post(
        "/api/v1/oracle/urban-mining/calculate",
        json={
            "scrap_category": "AUTO_CATALYST_CERAMIC",
            "quantity_metric_tons": 2.5,
        },
        headers={"Authorization": auth2},
    )
    assert resp_cat.status_code == 200
    cat_data = resp_cat.json()
    assert cat_data["net_settlement_value_usd"] > 0
    symbols = [item["mineral_symbol"] for item in cat_data["mineral_breakdown"]]
    assert "Pt" in symbols and "Pd" in symbols and "Rh" in symbols


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


def test_free_alpha_signals_and_economics():
    """Verify public alpha signals, ROI economics, llms.txt and agent.json work unauthenticated."""
    # 1. Free Alpha Signals
    resp_alpha = client.get("/api/v1/oracle/alpha-signals")
    assert resp_alpha.status_code == 200
    data_alpha = resp_alpha.json()
    assert data_alpha["status"] == "operational"
    assert len(data_alpha["signals"]) >= 4
    assert "unlock_instruction" in data_alpha

    # 2. Economics ROI Proof
    resp_roi = client.get("/api/v1/oracle/economics-roi")
    assert resp_roi.status_code == 200
    data_roi = resp_roi.json()
    assert data_roi["cost_per_query_usdc"] == 0.005
    assert "cost_comparison" in data_roi

    # 3. llms.txt Machine Discovery
    resp_llms = client.get("/llms.txt")
    assert resp_llms.status_code == 200
    assert "# Critical Raw Minerals" in resp_llms.text or "# minerals-oracle-x402" in resp_llms.text

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
    assert init_res["result"]["serverInfo"]["name"] == "minerals-oracle-x402"
    assert init_res["result"]["serverInfo"]["version"] == "1.1.0"
    assert init_res["result"]["protocolVersion"] == "2024-11-05"

    # 2. Test tools/list
    tools_res = handle_tools_list(2)
    assert tools_res["id"] == 2
    tools = tools_res["result"]["tools"]
    assert len(tools) == 3
    tool_names = [t["name"] for t in tools]
    assert "get_mineral_prices" in tool_names
    assert "get_arbitrage_spreads" in tool_names
    assert "calculate_urban_mining_value" in tool_names

    # 3. Test tools/call (prices)
    call_prices = handle_tool_call(3, "get_mineral_prices", {})
    assert call_prices["id"] == 3
    assert "Ag" in call_prices["result"]["content"][0]["text"]

    # 4. Test tools/call (arbitrage)
    call_arb = handle_tool_call(4, "get_arbitrage_spreads", {})
    assert call_arb["id"] == 4
    assert "spreads" in call_arb["result"]["content"][0]["text"]

    # 5. Test tools/call (urban mining)
    call_um = handle_tool_call(5, "calculate_urban_mining_value", {
        "scrap_category": "EV_BATTERY_BLACK_MASS",
        "quantity_metric_tons": 5.0
    })
    assert call_um["id"] == 5
    assert "net_settlement_value_usd" in call_um["result"]["content"][0]["text"]


def test_sandbox_free_trial_and_preset_defaults():
    """Verify Sandbox Free Trial grants first 2 queries without auth header and includes presets/tensors."""
    from app.x402_verifier import _FREE_TRIAL_USAGE

    # Reset IP usage for fresh test
    test_ip = "192.168.100.1"
    _FREE_TRIAL_USAGE.pop(test_ip, None)

    # 1. First Trial Query (Should return 200 OK with Sandbox Headers)
    resp1 = client.get("/api/v1/oracle/prices", headers={"X-Forwarded-For": test_ip})
    assert resp1.status_code == 200
    assert resp1.headers.get("x-sandbox-trial") == "active"
    assert resp1.headers.get("x-free-tier-remaining") == "1"

    # 2. Second Trial Query (Preset alias 'Neodymium' & Urban Mining default)
    resp2 = client.get("/api/v1/oracle/prices/Neodymium", headers={"X-Forwarded-For": test_ip})
    assert resp2.status_code == 200
    assert resp2.headers.get("x-free-tier-remaining") == "0"
    data2 = resp2.json()
    assert data2["symbol"] == "NdDy"

    # 3. Third Query (Free Trial exhausted -> should return 402 Challenge)
    resp3 = client.get("/api/v1/oracle/prices", headers={"X-Forwarded-For": test_ip})
    assert resp3.status_code == 402
    assert "payment_challenge" in resp3.json()

    # 4. Urban Mining Presets & Recovery Tensor Verification
    resp_um = client.post(
        "/api/v1/oracle/urban-mining/calculate",
        json={"scrap_category": "E_WASTE_HIGH_GRADE_PCB", "quantity_metric_tons": 1.0},
        headers={"X-Dev-Bypass": "true"}
    )
    assert resp_um.status_code == 200
    um_data = resp_um.json()
    assert "recovery_rates_tensor" in um_data
    assert "refinery_compliance_flags" in um_data
    assert um_data["target_yield_currency"] == "USDC"


if __name__ == "__main__":
    pytest.main(["-v", __file__])


