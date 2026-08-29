"""
Integration and unit tests for Phase 1: Pre-Funded Agent Vault, Tiered Pricing, and Cryptographic Receipts.
"""

import pytest
from fastapi.testclient import TestClient
from eth_account import Account
from eth_account.messages import encode_defunct

from app.main import app
from app.schemas import PricingTier
from app.vault_manager import vault_manager
from app.onchain_signer import onchain_signer
from app.x402_verifier import x402_verifier, TIER_PRICING


client = TestClient(app)


def test_pricing_tiers_endpoint():
    """Tests GET /api/v1/oracle/pricing-tiers schedule."""
    resp = client.get("/api/v1/oracle/pricing-tiers")
    assert resp.status_code == 200
    data = resp.json()
    assert "tiers" in data
    assert data["tiers"]["LIGHT"]["cost_usdc"] == "0.001"
    assert data["tiers"]["STANDARD"]["cost_usdc"] == "0.005"
    assert data["tiers"]["HEAVY"]["cost_usdc"] == "0.010"
    assert data["tiers"]["ONCHAIN"]["cost_usdc"] == "0.020"


def test_prefunded_agent_vault_deposit_and_balance():
    """Tests depositing USDC and querying balance in AgentPaymentVault."""
    agent_addr = "0x90F79bf6EB2c4f870365E785982E1f101E93b906"
    deposit_payload = {
        "agent_address": agent_addr,
        "amount_usdc": 15.00,
        "tx_hash": "0x" + "b" * 64,
    }

    # 1. Deposit $15.00 USDC
    dep_resp = client.post("/api/v1/vault/deposit", json=deposit_payload)
    assert dep_resp.status_code == 200
    dep_data = dep_resp.json()
    assert dep_data["balance_usdc"] == 15.00
    assert dep_data["session_key"].startswith("vault_key_")
    session_key = dep_data["session_key"]

    # 2. Query Balance
    bal_resp = client.get(f"/api/v1/vault/balance/{agent_addr}")
    assert bal_resp.status_code == 200
    bal_data = bal_resp.json()
    assert bal_data["balance_usdc"] == 15.00
    assert bal_data["session_key"] == session_key


def test_vault_fast_path_tiered_deduction_and_receipt():
    """Tests zero-latency querying using X-Agent-Vault-Key across Light and Heavy tiers."""
    agent_addr = "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65"
    dep_resp = client.post("/api/v1/vault/deposit", json={"agent_address": agent_addr, "amount_usdc": 10.00})
    session_key = dep_resp.json()["session_key"]

    headers = {
        "X-Agent-Vault-Key": session_key,
        "X-Trial-Bypass": "true",
    }

    # 1. Query Single Price (Light Tier: $0.001)
    p_resp = client.get("/api/v1/oracle/prices/Cu", headers=headers)
    assert p_resp.status_code == 200
    assert p_resp.headers["X-Pricing-Tier"] == "LIGHT"
    assert p_resp.headers["X-Payment-Method"] == "Pre-Funded-Vault"
    assert "9.999" in p_resp.headers["X-Vault-Balance-Remaining"]
    receipt_id = p_resp.headers.get("X-Receipt-ID")
    assert receipt_id is not None and receipt_id.startswith("rcpt_")

    # 2. Query Urban Mining Calculator (Heavy Tier: $0.010)
    um_payload = {
        "scrap_category": "EV_BATTERY_BLACK_MASS",
        "quantity_metric_tons": 1.0,
        "target_yield_currency": "USDC",
    }
    um_resp = client.post("/api/v1/oracle/urban-mining/calculate", json=um_payload, headers=headers)
    assert um_resp.status_code == 200
    assert um_resp.headers["X-Pricing-Tier"] == "HEAVY"
    assert "9.989" in um_resp.headers["X-Vault-Balance-Remaining"]

    # 3. Verify Payment Receipt on-chain audit endpoint
    rcpt_resp = client.get(f"/api/v1/oracle/receipts/{receipt_id}")
    assert rcpt_resp.status_code == 200
    rcpt_data = rcpt_resp.json()
    assert rcpt_data["receipt_id"] == receipt_id
    assert rcpt_data["amount_paid_usdc"] == 0.001
    assert rcpt_data["pricing_tier"] == "LIGHT"
    assert rcpt_data["oracle_receipt_signature"].startswith("0x")


def test_vault_insufficient_balance_returns_402():
    """Tests that an agent vault with insufficient balance receives 402 with detailed notice."""
    agent_addr = "0x9965507D1a55bcC2695C58ba16FB37d819B0A4df"
    # Deposit only $0.0005 USDC (less than Light Tier $0.001)
    dep_resp = client.post("/api/v1/vault/deposit", json={"agent_address": agent_addr, "amount_usdc": 0.0005})
    session_key = dep_resp.json()["session_key"]

    headers = {
        "X-Agent-Vault-Key": session_key,
        "X-Trial-Bypass": "true",
    }
    resp = client.get("/api/v1/oracle/prices/Cu", headers=headers)
    assert resp.status_code == 402
    data = resp.json()
    assert "Insufficient vault balance" in data["detail"]
