"""
Tests for 2026-10-27 Market & EUDR Regulatory Intelligence, Provenance & Supply Chain Upgrades.
Verifies:
1. Critical Metals Corp / European Lithium Ltd merger & Wolfsberg Lithium Project (Austria) provenance pipeline.
2. US DoD Title III Estelle Antimony & Gold Project (Alaska) and Anzob Antimony Complex (Tajikistan) provenance.
3. MineralType (ANTIMONY_INGOT, ALUMINIUM_INGOT) and SourceCountry (AUT, TJK, UZB, GIN) schema expansions and alias normalization.
4. 2026-10-27 Market Briefing and EUDR Regulatory Briefing markdown report presence and core structure.
"""

from pathlib import Path
import pytest
from app.schemas import (
    LithiumOriginVerifyRequest,
    RareEarthsOriginVerifyRequest,
    MineralType,
    SourceCountry,
)
from app.lithium_pipeline import LithiumProvenancePipeline, WA_LITHIUM_TENEMENT_REGISTRY
from app.rare_earths_pipeline import CANONICAL_RARE_EARTHS_TENEMENT_REGISTRY, rare_earths_pipeline


def test_wolfsberg_lithium_austria_pipeline():
    """Verify Wolfsberg Lithium Project (Austria) provenance for Critical Metals Corp / European Lithium merger."""
    assert "WOLFSBERG" in WA_LITHIUM_TENEMENT_REGISTRY
    wolfsberg_meta = WA_LITHIUM_TENEMENT_REGISTRY["WOLFSBERG"]
    assert wolfsberg_meta["country"] == "AUT"
    assert wolfsberg_meta["minedex_tenement_id"] == "AUT-CAR-WOLFSBERG-01"

    pipeline = LithiumProvenancePipeline()
    req = LithiumOriginVerifyRequest(
        trace_id="TR-LITH-WOLFSBERG-2026-OCT27-CRML",
        product="Lithium Hydroxide Monohydrate",
        mine_name="Wolfsberg Lithium Project",
        mine_country="AUT",
        coordinates=[46.840, 14.840],
        minedex_tenement_id="AUT-CAR-WOLFSBERG-01",
        spodumene_tonnage_extracted=7500.0,
        spodumene_grade_pct=6.0,
        refinery_facility="Wolfsberg Advanced Conversion Facility",
        refinery_country="AUT",
        refined_output_tonnage=1000.0,
        refinery_feoc_equity_pct=0.0,
        satellite_vegetation_index=0.15,
        sar_backscatter_db=-11.2,
        agent_address="0x71C84107b3a42E2F2Ab4Ba770265EC0c4ce5Cea6",
    )
    res = pipeline.evaluate_lithium_lot(req)

    assert res.status == "success"
    assert res.extraction_origin.country == "AUT"
    assert res.extraction_origin.geofence_passed is True
    assert res.extraction_origin.minedex_tenement_id == "AUT-CAR-WOLFSBERG-01"
    assert res.audit_verdict.crma_origin_eligible is True
    assert res.onchain_proof is not None
    assert len(res.onchain_proof) > 20


def test_antimony_and_rare_earths_canonical_registry():
    """Verify Estelle Antimony (Alaska) and Anzob Antimony (Tajikistan) registered concessions."""
    assert "ESTELLE_ALASKA" in CANONICAL_RARE_EARTHS_TENEMENT_REGISTRY
    estelle = CANONICAL_RARE_EARTHS_TENEMENT_REGISTRY["ESTELLE_ALASKA"]
    assert estelle["country"] == "USA"
    assert estelle["concession_id"] == "USA-AK-ESTELLE-01"

    assert "ANZOB_TAJIKISTAN" in CANONICAL_RARE_EARTHS_TENEMENT_REGISTRY
    anzob = CANONICAL_RARE_EARTHS_TENEMENT_REGISTRY["ANZOB_TAJIKISTAN"]
    assert anzob["country"] == "TJK"
    assert anzob["concession_id"] == "TJK-SUG-ANZOB-01"

    assert "DOE_PILOT_PLANT" in CANONICAL_RARE_EARTHS_TENEMENT_REGISTRY


def test_schema_antimony_and_aluminium_expansions():
    """Verify MineralType and SourceCountry enum definitions and normalization logic."""
    assert MineralType("ANTIMONY_INGOT") == MineralType.ANTIMONY_INGOT
    assert MineralType("ALUMINIUM_INGOT") == MineralType.ALUMINIUM_INGOT
    assert MineralType("ANTIMONY") == MineralType.ANTIMONY_INGOT
    assert MineralType("SB") == MineralType.ANTIMONY_INGOT
    assert MineralType("AL") == MineralType.ALUMINIUM_INGOT
    assert MineralType("ALUMINUM") == MineralType.ALUMINIUM_INGOT

    assert SourceCountry("AUT") == SourceCountry.AUT
    assert SourceCountry("AUSTRIA") == SourceCountry.AUT
    assert SourceCountry("AT") == SourceCountry.AUT
    assert SourceCountry("TJK") == SourceCountry.TJK
    assert SourceCountry("TAJIKISTAN") == SourceCountry.TJK
    assert SourceCountry("UZB") == SourceCountry.UZB
    assert SourceCountry("GIN") == SourceCountry.GIN
    assert SourceCountry("GUINEA") == SourceCountry.GIN


def test_oct27_market_briefing_report_integrity():
    """Verify that 2026-10-27_market_briefing.md exists and contains vital market sections."""
    root = Path(__file__).resolve().parent.parent
    report_file = root / "docs" / "reports" / "2026-10-27_market_briefing.md"
    assert report_file.exists(), "2026-10-27_market_briefing.md must exist"

    content = report_file.read_text(encoding="utf-8")
    assert "2026-10-27" in content
    assert "구리 (Copper)" in content
    assert "은 (Silver)" in content
    assert "금 (Gold)" in content
    assert "Critical Metals Corp" in content or "CRML" in content
    assert "Wolfsberg" in content or "볼프스베르크" in content


def test_oct27_eudr_briefing_report_integrity():
    """Verify that 2026-10-27_eudr_briefing.md exists and contains vital EUDR compliance sections."""
    root = Path(__file__).resolve().parent.parent
    report_file = root / "docs" / "reports" / "2026-10-27_eudr_briefing.md"
    assert report_file.exists(), "2026-10-27_eudr_briefing.md must exist"

    content = report_file.read_text(encoding="utf-8")
    assert "2026-10-27" in content
    assert "EUDR" in content
    assert "TRACES NT" in content
    assert "CSW-CERTEX" in content
