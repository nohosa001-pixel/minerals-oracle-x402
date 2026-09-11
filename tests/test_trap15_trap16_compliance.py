"""
Unit & Integration Tests for Gotcha Trap 15 (China Tech Licensing Jurisdiction),
Gotcha Trap 16 (Copper H2SO4 Deficit & Silver TOPCon Deficit), and EU CBAM 2028 Downstream Auditing.
"""

import pytest
from app.schemas import (
    MineralLotProvenanceRequest,
    MineralType,
    SourceCountry,
    MinePermitsRecord,
    EcologicalSpatialRecord,
    LaborHumanRightsRecord,
    RefiningMassBalanceRecord,
    MaritimeLogisticsRecord,
    MaritimeCIIRating,
    GeopoliticalSanctionsRecord,
)
from app.compliance_engine import compliance_engine


def build_base_request(mineral_type: MineralType, source_country: SourceCountry) -> MineralLotProvenanceRequest:
    return MineralLotProvenanceRequest(
        lot_id="LOT-TRAP15-16-TEST",
        mineral_type=mineral_type,
        source_country=source_country,
        net_weight_metric_tons=100.0,
        declared_purity_pct=99.9935 if mineral_type == MineralType.COPPER_CATHODE else 99.99,
        mine_permits=MinePermitsRecord(
            mining_license_id="LIC-CHL-001",
            mine_operator_name="Minera Test S.A.",
            chile_cochilco_export_id="COCHILCO-EXP-001",
            chile_dga_water_permit_id="DGA-PERMIT-001",
        ),
        ecological_spatial=EcologicalSpatialRecord(
            latitude=-22.283,
            longitude=-68.900,
            eudr_deforestation_free=True,
            tailing_dam_dce_certified=True,
        ),
        labor_human_rights=LaborHumanRightsRecord(
            child_labor_free_certified=True,
            rmi_rmap_audit_id="RMAP-TEST-001",
            csddd_audit_hash="0x" + "a" * 64,
        ),
        refining_mass_balance=RefiningMassBalanceRecord(
            refinery_id="REF-TEST-001",
            feedstock_input_metric_tons=350.0,
            refined_output_metric_tons=95.55,
            recovery_yield_pct=97.5,
            mass_balance_loss_discrepancy_pct=1.2,
            captive_coal_power_used=False,
            cbam_declaration_id="CBAM-DECL-2026-001",
            cbam_scope1_emissions_kg_co2e=0.85,
            cbam_scope2_emissions_kg_co2e=0.45,
            cbam_scope3_emissions_kg_co2e=12.0,
        ),
        maritime_logistics=MaritimeLogisticsRecord(
            vessel_imo_number=9876543,
            vessel_name="MV PACIFIC TRADER",
            cii_rating=MaritimeCIIRating.A,
            ebl_document_hash="0x" + "b" * 64,
            iso_17025_lab_coa_hash="0x" + "c" * 64,
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


def test_trap15_chinese_tech_licensing_unauthorized_fails():
    """Trap 15: Rejects smelters with > 50% Chinese proprietary tech dependency lacking MOFCOM clearance."""
    req = build_base_request(MineralType.NICKEL_MHP, SourceCountry.IDN)
    req.mine_permits.simbara_ntpn = "NTPN-88888888"
    req.mine_permits.dhe_forex_deposit_ref = "DHE-REC-001"
    req.refining_mass_balance.chinese_tech_dependency_pct = 75.0  # > 50% dependency
    req.refining_mass_balance.mofcom_extraterritorial_clearance_id = None
    req.refining_mass_balance.substitute_western_tech_certified = False

    passport = compliance_engine.evaluate_lot(req)
    assert passport.verdict.china_tech_licensing_cleared is False
    assert any("CHN_TECH_LICENSING_TAINT_VIOLATION" in d for d in passport.verdict.gotcha_defenses_applied)
    assert any(c.precedent_case_id == "CHN_MOFCOM_2026_EXTRATERRITORIAL_TECH_ORDER" and c.compliance_status == "VIOLATION" for c in passport.verdict.jurisprudence_citations)


def test_trap15_chinese_tech_licensing_with_clearance_passes():
    """Trap 15: Passes when Chinese tech dependency has official MOFCOM clearance."""
    req = build_base_request(MineralType.NICKEL_MHP, SourceCountry.IDN)
    req.mine_permits.simbara_ntpn = "NTPN-88888888"
    req.mine_permits.dhe_forex_deposit_ref = "DHE-REC-001"
    req.refining_mass_balance.chinese_tech_dependency_pct = 75.0
    req.refining_mass_balance.mofcom_extraterritorial_clearance_id = "MOFCOM-EXT-2026-OK99"
    req.refining_mass_balance.substitute_western_tech_certified = False

    passport = compliance_engine.evaluate_lot(req)
    assert passport.verdict.china_tech_licensing_cleared is True
    assert any("DEFENSE_CHN_TECH_LICENSING_CLEARED" in d for d in passport.verdict.gotcha_defenses_applied)


def test_trap16_copper_h2so4_supply_deficit_fails():
    """Trap 16: Rejects copper cathode lot when sulfuric acid supply variance exceeds 5.0%."""
    req = build_base_request(MineralType.COPPER_CATHODE, SourceCountry.CHL)
    req.refining_mass_balance.sulfuric_acid_discrepancy_pct = 14.5  # Exceeds 5.0%

    passport = compliance_engine.evaluate_lot(req)
    assert passport.verdict.copper_hvdc_certified is False
    assert any("COPPER_H2SO4_SUPPLY_DEFICIT" in d for d in passport.verdict.gotcha_defenses_applied)


def test_trap16_silver_topcon_purity_substandard_fails():
    """Trap 16: Rejects solar PV silver paste when assay purity is below 99.99%."""
    req = build_base_request(MineralType.SILVER_POWDER_SOLAR_PV, SourceCountry.MEX)
    req.declared_purity_pct = 99.70  # Substandard for TOPCon

    passport = compliance_engine.evaluate_lot(req)
    assert passport.verdict.silver_solar_pv_cleared is False
    assert any("SILVER_TOPCON_PURITY_REJECTED" in d for d in passport.verdict.gotcha_defenses_applied)


def test_downstream_cbam_2028_and_csddd_cleared():
    """Verifies EU CBAM 2028 downstream finished goods Scope 3 and CSDDD due diligence flags."""
    req = build_base_request(MineralType.COPPER_CATHODE, SourceCountry.CHL)
    passport = compliance_engine.evaluate_lot(req)
    assert passport.verdict.downstream_cbam_scope3_cleared is True
    assert passport.verdict.csddd_due_diligence_verified is True
    assert any("DEFENSE_EU_CBAM_2028_DOWNSTREAM_ALIGNED" in d for d in passport.verdict.gotcha_defenses_applied)
