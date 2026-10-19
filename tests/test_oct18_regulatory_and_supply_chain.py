"""
Tests for 2026-10-18 Market Briefing Regulatory, Provenance & Transatlantic Supply Chain Upgrades.
Verifies:
1. DRC Kolwezi (Kasulo / Kamoto / Tenke) cobalt traceability & EU CSDDD human rights / ILO anti-child labor compliance.
2. LME Week 2026 opening copper supply shock (LME $14,595/t, 225,425t low inventory, US 1.5M ton isolation).
3. China MOFCOM D-23 extraterritorial export control (0.1% rule) and US DoD DFARS 2027 non-China permanent magnets.
4. Multilateral Development Banks (MDB) critical minerals financing framework validation.
5. 2026-10-18 market briefing markdown report integrity and core telemetry validation.
"""

from pathlib import Path
import pytest
from app.schemas import (
    CobaltOriginVerifyRequest,
    CopperOriginVerifyRequest,
    RareEarthsOriginVerifyRequest,
    MineralType,
    SourceCountry,
)
from app.cobalt_pipeline import CobaltProvenancePipeline
from app.copper_pipeline import CopperProvenancePipeline
from app.rare_earths_pipeline import rare_earths_pipeline


def test_drc_kolwezi_cobalt_csddd_provenance():
    """Verify DRC Kolwezi cobalt supply chain under EU CSDDD and EGC artisanal custody governance."""
    pipeline = CobaltProvenancePipeline()
    req = CobaltOriginVerifyRequest(
        trace_id="COB-COD-2026-KOLWEZI-CSDDD",
        product="Crude Cobalt Hydroxide",
        concession_name="EGC_KASULO",
        province="Lualaba",
        coordinates=[-10.710, 25.490],  # Kolwezi, Lualaba
        mine_type="ASM",
        ceec_seal_id="CEEC-KAT-2026-881244",
        egc_custody_ref="EGC-KASULO-LOT-2026-X9",
        asm_comingled=True,
        zero_child_labor_audit_ref="ILO-138-182-AUDIT-EGC-01",
        heterogenite_ore_input_tons=23530.0,
        ore_grade_co_pct=1.50,
        refinery_name="EGC Kasulo Artisanal Depots",
        refinery_country="COD",
        rmi_rmap_smelter_id="CID003120-RMAP",
        cobalt_hydroxide_output_tons=1000.0,
        hydroxide_grade_co_pct=30.0,
        feoc_equity_pct=0.0,
        agent_address="0x71C84107b3a42E2F2Ab4Ba770265EC0c4ce5Cea6",
    )
    res = pipeline.evaluate_cobalt_lot(req)

    assert res.status == "success"
    assert res.extraction_concession.geofence_passed is True
    assert res.extraction_concession.province == "Lualaba"
    assert res.extraction_concession.ceec_seal_verified is True
    assert res.extraction_concession.child_labor_audit_verified is True
    assert res.mass_balance_audit.is_stoichiometrically_sound is True
    assert res.audit_verdict.ceec_export_cleared is True
    assert res.audit_verdict.asm_segregated is True
    assert res.audit_verdict.child_labor_free is True
    assert res.audit_verdict.ira_feoc_compliant is True
    assert res.audit_verdict.confidence_score >= 90.0
    assert res.onchain_proof is not None


def test_copper_lme_week_tightness_and_smelting():
    """Verify Copper cathode provenance during LME Week 2026 opening and 225,425t low inventory."""
    pipeline = CopperProvenancePipeline()
    req = CopperOriginVerifyRequest(
        lot_id="CU-CHL-ELTENIENTE-2026-1018",
        mine_concession_name="EL_TENIENTE",
        extraction_coordinates=(-34.083, -70.467),
        source_country=SourceCountry.CHL,
        feedstock_concentrate_tons=400.0,
        concentrate_grade_cu_pct=30.0,
        sulfuric_acid_input_tons=374.4,  # 117.0 * 3.2 = 374.4t
        refined_copper_cathode_tons=117.0,  # 400 * 0.30 * 0.975 = 117.0t
        copper_cathode_purity_pct=99.9940,
        cochilco_export_clearance_id="CHL-COCHILCO-2026-OCT18-LME",
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


def test_china_mofcom_d23_rare_earths_defense_procurement():
    """Verify Rare Earths origin under China MOFCOM D-23 deadline and DoD DFARS 2027 defense requirement."""
    req = RareEarthsOriginVerifyRequest(
        batch_id="RE-ARMY-GUIDED-DEFENSE-D23",
        tenement_id="SARFARTOQ",
        latitude=66.500,
        longitude=-51.250,
        ndpr_oxide_purity_pct=99.85,
        thorium_uranium_radiation_ppm=32.0,
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


def test_oct18_briefing_document_integrity():
    """Verify the 2026-10-18 market briefing document exists and contains core telemetry."""
    doc_path = Path("docs/reports/2026-10-18_market_briefing.md")
    assert doc_path.exists(), "2026-10-18_market_briefing.md must exist in docs/reports"
    content = doc_path.read_text(encoding="utf-8")

    assert "2026년 10월 18일" in content
    assert "$14,595" in content
    assert "22만 5,425" in content or "225,425" in content
    assert "$6.56" in content
    assert "$56.975" in content or "$57.50" in content
    assert "$4,164" in content or "$4,166" in content
    assert "LME 위크" in content or "LME Week" in content
    assert "콜웨지" in content or "Kolwezi" in content
    assert "CSDDD" in content
    assert "다자개발은행" in content or "MDB" in content
    assert "D-23" in content
    assert "CBAM" in content
