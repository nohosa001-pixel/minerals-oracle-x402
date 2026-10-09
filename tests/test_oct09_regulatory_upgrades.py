"""
Tests for 2026-10-09 Market Briefing Regulatory & Provenance Engine Upgrades.
Verifies:
1. Australian Arafura Nolans Rare Earths Project geofencing and registration.
2. US DoD DFARS 2027 100% Non-Covered-Nation (Non-China) Permanent Magnet rule.
3. Zambian Copperbelt (Kansanshi, Sentinel) geofencing and SourceCountry.ZMB integration.
"""

import pytest
from app.schemas import (
    RareEarthsOriginVerifyRequest,
    CopperOriginVerifyRequest,
    SourceCountry,
)
from app.rare_earths_pipeline import rare_earths_pipeline
from app.copper_pipeline import CopperProvenancePipeline


def test_arafura_nolans_rare_earths_geofence_and_dfars_clean():
    """Verify Arafura Nolans tenement in Northern Territory, Australia and 100% Non-China DFARS compliance."""
    req = RareEarthsOriginVerifyRequest(
        batch_id="RE-NOLANS-2026-001",
        tenement_id="NOLANS",
        latitude=-22.580,
        longitude=133.240,
        ndpr_oxide_purity_pct=99.8,
        thorium_uranium_radiation_ppm=180.0,
        declared_china_origin_ratio=0.0,  # 100% Clean Non-China origin
        source_country=SourceCountry.AUS,
    )
    res = rare_earths_pipeline.verify_rare_earths_batch(req)

    assert res.status == "success"
    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.geofence_verified is True
    assert res.audit_verdict.distance_to_concession_km == 0.0
    assert res.audit_verdict.purity_certified is True
    assert res.audit_verdict.radiation_safety_passed is True
    assert res.audit_verdict.mofcom_china_content_passed is True
    # DFARS 2027 100% clean check
    assert res.audit_verdict.dfars_2027_compliant is True
    assert any("DFARS 2027 Certified" in reason for reason in res.audit_verdict.reasons)
    assert res.onchain_signature is not None and res.onchain_signature.startswith("0x")


def test_dfars_2027_taint_advisory():
    """Verify that even small Chinese content (< 0.1% MOFCOM passing) triggers DFARS 2027 advisory."""
    req = RareEarthsOriginVerifyRequest(
        batch_id="RE-MTWELD-2026-002",
        tenement_id="MT_WELD",
        latitude=-28.868,
        longitude=122.500,
        ndpr_oxide_purity_pct=99.7,
        thorium_uranium_radiation_ppm=220.0,
        declared_china_origin_ratio=0.0005,  # 0.05% China origin: passes MOFCOM (<0.1%) but fails DFARS 100% clean
        source_country=SourceCountry.AUS,
    )
    res = rare_earths_pipeline.verify_rare_earths_batch(req)

    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.mofcom_china_content_passed is True
    assert res.audit_verdict.dfars_2027_compliant is False
    assert any("DFARS 2027 Advisory" in reason for reason in res.audit_verdict.reasons)


def test_zambian_copperbelt_kansanshi_geofence():
    """Verify Zambian Kansanshi copper mine geofence and ZMB country code integration."""
    pipeline = CopperProvenancePipeline()
    # 350t concentrate at 28.0% Cu = 98.0t contained * 0.975 recovery = 95.55t theoretical cathode
    # H2SO4: 95.55t * 3.2 = 305.76t
    req = CopperOriginVerifyRequest(
        lot_id="CU-ZMB-KANSAN-2026-01",
        mine_concession_name="KANSANSHI",
        extraction_coordinates=(-12.095, 26.425),
        source_country=SourceCountry.ZMB,
        feedstock_concentrate_tons=350.0,
        concentrate_grade_cu_pct=28.0,
        sulfuric_acid_input_tons=305.76,
        refined_copper_cathode_tons=95.55,
        copper_cathode_purity_pct=99.9935,
        cochilco_export_clearance_id="ZMB-EX-2026-KANSAN",
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
    assert res.extraction_origin["distance_km"] == 0.0
    assert res.extraction_origin["concession_id"] == "ZMB-NWP-KANSAN-01"
    assert res.verdict.confidence_score >= 90.0
    assert res.onchain_proof.startswith("0x")


def test_source_country_zambia_aliases():
    """Verify string parsing aliases for Zambia."""
    assert SourceCountry("ZMB") == SourceCountry.ZMB
    assert SourceCountry("ZAMBIA") == SourceCountry.ZMB
    assert SourceCountry("zm") == SourceCountry.ZMB
