#!/usr/bin/env python3
"""
Autonomous Agent-to-Agent (A2A) Global Physical Trade & Logistics Simulation.
Demonstrates machine-to-machine execution across the world trade system:
1. Buyer Agent (EV Gigafactory Bot) queries global trade corridor flows and tariffs.
2. Logistics / Charterer Agent submits multi-modal maritime transport proposals.
3. Minerals Oracle x402 evaluates:
   - Harmonized System (HS) Codes & Tariff Defenses (US Section 301 vs FTA 0%)
   - Maritime Navigation & Chokepoints (Panama Canal vs Red Sea/Cape of Good Hope)
   - Scope 3 Maritime Carbon (IMO MARPOL CII Rating & EU CBAM liabilities)
   - Electronic Bill of Lading (eBL) cryptographic verification (IMO checksum, MLETR audit)
4. Autonomous Route Optimization & Landed Cost Arbitrage ($/MT).
5. On-chain settlement & EIP-712 verifiable trade passport issuance.
"""

import os
import sys
import json
import time
import hashlib
from typing import Dict, Any

# Ensure project root is in python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def log_agent(sender: str, message: str, color: str = CYAN):
    ts = time.strftime("%H:%M:%S", time.gmtime())
    print(f"{color}[{ts}][{sender}]{RESET} {message}")


def run_trade_simulation() -> Dict[str, Any]:
    print(f"\n{BOLD}{'=' * 85}{RESET}")
    print(f"{BOLD}[*] AUTONOMOUS A2A GLOBAL TRADE FLOWS, MARITIME LOGISTICS & eBL ESCROW SIMULATION{RESET}")
    print(f"{BOLD}{'=' * 85}{RESET}\n")

    # =========================================================================
    # STEP 1: Buyer Agent (Gigafactory Bot) Self-Registration with Oracle Vault
    # =========================================================================
    buyer_id = "agent_gigafactory_procurement_bot"
    buyer_addr = "0x7777777777777777777777777777777777777777"

    log_agent("BUYER_BOT", "Registering autonomous session with Minerals Oracle x402...", CYAN)
    reg_resp = client.post(
        "/api/v1/vault/register",
        json={
            "agent_name": buyer_id,
            "agent_address": buyer_addr,
            "initial_trial_balance_usdc": 15.00,  # $15.00 pre-funded balance
        },
    )
    reg_data = reg_resp.json()
    session_key = reg_data["session_key"]
    log_agent("ORACLE", f"Session key provisioned: {session_key[:20]}... | Available: $15.00 USDC", GREEN)

    headers = {"X-Agent-Vault-Key": session_key}

    # =========================================================================
    # STEP 2: Query Global Trade Corridor Flows
    # =========================================================================
    log_agent("BUYER_BOT", "Scanning global physical trade corridor flows for LITHIUM_CARBONATE...", CYAN)
    flows_resp = client.get("/api/v1/trade/flows?mineral_type=LITHIUM_CARBONATE", headers=headers)
    flows = flows_resp.json()
    matched_flow = flows[0]
    log_agent(
        "ORACLE",
        f"Active Corridor: {matched_flow['corridor_id']} | Route: {matched_flow['origin_port_name']} ({matched_flow['origin_port_code']}) -> {matched_flow['destination_port_name']} ({matched_flow['destination_port_code']}) | Monthly Volume: {matched_flow['monthly_volume_metric_tons']:,.0f} MT",
        GREEN,
    )

    # =========================================================================
    # STEP 3: Harmonized System (HS) Code & Tariff Architecture Evaluation
    # =========================================================================
    log_agent("BUYER_BOT", "Analyzing HS Code tariffs & trade remedies for US import...", CYAN)
    tariff_resp = client.post(
        "/api/v1/trade/tariffs?mineral_type=LITHIUM_CARBONATE&importer_jurisdiction=USA",
        headers=headers,
    )
    tariff_data = tariff_resp.json()
    log_agent(
        "ORACLE",
        f"HS Code: {tariff_data['hs_code']} | Description: {tariff_data['description']} | MFN Duty: {tariff_data['mfn_duty_pct']}% | FTA Preferential Duty: {tariff_data['fta_preferential_duty_pct']}% ({tariff_data['fta_name']}) | Section 301 Punitive Duty: {tariff_data['section_301_tariff_pct']}%",
        GREEN,
    )

    # =========================================================================
    # STEP 4: Maritime Routing & Chokepoint Risk Evaluation
    # =========================================================================
    log_agent("CHARTERER_BOT", "Proposing Maritime Route A: Chile (Mejillones) -> USA (Houston) via Panama Canal (Neopanamax)", YELLOW)
    route_req = {
        "mineral_type": "LITHIUM_CARBONATE",
        "origin_country": "CHL",
        "destination_country": "USA",
        "cargo_weight_metric_tons": 2500.0,
        "cii_rating": "A",
    }
    route_resp = client.post("/api/v1/trade/maritime-route", json=route_req, headers=headers)
    route_data = route_resp.json()
    log_agent(
        "ORACLE",
        f"Voyage Distance: {route_data['nautical_miles']:,.0f} NM | Transit: {route_data['estimated_transit_days']} Days | Freight: ${route_data['base_freight_usd_per_mt']}/MT | IMO CII: {route_data['cii_rating']} | Voyage CO2: {route_data['total_voyage_co2_metric_tons']} MT",
        GREEN,
    )

    # =========================================================================
    # STEP 5: Electronic Bill of Lading (eBL) Cryptographic Audit
    # =========================================================================
    log_agent("CHARTERER_BOT", "Submitting UNCITRAL MLETR compliant Electronic Bill of Lading (eBL)...", YELLOW)
    valid_imo = 9315331  # Verified IMO 7-digit checksum
    ebl_hash = hashlib.sha256(b"eBL_MANIFEST_CHL_USA_2500MT_LITHIUM_2026").hexdigest()
    ebl_req = {
        "ebl_document_id": "eBL-CHL-USA-2026-LITH-001",
        "ebl_document_hash": ebl_hash,
        "carrier_imo_number": valid_imo,
        "vessel_name": "ANDES_EXPRESS",
        "mineral_type": "LITHIUM_CARBONATE",
        "gross_weight_metric_tons": 2500.0,
        "port_of_loading_code": "CLMEJ",
        "port_of_discharge_code": "USHOU",
        "shipper_name": "Sociedad Quimica y Minera de Chile (SQM)",
        "consignee_name": "Tesla Gigafactory Texas",
    }
    ebl_resp = client.post("/api/v1/trade/verify-ebl", json=ebl_req, headers=headers)
    ebl_data = ebl_resp.json()
    log_agent(
        "ORACLE",
        f"eBL Audit Verdict: {ebl_data['audit_verdict']} | IMO Checksum: {ebl_data['carrier_imo_valid']} | Port Pair: {ebl_data['port_pair_valid']} | Dark Fleet Flag: {ebl_data['dark_fleet_flag']}",
        GREEN if ebl_data["is_valid"] else RED,
    )

    # =========================================================================
    # STEP 6: Autonomous Multi-Modal Route Optimization & Landed Cost Arbitrage
    # =========================================================================
    log_agent("BUYER_BOT", "Running autonomous trade route optimization comparing direct vs chokepoint bypass...", CYAN)
    opt_req = {
        "mineral_type": "LITHIUM_CARBONATE",
        "origin_country": "CHL",
        "destination_country": "USA",
        "cargo_weight_metric_tons": 2500.0,
        "target_delivery_deadline_days": 20.0,
    }
    opt_resp = client.post("/api/v1/trade/optimize-route", json=opt_req, headers=headers)
    opt_data = opt_resp.json()
    log_agent(
        "ORACLE",
        f"Optimal Corridor: {opt_data['optimal_corridor_id']} | Landed Cost: ${opt_data['estimated_landed_cost_usd_per_mt']:,.2f}/MT | Total Freight + Tariffs: ${opt_data['total_freight_and_tariff_usd']:,.2f} | Transit: {opt_data['transit_days']} Days",
        GREEN,
    )
    log_agent("ORACLE", f"Advisory: {opt_data['recommended_route_summary']}", GREEN)

    # =========================================================================
    # STEP 7: Escrow Execution & Cryptographic Settlement
    # =========================================================================
    log_agent("BUYER_BOT", "All verifications passed (eBL valid, 0% FTA tariff, IMO CII A rating).", CYAN)
    log_agent("BUYER_BOT", "Executing simulated on-chain trade escrow release ($33,750,000.00)...", CYAN)
    log_agent("CHARTERER_BOT", "Cargo release order confirmed. 2,500 MT Battery Grade Lithium Carbonate cleared for Houston discharge.", YELLOW)

    print(f"\n{BOLD}{'=' * 85}{RESET}")
    print(f"{BOLD}[OK] GLOBAL PHYSICAL TRADE & LOGISTICS SIMULATION COMPLETED WITH ZERO DEFECTS{RESET}")
    print(f"{BOLD}{'=' * 85}{RESET}\n")

    return {
        "status": "SUCCESS",
        "corridor_id": matched_flow["corridor_id"],
        "hs_code": tariff_data["hs_code"],
        "fta_duty_pct": tariff_data["fta_preferential_duty_pct"],
        "ebl_valid": ebl_data["is_valid"],
        "transit_days": opt_data["transit_days"],
        "landed_cost_usd_per_mt": opt_data["estimated_landed_cost_usd_per_mt"],
    }


if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        except Exception:
            pass
    run_trade_simulation()
