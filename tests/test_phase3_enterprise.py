"""
Integration and unit tests for Phase 3: Enterprise VIP Keys and SLA Observability.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.enterprise_manager import enterprise_manager


client = TestClient(app)


def test_prometheus_metrics_endpoint():
    """Tests GET /metrics returns standard Prometheus text exposition format."""
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    body = resp.text
    assert "oracle_uptime_seconds" in body
    assert "oracle_queries_total" in body
    assert 'oracle_mineral_spot_price_usd{symbol="Cu"}' in body


def test_enterprise_sla_status_endpoint():
    """Tests GET /api/v1/enterprise/sla-status telemetry report."""
    resp = client.get("/api/v1/enterprise/sla-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "minerals-oracle-x402-enterprise"
    assert "99.99%" in data["sla_tier"]
    assert data["latency_telemetry"]["p50_ms"] < 1.0
    assert data["latency_telemetry"]["p99_ms"] < 2.5
    assert data["capacity"]["max_throughput_qps"] >= 25_000


def test_enterprise_key_provision_and_vip_access():
    """Tests provisioning an enterprise key and using it for priority VIP access without x402 payment challenge."""
    # 1. Provision new key for Citadel Commodities AI
    prov_payload = {
        "organization_name": "Citadel Commodities AI Hedge Fund",
        "contact_email": "commodities-quant@citadel-ai.com",
        "tier_plan": "Enterprise-10Gbps-Dedicated",
    }
    prov_resp = client.post("/api/v1/enterprise/provision-key", json=prov_payload)
    assert prov_resp.status_code == 200
    prov_data = prov_resp.json()
    ent_key = prov_data["enterprise_key"]
    assert ent_key.startswith("ent_key_")

    # 2. Access protected price feed with X-Enterprise-Key (Priority VIP Bypass)
    headers = {
        "X-Enterprise-Key": ent_key,
        "X-Trial-Bypass": "true",
    }
    feed_resp = client.get("/api/v1/oracle/prices", headers=headers)
    assert feed_resp.status_code == 200
    assert feed_resp.headers["X-Enterprise-Tenant"] == "Citadel Commodities AI Hedge Fund"
    receipt_id = feed_resp.headers.get("X-Receipt-ID")
    assert receipt_id is not None and receipt_id.startswith("rcpt_")

    # 3. Access with default Goldman test key
    headers_goldman = {
        "X-Enterprise-Key": "ent_key_goldman_commodity_quant_2026",
        "X-Trial-Bypass": "true",
    }
    g_resp = client.get("/api/v1/oracle/spreads", headers=headers_goldman)
    assert g_resp.status_code == 200
    assert "Global Commodity Quant" in g_resp.headers["X-Enterprise-Tenant"]
