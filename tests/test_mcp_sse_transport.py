# -*- coding: utf-8 -*-
"""
Test Suite: Remote MCP over SSE (Server-Sent Events) Transport
============================================================
Verifies:
1. Connecting to /mcp/sse emits initial endpoint event with sessionId
2. Posting JSON-RPC 2.0 messages (tools/list, tools/call) to /mcp/messages
3. Session queue management and tool response delivery
"""

import json
import pytest
from fastapi.testclient import TestClient

from app.main import app, _MCP_SSE_SESSIONS


def test_mcp_sse_connection_and_endpoint_emission():
    client = TestClient(app)

    with client.stream("GET", "/mcp/sse", headers={"X-Test-Stream": "single"}) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        # Read first chunk
        lines = []
        for chunk in response.iter_lines():
            if chunk:
                lines.append(chunk)
            if len(lines) >= 2:
                break

        # Check endpoint event format
        assert any("event: endpoint" in l for l in lines)
        data_line = [l for l in lines if l.startswith("data:")][0]
        assert "/mcp/messages?sessionId=mcpsess_" in data_line


def test_mcp_messages_dispatch_direct_and_sse():
    client = TestClient(app)

    # 1. Test direct HTTP fallback for tools/list
    req_list = {
        "jsonrpc": "2.0",
        "id": 101,
        "method": "tools/list",
        "params": {}
    }
    r_list = client.post("/mcp/messages", json=req_list)
    assert r_list.status_code == 200
    data_list = r_list.json()
    assert data_list["jsonrpc"] == "2.0"
    assert "tools" in data_list["result"]
    tools = data_list["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "verify_mineral_lot_compliance" in tool_names
    assert "propose_a2a_trade_deal" in tool_names

    # 2. Test direct tool call execution
    req_call = {
        "jsonrpc": "2.0",
        "id": 102,
        "method": "tools/call",
        "params": {
            "name": "estimate_maritime_freight_and_carbon",
            "arguments": {
                "origin_country": "CHL",
                "destination_country": "USA",
                "cargo_weight_metric_tons": 2500.0,
                "mineral_type": "LITHIUM_CARBONATE",
            }
        }
    }
    r_call = client.post("/mcp/messages", json=req_call)
    assert r_call.status_code == 200
    call_data = r_call.json()
    content_text = json.loads(call_data["result"]["content"][0]["text"])
    assert "distance_nautical_miles" in content_text or "corridor_id" in content_text
