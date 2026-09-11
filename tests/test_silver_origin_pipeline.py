"""
Unit & Integration Tests for Mexican & Global Silver Provenance Pipeline.
Validates Terronera/Fresnillo geofencing, Moebius/Thum electrolytic mass balance,
N-type TOPCon solar PV paste purity (>= 99.99% Ag), conflict ASM defenses, and LBMA audits.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import SilverOriginVerifyRequest, SourceCountry
from app.silver_pipeline import silver_pipeline
from app.mcp_stdio import handle_tool_call


client = TestClient(app)


def test_terronera_silver_clean_pass():
    """Validates clean Endeavour Silver Terronera solar PV silver paste lot passing all checks."""
    # 5,000kg Doré at 75.0% Ag = 3,750kg contained * 0.99 recovery = 3,712.5kg theoretical refined silver
    req = SilverOriginVerifyRequest(
        lot_id="SIL-MEX-2026-TER01",
        mine_concession_name="TERRONERA",
        extraction_coordinates=(20.590, -104.980),
        source_country=SourceCountry.MEX,
        feedstock_dore_or_ore_kg=5000.0,
        feedstock_silver_grade_pct=75.0,
        refined_solar_powder_kg=3712.5,
        refined_purity_pct=99.995,
        lbma_good_delivery_ref="LBMA-REF-MEX-01",
        conflict_free_asm_verified=True,
        topcon_pv_grade_compliant=True,
        feoc_shareholding_pct=0.0,
    )
    res = silver_pipeline.verify_origin(req)
    assert res.status == "success"
    assert res.verdict.geofence_verified is True
    assert res.verdict.refining_mass_balance_passed is True
    assert res.verdict.topcon_solar_pv_certified is True
    assert res.verdict.conflict_free_asm_passed is True
    assert res.verdict.lbma_cleared is True
    assert res.verdict.feoc_cleared is True
    assert res.verdict.confidence_score >= 90.0
    assert res.onchain_proof.startswith("0x")


def test_silver_topcon_purity_deficit_rejection():
    """Rejects solar PV silver lot when purity is under 99.99% Ag."""
    req = SilverOriginVerifyRequest(
        lot_id="SIL-MEX-2026-PURITY-FAIL",
        mine_concession_name="TERRONERA",
        extraction_coordinates=(20.590, -104.980),
        source_country=SourceCountry.MEX,
        feedstock_dore_or_ore_kg=5000.0,
        feedstock_silver_grade_pct=75.0,
        refined_solar_powder_kg=3712.5,
        refined_purity_pct=99.85,  # Substandard for TOPCon solar PV paste (< 99.99%)
        lbma_good_delivery_ref="LBMA-REF-MEX-01",
        conflict_free_asm_verified=True,
        topcon_pv_grade_compliant=True,
    )
    res = silver_pipeline.verify_origin(req)
    assert res.verdict.topcon_solar_pv_certified is False
    assert any("FATAL_SILVER_PURITY_DEFICIT" in d for d in res.verdict.defenses_applied)


def test_silver_conflict_asm_taint_rejection():
    """Rejects silver lot tainted by unverified artisanal or cartel laundering."""
    req = SilverOriginVerifyRequest(
        lot_id="SIL-MEX-2026-ASM-FAIL",
        mine_concession_name="TERRONERA",
        extraction_coordinates=(20.590, -104.980),
        source_country=SourceCountry.MEX,
        feedstock_dore_or_ore_kg=5000.0,
        feedstock_silver_grade_pct=75.0,
        refined_solar_powder_kg=3712.5,
        refined_purity_pct=99.995,
        conflict_free_asm_verified=False,  # Cartel / unverified ASM taint
    )
    res = silver_pipeline.verify_origin(req)
    assert res.verdict.conflict_free_asm_passed is False
    assert any("FATAL_SILVER_ASM_TAINT" in d for d in res.verdict.defenses_applied)


def test_silver_mass_balance_loss_exceeded():
    """Rejects silver lot when refining output diverges by > 2.0% from theoretical yield."""
    req = SilverOriginVerifyRequest(
        lot_id="SIL-MEX-2026-MASS-FAIL",
        mine_concession_name="TERRONERA",
        extraction_coordinates=(20.590, -104.980),
        source_country=SourceCountry.MEX,
        feedstock_dore_or_ore_kg=5000.0,
        feedstock_silver_grade_pct=75.0,
        refined_solar_powder_kg=4500.0,  # Far above 3,712.5kg (+21%)
        refined_purity_pct=99.995,
    )
    res = silver_pipeline.verify_origin(req)
    assert res.verdict.refining_mass_balance_passed is False
    assert any("FATAL_SILVER_MASS_BALANCE_EXCEEDED" in d for d in res.verdict.defenses_applied)


def test_fastapi_silver_verify_endpoint():
    """Tests FastAPI endpoint POST /api/v1/silver/verify-origin."""
    payload = {
        "lot_id": "SIL-TEST-001",
        "mine_concession_name": "FRESNILLO",
        "extraction_coordinates": [23.175, -102.870],
        "source_country": "MEX",
        "feedstock_dore_or_ore_kg": 2000.0,
        "feedstock_silver_grade_pct": 80.0,
        "refined_solar_powder_kg": 1584.0,
        "refined_purity_pct": 99.992,
        "lbma_good_delivery_ref": "LBMA-FRE-01",
        "conflict_free_asm_verified": True,
        "topcon_pv_grade_compliant": True,
        "feoc_shareholding_pct": 0.0,
    }
    r = client.post("/api/v1/silver/verify-origin", json=payload, headers={"X-Dev-Bypass": "true"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert data["lot_id"] == "SIL-TEST-001"
    assert data["verdict"]["topcon_solar_pv_certified"] is True


def test_mcp_verify_silver_origin_tool():
    """Tests FastMCP tool verify_silver_origin invocation."""
    args = {
        "lot_id": "SIL-MCP-001",
        "mine_concession_name": "ANTAMINA",
        "extraction_coordinates": [-9.533, -77.050],
        "source_country": "PER",
        "feedstock_dore_or_ore_kg": 1000.0,
        "feedstock_silver_grade_pct": 70.0,
        "refined_solar_powder_kg": 693.0,
        "refined_purity_pct": 99.995,
        "lbma_good_delivery_ref": "LBMA-PER-ANT-01",
    }
    resp = handle_tool_call(req_id="mcp-test-sil", name="verify_silver_origin", arguments=args)
    assert "result" in resp
    assert len(resp["result"]["content"]) > 0
    assert "DEFENSE_SILVER_GEOFENCE_PASSED" in resp["result"]["content"][0]["text"]
