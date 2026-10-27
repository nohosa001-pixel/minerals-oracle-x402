"""
Tests for 2026-10-23 Market Briefing Regulatory, Provenance & Transatlantic/Central-Asia Supply Chain Upgrades.
Verifies:
1. LME Week Day 5 Copper Cathode Provenance amidst 2027 physical premium negotiations, $14,441/t ($6.37/lb) floor, & negative TC/RC.
2. Silver $55/oz consolidation TOPCon & HJT solar cell conductive paste provenance & 6-year physical deficit screening.
3. Central Asian Strategic Minerals Corridor (Anzob, Tajikistan / CJSC Anzob / Comsup Commodities) under MOFCOM D-18 & DFARS 2027.
4. US DOE Critical Materials Pilot Facility (Solvent Extraction & Membrane Separation) non-China refining tech verification.
5. MineralType (ALUMINIUM_INGOT) and SourceCountry (TJK, UZB, GIN) schema expansions with aliases.
6. 2026-10-23 market briefing markdown report integrity and core telemetry validation.
"""

from pathlib import Path
import pytest
from app.schemas import (
    CopperOriginVerifyRequest,
    RareEarthsOriginVerifyRequest,
    SilverOriginVerifyRequest,
    MineralType,
    SourceCountry,
)
from app.copper_pipeline import CopperProvenancePipeline
from app.rare_earths_pipeline import rare_earths_pipeline
from app.silver_pipeline import silver_pipeline


def test_lme_week_day5_copper_cathode_pipeline():
    """Verify Chilean Centinela copper cathode lot during LME Week Day 5 closing & $14,441/t settlement."""
    pipeline = CopperProvenancePipeline()
    req = CopperOriginVerifyRequest(
        lot_id="CU-LME-WEEK-2026-OCT23-DAY5-14441USD",
        mine_concession_name="CENTINELA",
        extraction_coordinates=(-22.923, -69.255),
        source_country=SourceCountry.CHL,
        feedstock_concentrate_tons=650.0,
        concentrate_grade_cu_pct=29.0,
        sulfuric_acid_input_tons=602.16,  # 183.7125 * 3.2 = 587.88t (+ tolerance)
        refined_copper_cathode_tons=183.82,  # 650 * 0.29 * 0.975 = 183.7875t
        copper_cathode_purity_pct=99.996,
        cochilco_export_clearance_id="CHL-COCHILCO-2026-OCT23-LMEWEEK-D5",
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
    """Verify Silver lot provenance for N-Type TOPCon & HJT Solar PV paste during $55/oz consolidation."""
    # 2,600kg Doré at 79.0% Ag = 2,054kg contained * 0.99 recovery = 2,033.46kg theoretical refined silver
    req = SilverOriginVerifyRequest(
        lot_id="AG-MEX-TERRONERA-2026-OCT23-55USD",
        mine_concession_name="TERRONERA",
        extraction_coordinates=(20.590, -104.980),
        source_country=SourceCountry.MEX,
        feedstock_dore_or_ore_kg=2600.0,
        feedstock_silver_grade_pct=79.0,
        refined_solar_powder_kg=2033.46,
        refined_purity_pct=99.996,
        lbma_good_delivery_ref="LBMA-REF-MEX-2026-OCT23-TERR",
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


def test_tajikistan_anzob_antimony_central_asia_corridor():
    """Verify Anzob (Tajikistan) Strategic Minerals Corridor under US-Central Asia partnership, MOFCOM D-18, & DFARS 2027."""
    req = RareEarthsOriginVerifyRequest(
        batch_id="SB-TJK-ANZOB-CENTRAL-ASIA-2026",
        tenement_id="ANZOB_TAJIKISTAN",
        latitude=39.060,
        longitude=68.860,
        ndpr_oxide_purity_pct=99.88,
        thorium_uranium_radiation_ppm=14.5,
        declared_china_origin_ratio=0.0,
        source_country=SourceCountry.TJK,
    )
    res = rare_earths_pipeline.verify_rare_earths_batch(req)

    assert res.status == "success"
    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.geofence_verified is True
    assert res.audit_verdict.mofcom_china_content_passed is True
    assert res.audit_verdict.dfars_2027_compliant is True
    assert res.audit_verdict.status == "COMPLIANT_CERTIFIED"
    assert res.proof_hash.startswith("0x")


def test_us_doe_pilot_plant_refining_provenance():
    """Verify US DOE Critical Materials Pilot Facility for non-China solvent extraction and membrane separation."""
    req = RareEarthsOriginVerifyRequest(
        batch_id="RE-USA-DOE-PILOT-SOLVENT-EXT-2026",
        tenement_id="DOE_PILOT_PLANT",
        latitude=42.027,
        longitude=-93.647,
        ndpr_oxide_purity_pct=99.95,
        thorium_uranium_radiation_ppm=10.0,
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


def test_schema_expansions_aluminium_and_central_asia_and_guinea():
    """Verify ALUMINIUM_INGOT in MineralType and TJK, UZB, GIN in SourceCountry with all standard aliases."""
    assert MineralType("ALUMINIUM_INGOT") == MineralType.ALUMINIUM_INGOT
    assert MineralType("aluminium") == MineralType.ALUMINIUM_INGOT
    assert MineralType("aluminum") == MineralType.ALUMINIUM_INGOT
    assert MineralType("al") == MineralType.ALUMINIUM_INGOT

    assert SourceCountry("TJK") == SourceCountry.TJK
    assert SourceCountry("TAJIKISTAN") == SourceCountry.TJK
    assert SourceCountry("tj") == SourceCountry.TJK

    assert SourceCountry("UZB") == SourceCountry.UZB
    assert SourceCountry("UZBEKISTAN") == SourceCountry.UZB
    assert SourceCountry("uz") == SourceCountry.UZB

    assert SourceCountry("GIN") == SourceCountry.GIN
    assert SourceCountry("GUINEA") == SourceCountry.GIN
    assert SourceCountry("gn") == SourceCountry.GIN


def test_oct23_briefing_document_integrity():
    """Verify the 2026-10-23 market briefing document exists and contains core telemetry."""
    doc_path = Path("docs/reports/2026-10-23_market_briefing.md")
    assert doc_path.exists(), "2026-10-23_market_briefing.md must exist in docs/reports"
    content = doc_path.read_text(encoding="utf-8")

    assert "2026년 10월 23일" in content
    assert "245,275" in content
    assert "$14,441" in content or "$6.37" in content
    assert "$54.99" in content or "$55.94" in content or "$55" in content
    assert "$4,023" in content or "$4,051" in content or "$4,020" in content
    assert "Critical Metals" in content or "크리티컬 메탈스" in content
    assert "European Lithium" in content or "유럽 리튬" in content
    assert "볼프스베르크" in content or "Wolfsberg" in content
    assert "에너지부" in content or "DOE" in content
    assert "타지키스탄" in content or "Tajikistan" in content
    assert "CBAM" in content
    assert "10%" in content
    assert "CSDDD" in content
    assert "IAA" in content
    assert "0.1%" in content
    assert "DFARS" in content
    assert "Newmont" in content
