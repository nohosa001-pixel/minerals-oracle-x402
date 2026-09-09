import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import (
    MineralLotProvenanceRequest,
    MineralType,
    SourceCountry,
    MaritimeCIIRating,
    MinePermitsRecord,
    EcologicalSpatialRecord,
    LaborHumanRightsRecord,
    RefiningMassBalanceRecord,
    MaritimeLogisticsRecord,
    GeopoliticalSanctionsRecord,
)
from app.compliance_engine import compliance_engine


@pytest.fixture
def client():
    return TestClient(app)


def build_valid_indonesia_nickel_request() -> MineralLotProvenanceRequest:
    return MineralLotProvenanceRequest(
        lot_id="LOT-2026-NI-IDN-0412",
        mineral_type=MineralType.NICKEL_MHP,
        source_country=SourceCountry.IDN,
        net_weight_metric_tons=500.0,
        declared_purity_pct=38.5,
        mine_permits=MinePermitsRecord(
            mining_license_id="IUP-OP-4491-SULAWESI",
            mine_operator_name="PT Sulawesi Nickel Resources",
            simbara_ntpn="NTPN-884219482109",
            simbara_rkab_quota_id="RKAB-2026-IDN-771",
            dhe_forex_deposit_ref="DHE-BI-992144-USD",
        ),
        ecological_spatial=EcologicalSpatialRecord(
            latitude=-2.812451,
            longitude=121.341209,
            eudr_deforestation_free=True,
            periglacial_zone_violation=False,
            indigenous_territory_encroachment=False,
            tailing_dam_dce_certified=True,
            aquifer_depletion_alert=False,
        ),
        labor_human_rights=LaborHumanRightsRecord(
            child_labor_free_certified=True,
            rmi_rmap_audit_id="RMI-RMAP-2026-0811",
            forced_labor_uapa_cleared=True,
        ),
        refining_mass_balance=RefiningMassBalanceRecord(
            refinery_id="HPAL-IWIP-LINE-3",
            feedstock_input_metric_tons=4200.0,
            refined_output_metric_tons=500.0,
            recovery_yield_pct=91.4,
            mass_balance_loss_discrepancy_pct=1.12,  # <= 2.0%
            captive_coal_power_used=False,
        ),
        maritime_logistics=MaritimeLogisticsRecord(
            vessel_imo_number=9842144,
            vessel_name="MV Pacific Compliance",
            cii_rating=MaritimeCIIRating.B,
            ebl_document_hash="0x7a8f3b91c4d2e5a6f7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0",
            iso_17025_lab_coa_hash="0x11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff",
            tml_moisture_safe=True,
        ),
        geopolitical_sanctions=GeopoliticalSanctionsRecord(
            feoc_shareholding_pct=14.5,  # < 25%
            feoc_board_control_pct=10.0,
            contractual_operational_control=False,
            ofac_sdn_sanctioned=False,
            us_substantial_transformation_compliant=True,
        ),
        commercial_price_usd_per_ton=18500.0,
        agent_address="0x71C84107b3a42E2F2Ab4Ba770265EC0c4ce5Cea6",
    )


def test_indonesia_nickel_full_compliance_pass():
    """Verify clean Indonesian Nickel MHP lot passes all 7 pillars and issues passport."""
    req = build_valid_indonesia_nickel_request()
    res = compliance_engine.evaluate_lot(req)

    assert res.verdict.is_fully_compliant is True
    assert res.verdict.overall_compliance_score >= 85.0
    assert res.verdict.eu_battery_regulation_ready is True
    assert res.verdict.us_ira_feoc_compliant is True
    assert res.verdict.oecd_annex_ii_passed is True
    assert res.eip712_signature is not None
    assert "DEFENSE_IDN_SIMBARA_NTPN_VALIDATED" in str(res.verdict.gotcha_defenses_applied)
    assert any(c.precedent_case_id == "WTO_DS592_INDONESIA_RAW_MATERIALS" for c in res.verdict.jurisprudence_citations)
    # Legal Disclaimer & Fee-Capped Liability Assertions
    assert res.legal_disclaimer is not None
    assert res.legal_disclaimer.liability_cap_usdc == 0.50
    assert len(res.legal_disclaimer.binding_disclaimer_hash) == 66  # 0x + 64 hex
    assert "ALGORITHMIC_VERIFICATION_ONLY" in res.legal_disclaimer.warranty_disclaimer
    assert "ZERO_CONSEQUENTIAL_LIABILITY" in res.legal_disclaimer.consequential_damages_waiver
    assert "NON_DELEGABLE_IMPORTER_DUTY" in res.legal_disclaimer.non_delegable_audit_duty


def test_drc_cobalt_ceec_seal_failure():
    """Verify DRC Cobalt missing CEEC tamper-evident barcode tag is rejected."""
    req = build_valid_indonesia_nickel_request()
    req.source_country = SourceCountry.COD
    req.mineral_type = MineralType.COBALT_HYDROXIDE
    req.mine_permits.ceec_barcode_tag_id = None  # Missing seal!

    res = compliance_engine.evaluate_lot(req)
    assert res.verdict.is_fully_compliant is False
    assert any("COD_CEEC_BARCODE_INVALID" in d for d in res.verdict.gotcha_defenses_applied)


def test_oecd_mass_balance_loss_exceeded():
    """Verify mass balance discrepancy > 2.0% triggers OECD Annex II violation."""
    req = build_valid_indonesia_nickel_request()
    req.refining_mass_balance.mass_balance_loss_discrepancy_pct = 3.85  # Violates 2% rule

    res = compliance_engine.evaluate_lot(req)
    assert res.verdict.is_fully_compliant is False
    assert any("OECD_MASS_BALANCE_EXCEEDED" in d for d in res.verdict.gotcha_defenses_applied)


def test_us_ira_feoc_25_pct_exclusion():
    """Verify FEOC covered entity ownership >= 25% flags IRA credit exclusion."""
    req = build_valid_indonesia_nickel_request()
    req.geopolitical_sanctions.feoc_shareholding_pct = 28.5  # Exceeds 25% FEOC cap

    res = compliance_engine.evaluate_lot(req)
    assert res.verdict.us_ira_feoc_compliant is False
    assert any("FLAG_IRA_FEOC_EXCLUDED" in d for d in res.verdict.gotcha_defenses_applied)


def test_argentina_glacier_periglacial_violation():
    """Verify mining in Argentina Ley 26.639 periglacial zone is rejected."""
    req = build_valid_indonesia_nickel_request()
    req.source_country = SourceCountry.ARG
    req.mineral_type = MineralType.LITHIUM_CARBONATE
    req.ecological_spatial.periglacial_zone_violation = True

    res = compliance_engine.evaluate_lot(req)
    assert res.verdict.is_fully_compliant is False
    assert any("ARG_LEY_26639_VIOLATION" in d for d in res.verdict.gotcha_defenses_applied)


def test_api_compliance_verify_endpoint(client):
    """Test POST /api/v1/oracle/compliance/verify with dev bypass."""
    req = build_valid_indonesia_nickel_request()
    payload = req.model_dump()

    resp = client.post(
        "/api/v1/oracle/compliance/verify",
        json=payload,
        headers={"X-Dev-Bypass": "true"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["lot_id"] == "LOT-2026-NI-IDN-0412"
    assert data["verdict"]["is_fully_compliant"] is True
    assert "eip712_signature" in data
    assert "passport_qr_data" in data
    assert "legal_disclaimer" in data
    assert data["legal_disclaimer"]["liability_cap_usdc"] == 0.50
    assert "binding_disclaimer_hash" in data["legal_disclaimer"]


def test_api_compliance_precedents_endpoint(client):
    """Test GET /api/v1/oracle/compliance/precedents returns WTO/ICSID/CIT cases."""
    resp = client.get("/api/v1/oracle/compliance/precedents")
    assert resp.status_code == 200
    data = resp.json()
    assert data["jurisprudence_count"] >= 4
    case_ids = [p["case_id"] for p in data["precedents"]]
    assert "WTO_DS592_INDONESIA_RAW_MATERIALS" in case_ids
    assert "ICSID_ARB_15_31_GABRIEL_RESOURCES" in case_ids


def test_api_compliance_status_endpoint(client):
    """Test GET /api/v1/oracle/compliance/status returns healthy status."""
    resp = client.get("/api/v1/oracle/compliance/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "HEALTHY"
    assert data["pillars_active"] == 7
    assert data["traps_defended"] == 12
    assert "IDN" in data["monitored_jurisdictions"]
    assert "COD" in data["monitored_jurisdictions"]
