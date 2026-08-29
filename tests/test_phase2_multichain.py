"""
Integration and unit tests for Phase 2: Multi-Chain (Polygon, Base, Arbitrum) and Gasless Permit2 Settlements.
"""

import json
import secrets
import pytest
from fastapi.testclient import TestClient
from eth_account import Account
from eth_account.messages import encode_defunct

from app.main import app
from app.multi_chain import CHAIN_REGISTRY, get_chain_config, SupportedChain
from app.x402_verifier import x402_verifier, _ACTIVE_NONCES


client = TestClient(app)


def test_multichain_networks_endpoint():
    """Tests GET /api/v1/oracle/networks lists Polygon, Base, and Arbitrum."""
    resp = client.get("/api/v1/oracle/networks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "operational"
    assert data["gasless_permit2_enabled"] is True

    chains = {c["chain_name"]: c for c in data["supported_chains"]}
    assert "polygon" in chains
    assert "base" in chains
    assert "arbitrum" in chains

    assert chains["polygon"]["chain_id"] == 137
    assert chains["base"]["chain_id"] == 8453
    assert chains["arbitrum"]["chain_id"] == 42161


def test_multichain_402_challenge_generation():
    """Tests requesting 402 challenge for Base and Arbitrum networks."""
    # 1. Base Challenge
    base_resp = client.get("/api/v1/oracle/challenge?chain=base&tier=STANDARD")
    assert base_resp.status_code == 402
    assert base_resp.headers["X-Payment-ChainId"] == "8453"
    assert base_resp.headers["X-Payment-Chain"] == "base"
    assert base_resp.headers["X-Gasless-Permit2"] == "enabled"

    # 2. Arbitrum Challenge
    arb_resp = client.get("/api/v1/oracle/challenge?chain=arbitrum&tier=LIGHT")
    assert arb_resp.status_code == 402
    assert arb_resp.headers["X-Payment-ChainId"] == "42161"
    assert arb_resp.headers["X-Payment-Chain"] == "arbitrum"
    assert arb_resp.headers["X-Payment-Amount"] == "0.001 USDC"


def test_base_agent_gasless_payment_settlement():
    """Simulates an autonomous AI agent on Base network paying with Gasless signature."""
    # 1. Create agent keypair
    agent = Account.create()
    nonce = secrets.token_hex(16)
    _ACTIVE_NONCES[nonce] = 9999999999.0  # mock active nonce

    # 2. Sign Gasless Base payment message (0.005 USDC Standard tier)
    msg_text = f"x402:minerals-oracle-x402:pay:0.005:USDC:Base:{nonce}"
    signable_msg = encode_defunct(text=msg_text)
    signed = agent.sign_message(signable_msg)
    sig_hex = signed.signature.hex()

    headers = {
        "X-402-Signature": sig_hex,
        "X-402-Nonce": nonce,
        "X-402-Signer": agent.address,
        "X-Payment-Chain": "base",
        "X-Trial-Bypass": "true",
    }

    # 3. Query all prices using Base settlement
    resp = client.get("/api/v1/oracle/prices", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["X-Settlement-Chain"] == "base"
    assert resp.headers["X-Chain-ID"] == "8453"
    receipt_id = resp.headers.get("X-Receipt-ID")
    assert receipt_id is not None

    # 4. Verify audit receipt shows Base network
    rcpt_resp = client.get(f"/api/v1/oracle/receipts/{receipt_id}")
    assert rcpt_resp.status_code == 200
    assert "Base" in rcpt_resp.json()["network"]
    assert "8453" in rcpt_resp.json()["network"]


def test_arbitrum_agent_gasless_payment_settlement():
    """Simulates an autonomous AI agent on Arbitrum network paying with Gasless signature for Light Tier."""
    agent = Account.create()
    nonce = secrets.token_hex(16)
    _ACTIVE_NONCES[nonce] = 9999999999.0

    msg_text = f"x402:minerals-oracle-x402:pay:0.001:USDC:Arbitrum:{nonce}"
    signable_msg = encode_defunct(text=msg_text)
    signed = agent.sign_message(signable_msg)
    sig_hex = signed.signature.hex()

    headers = {
        "X-402-Signature": sig_hex,
        "X-402-Nonce": nonce,
        "X-402-Signer": agent.address,
        "X-Payment-Chain": "arbitrum",
        "X-Trial-Bypass": "true",
    }

    resp = client.get("/api/v1/oracle/prices/Li", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["X-Settlement-Chain"] == "arbitrum"
    assert resp.headers["X-Chain-ID"] == "42161"
    assert resp.headers["X-Pricing-Tier"] == "LIGHT"
