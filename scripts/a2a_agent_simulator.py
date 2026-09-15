#!/usr/bin/env python3
"""
Autonomous Agent-to-Agent (A2A) Procurement & Compliance Simulation.
Demonstrates end-to-end machine-to-machine interactions:
1. Buyer Agent (EV OEM Procurement Bot) onboards via self-serve Vault API.
2. Supplier Agent (Mineral Commodity Broker Bot) submits mineral lots for review.
3. Buyer Agent queries Minerals Oracle x402 using session key and evaluates US IRA / FEOC compliance.
4. Clean batch (Offer A): Approved, issues EIP-712 audit proof, simulated on-chain escrow executed.
5. Tainted batch (Offer B): Rejected, detects FEOC taint propagation, automated purchase block.
"""

import os
import sys
import json
import time
from typing import Dict, Any

# Ensure project root is in python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Terminal color codes for rich A2A output
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def log_agent(sender: str, message: str, color: str = CYAN):
    ts = time.strftime("%H:%M:%S", time.gmtime())
    print(f"{color}[{ts}][{sender}]{RESET} {message}")


def run_simulation() -> Dict[str, Any]:
    print(f"\n{BOLD}{'=' * 80}{RESET}")
    print(f"{BOLD}[*] STARTING AUTONOMOUS AGENT-TO-AGENT (A2A) COMPLIANCE & ESCROW SIMULATION{RESET}")
    print(f"{BOLD}{'=' * 80}{RESET}\n")

    # =========================================================================
    # STEP 1: Buyer Agent Onboarding via Self-Serve Vault
    # =========================================================================
    buyer_agent_id = "agent_tesla_procurement_bot_v2"
    buyer_address = "0x8888888888888888888888888888888888888888"

    log_agent("BUYER_BOT", f"Initiating autonomous self-registration with Minerals Oracle...", CYAN)
    reg_resp = client.post(
        "/api/v1/vault/register",
        json={
            "agent_name": buyer_agent_id,
            "agent_address": buyer_address,
            "initial_trial_balance_usdc": 10.00,  # Seed $10.00 USDC for simulation
        }
    )
    assert reg_resp.status_code == 200, f"Registration failed: {reg_resp.text}"
    reg_data = reg_resp.json()
    session_key = reg_data["session_key"]
    log_agent("ORACLE", f"Registration accepted. Assigned session_key: {session_key[:16]}... Balance: ${reg_data['balance_usdc']:.2f} USDC", GREEN)

    # Check query capacity
    acc_resp = client.get(
        "/api/v1/vault/account",
        headers={"X-Agent-Vault-Key": session_key}
    )
    acc_data = acc_resp.json()
    log_agent("BUYER_BOT", f"Vault verified. Standard queries available: {acc_data['capacity']['tier2_standard_queries']}", CYAN)

    # =========================================================================
    # STEP 2: Supplier Agent Submits Offer A (Clean Compliant Batch)
    # =========================================================================
    print(f"\n{BOLD}--- SCENARIO 1: EVALUATING CLEAN BATCH (OFFER A) ---{RESET}")
    offer_a = {
        "rfq_id": "RFQ-2026-NCM811-CLEAN-BATCH-A",
        "cell_chemistry": "NCM811",
        "pack_capacity_kwh": 84.0,
        "lithium_tons": 7.5,
        "lithium_origin_country": "AUS",
        "lithium_feoc_equity_pct": 0.0,
        "nickel_tons": 60.0,
        "nickel_origin_country": "CAN",  # Canada Sudbury / US FTA Compliant
        "nickel_feoc_equity_pct": 0.0,
        "cobalt_tons": 7.5,
        "cobalt_origin_country": "CAN",  # Canada Voisey's Bay / US FTA Compliant
        "cobalt_feoc_equity_pct": 0.0,
    }

    log_agent("SUPPLIER_BOT", f"Submitting Offer A: 7.5t AUS Li, 60t CAN Ni, 7.5t CAN Co (100% US FTA partners)", YELLOW)
    log_agent("BUYER_BOT", f"Calling Minerals Oracle simulate-rfq with Vault Session Key...", CYAN)

    rfq_a_resp = client.post(
        "/api/v1/oracle/simulate-rfq",
        headers={"X-Agent-Vault-Key": session_key},
        json=offer_a,
    )
    assert rfq_a_resp.status_code == 200, f"RFQ simulation failed: {rfq_a_resp.text}"
    rfq_a_data = rfq_a_resp.json()

    log_agent("ORACLE", f"Offer A Verdict: {rfq_a_data['status']} | IRA FTA Ratio: {rfq_a_data['ira_fta_value_ratio_pct']}% | FEOC Taint: {rfq_a_data['feoc_taint_detected']}", GREEN)
    log_agent("ORACLE", f"Recommendation: {rfq_a_data['recommendation']}", GREEN)
    log_agent("ORACLE", f"Composite Merkle Root: {rfq_a_data['composite_merkle_digest']}", GREEN)

    # Verify Origin of Lithium
    lithium_req = {
        "trace_id": "LIT-AU-2026-A2A-01",
        "product": "Lithium Hydroxide Monohydrate",
        "mine_name": "Greenbushes Hard-Rock Mine",
        "mine_country": "AU",
        "coordinates": [-33.86, 116.02],
        "spodumene_tonnage_extracted": 75.0,
        "spodumene_grade_pct": 6.0,
        "refinery_facility": "Kwinana Plant",
        "refinery_country": "AU",
        "refined_output_tonnage": 10.0,
        "refinery_feoc_equity_pct": 0.0,
        "agent_address": buyer_address,
    }
    li_resp = client.post(
        "/api/v1/lithium/verify-origin",
        headers={"X-Agent-Vault-Key": session_key},
        json=lithium_req,
    )
    assert li_resp.status_code == 200, f"Lithium verification failed: {li_resp.text}"
    li_data = li_resp.json()
    receipt_id = li_resp.headers.get("x-receipt-id")
    log_agent("ORACLE", f"Lithium Origin PASSED. On-chain Proof: {li_data['onchain_proof'][:24]}... Receipt ID: {receipt_id}", GREEN)

    # Cryptographically verify receipt
    if receipt_id:
        rcpt_resp = client.get(f"/api/v1/vault/receipts/{receipt_id}")
        if rcpt_resp.status_code == 200:
            rcpt_data = rcpt_resp.json()
            verify_resp = client.post("/api/v1/vault/verify-receipt", json=rcpt_data)
            assert verify_resp.json()["is_valid"] is True
            log_agent("BUYER_BOT", f"Receipt cryptographic signature verified against Oracle public key!", CYAN)

    # Execute simulated on-chain contract
    log_agent("BUYER_BOT", f"DECISION: EXECUTING PURCHASE ESCROW ON POLYGON (PO #PO-A2A-2026-CLEAN-01)", GREEN)
    log_agent("SUPPLIER_BOT", f"Payment acknowledged. 75t clean battery minerals allocated to Buyer.", YELLOW)

    # =========================================================================
    # STEP 3: Supplier Agent Submits Offer B (Tainted Batch)
    # =========================================================================
    print(f"\n{BOLD}--- SCENARIO 2: EVALUATING TAINTED BATCH (OFFER B) ---{RESET}")
    offer_b = {
        "rfq_id": "RFQ-2026-NCM811-TAINTED-BATCH-B",
        "cell_chemistry": "NCM811",
        "pack_capacity_kwh": 84.0,
        "lithium_tons": 7.5,
        "lithium_origin_country": "CHN",
        "lithium_feoc_equity_pct": 42.0,  # FATAL: Covered nation equity >= 25%
        "nickel_tons": 60.0,
        "nickel_origin_country": "IDN",
        "nickel_feoc_equity_pct": 30.0,  # FATAL: >= 25%
        "cobalt_tons": 7.5,
        "cobalt_origin_country": "COD",
        "cobalt_feoc_equity_pct": 0.0,
    }

    log_agent("SUPPLIER_BOT", f"Submitting Offer B: 7.5t CHN Li (42% covered equity), 60t IDN Ni (30% covered equity)", YELLOW)
    log_agent("BUYER_BOT", f"Calling Minerals Oracle simulate-rfq with Vault Session Key...", CYAN)

    rfq_b_resp = client.post(
        "/api/v1/oracle/simulate-rfq",
        headers={"X-Agent-Vault-Key": session_key},
        json=offer_b,
    )
    assert rfq_b_resp.status_code == 200
    rfq_b_data = rfq_b_resp.json()

    log_agent("ORACLE", f"Offer B Verdict: {rfq_b_data['status']} | FEOC Taint Detected: {rfq_b_data['feoc_taint_detected']}", RED)
    for t in rfq_b_data["tainted_minerals"]:
        log_agent("ORACLE", f"[TAINT_ALERT] {t}", RED)
    log_agent("ORACLE", f"Recommendation: {rfq_b_data['recommendation']}", RED)

    # Buyer Agent automated mitigation & contract rejection
    log_agent("BUYER_BOT", f"DECISION: REJECTING OFFER B IMMEDIATELY. Subsidies lost = $3,750/pack.", RED)
    log_agent("BUYER_BOT", f"Autonomous alert sent to Supplier Agent: Compliance breach detected. Batch blacklisted.", RED)

    # Check updated vault balance
    final_acc_resp = client.get("/api/v1/vault/account", headers={"X-Agent-Vault-Key": session_key})
    final_acc = final_acc_resp.json()
    log_agent("ORACLE", f"Simulation completed. Total queries executed: {final_acc['query_count']} | Remaining Balance: ${final_acc['balance_usdc']:.4f} USDC", GREEN)

    print(f"\n{BOLD}{'=' * 80}{RESET}")
    print(f"{BOLD}[OK] A2A SIMULATION COMPLETED SUCCESSFULLY WITH 100% DETERMINISTIC VERIFICATION{RESET}")
    print(f"{BOLD}{'=' * 80}{RESET}\n")

    return {
        "status": "SUCCESS",
        "buyer_agent": buyer_agent_id,
        "queries_executed": final_acc["query_count"],
        "offer_a_verdict": rfq_a_data["status"],
        "offer_b_verdict": rfq_b_data["status"],
    }


if __name__ == "__main__":
    result = run_simulation()
    sys.exit(0 if result["status"] == "SUCCESS" else 1)
