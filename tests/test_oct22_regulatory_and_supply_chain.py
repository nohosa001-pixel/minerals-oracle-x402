"""
Tests for 2026-10-22 Market Briefing Regulatory, Provenance & Transatlantic Supply Chain Upgrades.
Verifies:
1. LME Week Day 4 Copper Cathode Provenance amidst physical premium finalization & $14,540/t ($6.55/lb) floor support.
2. Silver $57.50/oz consolidation TOPCon solar cell conductive paste provenance & 6-year physical deficit screening.
3. Wolfsberg Lithium Project (Austria / Critical Metals Corp acquisition of European Lithium) transatlantic battery supply & EU CRMA origin.
4. Nova Minerals Estelle Antimony/Gold Project (Alaska / US DoD / Port MacKenzie rail link) under China MOFCOM D-19 (0.1% rule) & DFARS 2027.
5. MineralType (ANTIMONY_INGOT) and SourceCountry (AUT - Austria) schema expansions.
6. 2026-10-22 market briefing markdown report integrity and core telemetry validation.
"""

from pathlib import Path
import pytest
from app.schemas import (
    CopperOriginVerifyRequest,
    RareEarthsOriginVerifyRequest,
    SilverOriginVerifyRequest,
    LithiumOriginVerifyRequest,
    MineralType,
    SourceCountry,
)
from app.copper_pipeline import CopperProvenancePipeline
from app.rare_earths_pipeline import rare_earths_pipeline
from app.silver_pipeline import silver_pipeline
from app.lithium_pipeline import lithium_pipeline


def test_lme_week_day4_copper_cathode_pipeline():
    """Verify Chilean Centinela copper cathode lot during LME Week post-dinner 2027 physical premium finalization."""
    pipeline = CopperProvenancePipeline()
    req = CopperOriginVerifyRequest(
        lot_id="CU-LME-WEEK-2026-OCT22-CATHODE",
        mine_concession_name="CENTINELA",
        extraction_coordinates=(-22.923, -69.255),
        source_country=SourceCountry.CHL,
        feedstock_concentrate_tons=620.0,
        concentrate_grade_cu_pct=28.8,
        sulfuric_acid_input_tons=557.19,  # 174.1248 * 3.2 = 557.199t
        refined_copper_cathode_tons=174.1248,  # 620 * 0.288 * 0.975 = 174.1248t
        copper_cathode_purity_pct=99.9955,
        cochilco_export_clearance_id="CHL-COCHILCO-2026-OCT22-LMEWEEK-D4",
        hvdc_cable_spec_compliant=True,
        feoc_shareholding_pct=0.0,
    )
    res = pipeline.verify_origin(req)

    assert res.status == "success"
    assert res.verdict.geofence_verified is True
    assert res.verdict.stoichiometric_mass_balance_passed is True
    assert res.verdict.sulfuric_acid_ratio_passed is True
    assert res.verdict.cochilco_cleared is True
    assert res.verdict.hvdc_grid_certified is True
    assert res.verdict.feoc_cleared is True
    assert res.onchain_proof.startswith("0x")


def test_silver_consolidation_topcon_paste_provenance():
    """Verify Silver lot provenance for N-Type TOPCon Solar PV paste during $57.50/oz compression."""
    # 2,500kg Doré at 78.0% Ag = 1,950kg contained * 0.99 recovery = 1,930.5kg theoretical refined silver
    req = SilverOriginVerifyRequest(
        lot_id="AG-MEX-TERRONERA-2026-OCT22-57USD",
        mine_concession_name="TERRONERA",
        extraction_coordinates=(20.590, -104.980),
        source_country=SourceCountry.MEX,
        feedstock_dore_or_ore_kg=2500.0,
        feedstock_silver_grade_pct=78.0,
        refined_solar_powder_kg=1930.5,
        refined_purity_pct=99.995,
        lbma_good_delivery_ref="LBMA-REF-MEX-2026-OCT22-TERR",
        conflict_free_asm_verified=True,
        topcon_pv_grade_compliant=True,
        feoc_shareholding_pct=0.0,
    )
    res = silver_pipeline.verify_origin(req)

    assert res.status == "success"
    assert res.verdict.geofence_verified is True
    assert res.verdict.refining_mass_balance_passed is True
    assert res.verdict.topcon_solar_pv_certified is True
    assert res.verdict.lbma_cleared is True
    assert res.verdict.feoc_cleared is True
    assert res.onchain_proof.startswith("0x")


def test_wolfsberg_lithium_austria_crml_provenance():
    """Verify Wolfsberg Lithium Project (Austria) acquisition by Critical Metals Corp (NASDAQ: CRML) & EU CRMA origin."""
    req = LithiumOriginVerifyRequest(
        trace_id="LIT-AUT-WOLFSBERG-CRML-2026",
        product="Lithium Hydroxide Monohydrate",
        mine_name="Wolfsberg Lithium Project",
        mine_country="AUT",
        coordinates=[46.840, 14.840],
        minedex_tenement_id="AUT-CAR-WOLFSBERG-01",
        spodumene_tonnage_extracted=7500.0,
        spodumene_grade_pct=6.0,
        refinery_facility="Wolfsberg Integrated Hydrometallurgical Refinery",
        refinery_country="AUT",
        refined_output_tonnage=1000.0,
        refinery_feoc_equity_pct=0.0,
        satellite_vegetation_index=0.10,
        sar_backscatter_db=-10.5,
        agent_address="0x71C84107b3a42E2F2Ab4Ba770265EC0c4ce5Cea6",
    )
    res = lithium_pipeline.evaluate_lithium_lot(req)

    assert res.status == "success"
    assert res.extraction_origin.geofence_passed is True
    assert res.extraction_origin.minedex_tenement_id == "AUT-CAR-WOLFSBERG-01"
    assert res.extraction_origin.country == "AUT"
    assert res.mass_balance_audit.is_stoichiometrically_sound is True
    assert res.audit_verdict.ira_compliant is True
    assert res.audit_verdict.crma_origin_eligible is True
    assert res.audit_verdict.feoc_risk_detected is False
    assert res.audit_verdict.confidence_score >= 90.0
    assert res.onchain_proof.startswith("0x")


def test_nova_minerals_estelle_alaska_antimony_defense_d19():
    """Verify Estelle Critical Minerals Antimony & Gold Project (Alaska) under Port MacKenzie rail link, MOFCOM D-19 & DFARS 2027."""
    req = RareEarthsOriginVerifyRequest(
        batch_id="SB-AK-ESTELLE-US-DOD-RAIL-D19",
        tenement_id="ESTELLE_ALASKA",
        latitude=61.930,
        longitude=-152.020,
        ndpr_oxide_purity_pct=99.85,
        thorium_uranium_radiation_ppm=18.0,
        declared_china_origin_ratio=0.0,
        source_country=SourceCountry.USA,
    )
    res = rare_earths_pipeline.verify_rare_earths_batch(req)

    assert res.status == "success"
    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.geofence_verified is True
    assert res.audit_verdict.mofcom_china_content_passed is True
    assert res.audit_verdict.dfars_2027_compliant is True
    assert res.audit_verdict.status == "COMPLIANT_CERTIFIED"
    assert res.proof_hash.startswith("0x")


def test_schema_expansions_antimony_and_austria():
    """Verify ANTIMONY_INGOT in MineralType and AUT in SourceCountry with all standard aliases."""
    assert MineralType("ANTIMONY_INGOT") == MineralType.ANTIMONY_INGOT
    assert MineralType("antimony") == MineralType.ANTIMONY_INGOT
    assert MineralType("sb") == MineralType.ANTIMONY_INGOT

    assert SourceCountry("AUT") == SourceCountry.AUT
    assert SourceCountry("AUSTRIA") == SourceCountry.AUT
    assert SourceCountry("at") == SourceCountry.AUT


def test_oct22_briefing_document_integrity():
    """Verify the 2026-10-22 market briefing document exists and contains core telemetry."""
    doc_path = Path("docs/reports/2026-10-22_market_briefing.md")
    assert doc_path.exists(), "2026-10-22_market_briefing.md must exist in docs/reports"
    content = doc_path.read_text(encoding="utf-8")

    assert "2026년 10월 22일" in content
    assert "LME 위크" in content
    assert "$14,540" in content
    assert "$6.54" in content or "$6.57" in content or "$6.55" in content
    assert "$57.30" in content or "$57.57" in content or "$57.50" in content
    assert "$4,121" in content or "$4,133" in content or "$4,120" in content
    assert "크리티컬 메탈스" in content or "Critical Metals" in content
    assert "유럽 리튬" in content or "European Lithium" in content
    assert "볼프스베르크" in content or "Wolfsberg" in content
    assert "노바 미네랄스" in content or "Nova Minerals" in content
    assert "알래스카" in content or "Alaska" in content
    assert "2억 5,000만" in content or "250" in content
    assert "안티모니" in content or "Antimony" in content
    assert "D-19" in content or "19일" in content
    assert "CBAM" in content
    assert "+10%" in content
    assert "산업가속화법" in content or "IAA" in content
    assert "70%" in content
    assert "CSDDD" in content
