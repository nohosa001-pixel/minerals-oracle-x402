import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.composite_battery_pipeline import composite_battery_pipeline
from app.schemas import (
    CompositeBatteryVerifyRequest,
    LithiumOriginVerifyRequest,
    NickelOriginVerifyRequest,
    CobaltOriginVerifyRequest,
)
from app.mcp_stdio import handle_tool_call


@pytest.fixture
def client():
    return TestClient(app)


def build_clean_composite_battery_request() -> CompositeBatteryVerifyRequest:
    # 1. Clean Australian Lithium (1,000t LiOH at ~$18.5k/t = $18.5M value) -> 100% FTA
    lithium_lot = LithiumOriginVerifyRequest(
        trace_id="LITH-AU-2026-B01",
        mine_name="Greenbushes Lithium Operation",
        coordinates=[-33.864, 116.006],
        minedex_tenement_id="M01/03",
        spodumene_tonnage_extracted=7500.0,
        spodumene_grade_pct=6.0,
        refinery_facility="Kwinana Lithium Hydroxide Plant",
        refinery_country="AU",
        refined_output_tonnage=1000.0,
        refinery_feoc_equity_pct=0.0,
    )

    # 2. Clean Indonesian Nickel (300t MHP at 38.5% Ni = 115.5t Ni equiv at ~$17k/t = $1.96M value)
    nickel_lot = NickelOriginVerifyRequest(
        trace_id="NIC-IDN-2026-MHP01",
        product="Nickel Mixed Hydroxide Precipitate (MHP)",
        concession_name="PT Morowali Nickel Industrial Concession",
        coordinates=[-2.812, 122.152],
        simbara_ntpn="NTPN-884219482109",
        dhe_forex_deposit_ref="DHE-BI-992144-USD",
        limonite_ore_input_tons=9402.0,
        ore_grade_ni_pct=1.35,
        hpal_refinery_name="QMB New Energy Clean HPAL",
        mhp_output_tons=300.0,
        mhp_grade_ni_pct=38.5,
        captive_coal_power=False,
        feoc_equity_pct=15.0,  # < 25%
    )

    # 3. Clean DRC Cobalt (100t Hydroxide at 30% Co = 30t Co equiv at ~$32k/t = $0.96M value)
    cobalt_lot = CobaltOriginVerifyRequest(
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
        heterogenite_ore_input_tons=2353.0,
        ore_grade_co_pct=1.50,
        refinery_name="Luilu Metallurgical Plant",
        refinery_country="COD",
        rmi_rmap_smelter_id="CID002847-RMAP",
        cobalt_hydroxide_output_tons=100.0,
        hydroxide_grade_co_pct=30.0,
        feoc_equity_pct=0.0,
    )

    return CompositeBatteryVerifyRequest(
        battery_pack_id="BATT-NCM811-2026-PACK01",
        cell_chemistry="NCM811",
        pack_capacity_kwh=84.0,
        lithium_lot=lithium_lot,
        nickel_lot=nickel_lot,
        cobalt_lot=cobalt_lot,
        agent_address="0x71C84107b3a42E2F2Ab4Ba770265EC0c4ce5Cea6",
    )


def test_clean_ncm811_battery_pack_pass():
    req = build_clean_composite_battery_request()
    res = composite_battery_pipeline.evaluate_battery_pack(req)

    assert res.status == "success"
    assert res.battery_pack_id == "BATT-NCM811-2026-PACK01"
    assert res.composite_verdict.ira_30d_tax_credit_eligible is True
    assert res.composite_verdict.ira_critical_mineral_fta_ratio_pct >= 50.0
    assert res.composite_verdict.eu_battery_passport_approved is True
    assert res.composite_verdict.feoc_taint_detected is False
    assert res.composite_verdict.cbam_carbon_penalty_alert is False
    assert res.composite_verdict.lithium_cleared is True
    assert res.composite_verdict.nickel_cleared is True
    assert res.composite_verdict.cobalt_cleared is True
    assert res.composite_verdict.composite_confidence_score >= 85.0
    assert res.merkle_root.startswith("0x")
    assert len(res.merkle_root) == 66
    assert res.master_onchain_proof is not None
    assert len(res.master_onchain_proof) > 20
    assert any("DEFENSE_IRA_30D_QUALIFIED" in d for d in res.composite_verdict.composite_defenses_applied)
    assert any("DEFENSE_EU_BATTERY_PASSPORT_APPROVED" in d for d in res.composite_verdict.composite_defenses_applied)


def test_feoc_taint_propagation():
    req = build_clean_composite_battery_request()
    # Taint the Cobalt stream with 80% Chinese ownership (e.g. CMOC Tenke Fungurume)
    req.cobalt_lot.feoc_equity_pct = 80.0

    res = composite_battery_pipeline.evaluate_battery_pack(req)

    assert res.composite_verdict.feoc_taint_detected is True
    assert res.composite_verdict.ira_30d_tax_credit_eligible is False
    assert any("FLAG_COMPOSITE_FEOC_TAINT" in d for d in res.composite_verdict.composite_defenses_applied)


def test_captive_coal_cbam_propagation():
    req = build_clean_composite_battery_request()
    # Set nickel plant on captive coal power
    req.nickel_lot.captive_coal_power = True

    res = composite_battery_pipeline.evaluate_battery_pack(req)

    assert res.composite_verdict.cbam_carbon_penalty_alert is True
    assert res.composite_verdict.eu_battery_passport_approved is False
    assert res.composite_verdict.blended_carbon_footprint_kg_per_kwh > 70.0
    assert any("FLAG_EU_BATTERY_CBAM_SURCHARGE" in d for d in res.composite_verdict.composite_defenses_applied)


def test_child_labor_propagation():
    req = build_clean_composite_battery_request()
    req.cobalt_lot.zero_child_labor_audit_ref = None

    res = composite_battery_pipeline.evaluate_battery_pack(req)

    assert res.composite_verdict.cobalt_cleared is False
    assert res.composite_verdict.eu_battery_passport_approved is False
    assert any("FLAG_EU_BATTERY_PASSPORT_HOLD" in d for d in res.composite_verdict.composite_defenses_applied)


def test_fastapi_composite_battery_endpoint(client):
    req = build_clean_composite_battery_request()
    payload = req.model_dump()

    resp = client.post(
        "/api/v1/battery/composite-verify",
        json=payload,
        headers={"X-Dev-Bypass": "true"}
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "success"
    assert data["battery_pack_id"] == "BATT-NCM811-2026-PACK01"
    assert data["composite_verdict"]["ira_30d_tax_credit_eligible"] is True
    assert data["composite_verdict"]["eu_battery_passport_approved"] is True
    assert "merkle_root" in data
    assert "master_onchain_proof" in data


def test_mcp_verify_composite_battery_tool():
    req = build_clean_composite_battery_request()
    args = req.model_dump()

    mcp_res = handle_tool_call(req_id=103, name="verify_composite_battery_passport", arguments=args)
    assert mcp_res["jsonrpc"] == "2.0"
    assert "result" in mcp_res
    text_payload = mcp_res["result"]["content"][0]["text"]
    assert "BATT-NCM811-2026-PACK01" in text_payload
    assert "merkle_root" in text_payload
    assert "ira_30d_tax_credit_eligible" in text_payload
