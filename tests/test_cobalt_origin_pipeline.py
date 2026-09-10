import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.cobalt_pipeline import cobalt_pipeline
from app.schemas import CobaltOriginVerifyRequest
from app.mcp_stdio import handle_tool_call


@pytest.fixture
def client():
    return TestClient(app)


def build_valid_kcc_cobalt_request() -> CobaltOriginVerifyRequest:
    # Theoretical factor: 30.0% / (1.50% * 0.85) ≈ 23.5294
    # 1,000t Hydroxide requires ~23,529.4t of 1.5% Co ore
    return CobaltOriginVerifyRequest(
        trace_id="COB-COD-2026-HYD01",
        product="Crude Cobalt Hydroxide",
        concession_name="Kamoto Copper Company (KCC)",
        province="Lualaba",
        coordinates=[-10.720, 25.470],
        mine_type="LSM",
        ceec_seal_id="CEEC-KAT-2026-992144",
        egc_custody_ref=None,
        asm_comingled=False,
        zero_child_labor_audit_ref="ILO-138-182-AUDIT-KCC-09",
        heterogenite_ore_input_tons=23530.0,
        ore_grade_co_pct=1.50,
        refinery_name="Luilu Metallurgical Plant",
        refinery_country="COD",
        rmi_rmap_smelter_id="CID002847-RMAP",
        cobalt_hydroxide_output_tons=1000.0,
        hydroxide_grade_co_pct=30.0,
        feoc_equity_pct=0.0,  # Glencore Western control
        agent_address="0x71C84107b3a42E2F2Ab4Ba770265EC0c4ce5Cea6",
    )


def test_kcc_cobalt_clean_pass():
    req = build_valid_kcc_cobalt_request()
    res = cobalt_pipeline.evaluate_cobalt_lot(req)

    assert res.status == "success"
    assert res.extraction_concession.geofence_passed is True
    assert res.extraction_concession.ceec_seal_verified is True
    assert res.extraction_concession.child_labor_audit_verified is True
    assert res.mass_balance_audit.is_stoichiometrically_sound is True
    assert res.audit_verdict.ceec_export_cleared is True
    assert res.audit_verdict.asm_segregated is True
    assert res.audit_verdict.rmi_rmap_certified is True
    assert res.audit_verdict.child_labor_free is True
    assert res.audit_verdict.ira_feoc_compliant is True
    assert res.audit_verdict.confidence_score >= 90.0
    assert any("DEFENSE_GEOFENCE_VERIFIED" in d for d in res.audit_verdict.defenses_applied)
    assert any("DEFENSE_DRC_CEEC_SEAL_VALIDATED" in d for d in res.audit_verdict.defenses_applied)
    assert any("DEFENSE_LSM_SEGREGATED" in d for d in res.audit_verdict.defenses_applied)
    assert any("DEFENSE_ZERO_CHILD_LABOR_CERTIFIED" in d for d in res.audit_verdict.defenses_applied)
    assert res.onchain_proof is not None
    assert len(res.onchain_proof) > 20


def test_ceec_seal_missing_rejection():
    req = build_valid_kcc_cobalt_request()
    req.ceec_seal_id = ""  # Missing CEEC seal!

    res = cobalt_pipeline.evaluate_cobalt_lot(req)

    assert res.extraction_concession.ceec_seal_verified is False
    assert res.audit_verdict.ceec_export_cleared is False
    assert res.audit_verdict.confidence_score < 70.0
    assert any("FLAG_CEEC_SEAL_MISSING" in d for d in res.audit_verdict.defenses_applied)


def test_asm_uncontrolled_comingling_trap1():
    req = build_valid_kcc_cobalt_request()
    req.asm_comingled = True
    req.egc_custody_ref = None  # Uncertified ASM!

    res = cobalt_pipeline.evaluate_cobalt_lot(req)

    assert res.audit_verdict.asm_segregated is False
    assert any("FLAG_ASM_UNCONTROLLED_COMINGLING" in d for d in res.audit_verdict.defenses_applied)


def test_asm_governed_with_egc_custody():
    req = build_valid_kcc_cobalt_request()
    req.asm_comingled = True
    req.egc_custody_ref = "EGC-KASULO-PILOT-9981"  # Governed ASM!

    res = cobalt_pipeline.evaluate_cobalt_lot(req)

    assert res.audit_verdict.asm_segregated is True
    assert any("DEFENSE_EGC_ASM_GOVERNED" in d for d in res.audit_verdict.defenses_applied)


def test_child_labor_audit_missing():
    req = build_valid_kcc_cobalt_request()
    req.zero_child_labor_audit_ref = None

    res = cobalt_pipeline.evaluate_cobalt_lot(req)

    assert res.audit_verdict.child_labor_free is False
    assert any("FLAG_CHILD_LABOR_AUDIT_MISSING" in d for d in res.audit_verdict.defenses_applied)


def test_heterogenite_mass_balance_leakage():
    req = build_valid_kcc_cobalt_request()
    # 23,530t of 1.5% Co ore should yield ~1,000t hydroxide; 1,500t indicates illicit ore blending
    req.cobalt_hydroxide_output_tons = 1500.0

    res = cobalt_pipeline.evaluate_cobalt_lot(req)

    assert res.mass_balance_audit.is_stoichiometrically_sound is False
    assert res.mass_balance_audit.discrepancy_pct > 2.5
    assert any("FLAG_COBALT_MASS_LEAKAGE" in d for d in res.audit_verdict.defenses_applied)


def test_cmoc_feoc_excess_flag():
    req = build_valid_kcc_cobalt_request()
    req.concession_name = "Tenke Fungurume Mining (TFM)"
    req.coordinates = [-10.550, 26.180]
    req.feoc_equity_pct = 80.0  # CMOC Chinese parent ownership exceeds 25% cap

    res = cobalt_pipeline.evaluate_cobalt_lot(req)

    assert res.audit_verdict.ira_feoc_compliant is False
    assert any("FLAG_IRA_FEOC_EXCLUDED" in d for d in res.audit_verdict.defenses_applied)


def test_fastapi_cobalt_verify_endpoint(client):
    req = build_valid_kcc_cobalt_request()
    payload = req.model_dump()

    resp = client.post(
        "/api/v1/cobalt/verify-origin",
        json=payload,
        headers={"X-Dev-Bypass": "true"}
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "success"
    assert data["trace_id"] == "COB-COD-2026-HYD01"
    assert data["audit_verdict"]["ceec_export_cleared"] is True
    assert data["audit_verdict"]["child_labor_free"] is True
    assert "onchain_proof" in data


def test_mcp_verify_cobalt_origin_tool():
    req = build_valid_kcc_cobalt_request()
    args = req.model_dump()

    mcp_res = handle_tool_call(req_id=102, name="verify_cobalt_origin", arguments=args)
    assert mcp_res["jsonrpc"] == "2.0"
    assert "result" in mcp_res
    text_payload = mcp_res["result"]["content"][0]["text"]
    assert "Kamoto" in text_payload
    assert "ceec_export_cleared" in text_payload
