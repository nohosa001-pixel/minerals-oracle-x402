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
