"""
Comprehensive Unit Tests for the 5 Major Upgrades:
1. Rare Earths (NdPr), Tungsten & Recycled Black Mass Pipelines
2. Regulatory Advanced Engine (CBAM Mark-up Penalty, EU Industrial Act, Battery Passport VC)
3. Logistics Oracle Bridge (B/L Plausibility, Customs Clearance Bundle, Multi-Carrier Normalizer)
4. Dynamic Trade Escrow Contract Architecture
5. Zero-Knowledge Compliance Prover & Verifier
"""

import pytest
from app.schemas import (
    RareEarthsOriginVerifyRequest,
    TungstenOriginVerifyRequest,
    BlackMassOriginVerifyRequest,
    CBAMMarkupPenaltyRequest,
    EUIndustrialActVerifyRequest,
    BatteryPassportVCRequest,
    CustomsVerificationRequest,
    LogisticsTrackingStateRequest,
    ZKComplianceProofRequest,
    ZKProofVerifyRequest,
    SourceCountry,
)
from app.rare_earths_pipeline import rare_earths_pipeline
from app.tungsten_pipeline import tungsten_pipeline
from app.black_mass_pipeline import black_mass_pipeline
from app.regulatory_advanced_engine import regulatory_advanced_engine
from app.logistics_bridge import logistics_bridge
from app.zk_compliance_prover import zk_compliance_prover


# =====================================================================
# UPGRADE 1 TESTS: RARE EARTHS, TUNGSTEN & BLACK MASS
# =====================================================================

def test_rare_earths_pipeline_compliant():
    req = RareEarthsOriginVerifyRequest(
        batch_id="RE-TEST-001",
        tenement_id="MT_WELD",
        latitude=-28.868,
        longitude=122.500,
        ndpr_oxide_purity_pct=99.65,
        thorium_uranium_radiation_ppm=35.0,
        declared_china_origin_ratio=0.0004,  # 0.04% < 0.1%
        source_country=SourceCountry.AUS,
    )
    resp = rare_earths_pipeline.verify_rare_earths_batch(req)
    assert resp.status == "success"
    assert resp.audit_verdict.is_compliant is True
    assert resp.audit_verdict.geofence_verified is True
    assert resp.audit_verdict.purity_certified is True
    assert resp.audit_verdict.mofcom_china_content_passed is True
    assert resp.audit_verdict.mofcom_rule_d35_eligible is True
    assert resp.proof_hash.startswith("0x")
    assert resp.onchain_signature is not None


def test_rare_earths_pipeline_fails_mofcom_china_ratio():
    req = RareEarthsOriginVerifyRequest(
        batch_id="RE-TEST-002",
        tenement_id="MT_WELD",
        latitude=-28.868,
        longitude=122.500,
        ndpr_oxide_purity_pct=99.65,
        thorium_uranium_radiation_ppm=35.0,
        declared_china_origin_ratio=0.0025,  # 0.25% >= 0.1%
        source_country=SourceCountry.AUS,
    )
    resp = rare_earths_pipeline.verify_rare_earths_batch(req)
    assert resp.audit_verdict.is_compliant is False
    assert resp.audit_verdict.mofcom_china_content_passed is False
    assert resp.audit_verdict.mofcom_rule_d35_eligible is False


def test_tungsten_pipeline_compliant():
    req = TungstenOriginVerifyRequest(
        batch_id="W-TEST-001",
        tenement_id="PANASQUEIRA",
        latitude=40.158,
        longitude=-7.747,
        apt_wo3_grade_pct=88.9,
        dodd_frank_conflict_free=True,
        ndaa_defense_procurement_eligible=True,
        source_country=SourceCountry.PRT,
    )
    resp = tungsten_pipeline.verify_tungsten_batch(req)
    assert resp.status == "success"
    assert resp.audit_verdict.is_compliant is True
    assert resp.audit_verdict.geofence_verified is True
    assert resp.audit_verdict.apt_grade_certified is True
    assert resp.audit_verdict.ndaa_defense_eligible is True


def test_black_mass_pipeline_compliant():
    req = BlackMassOriginVerifyRequest(
        batch_id="BM-TEST-001",
        facility_id="ABTC_NEVADA",
        latitude=39.608,
        longitude=-119.251,
        nickel_content_pct=23.0,
        cobalt_content_pct=9.0,
        lithium_content_pct=4.5,
        fluorine_impurity_ppm=120.0,
        bis_export_license_id="BIS-D998811",
        recycled_content_ratio=0.95,
        source_country=SourceCountry.USA,
    )
    resp = black_mass_pipeline.verify_black_mass_batch(req)
    assert resp.status == "success"
    assert resp.audit_verdict.is_compliant is True
    assert resp.audit_verdict.bis_license_verified is True
    assert resp.audit_verdict.recycled_content_compliant is True
    assert resp.audit_verdict.fluorine_safety_passed is True


# =====================================================================
# UPGRADE 2 TESTS: REGULATORY ADVANCED (CBAM / IAA / BATTERY PASSPORT)
# =====================================================================

def test_cbam_markup_penalty_unverified():
    req = CBAMMarkupPenaltyRequest(
        import_year=2026,
        product_category="ALUMINUM",
        tonnage=100.0,
        default_embedded_emissions_tco2_per_ton=2.0,
        verified_scope1_2_emissions_tco2_per_ton=None,
        eu_allowance_price_eur=85.0,
    )
    resp = regulatory_advanced_engine.calculate_cbam_markup_penalty(req)
    assert resp.import_year == 2026
    assert resp.markup_penalty_rate == 0.10  # 10% penalty
    assert resp.is_verified_exempt is False
    assert resp.markup_penalty_surcharge_eur > 0.0


def test_cbam_markup_penalty_verified_exempt():
    req = CBAMMarkupPenaltyRequest(
        import_year=2026,
        product_category="ALUMINUM",
        tonnage=100.0,
        default_embedded_emissions_tco2_per_ton=2.0,
        verified_scope1_2_emissions_tco2_per_ton=1.5,
        eu_allowance_price_eur=85.0,
    )
    resp = regulatory_advanced_engine.calculate_cbam_markup_penalty(req)
    assert resp.markup_penalty_rate == 0.0
    assert resp.is_verified_exempt is True
    assert resp.markup_penalty_surcharge_eur == 0.0
    assert resp.savings_with_verified_report_eur > 0.0


def test_eu_industrial_act_verify():
    req = EUIndustrialActVerifyRequest(
        component_type="EV_BATTERY_PACK",
        eu_domestic_value_share_pct=75.0,  # >= 70%
        eu_steel_domestic_share_pct=45.0,  # >= 40%
        local_assembly_location="DEU",
    )
    resp = regulatory_advanced_engine.verify_eu_industrial_act(req)
    assert resp.iaa_70pct_threshold_passed is True
    assert resp.steel_40pct_threshold_passed is True
    assert resp.overall_subsidy_eligible is True


def test_battery_passport_vc_issuance():
    req = BatteryPassportVCRequest(
        battery_id="urn:uuid:pack-test-9999",
        chemistry="NMC811",
        rated_capacity_kwh=85.0,
        recycled_cobalt_pct=18.0,
        recycled_lithium_pct=8.0,
        recycled_nickel_pct=8.0,
        carbon_footprint_kg_co2_per_kwh=62.0,
        provenance_proof_hash="0xabcdef1234567890",
    )
    resp = regulatory_advanced_engine.generate_battery_passport_vc(req)
    assert resp.status == "success"
    assert resp.vc_token["type"] == ["VerifiableCredential", "DigitalProductPassport", "EUBatteryPassport"]
    assert "proof" in resp.vc_token
    assert resp.signature.startswith("0x")
    assert resp.qr_code_payload_uri.startswith("https://")


# =====================================================================
# UPGRADE 3 TESTS: LOGISTICS ORACLE BRIDGE
# =====================================================================

def test_logistics_bridge_customs_clearance():
    req = CustomsVerificationRequest(
        tracking_type="BOL",
        tracking_number="MEDU12345678",
        carrier_code="MSCU",
        port_of_loading="CLPRA",  # Antofagasta, Chile
        port_of_discharge="NLRTM",  # Rotterdam, Netherlands
        departure_date="2026-09-01",
        arrival_date="2026-09-25",
        mineral_batch_id="CU-BATCH-8888",
        mine_coordinates=(-22.283, -68.900),  # Chuquicamata
        gross_weight_kg=50000.0,
    )
    resp = logistics_bridge.verify_customs_clearance(req)
    assert resp.status == "success"
    assert resp.customs_clearance_eligible is True
    assert resp.transit_plausibility_passed is True
    assert resp.spatial_mine_to_port_km < 300.0
    assert "bundle_id" in resp.customs_clearance_bundle
    assert resp.proof_hash.startswith("0x")


def test_logistics_clean_tracking_feed():
    req = LogisticsTrackingStateRequest(
        tracking_numbers=["MEDU1234567", "CJ1234567890", "DHL987654321"],
    )
    resp = logistics_bridge.get_clean_tracking_feed(req)
    assert resp.status == "success"
    assert resp.total_queried == 3
    assert len(resp.results) == 3
    assert resp.results[0]["status_code"] == "IN_TRANSIT_HIGH_SEAS"


# =====================================================================
# UPGRADE 4 & 5 TESTS: ZK COMPLIANCE PROVER & PRIVACY ENGINE
# =====================================================================

def test_zk_compliance_prover_and_verifier():
    # 1. Generate Proof
    proof_req = ZKComplianceProofRequest(
        batch_id="ZK-BATCH-777",
        secret_mine_latitude=-24.267,
        secret_mine_longitude=-69.067,
        secret_unit_cost_usd=4200.50,
        secret_supplier_id="SECRET-VENDOR-CORP-99",
        public_authorized_zone_root="0xroot1234567890123456789012345678901234567890123456789012345678901234",
        public_china_origin_ratio=0.0003,  # 0.03% < 0.1%
        public_max_carbon_kg_co2=150.0,
    )
    proof_resp = zk_compliance_prover.generate_zk_compliance_proof(proof_req)
    assert proof_resp.status == "success"
    assert proof_resp.is_valid_zero_knowledge_proof is True
    assert proof_resp.public_commitment.startswith("0x")
    assert proof_resp.nullifier_hash.startswith("0x")
    assert "pi_a" in proof_resp.zk_proof["proof"]

    # 2. Public Verify Proof
    verify_req = ZKProofVerifyRequest(
        zk_proof=proof_resp.zk_proof,
        public_commitment=proof_resp.public_commitment,
        nullifier_hash=proof_resp.nullifier_hash,
        public_authorized_zone_root=proof_req.public_authorized_zone_root,
        public_china_origin_ratio=proof_req.public_china_origin_ratio,
    )
    verify_resp = zk_compliance_prover.verify_zk_proof(verify_req)
    assert verify_resp.status == "success"
    assert verify_resp.is_valid is True


# =====================================================================
# INTEGRATION TESTS: MCP PROTOCOL & MULTI-COUNTRY SCHEMA HARMONIZATION
# =====================================================================

def test_mcp_5_upgrades_tools_list_and_execution():
    from app.mcp_stdio import process_mcp_request
    # 1. tools/list check
    resp_list = process_mcp_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert resp_list is not None
    tool_names = [t["name"] for t in resp_list["result"]["tools"]]
    assert "verify_rare_earths_origin" in tool_names
    assert "verify_tungsten_origin" in tool_names
    assert "verify_black_mass_origin" in tool_names
    assert "verify_customs_clearance" in tool_names
    assert "generate_zk_compliance_proof" in tool_names

    # 2. tools/call execution for rare earths
    call_req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "verify_rare_earths_origin",
            "arguments": {
                "batch_id": "RE-MCP-001",
                "tenement_id": "MT_WELD",
                "latitude": -28.868,
                "longitude": 122.500,
                "ndpr_oxide_purity_pct": 99.65,
                "thorium_uranium_radiation_ppm": 35.0,
                "declared_china_origin_ratio": 0.0004,
                "source_country": "AUS",
            }
        }
    }
    resp_call = process_mcp_request(call_req)
    assert resp_call is not None
    assert "result" in resp_call
    import json
    content = json.loads(resp_call["result"]["content"][0]["text"])
    assert content["status"] == "success"
    assert content["audit_verdict"]["is_compliant"] is True


def test_source_country_korea_and_germany_support():
    # Korea Sangdong Tungsten
    req_kor = TungstenOriginVerifyRequest(
        batch_id="W-KOR-001",
        tenement_id="SANGDONG",
        latitude=37.150,
        longitude=128.833,
        apt_wo3_grade_pct=89.5,
        source_country=SourceCountry.KOR,
    )
    resp_kor = tungsten_pipeline.verify_tungsten_batch(req_kor)
    assert resp_kor.status == "success"
    assert resp_kor.audit_verdict.is_compliant is True
    assert resp_kor.audit_verdict.geofence_verified is True

    # Germany BASF Black Mass
    req_deu = BlackMassOriginVerifyRequest(
        batch_id="BM-DEU-001",
        facility_id="BASF_SCHWARZHEIDE",
        latitude=51.482,
        longitude=13.876,
        nickel_content_pct=21.0,
        cobalt_content_pct=9.0,
        lithium_content_pct=3.5,
        fluorine_impurity_ppm=120.0,
        bis_export_license_id="BIS-DEU-9900",
        recycled_content_ratio=0.88,
        source_country=SourceCountry.DEU,
    )
    resp_deu = black_mass_pipeline.verify_black_mass_batch(req_deu)
    assert resp_deu.status == "success"
    assert resp_deu.audit_verdict.is_compliant is True
    assert resp_deu.audit_verdict.geofence_verified is True


def test_black_mass_whitespace_bis_license_rejected():
    """Ensure whitespace-only BIS license is rejected for US origin."""
    req_us_whitespace = BlackMassOriginVerifyRequest(
        batch_id="BM-US-WHITESPACE",
        facility_id="CIRBA_SOLUTIONS_OH",
        latitude=40.417,
        longitude=-82.907,
        nickel_content_pct=20.0,
        cobalt_content_pct=10.0,
        lithium_content_pct=4.0,
        fluorine_impurity_ppm=150.0,
        bis_export_license_id="     ",  # Whitespace only bypass attempt
        recycled_content_ratio=0.90,
        source_country=SourceCountry.USA,
    )
    resp = black_mass_pipeline.verify_black_mass_batch(req_us_whitespace)
    assert resp.audit_verdict.is_compliant is False
    assert resp.audit_verdict.bis_license_verified is False


def test_logistics_bridge_retrograde_date_rejected():
    """Ensure arrival date preceding departure date is flagged as non-plausible transit."""
    req = CustomsVerificationRequest(
        tracking_number="MEDU-TIME-TRAVEL-01",
        port_of_loading="CNSHA",
        port_of_discharge="KRPUS",
        departure_date="2026-10-20",
        arrival_date="2026-10-05",  # Arrival before departure
        mineral_batch_id="CU-RETROGRADE-01",
        mine_coordinates=(-22.283, -68.900),
        gross_weight_kg=50000.0,
    )
    resp = logistics_bridge.verify_customs_clearance(req)
    assert resp.transit_plausibility_passed is False
    assert resp.customs_clearance_eligible is False


def test_zk_compliance_tampered_circuit_assertion_rejected():
    """Ensure verifier rejects proof if circuit assertion for China origin is False."""
    tampered_proof = {
        "protocol": "Groth16_Simulation_BN254",
        "circuit": "MineralsOriginAndPurityCircuit",
        "proof": {"pi_a": ["0x1", "0x2"]},
        "circuit_assertions": {
            "merkle_inclusion_satisfied": True,
            "china_origin_lt_0_1_pct_satisfied": False,  # Tampered / failed assertion
        }
    }
    verify_req = ZKProofVerifyRequest(
        zk_proof=tampered_proof,
        public_commitment="0x" + "a" * 64,
        nullifier_hash="0x" + "b" * 64,
        public_authorized_zone_root="0xroot",
        public_china_origin_ratio=0.0001,  # Low ratio claimed in public input
    )
    resp = zk_compliance_prover.verify_zk_proof(verify_req)
    assert resp.is_valid is False
    assert any("China origin ratio not proven under 0.1%" in r for r in resp.reasons)


