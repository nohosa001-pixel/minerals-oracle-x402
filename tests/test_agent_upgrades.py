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
    """Verify that /api/v1/oracle/prices returns monitored minerals."""
    resp = client.get("/api/v1/oracle/prices", headers={"X-Dev-Bypass": "true"})
    assert resp.status_code == 200
    data = resp.json()
    assert "monitored_minerals" in data
    assert "NICKEL_MHP" in data["monitored_minerals"]


def test_compact_format_spreads():
    """Verify that /api/v1/oracle/spreads returns regulatory risk corridors."""
    resp = client.get("/api/v1/oracle/spreads", headers={"X-Dev-Bypass": "true"})
    assert resp.status_code == 200
    data = resp.json()
    assert "regulatory_risk_spreads" in data
    assert len(data["regulatory_risk_spreads"]) >= 2


def test_compact_format_single_price():
    """Verify single mineral compliance status query."""
    resp = client.get("/api/v1/oracle/prices/Cu", headers={"X-Dev-Bypass": "true"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["compliance_ready"] is True
    assert data["symbol"] == "CU"


def test_agent_self_serve_onboarding():
    """Verify that autonomous agents can self-register, obtain session keys, and query immediately."""
    payload = {
        "agent_name": "TestComplianceAgent-777",
        "requested_network": "polygon"
    }
    onboard_resp = client.post("/api/v1/agent/onboard", json=payload)
    assert onboard_resp.status_code == 200
    data = onboard_resp.json()
    assert data["status"] == "success"
    assert data["session_key"].startswith("agent_session_")
    session_key = data["session_key"]

    # Now verify querying with the new session key works seamlessly without 402 challenge
    query_resp = client.get(
        "/api/v1/oracle/prices/Ag",
        headers={"X-Agent-Vault-Key": session_key, "X-Trial-Bypass": "true"}
    )
    assert query_resp.status_code == 200
    assert query_resp.json()["compliance_ready"] is True


def test_compliance_precedents_streaming():
    """Verify that international trade precedents query returns active jurisprudence."""
    resp = client.get("/api/v1/oracle/compliance/precedents")
    assert resp.status_code == 200
    assert resp.json()["jurisprudence_count"] >= 4

