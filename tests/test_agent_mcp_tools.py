"""
Unit and Integration Tests for Agent MCP Tools (both stdio handler and REST dispatcher).
"""

import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.mcp_stdio import handle_tools_list, handle_tool_call

client = TestClient(app)


def test_mcp_stdio_tools_list():
    tools_resp = handle_tools_list("req_001")
    tool_names = [t["name"] for t in tools_resp["result"]["tools"]]
    assert "register_agent_account" in tool_names
    assert "get_agent_vault_balance" in tool_names
    assert "request_x402_payment_challenge" in tool_names
    assert "simulate_procurement_rfq" in tool_names
    assert "verify_copper_origin" in tool_names
    assert "verify_silver_origin" in tool_names


def test_mcp_stdio_register_and_check_balance():
    # 1. Register agent via stdio
    reg_call = handle_tool_call(
        "req_002",
        "register_agent_account",
        {
            "agent_name": "MCP-Test-Bot",
            "initial_trial_balance_usdc": 0.25,
        }
    )
    assert "result" in reg_call
    reg_data = json.loads(reg_call["result"]["content"][0]["text"])
    assert reg_data["status"] == "REGISTERED"
    session_key = reg_data["session_key"]

    # 2. Query balance via stdio
    bal_call = handle_tool_call(
        "req_003",
        "get_agent_vault_balance",
        {"session_key": session_key}
    )
    assert "result" in bal_call
    bal_data = json.loads(bal_call["result"]["content"][0]["text"])
    assert bal_data["balance_usdc"] == 0.25
    assert bal_data["status"] == "ACTIVE"


def test_mcp_stdio_request_x402_challenge():
    call_res = handle_tool_call(
        "req_004",
        "request_x402_payment_challenge",
        {"pricing_tier": "ONCHAIN", "chain": "base"}
    )
    assert "result" in call_res
    ch_data = json.loads(call_res["result"]["content"][0]["text"])
    assert ch_data["network"] == "base"
    assert "nonce" in ch_data


def test_mcp_stdio_simulate_rfq():
    call_res = handle_tool_call(
        "req_005",
        "simulate_procurement_rfq",
        {
            "rfq_id": "RFQ-STDIO-01",
            "cell_chemistry": "NCM811",
            "lithium_tons": 5.0,
            "lithium_origin_country": "AUS",
            "lithium_feoc_equity_pct": 0.0,
            "nickel_tons": 40.0,
            "nickel_origin_country": "CAN",
            "nickel_feoc_equity_pct": 0.0,
            "cobalt_tons": 5.0,
            "cobalt_origin_country": "CAN",
            "cobalt_feoc_equity_pct": 0.0,
        }
    )
    assert "result" in call_res
    rfq_data = json.loads(call_res["result"]["content"][0]["text"])
    assert rfq_data["status"] == "QUALIFIED"
    assert rfq_data["ira_fta_compliant"] is True


def test_mcp_http_invoke_tool():
    # Register via HTTP MCP
    reg_resp = client.post(
        "/mcp/invoke",
        json={
            "name": "register_agent_account",
            "arguments": {"agent_name": "HTTP-Agent-Bot", "initial_trial_balance_usdc": 0.50}
        }
    )
    assert reg_resp.status_code == 200
    res_obj = reg_resp.json()
    reg_data = json.loads(res_obj["content"][0]["text"])
    assert reg_data["status"] == "REGISTERED"
    session_key = reg_data["session_key"]

    # Check balance via HTTP MCP
    bal_resp = client.post(
        "/mcp/invoke",
        json={
            "name": "get_agent_vault_balance",
            "arguments": {"session_key": session_key}
        }
    )
    assert bal_resp.status_code == 200
    bal_obj = bal_resp.json()
    bal_data = json.loads(bal_obj["content"][0]["text"])
    assert bal_data["balance_usdc"] == 0.50


def test_mcp_get_trade_escrow_calldata():
    """Verify get_trade_escrow_calldata tool via both stdio handler and REST dispatcher."""
    from app.a2a_deal_engine import get_a2a_deal_engine
    from app.schemas import TradeDealSpec, TradeDealProposeRequest, TradeDealDualSignRequest, MineralType, SourceCountry

    deal_engine = get_a2a_deal_engine()
    deal_id = "DEAL-MCP-TEST-ESCROW-01"
    buyer_addr = "0x3333333333333333333333333333333333333333"
    seller_addr = "0x4444444444444444444444444444444444444444"

    spec = TradeDealSpec(
        deal_id=deal_id,
        commodity=MineralType.LITHIUM_HYDROXIDE,
        volume_tons=10.0,
        unit_price_usd_per_ton=20000.0,
        total_deal_value_usd=200000.0,
        origin_country=SourceCountry.AUS,
        destination_country="USA",
        feoc_cleared=True,
        mass_balance_cleared=True,
        ebl_document_id="EBL-MCP-LIT-01",
        buyer_agent_address=buyer_addr,
        seller_agent_address=seller_addr,
        created_at_utc="2026-09-22T12:00:00Z",
    )

    # 1. Propose & dual-sign deal
    deal_engine.propose_deal(TradeDealProposeRequest(spec=spec, seller_signature="0x" + "a" * 130))
    deal_engine.dual_sign_deal(TradeDealDualSignRequest(deal_id=deal_id, buyer_agent_address=buyer_addr, buyer_signature="0x" + "b" * 130))

    # 2. Check stdio tools/list includes get_trade_escrow_calldata
    list_resp = handle_tools_list("req_list_escrow")
    tools = [t["name"] for t in list_resp["result"]["tools"]]
    assert "get_trade_escrow_calldata" in tools

    # 3. Call via stdio handle_tool_call
    stdio_resp = handle_tool_call(
        "req_call_escrow",
        "get_trade_escrow_calldata",
        {"deal_id": deal_id, "chain_name": "polygon"}
    )
    assert "result" in stdio_resp
    res_data = json.loads(stdio_resp["result"]["content"][0]["text"])
    assert res_data["deal_id"] == deal_id
    assert res_data["escrow_contract_address"].lower() == "0x1270ddebad0ca90070342336a581eaACBA2060Ab".lower()
    assert res_data["function_signature"] == "createEscrow(bytes32,address,uint256,bytes32,uint256)"

    # 4. Call via REST POST /mcp/invoke
    http_resp = client.post(
        "/mcp/invoke",
        json={
            "name": "get_trade_escrow_calldata",
            "arguments": {"deal_id": deal_id, "chain_name": "base"}
        },
        headers={"X-Dev-Bypass": "true"}
    )
    assert http_resp.status_code == 200
    http_res_obj = http_resp.json()
    assert not http_res_obj["isError"]
    http_data = json.loads(http_res_obj["content"][0]["text"])
    assert http_data["escrow_contract_address"].lower() == "0xfCf3BF5fB5858db9aE81bE458B39b0032fc0C638".lower()


def test_machine_sitemap_discovery():
    """Verify /sitemap.xml is properly formatted and indexes critical agent endpoints."""
    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/xml"
    content = resp.text
    assert "<loc>http://localhost:8000/llms.txt</loc>" in content
    assert "<loc>http://localhost:8000/.well-known/agent.json</loc>" in content
    assert "<loc>http://localhost:8000/.well-known/a2a.json</loc>" in content
    assert "<loc>http://localhost:8000/mcp/tools</loc>" in content
