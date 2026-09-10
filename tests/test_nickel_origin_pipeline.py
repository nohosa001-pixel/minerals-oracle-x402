import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.nickel_pipeline import nickel_pipeline
from app.schemas import NickelOriginVerifyRequest
from app.mcp_stdio import handle_tool_call


@pytest.fixture
def client():
    return TestClient(app)


def build_valid_morowali_mhp_request() -> NickelOriginVerifyRequest:
    return NickelOriginVerifyRequest(
        trace_id="NIC-IDN-2026-MHP01",
        product="Nickel Mixed Hydroxide Precipitate (MHP)",
        concession_name="PT Morowali Nickel Industrial Concession",
        coordinates=[-2.812, 122.152],
        simbara_ntpn="NTPN-884219482109",
        dhe_forex_deposit_ref="DHE-BI-992144-USD",
        limonite_ore_input_tons=31340.0,
        ore_grade_ni_pct=1.35,
        hpal_refinery_name="QMB New Energy Clean HPAL",
        mhp_output_tons=1000.0,
        mhp_grade_ni_pct=38.5,
        captive_coal_power=False,
        feoc_equity_pct=15.0,  # < 25%
        agent_address="0x71C84107b3a42E2F2Ab4Ba770265EC0c4ce5Cea6",
    )


def test_morowali_nickel_mhp_clean_pass():
    req = build_valid_morowali_mhp_request()
    res = nickel_pipeline.evaluate_nickel_lot(req)

    assert res.status == "success"
    assert res.extraction_concession.geofence_passed is True
    assert res.extraction_concession.simbara_ntpn_verified is True
    assert res.extraction_concession.dhe_forex_verified is True
    assert res.hpal_mass_balance.is_stoichiometrically_sound is True
    assert res.audit_verdict.simbara_export_cleared is True
    assert res.audit_verdict.wto_ds592_compliant is True
    assert res.audit_verdict.cbam_carbon_ready is True
    assert res.audit_verdict.ira_feoc_compliant is True
    assert res.audit_verdict.confidence_score >= 90.0
    assert any("DEFENSE_GEOFENCE_VERIFIED" in d for d in res.audit_verdict.defenses_applied)
    assert any("DEFENSE_IDN_SIMBARA_NTPN_VALIDATED" in d for d in res.audit_verdict.defenses_applied)
    assert any("DEFENSE_EU_CBAM_CLEARED" in d for d in res.audit_verdict.defenses_applied)
    assert res.onchain_proof is not None
    assert len(res.onchain_proof) > 20


def test_simbara_ntpn_missing_rejection():
    req = build_valid_morowali_mhp_request()
    req.simbara_ntpn = ""  # Missing SIMBARA tax code!

    res = nickel_pipeline.evaluate_nickel_lot(req)

    assert res.extraction_concession.simbara_ntpn_verified is False
    assert res.audit_verdict.simbara_export_cleared is False
    assert res.audit_verdict.confidence_score < 70.0
    assert any("FLAG_SIMBARA_NTPN_MISSING" in d for d in res.audit_verdict.defenses_applied)


def test_captive_coal_cbam_flag():
    req = build_valid_morowali_mhp_request()
    req.captive_coal_power = True

    res = nickel_pipeline.evaluate_nickel_lot(req)

    assert res.audit_verdict.cbam_carbon_ready is False
    assert any("FLAG_EU_CBAM_CAPTIVE_COAL" in d for d in res.audit_verdict.defenses_applied)


def test_hpal_mass_balance_leakage():
    req = build_valid_morowali_mhp_request()
    # 31,340 tons of limonite should yield ~1,000t MHP; 1,400t indicates unverified co-mingling
    req.mhp_output_tons = 1400.0

    res = nickel_pipeline.evaluate_nickel_lot(req)

    assert res.hpal_mass_balance.is_stoichiometrically_sound is False
    assert res.hpal_mass_balance.discrepancy_pct > 2.5
    assert any("FLAG_HPAL_MASS_LEAKAGE" in d for d in res.audit_verdict.defenses_applied)


def test_feoc_excess_rejection():
    req = build_valid_morowali_mhp_request()
    req.feoc_equity_pct = 45.0  # Exceeds 25% FEOC cap

    res = nickel_pipeline.evaluate_nickel_lot(req)

    assert res.audit_verdict.ira_feoc_compliant is False
    assert any("FLAG_IRA_FEOC_EXCLUDED" in d for d in res.audit_verdict.defenses_applied)


def test_fastapi_nickel_verify_endpoint(client):
    req = build_valid_morowali_mhp_request()
    payload = req.model_dump()

    resp = client.post(
        "/api/v1/nickel/verify-origin",
        json=payload,
        headers={"X-Dev-Bypass": "true"}
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "success"
    assert data["trace_id"] == "NIC-IDN-2026-MHP01"
    assert data["audit_verdict"]["simbara_export_cleared"] is True
    assert data["audit_verdict"]["cbam_carbon_ready"] is True
    assert "onchain_proof" in data


def test_mcp_verify_nickel_origin_tool():
    req = build_valid_morowali_mhp_request()
    args = req.model_dump()

    mcp_res = handle_tool_call(req_id=101, name="verify_nickel_origin", arguments=args)
    assert mcp_res["jsonrpc"] == "2.0"
    assert "result" in mcp_res
    text_payload = mcp_res["result"]["content"][0]["text"]
    assert "Morowali" in text_payload
    assert "simbara_export_cleared" in text_payload
