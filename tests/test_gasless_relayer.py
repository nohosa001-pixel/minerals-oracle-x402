# -*- coding: utf-8 -*-
"""
Test Suite: Gasless On-Chain Relayer (Meta-Transaction Sponsorship)
==================================================================
Verifies:
1. Sponsoring A2A trade deal attestation anchoring on Polygon
2. Sponsoring EU Battery Passport minting on Polygon
3. REST endpoints /api/v1/relay/sponsor-deal-attestation & /api/v1/relay/sponsor-battery-passport
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.gasless_relayer import (
    gasless_relayer,
    SponsoredDealAttestationRequest,
    SponsoredPassportMintRequest,
)


def test_gasless_relayer_deal_attestation_sponsorship():
    req = SponsoredDealAttestationRequest(
        deal_id="DEAL-GASLESS-TEST-001",
        deal_hash="0x" + "a" * 64,
        buyer_agent_address="0x" + "8" * 40,
        seller_agent_address="0x" + "7" * 40,
    )
    res = gasless_relayer.sponsor_deal_attestation(req)
    assert res.status == "SPONSORED_SUCCESS"
    assert res.chain_id == 137
    assert res.operation == "A2A_DEAL_ATTESTATION_ANCHOR"
    assert res.tx_hash.startswith("0x")
    assert res.sponsored_gas_pol > 0.0


def test_gasless_relayer_passport_minting_sponsorship():
    req = SponsoredPassportMintRequest(
        lot_id="LOT-GASLESS-BAT-001",
        mineral_type="NICKEL_MHP",
        compliance_verdict="PASSED_TIER_1",
        agent_address="0x" + "9" * 40,
    )
    res = gasless_relayer.sponsor_battery_passport(req)
    assert res.status == "SPONSORED_SUCCESS"
    assert res.operation == "BATTERY_PASSPORT_MINT"
    assert res.tx_hash.startswith("0x")


def test_gasless_relayer_rest_endpoints():
    client = TestClient(app)

    # 1. Sponsor deal attestation endpoint
    r_deal = client.post("/api/v1/relay/sponsor-deal-attestation", json={
        "deal_id": "DEAL-RELAY-API-001",
        "deal_hash": "0x" + "b" * 64,
        "buyer_agent_address": "0x" + "8" * 40,
        "seller_agent_address": "0x" + "7" * 40,
    })
    assert r_deal.status_code == 200
    data_deal = r_deal.json()
    assert data_deal["status"] == "SPONSORED_SUCCESS"
    assert data_deal["chain_id"] == 137

    # 2. Sponsor battery passport endpoint
    r_pass = client.post("/api/v1/relay/sponsor-battery-passport", json={
        "lot_id": "LOT-RELAY-API-001",
        "mineral_type": "LITHIUM_HYDROXIDE",
        "compliance_verdict": "VERIFIED",
        "agent_address": "0x" + "9" * 40,
    })
    assert r_pass.status_code == 200
    data_pass = r_pass.json()
    assert data_pass["status"] == "SPONSORED_SUCCESS"
    assert data_pass["tx_hash"].startswith("0x")
