import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.compliance_engine import compliance_engine
from app.enterprise_manager import enterprise_manager
from app.schemas import (
    SMELightweightInput,
    MineralType,
    SourceCountry,
)
from tests.test_compliance_engine import build_valid_indonesia_nickel_request

client = TestClient(app)


def test_sme_lightweight_engine_compliant():
    """Verify that a standard SME processing lot with good yield passes compliance at micro-tier."""
    sme_req = SMELightweightInput(
        supplier_name="Daehan Precision Metallurgy Co.",
        business_registration_no="123-45-67890",
        mineral_type=MineralType.COPPER_CATHODE,
        source_country=SourceCountry.CHL,
        feedstock_input_ton=100.0,
        refined_output_ton=98.0,
        scrap_recycled_ratio_pct=25.0,
        monthly_electricity_kwh=45000.0,
        grid_region="KR_GRID",
        purity_pct=99.99,
    )
    res = compliance_engine.evaluate_sme_lightweight(sme_req)
    assert res.status == "success"
    assert res.supplier_name == "Daehan Precision Metallurgy Co."
    assert res.mass_balance_loss_pct <= 2.0
    assert res.mass_balance_compliant is True
    assert res.cbam_ready is True
    assert res.verdict == "COMPLIANT"
    assert res.scope_2_indirect_co2_ton > 0
    assert res.scope_1_direct_co2_ton > 0
    assert res.attestation_hash.startswith("0x")
    assert "SME-VERIF-" in res.sme_verification_id


def test_sme_lightweight_engine_loss_exceeded():
    """Verify that excessive mass balance loss (>2.0%) triggers an immediate compliance flag."""
    sme_req = SMELightweightInput(
        supplier_name="Substandard Smelting LLC",
        mineral_type=MineralType.COPPER_CATHODE,
        source_country=SourceCountry.CHL,
        feedstock_input_ton=100.0,
        refined_output_ton=88.0,  # Huge loss > 10%
        scrap_recycled_ratio_pct=0.0,
        monthly_electricity_kwh=60000.0,
        grid_region="KR_GRID",
    )
    res = compliance_engine.evaluate_sme_lightweight(sme_req)
    assert res.mass_balance_compliant is False
    assert res.cbam_ready is False
    assert res.verdict == "FLAGGED_HIGH_EMISSIONS_OR_LOSS"


def test_sme_lightweight_api_endpoint():
    """Test POST /api/v1/compliance/sme-lightweight via FastAPI TestClient."""
    payload = {
        "supplier_name": "Hansol Metal Recycling Ltd",
        "mineral_type": "COPPER_CATHODE",
        "source_country": "CHL",
        "feedstock_input_ton": 50.0,
        "refined_output_ton": 49.0,
        "scrap_recycled_ratio_pct": 30.0,
        "monthly_electricity_kwh": 20000.0,
        "grid_region": "KR_GRID",
        "purity_pct": 99.99,
    }
    # In sandbox or test mode, authorization passes
    res = client.post("/api/v1/compliance/sme-lightweight", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["supplier_name"] == "Hansol Metal Recycling Ltd"
    assert data["cbam_ready"] is True
    assert data["attestation_hash"].startswith("0x")


def test_enterprise_batch_compliance():
    """Test POST /api/v1/enterprise/batch-compliance across multi-tier supplier lots."""
    lot_valid = build_valid_indonesia_nickel_request()

    batch_req = {
        "enterprise_api_key": "ent_key_goldman_commodity_quant_2026",
        "batch_title": "Q3-2026 Battery Materials Supply Chain Screening",
        "tier_suppliers": [lot_valid.model_dump()],
    }

    res = client.post("/api/v1/enterprise/batch-compliance", json=batch_req)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["total_audited"] == 1
    assert data["passed_count"] == 1
    assert data["failed_count"] == 0
    assert data["batch_compliance_rate_pct"] == 100.0
    assert data["composite_supply_chain_score"] == 100.0
    assert len(data["results"]) == 1
    assert data["results"][0]["lot_id"] == "LOT-2026-NI-IDN-0412"
    assert len(data["remediation_guidance"]) > 0


def test_voucher_evidence_package_endpoint():
    """Test GET /api/v1/compliance/voucher-evidence/{passport_id} for MOTIE K-CBAM subsidy format."""
    passport_id = "0x" + "f" * 64
    res = client.get(f"/api/v1/compliance/voucher-evidence/{passport_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["passport_id"] == passport_id
    assert "MOTIE_K-CBAM_2026" in data["standard_authority"]
    assert "carbon_accounting_breakdown" in data
    assert "mass_balance_audit_trail" in data
    assert "government_voucher_reconciliation_hash" in data
    assert data["government_voucher_reconciliation_hash"].startswith("0x")
