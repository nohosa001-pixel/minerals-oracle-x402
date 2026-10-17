"""
Tests for 2026-10-17 Market Briefing Regulatory, Provenance & Transatlantic Supply Chain Upgrades.
Verifies:
1. Australian Lodestar Minerals Black Diamond Silver project geofencing & non-conflict TOPCon solar PV certification.
2. U.S. Army weapon systems procurement defense under China MOFCOM D-24 extraterritorial export control and DFARS 2027.
3. Crux Investor copper isolation analysis (US 1.5M ton copper mountain vs LME cash backwardation & cash $14,539).
4. World Bank critical minerals 5x financing expansion & Canada Thompson nickel mine transaction closing.
5. 2026-10-16 and 2026-10-17 market briefing markdown report integrity and core telemetry validation.
"""

from pathlib import Path
import pytest
from app.schemas import (
    SilverOriginVerifyRequest,
    RareEarthsOriginVerifyRequest,
    CopperOriginVerifyRequest,
    MineralType,
    SourceCountry,
)
from app.silver_pipeline import SilverProvenancePipeline
from app.rare_earths_pipeline import rare_earths_pipeline
from app.copper_pipeline import CopperProvenancePipeline


def test_australia_black_diamond_silver():
    """Verify Lodestar Minerals Black Diamond project in Gascoyne/Murchison, Western Australia."""
    pipeline = SilverProvenancePipeline()
    req = SilverOriginVerifyRequest(
        lot_id="AG-AUS-BLACKDIAMOND-2026-001",
        mine_concession_name="BLACK_DIAMOND",
        extraction_coordinates=(-25.150, 115.800),
        source_country=SourceCountry.AUS,
        feedstock_dore_or_ore_kg=8000.0,
        feedstock_silver_grade_pct=72.5,
        refined_solar_powder_kg=5742.0,  # 8000 * 0.725 * 0.99 = 5742 kg
        refined_purity_pct=99.9950,
        lbma_good_delivery_ref="LBMA-REF-AUS-01",
        conflict_free_asm_verified=True,
        topcon_pv_grade_compliant=True,
        feoc_shareholding_pct=0.0,
    )
    res = pipeline.verify_origin(req)

    assert res.status == "success"
    assert res.verdict.geofence_verified is True
    assert res.extraction_origin["concession_id"] == "AUS-WA-LSR-01"
    assert res.extraction_origin["distance_km"] == 0.0
    assert res.verdict.refining_mass_balance_passed is True
    assert res.verdict.topcon_solar_pv_certified is True
    assert res.verdict.conflict_free_asm_passed is True
    assert res.verdict.feoc_cleared is True
    assert res.onchain_proof.startswith("0x")


def test_us_army_defense_procurement_dfars_2027_ree():
    """Verify Defense-grade Rare Earths origin under US Army weapon systems procurement & DFARS 2027 non-China rule."""
    req = RareEarthsOriginVerifyRequest(
        batch_id="RE-ARMY-GUIDED-MISSILE-2026-01",
        tenement_id="SARFARTOQ",
        latitude=66.500,
        longitude=-51.250,
        ndpr_oxide_purity_pct=99.80,
        thorium_uranium_radiation_ppm=38.0,
        declared_china_origin_ratio=0.0,
        source_country=SourceCountry.GRL,
    )
    res = rare_earths_pipeline.verify_rare_earths_batch(req)

    assert res.status == "success"
    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.geofence_verified is True
    assert res.audit_verdict.mofcom_china_content_passed is True
    assert res.audit_verdict.dfars_2027_compliant is True
    assert res.proof_hash.startswith("0x")


def test_copper_us_150m_ton_isolation_and_lme_tightness():
    """Verify Copper cathode origin and stoichiometry during US 1.5M ton isolation and LME $14,539 cash pricing."""
    pipeline = CopperProvenancePipeline()
    # 500t concentrate at 28.0% Cu = 140.0t Cu contained * 0.975 recovery = 136.5t cathode
    # Sulfuric acid: 136.5t * 3.2 = 436.8t H2SO4
    req = CopperOriginVerifyRequest(
        lot_id="CU-CHL-VALLECENTRAL-2026-1017",
        mine_concession_name="VALLE_CENTRAL",
        extraction_coordinates=(-34.170, -70.650),
        source_country=SourceCountry.CHL,
        feedstock_concentrate_tons=500.0,
        concentrate_grade_cu_pct=28.0,
        sulfuric_acid_input_tons=436.8,
        refined_copper_cathode_tons=136.5,
        copper_cathode_purity_pct=99.9935,
        cochilco_export_clearance_id="CHL-COCHILCO-2026-OCT17-01",
        hvdc_cable_spec_compliant=True,
        feoc_shareholding_pct=0.0,
    )
    res = pipeline.verify_origin(req)

    assert res.status == "success"
    assert res.verdict.geofence_verified is True
    assert res.extraction_origin["concession_id"] == "CHL-OHI-MVC-01"
    assert res.extraction_origin["distance_km"] == 0.0
    assert res.verdict.stoichiometric_mass_balance_passed is True
    assert res.verdict.sulfuric_acid_ratio_passed is True
    assert res.verdict.cochilco_cleared is True
    assert res.verdict.hvdc_grid_certified is True
    assert res.verdict.feoc_cleared is True
    assert res.onchain_proof.startswith("0x")


def test_oct16_briefing_document_integrity():
    """Verify the 2026-10-16 market briefing document exists and contains core telemetry."""
    doc_path = Path("docs/reports/2026-10-16_market_briefing.md")
    assert doc_path.exists(), "2026-10-16_market_briefing.md must exist in docs/reports"
    content = doc_path.read_text(encoding="utf-8")

    assert "2026년 10월 16일" in content
    assert "$6.59" in content or "$6.72" in content
    assert "22만 6,600톤" in content or "22만 6,600t" in content
    assert "$57.91" in content
    assert "$4,184" in content or "$4,169" in content
    assert "세계은행" in content or "World Bank" in content
    assert "톰슨" in content or "Thompson" in content
    assert "미 육군" in content or "U.S. Army" in content
    assert "D-25" in content


def test_oct17_briefing_document_integrity():
    """Verify the 2026-10-17 weekly market briefing document exists and contains core telemetry."""
    doc_path = Path("docs/reports/2026-10-17_weekly_market_briefing.md")
    assert doc_path.exists(), "2026-10-17_weekly_market_briefing.md must exist in docs/reports"
    content = doc_path.read_text(encoding="utf-8")

    assert "2026년 10월 17일" in content
    assert "$6.5620" in content or "$6.56" in content
    assert "150만 톤" in content or "150만t" in content
    assert "크럭스 인베스터" in content or "Crux Investor" in content
    assert "$57.00" in content or "$58.00" in content
    assert "$4,166" in content or "$4,171" in content
    assert "세계은행" in content or "World Bank" in content
    assert "톰슨" in content or "Thompson" in content
    assert "미 육군" in content or "U.S. Army" in content
    assert "D-24" in content
    assert "LME 위크" in content or "LME Week" in content
