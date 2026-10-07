"""
End-to-End Full System Harmony & Interoperability Orchestration Test Suite.
Validates that all micro-services, new and existing pipelines, smart contracts,
and multi-chain bridges work together in complete, unified harmony.

Lifecycle Scenario:
1. Upstream Mine & Scrap Provenance (NdPr Rare Earths, Tungsten APT, Recycled Black Mass)
2. Zero-Knowledge Privacy Preservation (Blinded Geocoordinates & Cost, Public ZK Verification)
3. Maritime Logistics Bridge & Port Customs Clearance (B/L Anchor, Spatial Analysis, Green Bundle)
4. Regulatory Carbon Economics & Verifiable Credentials (CBAM Savings, W3C Battery Passport VC)
5. Bilateral A2A Deal Lifecycle & Dynamic Escrow Multi-Party Settlement Alignment
6. Multi-Chain (Solana + EVM L2s) & Model Context Protocol (MCP) Unified Telemetry
"""

import json
import time
import hashlib
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import (
    SourceCountry,
    MineralType,
    RareEarthsOriginVerifyRequest,
    TungstenOriginVerifyRequest,
    BlackMassOriginVerifyRequest,
    ZKComplianceProofRequest,
    ZKProofVerifyRequest,
    CustomsVerificationRequest,
    CBAMMarkupPenaltyRequest,
    EUIndustrialActVerifyRequest,
    BatteryPassportVCRequest,
    TradeDealSpec,
    TradeDealProposeRequest,
    TradeDealDualSignRequest,
)
from app.rare_earths_pipeline import rare_earths_pipeline
from app.tungsten_pipeline import tungsten_pipeline
from app.black_mass_pipeline import black_mass_pipeline
from app.zk_compliance_prover import zk_compliance_prover
from app.logistics_bridge import logistics_bridge
from app.regulatory_advanced_engine import regulatory_advanced_engine
from app.a2a_deal_engine import get_a2a_deal_engine
from app.mcp_stdio import process_mcp_request
from app.multi_chain import list_supported_chains, get_chain_config

client = TestClient(app)
a2a_deal_engine = get_a2a_deal_engine()


def test_end_to_end_full_system_harmony():
    print("\n[HARMONY STEP 1] Upstream Mineral & Scrap Provenance Ingestion...")
    # 1A. Rare Earths (Australia Mt Weld)
    re_req = RareEarthsOriginVerifyRequest(
        batch_id="HARMONY-RE-001",
        tenement_id="MT_WELD",
        latitude=-28.868,
        longitude=122.500,
        ndpr_oxide_purity_pct=99.65,
        thorium_uranium_radiation_ppm=35.0,
        declared_china_origin_ratio=0.0003,  # 0.03% < 0.1% MOFCOM threshold
        source_country=SourceCountry.AUS,
    )
    re_res = rare_earths_pipeline.verify_rare_earths_batch(re_req)
    assert re_res.status == "success"
    assert re_res.audit_verdict.is_compliant is True
    re_proof_hash = re_res.proof_hash

    # 1B. Tungsten (South Korea Sangdong Mine)
    w_req = TungstenOriginVerifyRequest(
        batch_id="HARMONY-W-001",
        tenement_id="SANGDONG",
        latitude=37.150,
        longitude=128.833,
        apt_wo3_grade_pct=89.5,
        dodd_frank_conflict_free=True,
        ndaa_defense_procurement_eligible=True,
        source_country=SourceCountry.KOR,
    )
    w_res = tungsten_pipeline.verify_tungsten_batch(w_req)
    assert w_res.status == "success"
    assert w_res.audit_verdict.is_compliant is True
    w_proof_hash = w_res.proof_hash

    # 1C. Recycled Battery Black Mass (USA Nevada ABTC)
    bm_req = BlackMassOriginVerifyRequest(
        batch_id="HARMONY-BM-001",
        facility_id="ABTC_NEVADA",
        latitude=39.608,
        longitude=-119.251,
        nickel_content_pct=22.5,
        cobalt_content_pct=8.5,
        lithium_content_pct=4.2,
        fluorine_impurity_ppm=140.0,
        bis_export_license_id="BIS-HARMONY-2026",
        recycled_content_ratio=0.91,
        source_country=SourceCountry.USA,
    )
    bm_res = black_mass_pipeline.verify_black_mass_batch(bm_req)
    assert bm_res.status == "success"
    assert bm_res.audit_verdict.is_compliant is True
    bm_proof_hash = bm_res.proof_hash

    # -------------------------------------------------------------
    print("[HARMONY STEP 2] Privacy-Preserving Zero-Knowledge Shielding...")
    # Shield extraction coordinates & confidential unit costs
    zk_gen_req = ZKComplianceProofRequest(
        batch_id="HARMONY-RE-001",
        mineral_type="RARE_EARTHS_NDPR",
        secret_mine_latitude=-28.868,
        secret_mine_longitude=122.500,
        secret_supplier_id="SECRET-LYNAS-MTWELD-CORP",
        secret_unit_cost_usd=92500.0,
        public_authorized_zone_root="0x" + hashlib.sha256(b"WA_AUSTRALIA_MINING_PERMIT_ZONE").hexdigest(),
        public_china_origin_ratio=0.0003,
        public_carbon_intensity_kg_co2=48.5,
    )
    zk_gen_res = zk_compliance_prover.generate_zk_compliance_proof(zk_gen_req)
    assert zk_gen_res.status == "success"
    assert zk_gen_res.is_valid_zero_knowledge_proof is True

    # Public Auditor verifier verifies proof with zero confidential data leak
    zk_ver_req = ZKProofVerifyRequest(
        zk_proof=zk_gen_res.zk_proof,
        public_commitment=zk_gen_res.public_commitment,
        nullifier_hash=zk_gen_res.nullifier_hash,
        public_authorized_zone_root=zk_gen_req.public_authorized_zone_root,
        public_china_origin_ratio=zk_gen_req.public_china_origin_ratio,
    )
    zk_ver_res = zk_compliance_prover.verify_zk_proof(zk_ver_req)
    assert zk_ver_res.status == "success"
    assert zk_ver_res.is_valid is True

    # -------------------------------------------------------------
    print("[HARMONY STEP 3] Physical Logistics Ocean Bridge & Customs Bundle...")
    logistics_req = CustomsVerificationRequest(
        tracking_type="BOL",
        tracking_number="MSCU-HARMONY-9922",
        carrier_code="MSCU",
        port_of_loading="KRPUS",   # Busan Port
        port_of_discharge="NLRTM", # Rotterdam Port
        departure_date="2026-09-01",
        arrival_date="2026-09-26",
        mineral_batch_id="HARMONY-W-001",
        mine_coordinates=[37.150, 128.833], # Sangdong Mine
        gross_weight_kg=50000.0,
    )
    logistics_res = logistics_bridge.verify_customs_clearance(logistics_req)
    assert logistics_res.status == "success"
    assert logistics_res.customs_clearance_eligible is True
    assert logistics_res.transit_plausibility_passed is True
    logistics_proof_hash = logistics_res.proof_hash

    # -------------------------------------------------------------
    print("[HARMONY STEP 4] Downstream Regulatory Carbon & Battery Passport VC...")
    # 4A. CBAM Markup Penalty and Savings
    cbam_req = CBAMMarkupPenaltyRequest(
        import_year=2026,
        product_category="ALUMINIUM",
        tonnage=250.0,
        default_embedded_emissions_tco2_per_ton=3.1,
        verified_scope1_2_emissions_tco2_per_ton=1.8,
        eu_allowance_price_eur=82.50,
    )
    cbam_res = regulatory_advanced_engine.calculate_cbam_markup_penalty(cbam_req)
    assert cbam_res.markup_penalty_rate == 0.0
    assert cbam_res.is_verified_exempt is True
    assert cbam_res.savings_with_verified_report_eur > 0.0

    # 4B. W3C Digital Product Passport (DPP) Verifiable Credential
    vc_req = BatteryPassportVCRequest(
        battery_id="urn:uuid:pack-harmony-811-001",
        chemistry="NMC811",
        rated_capacity_kwh=96.0,
        recycled_cobalt_pct=18.0,
        recycled_lithium_pct=10.0,
        recycled_nickel_pct=22.0,
        carbon_footprint_kg_co2_per_kwh=49.2,
        provenance_proof_hash=re_proof_hash,
    )
    vc_res = regulatory_advanced_engine.generate_battery_passport_vc(vc_req)
    assert vc_res.status == "success"
    assert "proof" in vc_res.vc_token
    assert vc_res.signature.startswith("0x")
    assert vc_res.qr_code_payload_uri.startswith("https://")

    # -------------------------------------------------------------
    print("[HARMONY STEP 5] Bilateral A2A Deal Negotiation & Dynamic Escrow Alignment...")
    buyer_addr = "0x1111111111111111111111111111111111111111"
    seller_addr = "0x2222222222222222222222222222222222222222"
    deal_spec = TradeDealSpec(
        deal_id="DEAL-HARMONY-2026-001",
        commodity="TUNGSTEN_APT",
        volume_tons=50.0,
        unit_price_usd_per_ton=34000.0,
        total_deal_value_usd=1700000.0,
        origin_country="KOR",
        destination_country="EU",
        feoc_cleared=True,
        mass_balance_cleared=True,
        ebl_document_id=logistics_proof_hash,
        buyer_agent_address=buyer_addr,
        seller_agent_address=seller_addr,
        projected_savings_usd=15000.0,
        created_at_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )
    # Propose Deal
    seller_sig = "0x" + "a" * 130
    prop_req = TradeDealProposeRequest(spec=deal_spec, seller_signature=seller_sig)
    prop_res = a2a_deal_engine.propose_deal(prop_req)
    assert prop_res.deal_id == "DEAL-HARMONY-2026-001"
    assert prop_res.status == "PROPOSED"

    # Buyer Countersigns Deal
    buyer_sig = "0x" + "b" * 130
    dual_req = TradeDealDualSignRequest(
        deal_id="DEAL-HARMONY-2026-001",
        buyer_signature=buyer_sig,
        buyer_agent_address=buyer_addr,
    )
    dual_res = a2a_deal_engine.dual_sign_deal(dual_req)
    assert dual_res.status == "DUAL_SIGNED_CONFIRMED"
    assert dual_res.oracle_attestation_signature.startswith("0x")

    # Build Escrow Calldata for DynamicTradeEscrow.sol on Polygon
    calldata_res = a2a_deal_engine.build_escrow_deposit_calldata(
        deal_id="DEAL-HARMONY-2026-001",
        chain_name="polygon",
    )
    assert "calldata" in calldata_res
    assert calldata_res["calldata"].startswith("0x")
    assert calldata_res["escrow_contract_address"].startswith("0x")

    # -------------------------------------------------------------
    print("[HARMONY STEP 6] Multi-Chain & Model Context Protocol (MCP) Unified Execution...")
    # MCP tools/list discovers complete 37-tool suite
    mcp_list_resp = process_mcp_request({"jsonrpc": "2.0", "id": "mcp-h1", "method": "tools/list"})
    assert mcp_list_resp is not None
    mcp_tools = {t["name"]: t for t in mcp_list_resp["result"]["tools"]}
    assert len(mcp_tools) == 37
    assert "verify_rare_earths_origin" in mcp_tools
    assert "verify_tungsten_origin" in mcp_tools
    assert "verify_black_mass_origin" in mcp_tools
    assert "verify_customs_clearance" in mcp_tools
    assert "generate_zk_compliance_proof" in mcp_tools

    # Multi-Chain Registry has strict parity across Polygon (137), Base (8453), Arbitrum (42161), and Solana (501)
    chains = list_supported_chains()
    assert len(chains) == 4
    chain_names = {c["chain_name"] for c in chains}
    assert chain_names == {"polygon", "base", "arbitrum", "solana"}

    print("\n>>> FULL SYSTEM HARMONY ORCHESTRATION COMPLETED WITH 100% SUCCESS! <<<")
