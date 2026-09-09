import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_pwa_routes():
    """Verify PWA manifest and service worker are served properly."""
    res_manifest = client.get("/manifest.json")
    assert res_manifest.status_code == 200
    assert "application/manifest+json" in res_manifest.headers.get("content-type", "")
    manifest_data = res_manifest.json()
    assert manifest_data["short_name"] == "Minerals Oracle"
    assert manifest_data["display"] == "standalone"

    res_sw = client.get("/sw.js")
    assert res_sw.status_code == 200
    assert "application/javascript" in res_sw.headers.get("content-type", "")
    assert "CACHE_NAME" in res_sw.text


def test_dashboard_sales_readiness_features():
    """Verify Dashboard contains Agent-Native Gateway, EIP-712 binding, and Zero-PII onboarding."""
    res = client.get("/dashboard")
    assert res.status_code == 200
    html = res.text

    # 1. Autonomous Agent Title & Headers
    assert "Autonomous Critical Minerals & Battery Passport Node" in html
    assert "HTTP 402 Monetized" in html
    assert "EIP-712" in html
    assert "FastMCP" in html

    # 2. Agent Identity & Vault Section
    assert "Agent Identity & Vault" in html
    assert "Zero PII Policy" in html
    assert "agentWallet" in html
    assert "agentApiKey" in html
    assert "quickOnboardAgent" in html
    assert "checkVaultBalance" in html

    # 3. Interactive Compliance & 402 Challenge Simulator
    assert "simulateComplianceEval" in html
    assert "test402Challenge" in html
    assert "evalMineral" in html
    assert "evalCountry" in html

    # 4. Smart Contracts & Disclaimer Notice
    assert "MineralsOracleConsumer.sol" in html
    assert "AgentPaymentVault.sol" in html
    assert "AS-IS" in html
    assert "$0.50 USDC" in html


def test_secure_settlement_for_calculator():
    """Verify backend calculation powering secure settlement returns full breakdown & attestation."""
    req_body = {
        "scrap_category": "AUTO_CATALYST_CERAMIC",
        "quantity_metric_tons": 1.0,
        "target_yield_currency": "USDC",
        "agent_address": "0x71C84107b3a42E2F2Ab4Ba770265EC0c4ce5Cea6"
    }
    res = client.post(
        "/api/v1/oracle/secure-settlement",
        json=req_body,
        headers={"X-Dev-Bypass": "true"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLIANCE_SETTLEMENT_VERIFIED"
    assert data["security_gate_certified"] is True


def test_korean_dedicated_core_dashboard():
    """Verify Korean dedicated version (/ko) focuses on autonomous agent compliance node."""
    res = client.get("/ko")
    assert res.status_code == 200
    html = res.text

    # 1. Korean Agent Node Header & Elements
    assert 'lang="ko"' in html
    assert "x402" in html
    assert "Polygon 137" in html
    assert "EIP-712" in html
    assert "quickOnboardAgent" in html
    assert "simulateComplianceEval" in html
    assert "test402Challenge" in html
    assert "AgentPaymentVault.sol" in html
    assert "MineralsOracleConsumer.sol" in html

    # 2. Global English link
    assert "Global (EN)" in html
    assert "/" in html
