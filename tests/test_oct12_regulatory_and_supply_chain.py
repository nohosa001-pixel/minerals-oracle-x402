"""
Tests for 2026-10-12 Market Briefing Regulatory, Provenance & Transatlantic Supply Chain Upgrades.
Verifies:
1. Chilean Centinela Copper Mine (Antofagasta Minerals) geofencing and mass balance verification.
2. Greenland Sarfartoq REE deposit & Estonian Silmet 2.0 EU CRMA Strategic Project transatlantic integration.
3. Kazakhstan Bakuta Tungsten deposit (US DFC $700M LOI) geofencing and defense procurement verification.
4. SourceCountry expansion (GRL, EST, KAZ, ESP) and string alias normalization.
"""

import pytest
from app.schemas import (
    CopperOriginVerifyRequest,
    RareEarthsOriginVerifyRequest,
    TungstenOriginVerifyRequest,
    SourceCountry,
)
from app.copper_pipeline import CopperProvenancePipeline
from app.rare_earths_pipeline import rare_earths_pipeline
from app.tungsten_pipeline import tungsten_pipeline


def test_centinela_chile_copper_geofence_and_cochilco():
    """Verify Chilean Centinela copper mine geofence and full metallurgical balance."""
    pipeline = CopperProvenancePipeline()
    # 400t concentrate at 27.5% Cu = 110.0t Cu contained * 0.975 recovery = 107.25t cathode
    # Sulfuric acid: 107.25t * 3.2 = 343.2t H2SO4
    req = CopperOriginVerifyRequest(
        lot_id="CU-CHL-CENTINELA-2026-01",
        mine_concession_name="CENTINELA",
        extraction_coordinates=(-22.923, -69.255),
        source_country=SourceCountry.CHL,
        feedstock_concentrate_tons=400.0,
        concentrate_grade_cu_pct=27.5,
        sulfuric_acid_input_tons=343.2,
        refined_copper_cathode_tons=107.25,
        copper_cathode_purity_pct=99.9935,
        cochilco_export_clearance_id="CHL-COCHILCO-2026-CENTINELA-01",
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


def test_greenland_sarfartoq_transatlantic_silmet_ree():
    """Verify Greenland Sarfartoq Carbonatite Complex and transatlantic linkage to Silmet 2.0."""
    req = RareEarthsOriginVerifyRequest(
        batch_id="RE-GRL-SARFARTOQ-2026-001",
        tenement_id="SARFARTOQ",
        latitude=66.500,
        longitude=-51.250,
        ndpr_oxide_purity_pct=99.85,
        thorium_uranium_radiation_ppm=165.0,
        declared_china_origin_ratio=0.0,  # 100% Non-China Transatlantic origin
        source_country=SourceCountry.GRL,
    )
    res = rare_earths_pipeline.verify_rare_earths_batch(req)

    assert res.status == "success"
    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.geofence_verified is True
    assert res.audit_verdict.distance_to_concession_km == 0.0
    assert res.audit_verdict.purity_certified is True
    assert res.audit_verdict.radiation_safety_passed is True
    assert res.audit_verdict.mofcom_china_content_passed is True
    assert res.audit_verdict.dfars_2027_compliant is True
    assert res.onchain_signature.startswith("0x")


def test_estonia_silmet_refinery_geofence():
    """Verify Neo Performance Materials Silmet 2.0 EU CRMA Strategic Project in Estonia."""
    req = RareEarthsOriginVerifyRequest(
        batch_id="RE-EST-SILMET-2026-002",
        tenement_id="SILMET",
        latitude=59.395,
        longitude=27.764,
        ndpr_oxide_purity_pct=99.90,
        thorium_uranium_radiation_ppm=85.0,
        declared_china_origin_ratio=0.0,
        source_country=SourceCountry.EST,
    )
    res = rare_earths_pipeline.verify_rare_earths_batch(req)

    assert res.status == "success"
    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.geofence_verified is True
    assert res.audit_verdict.distance_to_concession_km == 0.0
    assert res.audit_verdict.purity_certified is True


def test_kazakhstan_bakuta_tungsten_dfc_consortium():
    """Verify Bakuta Tungsten deposit in Almaty Region, Kazakhstan under US DFC $700M LOI."""
    req = TungstenOriginVerifyRequest(
        batch_id="W-KAZ-BAKUTA-2026-001",
        tenement_id="BAKUTA",
        latitude=43.467,
        longitude=78.433,
        apt_wo3_grade_pct=89.20,
        dodd_frank_conflict_free=True,
        ndaa_defense_procurement_eligible=True,
        source_country=SourceCountry.KAZ,
    )
    res = tungsten_pipeline.verify_tungsten_batch(req)

    assert res.status == "success"
    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.geofence_verified is True
    assert res.audit_verdict.distance_to_concession_km == 0.0
    assert res.audit_verdict.apt_grade_certified is True
    assert res.audit_verdict.ndaa_defense_eligible is True


def test_source_country_new_aliases():
    """Verify alias parsing for GRL, EST, KAZ, and ESP."""
    assert SourceCountry("GREENLAND") == SourceCountry.GRL
    assert SourceCountry("gl") == SourceCountry.GRL
    assert SourceCountry("ESTONIA") == SourceCountry.EST
    assert SourceCountry("ee") == SourceCountry.EST
    assert SourceCountry("KAZAKHSTAN") == SourceCountry.KAZ
    assert SourceCountry("kz") == SourceCountry.KAZ
    assert SourceCountry("SPAIN") == SourceCountry.ESP
    assert SourceCountry("es") == SourceCountry.ESP
