# -*- coding: utf-8 -*-
"""
Tests for Collaborator Event Mediator & Harmonious Pipeline (Phase 3).
Verifies fluid trade flow ('like flowing water') across A2A, Logistics, Satellite, Escrow, and A.GRID clearing.
"""

import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.collaborator_mediator import collaborator_mediator, HarmonizedTradeFlowRequest
from app.mcp_stdio import process_mcp_request

client = TestClient(app)


def test_mediator_direct_flow_execution():
    """Verify direct invocation of collaborator mediator fluid pipeline."""
    req = HarmonizedTradeFlowRequest(
        deal_id="DEAL-HARMONY-001",
        commodity="COPPER_CATHODE",
        volume_tons=2500.0,
        unit_price_usd_per_ton=9650.0,
        origin_country="CHL",
        destination_country="USA",
        buyer_agent_address="0x1111111111111111111111111111111111111111",
        seller_agent_address="0x2222222222222222222222222222222222222222",
        ebl_document_id="EBL-CHL-HOU-001",
        concession_id="CONCESSION-CHL-ANDINA-01",
        settlement_chain="polygon",
    )
    result = collaborator_mediator.flow_deal_to_settlement(req)

    assert result.status == "FLOW_HARMONIZED"
    assert result.deal_id == "DEAL-HARMONY-001"
    assert result.total_deal_value_usd == 24125000.0
    assert result.landed_cost_usd > 0
    assert result.maritime_transit_days > 0
    assert result.ebl_audit_status == "VERIFIED_AUTHENTIC"
    assert result.satellite_audit_compliant is True
    assert result.escrow_ready is True
    assert result.clearing_state == "A_GRID_CLEARING_APPROVED"
    assert result.pipeline_latency_ms < 500.0  # Ultra-fast pipeline
    assert result.harmonized_audit_hash.startswith("0x")


def test_mediator_http_api_endpoint():
    """Verify HTTP REST invocation of /api/v1/trade/harmonize-flow."""
    payload = {
        "deal_id": "DEAL-HARMONY-REST-002",
        "commodity": "NICKEL_MHP",
        "volume_tons": 1000.0,
        "unit_price_usd_per_ton": 16800.0,
        "origin_country": "IDN",
        "destination_country": "USA",
        "buyer_agent_address": "0x3333333333333333333333333333333333333333",
        "seller_agent_address": "0x4444444444444444444444444444444444444444",
        "ebl_document_id": "EBL-IDN-USA-002",
        "settlement_chain": "base",
    }
    resp = client.post("/api/v1/trade/harmonize-flow", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "FLOW_HARMONIZED"
    assert data["deal_id"] == "DEAL-HARMONY-REST-002"
    assert data["total_deal_value_usd"] == 16800000.0
    assert data["escrow_chain"] == "base"
    assert data["escrow_ready"] is True
    assert data["carbon_intensity_rating"] in ["A", "B", "C", "D", "E"]
    assert "DDS-" in data["traces_nt_reference"]


def test_mediator_mcp_tool_invocation():
    """Verify agent invocation via MCP JSON-RPC protocol."""
    mcp_req = {
        "jsonrpc": "2.0",
        "id": 999,
        "method": "tools/call",
        "params": {
            "name": "harmonize_trade_flow",
            "arguments": {
                "deal_id": "DEAL-MCP-HARMONY-003",
                "commodity": "LITHIUM_HYDROXIDE",
                "volume_tons": 500.0,
                "unit_price_usd_per_ton": 15000.0,
                "origin_country": "AUS",
                "destination_country": "USA",
                "buyer_agent_address": "0x5555555555555555555555555555555555555555",
                "seller_agent_address": "0x6666666666666666666666666666666666666666",
            }
        }
    }
    mcp_res = process_mcp_request(mcp_req) or {}
    assert "result" in mcp_res
    text_content = mcp_res["result"]["content"][0]["text"]
    parsed = json.loads(text_content)

    assert parsed["status"] == "FLOW_HARMONIZED"
    assert parsed["deal_id"] == "DEAL-MCP-HARMONY-003"
    assert parsed["total_deal_value_usd"] == 7500000.0
    assert parsed["ebl_audit_status"] == "VERIFIED_AUTHENTIC"
    assert parsed["clearing_state"] == "A_GRID_CLEARING_APPROVED"
