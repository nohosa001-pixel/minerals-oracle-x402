"""
Tests for 2026-10-14 Market Briefing Regulatory, Provenance & Transatlantic Supply Chain Upgrades.
Verifies:
1. EU-Vietnam Strategic Mineral Partnership: Dong Pao Rare Earths Mine geofencing and non-China provenance.
2. EU-Vietnam Strategic Mineral Partnership: Nui Phao Polymetallic Tungsten Mine geofencing and defense compliance.
3. Canadian North American Niobium Bardy SE project geofencing for Rare Earths and Ferroniobium.
4. Chilean Centinela Copper Mine provenance and mass balance amidst global $6.7645 rally and US 100만t copper mountain.
5. EU CBAM 2026 Statutory +10% Mark-up Penalty Surcharge and EU IAA 70% EV domestic sourcing compliance.
6. 2026-10-14 Market Briefing markdown report presence and core telemetry validation.
"""

from pathlib import Path
import pytest
from app.schemas import (
    CopperOriginVerifyRequest,
    RareEarthsOriginVerifyRequest,
    TungstenOriginVerifyRequest,
    NiobiumScandiumOriginVerifyRequest,
    CBAMMarkupPenaltyRequest,
    EUIndustrialActVerifyRequest,
    MineralType,
    SourceCountry,
)
from app.copper_pipeline import CopperProvenancePipeline
from app.rare_earths_pipeline import rare_earths_pipeline
from app.tungsten_pipeline import tungsten_pipeline
from app.niobium_scandium_pipeline import NiobiumScandiumPipeline
from app.regulatory_advanced_engine import RegulatoryAdvancedEngine


def test_vietnam_dong_pao_rare_earths():
    """Verify Dong Pao Rare Earths Mine in Lai Chau, Vietnam (EU-Vietnam Strategic Partnership)."""
    req = RareEarthsOriginVerifyRequest(
        batch_id="RE-VNM-DONGPAO-2026-001",
        tenement_id="DONG_PAO",
        latitude=22.283,
        longitude=103.500,
        ndpr_oxide_purity_pct=99.85,
        thorium_uranium_radiation_ppm=35.0,
        declared_china_origin_ratio=0.0,
        source_country=SourceCountry.VNM,
    )
    res = rare_earths_pipeline.verify_rare_earths_batch(req)

    assert res.status == "success"
    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.geofence_verified is True
    assert res.audit_verdict.distance_to_concession_km == 0.0
    assert res.audit_verdict.purity_certified is True
    assert res.audit_verdict.mofcom_china_content_passed is True
    assert res.audit_verdict.dfars_2027_compliant is True
    assert res.proof_hash.startswith("0x")


def test_vietnam_nui_phao_tungsten():
    """Verify Nui Phao Polymetallic Tungsten Mine in Thai Nguyen, Vietnam (EU-Vietnam Strategic Partnership)."""
    req = TungstenOriginVerifyRequest(
        batch_id="W-VNM-NUIPHAO-2026-001",
        tenement_id="NUI_PHAO",
        latitude=21.608,
        longitude=105.748,
        apt_wo3_grade_pct=89.20,
        dodd_frank_conflict_free=True,
        ndaa_defense_procurement_eligible=True,
        source_country=SourceCountry.VNM,
    )
    res = tungsten_pipeline.verify_tungsten_batch(req)

    assert res.status == "success"
    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.geofence_verified is True
    assert res.audit_verdict.distance_to_concession_km == 0.0
    assert res.audit_verdict.apt_grade_certified is True
    assert res.audit_verdict.ndaa_defense_eligible is True
    assert res.audit_verdict.dodd_frank_passed is True
    assert res.proof_hash.startswith("0x")


def test_north_american_niobium_bardy_se_ree():
    """Verify North American Niobium Bardy SE airborne magnetic target in Quebec, Canada (REE)."""
    req = RareEarthsOriginVerifyRequest(
        batch_id="RE-CAN-BARDY-2026-001",
        tenement_id="BARDY_SE",
        latitude=49.350,
        longitude=-70.150,
        ndpr_oxide_purity_pct=99.60,
        thorium_uranium_radiation_ppm=40.0,
        declared_china_origin_ratio=0.0,
        source_country=SourceCountry.CAN,
    )
    res = rare_earths_pipeline.verify_rare_earths_batch(req)

    assert res.status == "success"
    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.geofence_verified is True
    assert res.audit_verdict.distance_to_concession_km == 0.0
    assert res.audit_verdict.purity_certified is True
    assert res.audit_verdict.dfars_2027_compliant is True


def test_north_american_niobium_bardy_se_niobium():
    """Verify North American Niobium Bardy SE prospect for Ferroniobium."""
    pipeline = NiobiumScandiumPipeline()
    req = NiobiumScandiumOriginVerifyRequest(
        batch_id="NB-CAN-BARDY-2026-001",
        tenement_id="BARDY_SE",
        latitude=49.350,
        longitude=-70.150,
        commodity_type=MineralType.FERRONIOBIUM,
        fe_nb_grade_pct=65.2,
        doe_exim_loan_eligible=True,
        ndaa_defense_procurement_eligible=True,
        source_country=SourceCountry.CAN,
    )
    res = pipeline.verify_origin(req)

    assert res.status == "success"
    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.geofence_verified is True
    assert res.audit_verdict.distance_to_concession_km == 0.0
    assert res.audit_verdict.grade_assay_certified is True
    assert res.audit_verdict.defense_procurement_eligible is True


def test_copper_centinela_oct14_rally_and_us_stockpile_backdrop():
    """Verify Centinela copper origin and metallurgical balance during COMEX $6.7645 rally."""
    pipeline = CopperProvenancePipeline()
    # 400t concentrate at 28.0% Cu = 112.0t Cu contained * 0.975 recovery = 109.2t cathode
    # Sulfuric acid: 109.2t * 3.2 = 349.44t H2SO4
    req = CopperOriginVerifyRequest(
        lot_id="CU-CHL-CENTINELA-2026-1014",
        mine_concession_name="CENTINELA",
        extraction_coordinates=(-22.923, -69.255),
        source_country=SourceCountry.CHL,
        feedstock_concentrate_tons=400.0,
        concentrate_grade_cu_pct=28.0,
        sulfuric_acid_input_tons=349.44,
        refined_copper_cathode_tons=109.2,
        copper_cathode_purity_pct=99.9935,
        cochilco_export_clearance_id="CHL-COCHILCO-2026-OCT14-01",
        hvdc_cable_spec_compliant=True,
        feoc_shareholding_pct=0.0,
    )
    res = pipeline.verify_origin(req)

    assert res.status == "success"
    assert res.verdict.geofence_verified is True
    assert res.extraction_origin["concession_id"] == "AMSA-CEN-01"
    assert res.extraction_origin["distance_km"] == 0.0
    assert res.verdict.stoichiometric_mass_balance_passed is True
    assert res.verdict.sulfuric_acid_ratio_passed is True
    assert res.verdict.cochilco_cleared is True
    assert res.verdict.hvdc_grid_certified is True
    assert res.verdict.feoc_cleared is True
    assert res.onchain_proof.startswith("0x")


def test_cbam_2026_markup_penalty_and_iaa_70_ev():
    """Verify EU CBAM 2026 +10% mark-up penalty on unverified defaults and IAA 70% EV content."""
    reg_engine = RegulatoryAdvancedEngine()

    # 1. CBAM 2026 Unverified Default: 100t * 2.0 tCO2/t = 200 tCO2. Mark-up +10% = 220 tCO2 @ €85/t = €18,700
    cbam_req = CBAMMarkupPenaltyRequest(
        cargo_id="CBAM-CARGO-2026-1014",
        importer_eori="NL123456789",
        commodity_code="74031100",  # Copper Cathode
        tonnage=100.0,
        default_embedded_emissions_tco2_per_ton=2.0,
        verified_scope1_2_emissions_tco2_per_ton=None,  # Unverified default
        import_year=2026,
        eu_allowance_price_eur=85.0,
    )
    cbam_res = reg_engine.calculate_cbam_markup_penalty(cbam_req)
    assert cbam_res.status == "success"
    assert cbam_res.markup_penalty_rate == 0.10
    assert cbam_res.is_verified_exempt is False
    assert cbam_res.effective_emissions_billed_tco2 == 220.0
    assert cbam_res.total_cbam_liability_eur == 18700.0
    assert cbam_res.markup_penalty_surcharge_eur == 1700.0

    # 2. EU Industrial Accelerator Act (IAA) 70% local content requirement
    iaa_req = EUIndustrialActVerifyRequest(
        product_id="EV-BATTERY-PACK-2026-001",
        eu_domestic_value_share_pct=72.5,
        eu_steel_domestic_share_pct=45.0,
        battery_recycling_passport_id="EU-BATT-2026-7788",
    )
    iaa_res = reg_engine.verify_eu_industrial_act(iaa_req)
    assert iaa_res.status == "success"
    assert iaa_res.overall_subsidy_eligible is True
    assert iaa_res.iaa_70pct_threshold_passed is True
    assert iaa_res.steel_40pct_threshold_passed is True


def test_oct14_briefing_document_integrity():
    """Verify the 2026-10-14 market briefing document exists and contains all required data."""
    doc_path = Path("docs/reports/2026-10-14_market_briefing.md")
    assert doc_path.exists(), "2026-10-14_market_briefing.md must exist in docs/reports"
    content = doc_path.read_text(encoding="utf-8")

    assert "2026년 10월 14일" in content
    assert "$6.7645" in content or "$6.76" in content
    assert "100만 톤" in content or "100만t" in content
    assert "$58.56" in content or "$58.50" in content
    assert "$4,142" in content or "$4,150" in content
    assert "BofA" in content or "5,000달러" in content
    assert "베트남" in content
    assert "안티모니" in content
    assert "빅토리아" in content
    assert "Bardy" in content or "노스 아메리칸 니오븀" in content
    assert "NioCorp" in content or "니오콥" in content
    assert "CBAM" in content
    assert "0.1%" in content
    assert "D-27" in content
