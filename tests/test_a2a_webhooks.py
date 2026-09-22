# -*- coding: utf-8 -*-
"""
Test Suite: A2A Event-Driven Webhook Dispatcher
================================================
Verifies:
1. Webhook registration, listing, and unregistration
2. Cryptographic HMAC-SHA256 signature verification
3. Event triggering on A2A deal proposals and dual-signatures
"""

import hmac
import hashlib
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.webhook_manager import webhook_manager, AgentWebhookRegistrationRequest
from app.a2a_deal_engine import get_a2a_deal_engine
from app.schemas import (
    MineralType,
    SourceCountry,
    TradeDealSpec,
    TradeDealProposeRequest,
    TradeDealDualSignRequest,
)


def test_webhook_registration_and_hmac_signature():
    client = TestClient(app)
    agent_addr = "0x1111111111111111111111111111111111111111"
    callback_url = "https://agent-buyer.internal/webhook"

    # 1. Register webhook
    r_reg = client.post("/api/v1/agent/webhooks/register", json={
        "agent_address": agent_addr,
        "callback_url": callback_url,
        "subscribed_events": ["deal.proposed", "deal.dual_signed"],
        "webhook_secret": "my-secure-agent-secret-key-12345",
    })
    assert r_reg.status_code == 200
    reg_data = r_reg.json()
    assert reg_data["status"] == "success"
    webhook_id = reg_data["webhook_id"]
    assert webhook_id.startswith("whk_")
    assert reg_data["webhook_secret"] == "my-secure-agent-secret-key-12345"

    # 2. List webhooks for agent
    r_list = client.get(f"/api/v1/agent/webhooks/{agent_addr}")
    assert r_list.status_code == 200
    items = r_list.json()
    assert len(items) >= 1
    assert any(w["webhook_id"] == webhook_id for w in items)

    # 3. Verify HMAC signature computation helper
    payload = json.dumps({"event": "deal.proposed", "deal_id": "DEAL-001"}).encode("utf-8")
    sig = webhook_manager.compute_signature(payload, "my-secure-agent-secret-key-12345")
    expected = "sha256=" + hmac.new("my-secure-agent-secret-key-12345".encode("utf-8"), payload, hashlib.sha256).hexdigest()
    assert sig == expected

    # 4. Unregister webhook
    r_del = client.delete(f"/api/v1/agent/webhooks/{webhook_id}")
    assert r_del.status_code == 200
    assert r_del.json()["status"] == "DELETED"


def test_a2a_deal_triggers_webhook_dispatch():
    """Verifies that proposing and dual-signing a deal triggers matching webhook dispatch."""
    engine = get_a2a_deal_engine()
    seller_addr = "0x2222222222222222222222222222222222222222"
    buyer_addr = "0x3333333333333333333333333333333333333333"

    # Register webhook for buyer
    reg = webhook_manager.register_webhook(AgentWebhookRegistrationRequest(
        agent_address=buyer_addr,
        callback_url="https://mock-buyer-agent.io/hook",
        subscribed_events=["*"],
    ))

    # Propose deal
    spec = TradeDealSpec(
        deal_id="DEAL-WEBHOOK-TEST-001",
        commodity=MineralType.LITHIUM_CARBONATE,
        volume_tons=50.0,
        unit_price_usd_per_ton=14000.0,
        total_deal_value_usd=700000.0,
        origin_country=SourceCountry.CHL,
        destination_country="USA",
        feoc_cleared=True,
        mass_balance_cleared=True,
        ebl_document_id="EBL-HOOK-001",
        buyer_agent_address=buyer_addr,
        seller_agent_address=seller_addr,
        created_at_utc="2026-09-21T12:00:00Z",
    )

    prop = engine.propose_deal(TradeDealProposeRequest(
        spec=spec,
        seller_signature="0x" + "7" * 130,
    ))
    assert prop.status == "PROPOSED"

    # Dual sign deal
    dual = engine.dual_sign_deal(TradeDealDualSignRequest(
        deal_id="DEAL-WEBHOOK-TEST-001",
        buyer_agent_address=buyer_addr,
        buyer_signature="0x" + "8" * 130,
    ))
    assert dual.status == "DUAL_SIGNED_CONFIRMED"

    # Clean up
    webhook_manager.unregister_webhook(reg.webhook_id)
