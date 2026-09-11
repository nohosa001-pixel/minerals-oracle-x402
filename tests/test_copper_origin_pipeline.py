"""
Unit & Integration Tests for Chilean/South American Copper Provenance Pipeline.
Validates Codelco/Escondida geofencing, flotation-to-cathode mass balance,
H2SO4 deficit screening, COCHILCO permits, and HVDC grid compliance.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import CopperOriginVerifyRequest, SourceCountry
from app.copper_pipeline import copper_pipeline
from app.mcp_stdio import handle_tool_call


client = TestClient(app)


def test_codelco_chuquicamata_clean_pass():
    """Validates clean Codelco Chuquicamata copper cathode lot passing all checks."""
    # 350t concentrate at 28.0% Cu = 98.0t Cu contained * 0.975 recovery = 95.55t theoretical cathode
    # Expected H2SO4: 95.55t * 3.2 = 305.76t
    req = CopperOriginVerifyRequest(
        lot_id="COP-CHL-2026-CHU01",
        mine_concession_name="CHUQUICAMATA",
        extraction_coordinates=(-22.283, -68.900),
        source_country=SourceCountry.CHL,
        feedstock_concentrate_tons=350.0,
        concentrate_grade_cu_pct=28.0,
        sulfuric_acid_input_tons=305.76,
        refined_copper_cathode_tons=95.55,
        copper_cathode_purity_pct=99.9935,
        cochilco_export_clearance_id="COCHILCO-EXP-2026-CH01",
        hvdc_cable_spec_compliant=True,
        feoc_shareholding_pct=0.0,
    )
    res = copper_pipeline.verify_origin(req)
    assert res.status == "success"
    assert res.verdict.geofence_verified is True
    assert res.verdict.stoichiometric_mass_balance_passed is True
    assert res.verdict.sulfuric_acid_ratio_passed is True
    assert res.verdict.cochilco_cleared is True
    assert res.verdict.hvdc_grid_certified is True
    assert res.verdict.feoc_cleared is True
    assert res.verdict.confidence_score >= 90.0
    assert res.onchain_proof.startswith("0x")


def test_copper_sulfuric_acid_deficit_rejection():
    """Rejects copper lot when sulfuric acid variance exceeds 5.0% (smelter deficit)."""
    req = CopperOriginVerifyRequest(
        lot_id="COP-CHL-2026-DEFICIT",
        mine_concession_name="CHUQUICAMATA",
        extraction_coordinates=(-22.283, -68.900),
        source_country=SourceCountry.CHL,
        feedstock_concentrate_tons=350.0,
        concentrate_grade_cu_pct=28.0,
        sulfuric_acid_input_tons=200.0,  # Far below 305.76t expected (~34% deficit)
        refined_copper_cathode_tons=95.55,
        copper_cathode_purity_pct=99.9935,
        cochilco_export_clearance_id="COCHILCO-EXP-2026-CH01",
        hvdc_cable_spec_compliant=True,
        feoc_shareholding_pct=0.0,
    )
    res = copper_pipeline.verify_origin(req)
    assert res.verdict.sulfuric_acid_ratio_passed is False
    assert any("FATAL_COPPER_H2SO4_DEFICIT" in d for d in res.verdict.defenses_applied)


def test_copper_geofence_exceeded_rejection():
    """Rejects lot when extraction coordinates fall outside concession radius."""
    req = CopperOriginVerifyRequest(
        lot_id="COP-CHL-2026-GEOFENCE-FAIL",
        mine_concession_name="CHUQUICAMATA",
        extraction_coordinates=(10.0, 20.0),  # In Africa, far from Chile
        source_country=SourceCountry.CHL,
        feedstock_concentrate_tons=350.0,
        concentrate_grade_cu_pct=28.0,
        sulfuric_acid_input_tons=305.76,
        refined_copper_cathode_tons=95.55,
        copper_cathode_purity_pct=99.9935,
        cochilco_export_clearance_id="COCHILCO-EXP-2026-CH01",
        hvdc_cable_spec_compliant=True,
    )
    res = copper_pipeline.verify_origin(req)
    assert res.verdict.geofence_verified is False
    assert any("FATAL_COPPER_GEOFENCE_EXCEEDED" in d for d in res.verdict.defenses_applied)


def test_copper_mass_balance_loss_exceeded():
    """Rejects lot when reported cathode output diverges by > 2.0% from theoretical yield."""
    req = CopperOriginVerifyRequest(
        lot_id="COP-CHL-2026-MASS-FAIL",
        mine_concession_name="CHUQUICAMATA",
        extraction_coordinates=(-22.283, -68.900),
        source_country=SourceCountry.CHL,
        feedstock_concentrate_tons=350.0,
        concentrate_grade_cu_pct=28.0,
        sulfuric_acid_input_tons=305.76,
        refined_copper_cathode_tons=130.0,  # Far above 95.55t theoretical yield (+36%)
        copper_cathode_purity_pct=99.9935,
        cochilco_export_clearance_id="COCHILCO-EXP-2026-CH01",
    )
    res = copper_pipeline.verify_origin(req)
    assert res.verdict.stoichiometric_mass_balance_passed is False
    assert any("FATAL_COPPER_MASS_BALANCE_EXCEEDED" in d for d in res.verdict.defenses_applied)


def test_fastapi_copper_verify_endpoint():
    """Tests FastAPI endpoint POST /api/v1/copper/verify-origin."""
    payload = {
        "lot_id": "COP-TEST-001",
        "mine_concession_name": "EL_TENIENTE",
        "extraction_coordinates": [-34.083, -70.467],
        "source_country": "CHL",
        "feedstock_concentrate_tons": 200.0,
        "concentrate_grade_cu_pct": 28.0,
        "sulfuric_acid_input_tons": 174.72,
        "refined_copper_cathode_tons": 54.60,
        "copper_cathode_purity_pct": 99.994,
        "cochilco_export_clearance_id": "COCHILCO-EXP-TEN-01",
        "hvdc_cable_spec_compliant": True,
        "feoc_shareholding_pct": 0.0,
    }
    r = client.post("/api/v1/copper/verify-origin", json=payload, headers={"X-Dev-Bypass": "true"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert data["lot_id"] == "COP-TEST-001"
    assert data["verdict"]["geofence_verified"] is True
    assert data["verdict"]["hvdc_grid_certified"] is True


def test_mcp_verify_copper_origin_tool():
    """Tests FastMCP tool verify_copper_origin invocation."""
    args = {
        "lot_id": "COP-MCP-001",
        "mine_concession_name": "ANDINA",
        "extraction_coordinates": [-33.150, -70.283],
        "feedstock_concentrate_tons": 100.0,
        "concentrate_grade_cu_pct": 28.0,
        "sulfuric_acid_input_tons": 87.36,
        "refined_copper_cathode_tons": 27.30,
        "copper_cathode_purity_pct": 99.9935,
        "cochilco_export_clearance_id": "COCHILCO-EXP-AND-01",
        "hvdc_cable_spec_compliant": True,
    }
    resp = handle_tool_call(req_id="mcp-test-cop", name="verify_copper_origin", arguments=args)
    assert "result" in resp
    assert len(resp["result"]["content"]) > 0
    assert "DEFENSE_COPPER_GEOFENCE_PASSED" in resp["result"]["content"][0]["text"]
