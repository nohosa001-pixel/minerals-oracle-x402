"""
Unit and Integration Tests for Agent Payment Vault REST Endpoints & RFQ Simulation.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.vault_manager import vault_manager
from app.onchain_signer import onchain_signer

import secrets

client = TestClient(app)


def test_agent_vault_registration():
    unique_addr = "0x" + secrets.token_hex(20)
    resp = client.post(
        "/api/v1/vault/register",
        json={
            "agent_name": "TestBot-Autonomous-01",
            "agent_address": unique_addr,
            "initial_trial_balance_usdc": 0.50,
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["agent_name"] == "TestBot-Autonomous-01"
    assert data["balance_usdc"] == 0.50
    assert "session_key" in data
    assert data["capacity"]["tier2_standard_queries"] == 100


def test_agent_vault_account_retrieval():
    # Register an agent
    reg_resp = client.post(
        "/api/v1/vault/register",
        json={
            "agent_name": "TestBot-Account-Query",
            "initial_trial_balance_usdc": 1.00,
        }
    )
    session_key = reg_resp.json()["session_key"]

    # Query by session key header
    acc_resp = client.get(
        "/api/v1/vault/account",
        headers={"X-Agent-Vault-Key": session_key}
    )
    assert acc_resp.status_code == 200
    acc_data = acc_resp.json()
    assert acc_data["balance_usdc"] == 1.00
    assert acc_data["session_key"] == session_key
    assert acc_data["capacity"]["tier1_light_queries"] == 1000


def test_agent_vault_deposit():
    reg_resp = client.post(
        "/api/v1/vault/register",
        json={"agent_name": "TestBot-Depositor", "initial_trial_balance_usdc": 0.10}
    )
    session_key = reg_resp.json()["session_key"]

    dep_resp = client.post(
        "/api/v1/vault/deposit",
        json={
            "identifier": session_key,
            "amount_usdc": 5.00,
            "tx_hash": "0xtest_deposit_hash_12345",
            "chain": "polygon"
        }
    )
    assert dep_resp.status_code == 200
    dep_data = dep_resp.json()
    assert dep_data["status"] == "DEPOSIT_CONFIRMED"
    assert dep_data["receipt"]["new_balance_usdc"] == 5.10
    assert dep_data["receipt"]["chain"] == "polygon"


def test_simulate_procurement_rfq_clean():
    clean_rfq = {
        "rfq_id": "RFQ-TEST-CLEAN",
        "cell_chemistry": "NCM811",
        "pack_capacity_kwh": 84.0,
        "lithium_tons": 10.0,
        "lithium_origin_country": "AUS",
        "lithium_feoc_equity_pct": 0.0,
        "nickel_tons": 80.0,
        "nickel_origin_country": "CAN",
        "nickel_feoc_equity_pct": 0.0,
        "cobalt_tons": 10.0,
        "cobalt_origin_country": "CAN",
        "cobalt_feoc_equity_pct": 0.0,
    }
    resp = client.post("/api/v1/oracle/simulate-rfq", json=clean_rfq)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "QUALIFIED"
    assert data["ira_fta_compliant"] is True
    assert data["ira_fta_value_ratio_pct"] == 100.0
    assert data["feoc_taint_detected"] is False
    assert data["us_subsidy_qualified_per_pack_usd"] == 3750.0


def test_simulate_procurement_rfq_tainted():
    tainted_rfq = {
        "rfq_id": "RFQ-TEST-TAINTED",
        "cell_chemistry": "NCM811",
        "pack_capacity_kwh": 84.0,
        "lithium_tons": 10.0,
        "lithium_origin_country": "CHN",
        "lithium_feoc_equity_pct": 35.0,  # Tainted
        "nickel_tons": 80.0,
        "nickel_origin_country": "IDN",
        "nickel_feoc_equity_pct": 0.0,
        "cobalt_tons": 10.0,
        "cobalt_origin_country": "COD",
        "cobalt_feoc_equity_pct": 0.0,
    }
    resp = client.post("/api/v1/oracle/simulate-rfq", json=tainted_rfq)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "DISQUALIFIED"
    assert data["feoc_taint_detected"] is True
    assert len(data["tainted_minerals"]) >= 1
    assert data["us_subsidy_qualified_per_pack_usd"] == 0.0


def test_receipt_verification():
    # Issue a real receipt through paywalled query with vault session key
    reg_resp = client.post(
        "/api/v1/vault/register",
        json={"agent_name": "TestBot-ReceiptAgent", "initial_trial_balance_usdc": 1.00}
    )
    session_key = reg_resp.json()["session_key"]

    # Query lithium origin
    li_resp = client.post(
        "/api/v1/lithium/verify-origin",
        headers={"X-Agent-Vault-Key": session_key},
        json={
            "trace_id": "LIT-AU-TEST-001",
            "product": "Lithium Hydroxide Monohydrate",
            "mine_name": "Greenbushes Mine",
            "mine_country": "AU",
            "coordinates": [-33.86, 116.02],
            "spodumene_tonnage_extracted": 75.0,
            "refinery_facility": "Kwinana Plant",
            "refined_output_tonnage": 10.0,
        }
    )
    assert li_resp.status_code == 200
    receipt_id = li_resp.headers.get("x-receipt-id")
    assert receipt_id is not None

    # Retrieve receipt
    rcpt_resp = client.get(f"/api/v1/vault/receipts/{receipt_id}")
    assert rcpt_resp.status_code == 200
    rcpt_data = rcpt_resp.json()
    assert rcpt_data["receipt_id"] == receipt_id

    # Verify signature
    verify_resp = client.post("/api/v1/vault/verify-receipt", json=rcpt_data)
    assert verify_resp.status_code == 200
    verify_data = verify_resp.json()
    assert verify_data["is_valid"] is True
    assert verify_data["oracle_signing_address"].lower() == onchain_signer.account.address.lower()
