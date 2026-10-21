"""
Tests for 2026-10-20 Market Briefing Regulatory, Provenance & Transatlantic Supply Chain Upgrades.
Verifies:
1. Centinela (Chile) mediation & Kutcho Copper (Canada NRCan Showcase) geofencing and provenance verification.
2. Japan Defense Yttrium emergency reserve & Minamitorishima REE under China MOFCOM D-21 (0.1% rule) & DoD DFARS 2027.
3. Micron Indium/Gallium semiconductor grade materials, deep-sea manganese nodule schemas & Japan SourceCountry mapping.
4. 2026-10-20 market briefing markdown report integrity and core telemetry validation.
"""

from pathlib import Path
import pytest
from app.schemas import (
    CopperOriginVerifyRequest,
    RareEarthsOriginVerifyRequest,
    MineralType,
    SourceCountry,
)
from app.copper_pipeline import CopperProvenancePipeline
from app.rare_earths_pipeline import rare_earths_pipeline


def test_centinela_copper_pipeline_verification():
    """Verify Chilean Minera Centinela open-pit complex provenance amidst labor mediation & LME $14,496/t market."""
    pipeline = CopperProvenancePipeline()
    req = CopperOriginVerifyRequest(
        lot_id="CU-CHL-CENTINELA-2026-1020",
        mine_concession_name="CENTINELA",
        extraction_coordinates=(-22.923, -69.255),
        source_country=SourceCountry.CHL,
        feedstock_concentrate_tons=500.0,
        concentrate_grade_cu_pct=28.5,
        sulfuric_acid_input_tons=444.6,  # 138.9375 * 3.2 = 444.6t
        refined_copper_cathode_tons=138.9375,  # 500 * 0.285 * 0.975 = 138.9375t
        copper_cathode_purity_pct=99.9950,
        cochilco_export_clearance_id="CHL-COCHILCO-2026-OCT20-CENTINELA",
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


def test_kutcho_copper_canada_nrcan_showcase():
    """Verify Kutcho Copper project in British Columbia, Canada selected for NRCan Critical Mineral Project Showcase."""
    pipeline = CopperProvenancePipeline()
    req = CopperOriginVerifyRequest(
        lot_id="CU-CAN-KUTCHO-2026-NRCAN",
        mine_concession_name="KUTCHO",
        extraction_coordinates=(58.200, -128.400),
        source_country=SourceCountry.CAN,
        feedstock_concentrate_tons=300.0,
        concentrate_grade_cu_pct=25.0,
        sulfuric_acid_input_tons=234.0,  # 73.125 * 3.2 = 234.0t
        refined_copper_cathode_tons=73.125,  # 300 * 0.25 * 0.975 = 73.125t
        copper_cathode_purity_pct=99.9945,
        cochilco_export_clearance_id="CAN-NRCAN-SHOWCASE-2026-KUTCHO",
        hvdc_cable_spec_compliant=True,
        feoc_shareholding_pct=0.0,
    )
    res = pipeline.verify_origin(req)

    assert res.status == "success"
    assert res.verdict.geofence_verified is True
    assert res.extraction_origin["concession_id"] == "CAN-BC-KUTCHO-01"
    assert res.extraction_origin["country"] == "CAN"
    assert res.verdict.stoichiometric_mass_balance_passed is True
    assert res.verdict.feoc_cleared is True
    assert res.onchain_proof.startswith("0x")


def test_japan_defense_yttrium_minamitorishima_mofcom_d21():
    """Verify Defense-grade Yttrium & Heavy REE from Minamitorishima under China MOFCOM D-21 countdown & DFARS 2027."""
    req = RareEarthsOriginVerifyRequest(
        batch_id="RE-Y-JPN-DEFENSE-D21-MISSILE",
        tenement_id="MINAMITORISHIMA",
        latitude=24.287,
        longitude=153.980,
        ndpr_oxide_purity_pct=99.90,
        thorium_uranium_radiation_ppm=28.5,
        declared_china_origin_ratio=0.0,
        source_country=SourceCountry.JPN,
    )
    res = rare_earths_pipeline.verify_rare_earths_batch(req)

    assert res.status == "success"
    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.geofence_verified is True
    assert res.audit_verdict.mofcom_china_content_passed is True
    assert res.audit_verdict.dfars_2027_compliant is True
    assert res.audit_verdict.status == "COMPLIANT_CERTIFIED"
    assert res.proof_hash.startswith("0x")


def test_semiconductor_and_defense_schemas_expansion():
    """Verify INDIUM_INGOT, GALLIUM_METAL, YTTRIUM_OXIDE and Japan SourceCountry enum expansions."""
    assert MineralType("INDIUM_INGOT") == MineralType.INDIUM_INGOT
    assert MineralType("indium") == MineralType.INDIUM_INGOT
    assert MineralType("gallium") == MineralType.GALLIUM_METAL
    assert MineralType("yttrium") == MineralType.YTTRIUM_OXIDE
    assert MineralType("Y2O3") == MineralType.YTTRIUM_OXIDE

    assert SourceCountry("JPN") == SourceCountry.JPN
    assert SourceCountry("JAPAN") == SourceCountry.JPN
    assert SourceCountry("jp") == SourceCountry.JPN


def test_oct20_briefing_document_integrity():
    """Verify the 2026-10-20 market briefing document exists and contains core telemetry."""
    doc_path = Path("docs/reports/2026-10-20_market_briefing.md")
    assert doc_path.exists(), "2026-10-20_market_briefing.md must exist in docs/reports"
    content = doc_path.read_text(encoding="utf-8")

    assert "2026년 10월 20일" in content
    assert "$14,496" in content
    assert "23만 2,175" in content or "232,175" in content
    assert "$6.54" in content or "$6.66" in content
    assert "$57.20" in content
    assert "$4,122" in content or "$4,124" in content
    assert "LME 위크" in content or "LME Week" in content
    assert "센티넬라" in content or "Centinela" in content
    assert "쿠초" in content or "Kutcho" in content
    assert "마이크론" in content or "Micron" in content
    assert "인듐" in content or "Indium" in content
    assert "갈륨" in content or "Gallium" in content
    assert "심해" in content or "American Metal" in content
    assert "이트륨" in content or "Yttrium" in content
    assert "D-21" in content
    assert "CBAM" in content
