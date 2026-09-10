import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.lithium_pipeline import lithium_pipeline
from app.schemas import LithiumOriginVerifyRequest
from app.mcp_stdio import handle_tool_call


@pytest.fixture
def client():
    return TestClient(app)


def build_valid_greenbushes_request() -> LithiumOriginVerifyRequest:
    return LithiumOriginVerifyRequest(
        trace_id="LIT-AU-2026-X091",
        product="Lithium Hydroxide Monohydrate",
        mine_name="Greenbushes Lithium Mine",
        mine_country="AU",
        coordinates=[-33.864, 116.006],
        minedex_tenement_id="M01/03",
        spodumene_tonnage_extracted=7500.0,
        spodumene_grade_pct=6.0,
        refinery_facility="Kwinana Lithium Hydroxide Plant",
        refinery_country="AU",
        refined_output_tonnage=1000.0,
        refinery_feoc_equity_pct=0.0,
        satellite_vegetation_index=0.12,
        sar_backscatter_db=-11.8,
        agent_address="0x71C84107b3a42E2F2Ab4Ba770265EC0c4ce5Cea6",
    )


def test_greenbushes_to_kwinana_clean_pass():
    req = build_valid_greenbushes_request()
    res = lithium_pipeline.evaluate_lithium_lot(req)

    assert res.status == "success"
    assert res.extraction_origin.geofence_passed is True
    assert res.extraction_origin.minedex_tenement_id == "M01/03"
    assert res.extraction_origin.satellite_evidence["active_status"] == "CONFIRMED"
    assert res.mass_balance_audit.is_stoichiometrically_sound is True
    assert res.audit_verdict.ira_compliant is True
    assert res.audit_verdict.crma_origin_eligible is True
    assert res.audit_verdict.feoc_risk_detected is False
    assert res.audit_verdict.confidence_score >= 90.0
    assert any("DEFENSE_GEOFENCE_VERIFIED" in d for d in res.audit_verdict.defenses_applied)
    assert any("DEFENSE_IRA_FEOC_CLEARED" in d for d in res.audit_verdict.defenses_applied)
    assert res.onchain_proof is not None
    assert len(res.onchain_proof) > 20


def test_geofence_exceeded_rejection():
    req = build_valid_greenbushes_request()
    req.coordinates = [-31.500, 115.000]  # ~300km away from Greenbushes

    res = lithium_pipeline.evaluate_lithium_lot(req)

    assert res.extraction_origin.geofence_passed is False
    assert res.audit_verdict.crma_origin_eligible is False
    assert res.audit_verdict.confidence_score < 75.0
    assert any("FLAG_GEOFENCE_EXCEEDED" in d for d in res.audit_verdict.defenses_applied)


def test_china_smelter_feoc_rejection():
    req = build_valid_greenbushes_request()
    req.refinery_facility = "Yingkou Conversion Facility"
    req.refinery_country = "CHN"
    req.refinery_feoc_equity_pct = 100.0

    res = lithium_pipeline.evaluate_lithium_lot(req)

    assert res.audit_verdict.ira_compliant is False
    assert res.audit_verdict.feoc_risk_detected is True
    assert any("FLAG_IRA_FEOC_EXCLUDED" in d for d in res.audit_verdict.defenses_applied)


def test_stoichiometric_mass_balance_leakage():
    req = build_valid_greenbushes_request()
    # 7,500t should yield ~1,000t LiOH; 1,400t indicates unverified feed co-mingling
    req.refined_output_tonnage = 1400.0

    res = lithium_pipeline.evaluate_lithium_lot(req)

    assert res.mass_balance_audit.is_stoichiometrically_sound is False
    assert res.mass_balance_audit.discrepancy_pct > 2.5
    assert any("FLAG_STOICHIOMETRIC_LEAKAGE" in d for d in res.audit_verdict.defenses_applied)


def test_fastapi_lithium_verify_endpoint(client):
    req = build_valid_greenbushes_request()
    payload = req.model_dump()

    resp = client.post(
        "/api/v1/lithium/verify-origin",
        json=payload,
        headers={"X-Dev-Bypass": "true"}
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "success"
    assert data["trace_id"] == "LIT-AU-2026-X091"
    assert data["extraction_origin"]["geofence_passed"] is True
    assert data["audit_verdict"]["ira_compliant"] is True
    assert "onchain_proof" in data


def test_mcp_verify_lithium_origin_tool():
    req = build_valid_greenbushes_request()
    args = req.model_dump()

    mcp_res = handle_tool_call(req_id=99, name="verify_lithium_origin", arguments=args)
    assert mcp_res["jsonrpc"] == "2.0"
    assert "result" in mcp_res
    text_payload = mcp_res["result"]["content"][0]["text"]
    assert "Greenbushes" in text_payload
    assert "ira_compliant" in text_payload
