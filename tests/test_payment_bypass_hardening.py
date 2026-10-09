"""
Rigorous Security Audit & Hardening Tests for x402 Payment Bypass Defense.
Verifies that:
1. Production mode strictly rejects 'X-Dev-Bypass: true' (prevents unauthorized zero-cost calls).
2. External spoofed Referer headers (e.g., https://attacker.com/dashboard) are blocked (HTTP 402).
3. Legitimate same-origin dashboard accesses (e.g., http://testserver/dashboard) are permitted.
4. Pre-funded vault and authorized payment methods remain fully operational.
"""

import os
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import SourceCountry
from app.vault_manager import vault_manager

client = TestClient(app)

SAMPLE_SILVER_REQUEST = {
    "lot_id": "SIL-MEX-2026-TER01",
    "mine_concession_name": "TERRONERA",
    "extraction_coordinates": [20.590, -104.980],
    "source_country": "MEX",
    "feedstock_dore_or_ore_kg": 5000.0,
    "feedstock_silver_grade_pct": 75.0,
    "refined_solar_powder_kg": 3712.5,
    "refined_purity_pct": 99.995,
    "lbma_good_delivery_ref": "LBMA-REF-MEX-01",
    "conflict_free_asm_verified": True,
    "topcon_pv_grade_compliant": True,
    "feoc_shareholding_pct": 0.0,
}


def test_production_mode_rejects_dev_bypass_header():
    """Verify that when ALLOW_DEV_BYPASS is False and outside pytest, X-Dev-Bypass is blocked."""
    from app import x402_verifier

    # Temporarily simulate production environment (ALLOW_DEV_BYPASS=False, no test flag in environment)
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("PYTEST_CURRENT_TEST", None)
        with patch.object(x402_verifier, "ALLOW_DEV_BYPASS", False):
            res = client.post(
                "/api/v1/silver/verify-origin",
                json=SAMPLE_SILVER_REQUEST,
                headers={"X-Dev-Bypass": "true", "X-Trial-Bypass": "true"}
            )
            assert res.status_code == 402
            assert res.json()["error"] == "Payment Required"


def test_external_referer_spoofing_blocked():
    """Verify that an attacker providing an external domain referer cannot bypass payment."""
    res = client.post(
        "/api/v1/silver/verify-origin",
        json=SAMPLE_SILVER_REQUEST,
        headers={
            "Referer": "https://attacker.org/dashboard",
            "Host": "api.minerals-oracle.com",
            "X-Trial-Bypass": "true",
        }
    )
    assert res.status_code == 402
    assert res.json()["error"] == "Payment Required"


def test_legitimate_same_host_dashboard_allowed():
    """Verify that same-host referer (web dashboard console) is permitted."""
    res = client.post(
        "/api/v1/silver/verify-origin",
        json=SAMPLE_SILVER_REQUEST,
        headers={
            "Referer": "http://testserver/dashboard",
            "Host": "testserver",
        }
    )
    # Allowed via legitimate dashboard path
    assert res.status_code == 200
    assert res.json()["status"] == "success"
    assert res.headers.get("X-Dashboard-Access") == "granted"


def test_pre_funded_vault_legitimate_payment():
    """Verify that authorized payment via Agent Vault Key functions correctly."""
    acc = vault_manager.deposit(agent_address="0x70997970C51812dc3A010C7d01b50e0d17dc79C8", amount_usdc=5.0)
    vault_key = acc.session_key

    res = client.post(
        "/api/v1/silver/verify-origin",
        json=SAMPLE_SILVER_REQUEST,
        headers={"X-Agent-Vault-Key": vault_key, "X-Trial-Bypass": "true"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "success"
    assert res.headers.get("X-Payment-Method") == "Pre-Funded-Vault"
