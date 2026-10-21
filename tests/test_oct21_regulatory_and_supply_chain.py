"""
Tests for 2026-10-21 Market Briefing Regulatory, Provenance & Transatlantic Supply Chain Upgrades.
Verifies:
1. LME Week Day 3 Copper Cathode Provenance amidst physical premium negotiations & LME 225,425t depletion.
2. US-AU Critical Minerals Pact 1st Anniversary Arafura Nolans REE verification under China MOFCOM D-20 (0.1% rule) & DoD DFARS 2027.
3. Silver $58 breakout TOPCon solar cell conductive paste provenance & physical deficit screening.
4. 2026-10-21 market briefing markdown report integrity and core telemetry validation.
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


def test_lme_week_day3_copper_cathode_pipeline():
    """Verify Chilean Escondida/Centinela cathode supply contract compliance during LME Week 2027 premium negotiations."""
    pipeline = CopperProvenancePipeline()
    req = CopperOriginVerifyRequest(
        lot_id="CU-LME-WEEK-2026-OCT21-CATHODE",
        mine_concession_name="CENTINELA",
        extraction_coordinates=(-22.923, -69.255),
        source_country=SourceCountry.CHL,
        feedstock_concentrate_tons=600.0,
        concentrate_grade_cu_pct=29.0,
        sulfuric_acid_input_tons=542.88,  # 169.65 * 3.2 = 542.88t
        refined_copper_cathode_tons=169.65,  # 600 * 0.29 * 0.975 = 169.65t
        copper_cathode_purity_pct=99.9950,
        cochilco_export_clearance_id="CHL-COCHILCO-2026-OCT21-LMEWEEK",
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


def test_us_au_pact_nolans_rare_earths_d20_compliance():
    """Verify Australian Nolans REE under US-AU Pact 1st Anniversary, DoD DFARS 2027 & China MOFCOM D-20 countdown."""
    req = RareEarthsOriginVerifyRequest(
        batch_id="RE-AU-NOLANS-USAU-PACT-D20",
        tenement_id="NOLANS_BORE",
        latitude=-22.583,
        longitude=133.233,
        ndpr_oxide_purity_pct=99.92,
        thorium_uranium_radiation_ppm=34.0,
        declared_china_origin_ratio=0.0,
        source_country=SourceCountry.AUS,
    )
    res = rare_earths_pipeline.verify_rare_earths_batch(req)

    assert res.status == "success"
    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.geofence_verified is True
    assert res.audit_verdict.mofcom_china_content_passed is True
    assert res.audit_verdict.dfars_2027_compliant is True
    assert res.audit_verdict.status == "COMPLIANT_CERTIFIED"
    assert res.proof_hash.startswith("0x")


def test_silver_58_breakout_topcon_paste_provenance():
    """Verify Silver lot provenance for N-Type TOPCon Solar PV paste during $58/oz breakout."""
    # 2,000kg Doré at 80.0% Ag = 1,600kg contained * 0.99 recovery = 1,584.0kg theoretical refined silver
    req = SilverOriginVerifyRequest(
        lot_id="AG-MEX-TERRONERA-2026-OCT21-58USD",
        mine_concession_name="TERRONERA",
        extraction_coordinates=(20.590, -104.980),
        source_country=SourceCountry.MEX,
        feedstock_dore_or_ore_kg=2000.0,
        feedstock_silver_grade_pct=80.0,
        refined_solar_powder_kg=1584.0,
        refined_purity_pct=99.995,
        lbma_good_delivery_ref="LBMA-REF-MEX-2026-OCT21",
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


def test_oct21_briefing_document_integrity():
    """Verify the 2026-10-21 market briefing document exists and contains core telemetry."""
    doc_path = Path("docs/reports/2026-10-21_market_briefing.md")
    assert doc_path.exists(), "2026-10-21_market_briefing.md must exist in docs/reports"
    content = doc_path.read_text(encoding="utf-8")

    assert "2026년 10월 21일" in content
    assert "LME 위크" in content
    assert "$14,595" in content
    assert "22만 5,425" in content or "225,425" in content
    assert "$6.58" in content or "$6.69" in content
    assert "$57.99" in content or "$58.05" in content or "$58선" in content
    assert "$4,122" in content or "$4,136" in content
    assert "5.14%" in content
    assert "미국-호주" in content or "미-호주" in content
    assert "놀란스" in content or "Nolans" in content
    assert "라이너스" in content or "Lynas" in content
    assert "32억" in content or "32.4억" in content
    assert "마이레" in content or "Maire" in content
    assert "MEAB" in content
    assert "용매 추출" in content or "NextChem" in content
    assert "잭 리프턴" in content or "Jack Lifton" in content
    assert "D-20" in content or "20일" in content
    assert "CBAM" in content
    assert "+10%" in content
    assert "산업가속화법" in content or "IAA" in content
    assert "70%" in content
    assert "CSDDD" in content
