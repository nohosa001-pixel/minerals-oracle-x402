"""
Unit & Integration Tests for Autonomous Agent Evolution & Proposals in Minerals Oracle x402.
Verifies REST API endpoints, MCP tool dispatching, and stdio execution for autonomous proposals.
"""

import pytest
import json
from fastapi.testclient import TestClient
from app.main import app
from app.evolution_manager import evolution_manager
from app.mcp_stdio import handle_tools_list, handle_tool_call


client = TestClient(app)


def test_list_initial_proposals():
    """Verify that initial seed proposals are present and correctly formatted."""
    response = client.get("/api/v1/oracle/agent/feedback")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["total_proposals"] >= 3
    
    # Check that seed proposal IDs exist
    feedback_ids = [p["feedback_id"] for p in data["items"]]
    assert any("PROP-LME" in fid for fid in feedback_ids)
    assert any("PROP-SATELLITE" in fid for fid in feedback_ids)
    assert any("PROP-FEOC" in fid for fid in feedback_ids)


def test_submit_agent_feedback_rest():
    """Verify an autonomous AI agent submitting an evolution proposal via REST API."""
    payload = {
        "agent_id": "test-procurement-agent-99",
        "feedback_type": "DATASET_SUGGESTION",
        "mineral_focus": "COBALT",
        "title": "Add DRC Artisanal Cobalt Fair-Trade GPS Polygon Boundary Check",
        "content": "Autonomous agents need to cross-check artisanal ASM cooperative boundaries in Katanga to verify no ASM-mined cobalt enters industrial refining streams without OECD red-flagging.",
        "proposed_solution": "Ingest RCS Global Better Mining ASM traceability polygon coordinates.",
        "caller_model": "claude-3-5-sonnet",
        "contact_channel": "agent-webhook://procure.drc-cobalt.org"
    }
    
    response = client.post("/api/v1/oracle/agent/feedback", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "PROPOSAL_ACCEPTED"
    assert "feedback_id" in data
    assert data["proposal"]["agent_id"] == "test-procurement-agent-99"
    assert data["proposal"]["mineral_focus"] == "COBALT"
    assert data["proposal"]["votes"] == 1


def test_vote_agent_feedback():
    """Verify upvoting a proposal by an agent."""
    # First submit or get a proposal
    props = evolution_manager.list_proposals(limit=1)
    target_id = props[0].feedback_id
    initial_votes = props[0].votes
    
    response = client.post(
        f"/api/v1/oracle/agent/feedback/{target_id}/vote",
        json={"voter_agent_id": "0x1234567890abcdef1234567890abcdef12345678"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "VOTE_RECORDED"
    assert data["votes"] == initial_votes + 1


def test_vote_nonexistent_feedback():
    """Verify 404 on voting for non-existent proposal."""
    response = client.post("/api/v1/oracle/agent/feedback/NON-EXISTENT-ID/vote")
    assert response.status_code == 404


def test_mcp_invoke_submit_feedback_free_of_charge():
    """Verify autonomous agents can submit feedback via FastMCP invoke without paying x402 fee."""
    tool_call = {
        "name": "minerals_submit_agent_feedback",
        "arguments": {
            "agent_id": "mcp-agent-bot-01",
            "title": "Support EIP-4337 Smart Account Batched Provenance",
            "content": "Requesting bundler sponsorship support for micro-lot provenance verification.",
            "feedback_type": "PROTOCOL_PROPOSAL",
            "mineral_focus": "LITHIUM",
            "caller_model": "gemini-1.5-pro"
        }
    }
    
    # Notice: No X-API-Key or 402 payment header is supplied
    response = client.post("/mcp/invoke", json=tool_call)
    assert response.status_code == 200
    data = response.json()
    assert not data["isError"]
    content_text = data["content"][0]["text"]
    parsed = json.loads(content_text)
    assert parsed["status"] == "PROPOSAL_ACCEPTED"
    assert "feedback_id" in parsed


def test_mcp_invoke_list_proposals():
    """Verify autonomous agents can list evolution proposals via FastMCP invoke."""
    tool_call = {
        "name": "minerals_list_evolution_proposals",
        "arguments": {"limit": 10, "mineral_focus": "ALL"}
    }
    
    response = client.post("/mcp/invoke", json=tool_call)
    assert response.status_code == 200
    data = response.json()
    assert not data["isError"]
    parsed = json.loads(data["content"][0]["text"])
    assert parsed["status"] == "SUCCESS"
    assert parsed["total_proposals"] >= 3


def test_mcp_stdio_tools_and_execution():
    """Verify mcp_stdio handler lists evolution tools and executes submit/list."""
    tools_resp = handle_tools_list("req-1")
    tool_names = [t["name"] for t in tools_resp["result"]["tools"]]
    assert "minerals_submit_agent_feedback" in tool_names
    assert "minerals_list_evolution_proposals" in tool_names
    
    # Execute tool call via stdio handler
    exec_resp = handle_tool_call(
        req_id="req-2",
        name="minerals_submit_agent_feedback",
        arguments={
            "agent_id": "stdio-agent-77",
            "title": "Add ISO 14040 Life Cycle Assessment Carbon Intensity Formula",
            "content": "Include Scope 1-3 GHG emission factor calculation for nickel sulfate crystallization."
        }
    )
    assert "result" in exec_resp
    result_text = exec_resp["result"]["content"][0]["text"]
    result_json = json.loads(result_text)
    assert result_json["status"] == "PROPOSAL_ACCEPTED"
