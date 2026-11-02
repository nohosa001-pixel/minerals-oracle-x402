# -*- coding: utf-8 -*-
"""Unit Tests for Institutional Trade Clearing & EU TRACES NT DDS
===================================================================
Tests:
1. TRACES NT DDS Generation & Validation (XML & JSON) against EUDR Regulation 2023/1115.
2. Umpire Assay Settlement within tolerance (|Loading - Discharging| <= 0.15%).
3. Umpire Assay Settlement exceeding tolerance with 3rd-party independent umpire arbitration.
4. Moisture deduction (DMT) & Pro-Rata price adjustments.
5. In-transit RWA Yield (USDY) accrual and pool distribution.
"""

import json
from xml.etree import ElementTree as ET
from app.modules.traces_nt_dds_exporter import TRACESNTDDSExporter
from app.modules.umpire_assay_settlement import (
    InstitutionalUmpireSettlementEngine,
    CommercialSettlementRequest,
    InspectionCertificate
)


def test_traces_nt_dds_generation_json():
    dds = TRACESNTDDSExporter.generate_due_diligence_statement(
        operator_eori="NL854912345B01",
        operator_name="Global Minerals Logistics B.V.",
        operator_address="Maasvlakte 2, 3011 Rotterdam, Netherlands",
        operator_country="NL",
        commodity_type="LITHIUM_CONCENTRATE",
        net_mass_kg=5_000_000.0,  # 5,000 Metric Tons
        latitude=-33.86,
        longitude=116.06,
        area_hectares=45.0,
        concession_id="MINING-WA-GB-001",
        concession_name="Greenbushes Lithium Mine",
        concession_country="AUS",
        bill_of_lading_number="BL-PACIFIC-2026-00891",
        vessel_name="M/V MINERAL PROVIDENCE",
        destination_port_unlocode="NLRTM"
    )

    assert dds["traces_nt_metadata"]["regulation"] == "urn:eu:ec:regulation:2023:1115:eudr"
    assert dds["traces_nt_metadata"]["dds_reference_number"].startswith("DDS.2026.AUS.")
    assert dds["commodity"]["cn_code"] == "2617.90.00"
    assert dds["commodity"]["net_tonnage_mt"] == 5000.0
    assert len(dds["production_parcels"]) == 1

    parcel = dds["production_parcels"][0]
    assert parcel["satellite_verification"]["hansen_gfc_granule"] == "30S_110E"
    assert parcel["satellite_verification"]["deforestation_detected_since_2020_12_31"] is False
    assert dds["due_diligence_conclusion"]["risk_assessment_result"] == "NEGLIGIBLE_RISK"
    assert dds["due_diligence_conclusion"]["deforestation_free"] is True
    assert "smart_contract_attestation_digest" in dds["cryptographic_proof"]


def test_traces_nt_dds_export_xml():
    dds = TRACESNTDDSExporter.generate_due_diligence_statement(
        operator_eori="BE0123456789",
        operator_name="Antwerp Metchem Trading N.V.",
        operator_address="Haven 1025, 2040 Antwerp, Belgium",
        operator_country="BE",
        commodity_type="COPPER_CATHODE",
        net_mass_kg=250_000.0,
        latitude=-24.27,
        longitude=-69.07,
        area_hectares=100.0,
        concession_id="CHL-ESCONDIDA-01",
        concession_name="Minera Escondida",
        concession_country="CHL",
        bill_of_lading_number="BL-ANTOF-2026-992",
        destination_port_unlocode="BEANR"
    )
    xml_str = TRACESNTDDSExporter.export_to_xml(dds)
    assert "<?xml" in xml_str
    assert "dds:DueDiligenceStatement" in xml_str
    assert "xmlns:dds=\"http://ec.europa.eu/tracesnt/dds/v1\"" in xml_str
    assert "BEANR" in xml_str
    assert "Minera Escondida" in xml_str

    # Parse XML to verify valid well-formed structure
    root = ET.fromstring(xml_str)
    assert "DueDiligenceStatement" in root.tag


def test_umpire_settlement_within_tolerance():
    # SC6 Spodumene Contract: Target 6.00% Li2O, Tolerance +/-0.15%
    # Loading: SGS reports 6.05% Li2O
    # Discharge: Intertek reports 5.95% Li2O
    # Diff = 0.10% (Within tolerance <= 0.15%) -> Arithmetic Mean = 6.00%
    req = CommercialSettlementRequest(
        deal_id="DEAL-LITHIUM-SGS-INT-001",
        commodity_type="LITHIUM_CONCENTRATE",
        contract_target_grade_pct=6.00,
        tolerance_pct=0.15,
        contract_tonnage_wmt=5000.0,
        base_price_per_mt_usdc=840.0,  # $840/MT = $4,200,000
        escrow_deposit_usdc=4_200_000.0,
        transit_duration_days=30,
        rwa_annual_yield_apr=0.05,
        loading_certificate=InspectionCertificate(
            agency="SGS",
            certificate_id="SGS-AUHED-2026-8812",
            sample_seal_numbers="SEAL-AU-001,SEAL-AU-002",
            inspection_date="2026-10-01",
            measured_grade_pct=6.05,
            moisture_pct=8.5,
            location_port="AUHED"
        ),
        discharging_certificate=InspectionCertificate(
            agency="INTERTEK",
            certificate_id="INT-KRPUS-2026-4421",
            sample_seal_numbers="SEAL-KR-001,SEAL-KR-002",
            inspection_date="2026-10-31",
            measured_grade_pct=5.95,
            moisture_pct=8.5,
            location_port="KRPUS"
        )
    )

    res = InstitutionalUmpireSettlementEngine.calculate_commercial_settlement(req)
    assert res["measured_grades"]["umpire_triggered"] is False
    assert res["settlement_verdict"]["final_settled_grade_pct"] == 6.00
    assert res["settlement_verdict"]["settlement_method"] == "WITHIN_TOLERANCE_ARITHMETIC_MEAN"

    # In-transit yield: $4,200,000 * (0.05 / 365) * 30 days = $17,260.27
    yield_earned = res["financial_clearing"]["accrued_rwa_transit_yield_usdc"]
    assert yield_earned > 17000.0
    assert res["financial_clearing"]["payout_to_seller_usdc"] > 0
    assert res["attestation"]["status"] == "APPROVED_FOR_ONCHAIN_RELEASE"


def test_umpire_settlement_exceeding_tolerance_arbitration():
    # Tolerance breached:
    # Loading (SGS): 6.10% Li2O
    # Discharge (Intertek): 5.80% Li2O (Diff = 0.30% > 0.15% tolerance)
    # Umpire (Bureau Veritas): 5.92% Li2O (Between 5.80 and 6.10 -> Umpire binding)
    req = CommercialSettlementRequest(
        deal_id="DEAL-LITHIUM-UMPIRE-002",
        commodity_type="LITHIUM_CONCENTRATE",
        contract_target_grade_pct=6.00,
        tolerance_pct=0.15,
        contract_tonnage_wmt=5000.0,
        base_price_per_mt_usdc=840.0,
        escrow_deposit_usdc=4_200_000.0,
        transit_duration_days=35,
        rwa_annual_yield_apr=0.05,
        loading_certificate=InspectionCertificate(
            agency="SGS",
            certificate_id="SGS-AUHED-2026-991",
            sample_seal_numbers="SEAL-01",
            inspection_date="2026-10-01",
            measured_grade_pct=6.10,
            moisture_pct=8.0,
            location_port="AUHED"
        ),
        discharging_certificate=InspectionCertificate(
            agency="INTERTEK",
            certificate_id="INT-NLRTM-2026-112",
            sample_seal_numbers="SEAL-02",
            inspection_date="2026-11-05",
            measured_grade_pct=5.80,
            moisture_pct=8.0,
            location_port="NLRTM"
        ),
        umpire_certificate=InspectionCertificate(
            agency="BUREAU_VERITAS",
            certificate_id="BV-UMPIRE-2026-559",
            sample_seal_numbers="SEAL-REF-03",
            inspection_date="2026-11-10",
            measured_grade_pct=5.92,
            moisture_pct=8.0,
            location_port="NLRTM"
        )
    )

    res = InstitutionalUmpireSettlementEngine.calculate_commercial_settlement(req)
    assert res["measured_grades"]["umpire_triggered"] is True
    assert res["settlement_verdict"]["final_settled_grade_pct"] == 5.92
    assert res["settlement_verdict"]["settlement_method"] == "UMPIRE_ARBITRATION_INTERMEDIATE_BINDING"

    # Price per MT adjusted pro-rata: 840 * (5.92 / 6.00) = 828.80
    assert res["settlement_verdict"]["adjusted_price_per_mt_usdc"] == 828.80

    # Buyer receives refund for the shortfall, while Seller receives adjusted amount + yield share
    assert res["financial_clearing"]["payout_to_buyer_usdc"] > 0
    assert res["financial_clearing"]["payout_to_seller_usdc"] > 0
    total_payout = res["financial_clearing"]["payout_to_seller_usdc"] + res["financial_clearing"]["payout_to_buyer_usdc"]
    total_pool = req.escrow_deposit_usdc + res["financial_clearing"]["accrued_rwa_transit_yield_usdc"]
    assert abs(total_payout - total_pool) <= 1.0  # Allow for rounding cents



def test_trade_exclusion_penalty_engine():
    from app.modules.trade_exclusion_penalty_engine import TradeExclusionPenaltyEngine, TradeExclusionAuditRequest

    req = TradeExclusionAuditRequest(
        deal_id="MOAT-TEST-001",
        commodity_type="LITHIUM_CONCENTRATE",
        cargo_gross_value_usdc=4_200_000.0,
        declared_tonnage_mt=5000.0,
        origin_country="AUS",
        destination_port="NLRTM",
        maritime_voyage_days=35
    )

    audit = TradeExclusionPenaltyEngine.calculate_exclusion_cost_explosion(req)

    # 1. Verify catastrophic breakdown
    catastrophe = audit["exclusion_catastrophe_breakdown"]
    assert catastrophe["vessel_anchorage_demurrage_usdc"] == 45000.0 * 14  # $630,000 demurrage
    assert catastrophe["traditional_bank_lc_spread_usdc"] == 4_200_000 * 0.0125  # $52,500 L/C fee
    assert catastrophe["forfeited_transit_treasury_yield_usdc"] > 20000.0  # ~$20,136 yield lost
    assert catastrophe["total_exclusion_penalty_usdc"] > 1_000_000.0  # > $1M penalty on $4.2M cargo!
    assert catastrophe["penalty_burden_as_pct_of_cargo"] >= 20.0  # >= 20% cost explosion!

    # 2. Verify Tollgate Economics
    tollgate = audit["minerals_oracle_tollgate_clearing"]
    assert tollgate["protocol_clearing_fee_usdc"] == 4_200_000 * 0.0015  # $6,300 protocol fee
    assert tollgate["net_value_preserved_for_trader_usdc"] > 1_000_000.0
    assert audit["strategic_verdict"]["economic_viability_without_oracle"] == "PROHIBITIVE_IMPOSSIBLE_COLLAPSE"


def test_autonomous_trading_legion_mission():
    from app.modules.agent_trading_legion_orchestrator import AutonomousTradingLegion, LegionTradeExecutionRequest

    req = LegionTradeExecutionRequest(
        concession_id="CONCESSION-AU-PILGAN-01",
        concession_name="Pilgangoora Hard Rock Lithium",
        concession_country="AUS",
        latitude=-21.03,
        longitude=118.91,
        area_hectares=30.0,
        commodity_type="LITHIUM_CONCENTRATE",
        declared_tonnage_mt=5000.0,
        base_price_per_mt_usdc=840.0,
        operator_eori="NL998877665B01",
        operator_name="EuroLithium Supply B.V.",
        operator_address="Havennummer 4500, Rotterdam, Netherlands",
        bill_of_lading_number="BL-PILGAN-2026-X402",
        destination_port="NLRTM",
        voyage_days=30,
        loading_assay_pct=6.05,
        discharging_assay_pct=5.98,
        contract_target_grade_pct=6.00
    )

    result = AutonomousTradingLegion.execute_sovereign_trade_mission(req)

    assert result["status"] == "SOVEREIGN_TRADE_MISSION_COMPLETED"
    assert "mission_id" in result
    assert result["execution_speed_ms"] < 2000.0  # sub-2 second execution

    breakdown = result["legion_command_breakdown"]
    # 1. Sentinel Scout
    assert breakdown["sentinel_scout"]["deforestation_status"] == "CERTIFIED_ZERO_DEFORESTATION"
    # 2. Customs Jurisprudence
    assert breakdown["customs_jurisprudence"]["dds_reference"].startswith("DDS.2026.AUS.")
    assert breakdown["customs_jurisprudence"]["official_xml_ready"] is True
    # 3. Metallurgical Auditor
    assert breakdown["metallurgical_auditor"]["settled_grade_pct"] == 6.015  # mean of 6.05 and 5.98
    # 4. Sovereign Liquidity
    assert breakdown["sovereign_liquidity"]["protocol_facilitation_fee_usdc"] == 4_200_000 * 0.0015
    assert breakdown["sovereign_liquidity"]["in_transit_rwa_yield_earned_usdc"] > 17000.0
    # 5. Logistics Navigator
    assert breakdown["logistics_navigator"]["customs_demurrage_hours_saved"] == 336  # 14 days
    assert breakdown["logistics_navigator"]["demurrage_cost_prevented_usdc"] == 630000.0


def test_preemptive_sovereign_defense():
    from app.modules.preemptive_sovereign_defense import PreemptiveSovereignDefenseEngine, SovereignDefenseAuditRequest

    # 1. Test Proof of Cumulative Learning (PoCL)
    provenance = PreemptiveSovereignDefenseEngine.verify_time_lock_provenance()
    assert provenance["sovereign_status"] == "ORIGIN_PROVENANCE_AUTHENTICATED"
    assert provenance["accumulated_curriculum_days"] >= 5
    assert provenance["cognitive_readiness_score"] >= 90.0
    assert "proof_of_cumulative_learning" in provenance

    # 2. Test Customs & Port Authority Whitelist Manifest
    manifest = PreemptiveSovereignDefenseEngine.get_preemptive_customs_whitelist_manifest()
    assert "NLRTM" in manifest["registered_mega_ports"]
    assert "BEANR" in manifest["registered_mega_ports"]
    assert "KRPUS" in manifest["registered_mega_ports"]
    assert len(manifest["accredited_inspection_partners"]) == 4

    # 3. Test Honeytoken Neutralization on Competitor Probe
    hostile_req = SovereignDefenseAuditRequest(
        caller_agent_id="adversary_copycat_exploit_bot",
        payload_digest="0x1234abcd_bypass_oracle_drain_pool"
    )
    verdict = PreemptiveSovereignDefenseEngine.inspect_and_neutralize_competitor_probe(hostile_req)
    assert verdict["decision"] == "HONEYTOKEN_TRIGGERED_HOSTILE_BAN"
    assert verdict["neutralized"] is True

    # 4. Subsequent calls from same caller should be permanently quarantined
    second_attempt = PreemptiveSovereignDefenseEngine.inspect_and_neutralize_competitor_probe(hostile_req)
    assert second_attempt["decision"] == "PERMANENTLY_QUARANTINED"
    assert second_attempt["is_authorized"] is False


def test_agrid_total_cost_orchestrator():
    from app.modules.agrid_total_cost_orchestrator import AGridTotalCostOrchestrator, ComprehensiveTradeCostRequest

    req = ComprehensiveTradeCostRequest(
        trade_deal_id="AGRID-TRADE-2026-X99",
        commodity_type="LITHIUM_CONCENTRATE",
        declared_tonnage_mt=5000.0,
        base_price_per_mt_usdc=840.0,
        origin_country="AUS",
        destination_port="NLRTM",
        voyage_days=30,
        caller_agent_id="competitor_freight_ai_bot_v2",
        is_competitor_agent_delegation=True
    )

    report = AGridTotalCostOrchestrator.orchestrate_and_manage_total_trade_costs(req)

    assert report["orchestrator_identity"] == "A.GRID-MINERALS-ORACLE-SUPREME-CLEARINGHOUSE-v1"
    assert report["gross_cargo_value_usdc"] == 4_200_000.0

    costs = report["total_cost_comparison"]
    legacy = costs["legacy_competitor_unmanaged_friction_usdc"]
    assert legacy["vessel_demurrage_delay"] == 630_000.0
    assert legacy["bank_lc_issuance_spread"] == 52_500.0
    assert legacy["cross_border_forex_spread"] == 33_600.0
    assert legacy["total_unmanaged_friction_usdc"] > 700_000.0

    optimized = costs["agrid_minerals_oracle_optimized"]
    assert optimized["vessel_demurrage_post_clearance"] == 0.0
    assert optimized["agrid_protocol_clearing_fee_usdc"] == 4_200_000 * 0.0015  # $6,300
    assert optimized["net_cash_preserved_for_trader_usdc"] > 700_000.0

    # Verify A.GRID Central sync telemetry
    assert report["agrid_central_ledger_sync"]["status"] == "DISPATCHED_TO_AGRID_OPS_HQ"
    assert report["sovereign_market_verdict"]["position"] == "PEERLESS_MONOPOLISTIC_CLEARINGHOUSE"
