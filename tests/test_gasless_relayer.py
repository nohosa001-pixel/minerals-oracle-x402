# -*- coding: utf-8 -*-
"""
Test Suite: Gasless On-Chain Relayer (Meta-Transaction & Multi-Chain Gas Sponsorship)
=====================================================================================
Verifies:
1. Sponsoring A2A trade deal attestation anchoring on Polygon, Base, and Arbitrum
2. Sponsoring EU Battery Passport minting across supported chains
3. Multi-chain gas balance introspection (Polygon POL, Base ETH, Arbitrum ETH)
4. REST endpoints /api/v1/relay/sponsor-deal-attestation, /api/v1/relay/sponsor-battery-passport,
   and /api/v1/relay/multichain/gas-balances
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
    # Polygon
    req_poly = SponsoredDealAttestationRequest(
        deal_id="DEAL-GASLESS-TEST-001",
        deal_hash="0x" + "a" * 64,
        buyer_agent_address="0x" + "8" * 40,
        seller_agent_address="0x" + "7" * 40,
        chain="polygon",
    )
    res_poly = gasless_relayer.sponsor_deal_attestation(req_poly)
    assert res_poly.status == "SPONSORED_SUCCESS"
    assert res_poly.chain_id == 137
    assert res_poly.gas_token == "POL"
    assert res_poly.operation == "A2A_DEAL_ATTESTATION_ANCHOR"
    assert res_poly.tx_hash.startswith("0x")
    assert res_poly.sponsored_gas_pol > 0.0

    # Base
    req_base = SponsoredDealAttestationRequest(
        deal_id="DEAL-GASLESS-BASE-001",
        deal_hash="0x" + "b" * 64,
        buyer_agent_address="0x" + "8" * 40,
        seller_agent_address="0x" + "7" * 40,
        chain="base",
    )
    res_base = gasless_relayer.sponsor_deal_attestation(req_base)
    assert res_base.status == "SPONSORED_SUCCESS"
    assert res_base.chain_id == 8453
    assert res_base.gas_token == "ETH"

    # Arbitrum
    req_arb = SponsoredDealAttestationRequest(
        deal_id="DEAL-GASLESS-ARB-001",
        deal_hash="0x" + "c" * 64,
        buyer_agent_address="0x" + "8" * 40,
        seller_agent_address="0x" + "7" * 40,
        chain="arbitrum",
    )
    res_arb = gasless_relayer.sponsor_deal_attestation(req_arb)
    assert res_arb.status == "SPONSORED_SUCCESS"
    assert res_arb.chain_id == 42161
    assert res_arb.gas_token == "ETH"


def test_gasless_relayer_passport_minting_sponsorship():
    req = SponsoredPassportMintRequest(
        lot_id="LOT-GASLESS-BAT-001",
        mineral_type="NICKEL_MHP",
        compliance_verdict="PASSED_TIER_1",
        agent_address="0x" + "9" * 40,
        chain="polygon",
    )
    res = gasless_relayer.sponsor_battery_passport(req)
    assert res.status == "SPONSORED_SUCCESS"
    assert res.operation == "BATTERY_PASSPORT_MINT"
    assert res.tx_hash.startswith("0x")


def test_gasless_relayer_multichain_balances():
    balances = gasless_relayer.get_multichain_gas_balances()
    assert "chains" in balances
    assert "polygon" in balances["chains"]
    assert "base" in balances["chains"]
    assert "arbitrum" in balances["chains"]
    assert balances["chains"]["polygon"]["gas_token"] == "POL"
    assert balances["chains"]["base"]["gas_token"] == "ETH"
    assert balances["chains"]["arbitrum"]["gas_token"] == "ETH"


def test_gasless_relayer_rest_endpoints():
    client = TestClient(app)

    # 1. Sponsor deal attestation endpoint (Polygon)
    r_deal = client.post("/api/v1/relay/sponsor-deal-attestation", json={
        "deal_id": "DEAL-RELAY-API-001",
        "deal_hash": "0x" + "b" * 64,
        "buyer_agent_address": "0x" + "8" * 40,
        "seller_agent_address": "0x" + "7" * 40,
        "chain": "polygon"
    })
    assert r_deal.status_code == 200
    data_deal = r_deal.json()
    assert data_deal["status"] == "SPONSORED_SUCCESS"
    assert data_deal["chain_id"] == 137

    # 2. Sponsor deal attestation endpoint (Base)
    r_base = client.post("/api/v1/relay/sponsor-deal-attestation", json={
        "deal_id": "DEAL-RELAY-BASE-001",
        "deal_hash": "0x" + "c" * 64,
        "buyer_agent_address": "0x" + "8" * 40,
        "seller_agent_address": "0x" + "7" * 40,
        "chain": "base"
    })
    assert r_base.status_code == 200
    assert r_base.json()["chain_id"] == 8453
    assert r_base.json()["gas_token"] == "ETH"

    # 3. Sponsor battery passport endpoint
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

    # 4. Multi-chain gas balances endpoint
    r_bal = client.post if False else client.get("/api/v1/relay/multichain/gas-balances")
    assert r_bal.status_code == 200
    data_bal = r_bal.json()
    assert "chains" in data_bal
    assert "polygon" in data_bal["chains"]
    assert "base" in data_bal["chains"]
    assert "arbitrum" in data_bal["chains"]
