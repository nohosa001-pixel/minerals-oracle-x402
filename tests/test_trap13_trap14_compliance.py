import pytest
from app.compliance_engine import compliance_engine
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


def create_base_provenance_request() -> MineralLotProvenanceRequest:
    return MineralLotProvenanceRequest(
        lot_id="LOT-2026-TEST-PROVENANCE-001",
        mineral_type=MineralType.LITHIUM_HYDROXIDE,
        source_country=SourceCountry.AUS,
        net_weight_metric_tons=100.0,
        declared_purity_pct=99.5,
        mine_permits=MinePermitsRecord(
            mining_license_id="AUS-MINING-LIC-9921",
            mine_operator_name="Pilbara Clean Minerals Ltd",
            australia_epbc_ref_no="EPBC-2026-9901",
        ),
        ecological_spatial=EcologicalSpatialRecord(
            latitude=-21.123456,
            longitude=119.654321,
            eudr_deforestation_free=True,
            periglacial_zone_violation=False,
            indigenous_territory_encroachment=False,
            tailing_dam_dce_certified=True,
            aquifer_depletion_alert=False,
        ),
        labor_human_rights=LaborHumanRightsRecord(
            child_labor_free_certified=True,
            rmi_rmap_audit_id="RMI-RMAP-AUS-2026-01",
            ilua_registration_id="ILUA-NT-2026-881",
            forced_labor_uapa_cleared=True,
        ),
        refining_mass_balance=RefiningMassBalanceRecord(
            refinery_id="KWINANA-HYDROXIDE-REFINERY",
            feedstock_input_metric_tons=800.0,
            refined_output_metric_tons=100.0,
            recovery_yield_pct=92.0,
            mass_balance_loss_discrepancy_pct=1.05,
            captive_coal_power_used=False,
            solvent_extraction_tech_origin="WESTERN",
        ),
        maritime_logistics=MaritimeLogisticsRecord(
            vessel_imo_number=9812456,
            vessel_name="PACIFIC BULKER",
            cii_rating=MaritimeCIIRating.B,
            ebl_document_hash="0x" + "c" * 64,
            iso_17025_lab_coa_hash="0x" + "d" * 64,
            tml_moisture_safe=True,
        ),
        geopolitical_sanctions=GeopoliticalSanctionsRecord(
            feoc_shareholding_pct=0.0,
            feoc_board_control_pct=0.0,
            contractual_operational_control=False,
            ofac_sdn_sanctioned=False,
            us_substantial_transformation_compliant=True,
        ),
    )


def test_trap13_us_bis_black_mass_unauthorized_fails():
    req = create_base_provenance_request()
    req.mineral_type = MineralType.LITHIUM_BLACK_MASS
    req.source_country = SourceCountry.USA
    req.is_recycled_black_mass = True
    req.us_bis_export_authorized = False  # Unauthorized overseas export attempt
    req.mine_permits.us_bis_scrap_export_license = None

    res = compliance_engine.evaluate_lot(req)
    verdict = res.verdict

    assert not verdict.is_fully_compliant
    assert not verdict.us_bis_scrap_retention_cleared
    assert any("US_BIS_15CFR744_SCRAP_RETENTION_VIOLATION" in flag for flag in verdict.gotcha_defenses_applied)
    assert any(c.precedent_case_id == "US_BIS_15CFR744_DEFENSE_PRODUCTION_ACT" and c.compliance_status == "VIOLATION" for c in verdict.jurisprudence_citations)


def test_trap13_us_bis_black_mass_with_valid_license_passes():
    req = create_base_provenance_request()
    req.mineral_type = MineralType.NICKEL_COBALT_BLACK_MASS
    req.source_country = SourceCountry.USA
    req.is_recycled_black_mass = True
    req.us_bis_export_authorized = True
    req.mine_permits.us_bis_scrap_export_license = "BIS-DPA-2026-X883921"

    res = compliance_engine.evaluate_lot(req)
    verdict = res.verdict

    assert verdict.is_fully_compliant
    assert verdict.us_bis_scrap_retention_cleared
    assert any("DEFENSE_US_BIS_SCRAP_COMPLIANT" in flag for flag in verdict.gotcha_defenses_applied)


def test_trap14_china_unlicensed_sx_tech_fails():
    req = create_base_provenance_request()
    req.refining_mass_balance.solvent_extraction_tech_origin = "CHINA_UNLICENSED"

    res = compliance_engine.evaluate_lot(req)
    verdict = res.verdict

    assert not verdict.is_fully_compliant
    assert not verdict.china_tech_jurisdiction_cleared
    assert any("CHN_MINERAL_LAW_TECH_VIOLATION" in flag for flag in verdict.gotcha_defenses_applied)
    assert any(c.precedent_case_id == "CHN_MINERAL_RESOURCES_LAW_EXTRATERRITORIAL" and c.compliance_status == "VIOLATION" for c in verdict.jurisprudence_citations)


def test_trap14_independent_western_sx_tech_passes():
    req = create_base_provenance_request()
    req.refining_mass_balance.solvent_extraction_tech_origin = "DOMESTIC"

    res = compliance_engine.evaluate_lot(req)
    verdict = res.verdict

    assert verdict.is_fully_compliant
    assert verdict.china_tech_jurisdiction_cleared
    assert any("DEFENSE_CHN_TECH_JURISDICTION_CLEARED" in flag for flag in verdict.gotcha_defenses_applied)


def test_cbam_definitive_period_and_csddd_audit():
    req = create_base_provenance_request()
    req.refining_mass_balance.cbam_declaration_id = "CBAM-DECL-2026-EU-0910"
    req.refining_mass_balance.cbam_scope1_emissions_kg_co2e = 1.25
    req.refining_mass_balance.cbam_scope2_emissions_kg_co2e = 0.65
    req.labor_human_rights.csddd_audit_hash = "0x" + "e" * 64

    res = compliance_engine.evaluate_lot(req)
    verdict = res.verdict

    assert verdict.is_fully_compliant
    assert verdict.cbam_definitive_period_verified
    assert verdict.csddd_civil_liability_shielded
    assert any("DEFENSE_EU_CBAM_DEFINITIVE_DECLARATION" in flag for flag in verdict.gotcha_defenses_applied)
    assert any("DEFENSE_EU_CBAM_EMISSIONS_AUDITED" in flag for flag in verdict.gotcha_defenses_applied)
