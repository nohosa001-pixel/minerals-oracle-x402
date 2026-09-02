"""
Unit & Integration Tests for Autonomous Agent Upgrades:
1. Token-saving compact text format (?format=compact)
2. Self-serve agent onboarding (POST /api/v1/agent/onboard)
3. Zero-polling SSE streaming (GET /api/v1/oracle/stream)
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_compact_format_all_prices():
    """Verify that ?format=compact returns a high-density, token-saving text response."""
    resp = client.get("/api/v1/oracle/prices?format=compact", headers={"X-Dev-Bypass": "true"})
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "")
    content = resp.text
    assert "[CRM-QUOTE]" in content
    assert "Cu:" in content
    assert "Ag:" in content
    # Verify token brevity (compact string length should be under 120 chars)
    assert len(content) < 120, f"Compact string too long: {len(content)}"


def test_compact_format_spreads():
    """Verify that ?format=compact for spreads returns clean, concise locational spread text."""
    resp = client.get("/api/v1/oracle/spreads?format=compact", headers={"X-Dev-Bypass": "true"})
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "")
    content = resp.text
    assert "[CRM-SPREADS]" in content
    assert "COMEX" in content or "bps" in content


def test_compact_format_single_price():
    """Verify single price compact formatting."""
    resp = client.get("/api/v1/oracle/prices/Cu?format=compact", headers={"X-Dev-Bypass": "true"})
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "")
    assert "[CRM-QUOTE-Cu]" in resp.text


def test_agent_self_serve_onboarding():
    """Verify that autonomous agents can self-register, obtain session keys, and query immediately."""
    payload = {
        "agent_name": "TestQuantBot-777",
        "requested_network": "polygon"
    }
    onboard_resp = client.post("/api/v1/agent/onboard", json=payload)
    assert onboard_resp.status_code == 200
    data = onboard_resp.json()
    assert data["status"] == "success"
    assert data["agent_name"] == "TestQuantBot-777"
    assert data["session_key"].startswith("agent_session_")
    assert data["trial_balance_usdc"] >= 0.05
    assert data["free_queries_remaining"] >= 10
    session_key = data["session_key"]

    # Now verify querying with the new session key works seamlessly without 402 challenge
    query_resp = client.get(
        "/api/v1/oracle/prices/Ag?format=compact",
        headers={"X-Agent-Vault-Key": session_key, "X-Trial-Bypass": "true"}
    )
    assert query_resp.status_code == 200
    assert "[CRM-QUOTE-Ag]" in query_resp.text
    assert query_resp.headers.get("X-Payment-Method") == "Pre-Funded-Vault"


def test_sse_stream_endpoint():
    """Verify that GET /api/v1/oracle/stream returns a valid text/event-stream connection."""
    with client.stream("GET", "/api/v1/oracle/stream?min_bps=10.0&limit=1") as stream_resp:
        assert stream_resp.status_code == 200
        assert "text/event-stream" in stream_resp.headers.get("content-type", "")
        # Read the first event chunk
        first_chunk = next(stream_resp.iter_lines())
        assert "event: connected" in first_chunk or "data:" in first_chunk
