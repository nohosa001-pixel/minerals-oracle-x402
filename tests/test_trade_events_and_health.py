# -*- coding: utf-8 -*-
"""
Tests for Trade Events Stream & Health Probe endpoints.
Verifies SSE streaming, circular event buffer, and container orchestrator health checks.
"""

import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.collaborator_mediator import collaborator_mediator, HarmonizedTradeFlowRequest

client = TestClient(app)


def test_healthz_and_health_probes():
    """Verify liveness and readiness probe endpoints for Docker and Cloud Run."""
    r1 = client.get("/healthz")
    assert r1.status_code == 200
    data1 = r1.json()
    assert data1["status"] == "healthy"
    assert data1["service"] == "minerals-oracle-x402"

    r2 = client.get("/health")
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["status"] == "healthy"


def test_trade_events_recent_endpoint():
    """Verify in-memory circular buffer of trade events."""
    # First invoke a flow to generate an event
    req = HarmonizedTradeFlowRequest(
        deal_id="DEAL-SSE-TEST-001",
        commodity="LITHIUM_HYDROXIDE",
        volume_tons=100.0,
        unit_price_usd_per_ton=13500.0,
        origin_country="AUS",
        destination_country="USA",
        buyer_agent_address="0x1111111111111111111111111111111111111111",
        seller_agent_address="0x2222222222222222222222222222222222222222",
        settlement_chain="polygon",
    )
    collaborator_mediator.flow_deal_to_settlement(req)

    res = client.get("/api/v1/trade/events/recent?deal_id=DEAL-SSE-TEST-001")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"
    assert body["total"] >= 1
    assert body["events"][-1]["event_type"] == "DEAL_FLOW_HARMONIZED"
    assert body["events"][-1]["data"]["deal_id"] == "DEAL-SSE-TEST-001"


def test_trade_events_sse_stream_single_mode():
    """Verify SSE streaming connection handshake in single test mode."""
    headers = {"X-Test-Stream": "single"}
    res = client.get("/api/v1/trade/events/stream", headers=headers)
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]
    text = res.text
    assert "event: connected" in text
    assert '"event": "connected"' in text
