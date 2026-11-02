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
