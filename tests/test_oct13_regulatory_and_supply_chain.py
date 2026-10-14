"""
Tests for 2026-10-13 Market Briefing Regulatory, Provenance & Transatlantic Supply Chain Upgrades.
Verifies:
1. Chilean Minera Valle Central (Amerigo Resources) copper tailings operation geofencing and mass balance.
2. Canadian Rackla Metals Lentung Skarn Tungsten Project (Yukon/NWT) geofencing and defense procurement.
3. US HyproMag Texas Fort Worth Hub & German HyproMag GmbH EU CRMA Strategic Project permanent magnet recycling.
4. Australian Matrix Critical Minerals Narraburra REE Project (ASX IPO) geofencing and non-China compliance.
5. US NioCorp Elk Creek Ferroniobium & Scandium Oxide Traxys 100% commercial offtake placement.
6. 2026-10-13 Market Briefing markdown report presence and core telemetry validation.
"""

from pathlib import Path
import pytest
from app.schemas import (
    CopperOriginVerifyRequest,
    RareEarthsOriginVerifyRequest,
    TungstenOriginVerifyRequest,
    NiobiumScandiumOriginVerifyRequest,
    MineralType,
    SourceCountry,
)
from app.copper_pipeline import CopperProvenancePipeline
from app.rare_earths_pipeline import rare_earths_pipeline
from app.tungsten_pipeline import tungsten_pipeline
from app.niobium_scandium_pipeline import NiobiumScandiumPipeline


def test_valle_central_amerigo_copper_tailings_geofence():
    """Verify Chilean Minera Valle Central (Amerigo) copper tailings geofence and metallurgical balance."""
    pipeline = CopperProvenancePipeline()
    # 500t concentrate at 28.0% Cu = 140.0t Cu contained * 0.975 recovery = 136.5t cathode
    # Sulfuric acid: 136.5t * 3.2 = 436.8t H2SO4
    req = CopperOriginVerifyRequest(
        lot_id="CU-CHL-VALLECENTRAL-2026-01",
        mine_concession_name="VALLE_CENTRAL",
        extraction_coordinates=(-34.170, -70.650),
        source_country=SourceCountry.CHL,
        feedstock_concentrate_tons=500.0,
        concentrate_grade_cu_pct=28.0,
        sulfuric_acid_input_tons=436.8,
        refined_copper_cathode_tons=136.5,
        copper_cathode_purity_pct=99.9935,
        cochilco_export_clearance_id="CHL-COCHILCO-2026-MVC-01",
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


def test_rackla_metals_lentung_skarn_tungsten():
    """Verify Rackla Metals Lentung skarn deposit in Yukon/NWT border, Canada."""
    req = TungstenOriginVerifyRequest(
        batch_id="W-CAN-LENTUNG-2026-001",
        tenement_id="LENTUNG",
        latitude=63.500,
        longitude=-130.500,
        apt_wo3_grade_pct=89.50,
        dodd_frank_conflict_free=True,
        ndaa_defense_procurement_eligible=True,
        source_country=SourceCountry.CAN,
    )
    res = tungsten_pipeline.verify_tungsten_batch(req)

    assert res.status == "success"
    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.geofence_verified is True
    assert res.audit_verdict.distance_to_concession_km == 0.0
    assert res.audit_verdict.apt_grade_certified is True
    assert res.audit_verdict.ndaa_defense_eligible is True
    assert res.audit_verdict.dodd_frank_passed is True


def test_hypromag_usa_texas_hub_recycling_ree():
    """Verify HyproMag USA Texas Fort Worth rare earth magnet recycling hub."""
    req = RareEarthsOriginVerifyRequest(
        batch_id="RE-USA-HYPROMAG-2026-001",
        tenement_id="HYPROMAG_USA",
        latitude=32.755,
        longitude=-97.330,
        ndpr_oxide_purity_pct=99.95,
        thorium_uranium_radiation_ppm=25.0,
        declared_china_origin_ratio=0.0,
        source_country=SourceCountry.USA,
    )
    res = rare_earths_pipeline.verify_rare_earths_batch(req)

    assert res.status == "success"
    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.geofence_verified is True
    assert res.audit_verdict.distance_to_concession_km == 0.0
    assert res.audit_verdict.purity_certified is True
    assert res.audit_verdict.mofcom_china_content_passed is True
    assert res.audit_verdict.dfars_2027_compliant is True


def test_hypromag_germany_eu_crma_hub():
    """Verify HyproMag GmbH permanent magnet processing facility in Germany (EU CRMA Strategic Project)."""
    req = RareEarthsOriginVerifyRequest(
        batch_id="RE-DEU-HYPROMAG-2026-002",
        tenement_id="HYPROMAG_DEU",
        latitude=48.775,
        longitude=9.182,
        ndpr_oxide_purity_pct=99.90,
        thorium_uranium_radiation_ppm=15.0,
        declared_china_origin_ratio=0.0,
        source_country=SourceCountry.DEU,
    )
    res = rare_earths_pipeline.verify_rare_earths_batch(req)

    assert res.status == "success"
    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.geofence_verified is True
    assert res.audit_verdict.distance_to_concession_km == 0.0
    assert res.audit_verdict.purity_certified is True


def test_narraburra_matrix_critical_minerals_ree():
    """Verify Matrix Critical Minerals Narraburra REE Project in New South Wales, Australia."""
    req = RareEarthsOriginVerifyRequest(
        batch_id="RE-AUS-NARRA-2026-001",
        tenement_id="NARRABURRA",
        latitude=-34.250,
        longitude=147.500,
        ndpr_oxide_purity_pct=99.60,
        thorium_uranium_radiation_ppm=180.0,
        declared_china_origin_ratio=0.0,
        source_country=SourceCountry.AUS,
    )
    res = rare_earths_pipeline.verify_rare_earths_batch(req)

    assert res.status == "success"
    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.geofence_verified is True
    assert res.audit_verdict.distance_to_concession_km == 0.0
    assert res.audit_verdict.purity_certified is True


def test_niocorp_elk_creek_traxys_offtake_provenance():
    """Verify NioCorp Elk Creek Niobium & Scandium Defense Strategic Materials Pipeline."""
    pipeline = NiobiumScandiumPipeline()
    req = NiobiumScandiumOriginVerifyRequest(
        batch_id="NB-SC-2026-TRAXYS-100",
        tenement_id="ELK_CREEK",
        latitude=40.274,
        longitude=-96.183,
        commodity_type=MineralType.FERRONIOBIUM,
        fe_nb_grade_pct=66.5,
        doe_exim_loan_eligible=True,
        ndaa_defense_procurement_eligible=True,
        source_country=SourceCountry.USA,
    )
    res = pipeline.verify_origin(req)

    assert res.status == "success"
    assert res.audit_verdict.is_compliant is True
    assert res.audit_verdict.geofence_verified is True
    assert res.audit_verdict.distance_to_concession_km == 0.0
    assert res.audit_verdict.grade_assay_certified is True
    assert res.audit_verdict.defense_procurement_eligible is True
    assert res.audit_verdict.doe_exim_loan_eligible is True
    assert "Traxys 100% Commercial Offtake" in pipeline.tenements["ELK_CREEK"]["operator"]


def test_oct13_briefing_document_integrity():
    """Verify the 2026-10-13 market briefing document exists and has the required analytical sections."""
    doc_path = Path("docs/reports/2026-10-13_market_briefing.md")
    assert doc_path.exists(), "2026-10-13_market_briefing.md must exist in docs/reports"
    content = doc_path.read_text(encoding="utf-8")

    assert "2026년 10월 13일" in content
    assert "$6.72" in content
    assert "Centinela" in content
    assert "23만 3,025톤" in content
    assert "$60.53" in content
    assert "$4,188" in content or "$4,190" in content
    assert "NioCorp" in content
    assert "Traxys" in content
    assert "HyproMag" in content
    assert "Rackla" in content or "Lentung" in content
    assert "Narraburra" in content
    assert "D-28" in content
    assert "CBAM" in content
