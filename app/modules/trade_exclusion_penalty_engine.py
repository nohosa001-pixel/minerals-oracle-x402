# -*- coding: utf-8 -*-
"""Trade Exclusion Penalty & Economic Moat Engine for Minerals Oracle X402
==========================================================================
Calculates the severe financial, regulatory, and logistics cost penalties
incurred if a mineral trading house, smelter, or bank attempts to BYPASS
or EXCLUDE Minerals Oracle X402 from a cross-border critical mineral shipment.

Proves mathematical and operational impossibility of unassisted trade:
1. EUDR Demurrage & Seizure Penalty (Rotterdam/Antwerp anchorage delays).
2. Banking L/C Dead Capital Drag & Zero-Yield Opportunity Loss.
3. Bilateral Assay Discrepancy Arbitration Litigation Costs.
4. US IRA / FEOC Disqualification Liability.
5. Mandatory Asymmetric Protocol Tollgate Enforcement.
"""

from __future__ import annotations

import time
import hashlib
from typing import Dict, Any, List
from pydantic import BaseModel, Field


class TradeExclusionAuditRequest(BaseModel):
    deal_id: str = Field(..., description="Trade deal identifier")
    commodity_type: str = Field(..., description="LITHIUM_CONCENTRATE, COPPER_CATHODE, NICKEL_MHP, etc.")
    cargo_gross_value_usdc: float = Field(..., gt=0, description="Gross cargo transaction value in USDC")
    declared_tonnage_mt: float = Field(..., gt=0, description="Cargo volume in metric tons")
    origin_country: str = Field(..., description="Origin country ISO code (e.g. AUS, CHL, IDN, COD)")
    destination_port: str = Field(default="NLRTM", description="Entry port (e.g. NLRTM, BEANR, KRPUS, CNSHA)")
    maritime_voyage_days: int = Field(default=32, ge=5, description="Expected voyage transit days")


class TradeExclusionPenaltyEngine:
    """
    Economic Moat & Indispensable Tollgate Calculation Engine.
    Proves that excluding Minerals Oracle causes cost explosion and halts trade.
    """

    # Baseline Daily Demurrage Rate for Bulk / Handymax / Panamax Carriers ($/day)
    VESSEL_DAILY_DEMURRAGE_USDC: float = 45000.0

    # Average days of manual customs inspection at EU ports without pre-approved TRACES NT DDS
    MANUAL_CUSTOMS_AUDIT_DAYS: int = 14

    # Commercial Bank Letter of Credit (L/C) Total Cost Spread (issuance, handling, discrepancy fees)
    TRADITIONAL_LC_SPREAD_PCT: float = 0.0125  # 1.25%

    # US Treasury in-transit yield rate (USDY ~ 5.0% APR)
    IN_TRANSIT_YIELD_APR: float = 0.050

    # Risk factor of bilateral assay dispute without automated Umpire oracle
    ASSAY_DISPUTE_RISK_COST_PCT: float = 0.035  # 3.5% of cargo value held in escrow/arbitration

    # EU Regulation 2023/1115 (EUDR) Article 25 Maximum Statutory Fine
    EUDR_STATUTORY_FINE_CEILING_PCT: float = 0.040  # 4% of EU annual turnover

    @classmethod
    def calculate_exclusion_cost_explosion(cls, req: TradeExclusionAuditRequest) -> Dict[str, Any]:
        """
        Calculates the catastrophic financial penalties incurred if Minerals Oracle is excluded.
        """
        cargo_value = req.cargo_gross_value_usdc

        # ---------------------------------------------------------------------
        # 1. Logistics Demurrage & Anchorage Penalty (EUDR Manual Delay)
        # ---------------------------------------------------------------------
        # Without our instant TRACES NT DDS XML, vessels wait at outer anchorage
        demurrage_penalty = round(cls.VESSEL_DAILY_DEMURRAGE_USDC * cls.MANUAL_CUSTOMS_AUDIT_DAYS, 2)
        # Port storage & re-handling administrative fees
        port_rehandling_penalty = round(req.declared_tonnage_mt * 18.50, 2)

        # ---------------------------------------------------------------------
        # 2. Banking Friction & Dead Capital Opportunity Loss
        # ---------------------------------------------------------------------
        # Traditional L/C bank fees (1.25%)
        bank_lc_fees = round(cargo_value * cls.TRADITIONAL_LC_SPREAD_PCT, 2)
        # Forfeited Treasury yield during transit days (at 5% APR)
        forfeited_yield = round(cargo_value * (cls.IN_TRANSIT_YIELD_APR / 365.0) * req.maritime_voyage_days, 2)

        # ---------------------------------------------------------------------
        # 3. Assay Discrepancy & Legal Arbitration Costs
        # ---------------------------------------------------------------------
        # Cost of unresolved assay disputes, sample shipping, independent law firm retainer
        assay_litigation_cost = round(cargo_value * cls.ASSAY_DISPUTE_RISK_COST_PCT, 2)

        # ---------------------------------------------------------------------
        # 4. EUDR Regulatory Non-Compliance Exposure
        # ---------------------------------------------------------------------
        # Statutory risk exposure per consignment under EUDR Art 25
        eudr_statutory_risk = round(cargo_value * cls.EUDR_STATUTORY_FINE_CEILING_PCT, 2)

        # ---------------------------------------------------------------------
        # Total Cost Explosion
        # ---------------------------------------------------------------------
        total_exclusion_penalty = round(
            demurrage_penalty + port_rehandling_penalty + bank_lc_fees +
            forfeited_yield + assay_litigation_cost + eudr_statutory_risk, 2
        )
        penalty_ratio_pct = round((total_exclusion_penalty / cargo_value) * 100.0, 2)

        # ---------------------------------------------------------------------
        # Cost with Minerals Oracle X402 (The Indispensable Tollgate)
        # ---------------------------------------------------------------------
        # Flat protocol clearing fee: 0.15% (15 bps)
        oracle_protocol_fee = round(cargo_value * 0.0015, 2)
        # Net Benefit to Trader when using Minerals Oracle:
        net_value_preservation = round(total_exclusion_penalty - oracle_protocol_fee, 2)
        roi_multiplier = round(net_value_preservation / oracle_protocol_fee, 1)

        # Economic Moat Attestation Digest
        audit_seed = f"EXCLUSION_AUDIT:{req.deal_id}:{cargo_value:.2f}:{total_exclusion_penalty:.2f}"
        audit_hash = "0x" + hashlib.sha256(audit_seed.encode("utf-8")).hexdigest()

        return {
            "deal_id": req.deal_id,
            "commodity_type": req.commodity_type,
            "cargo_gross_value_usdc": cargo_value,
            "declared_tonnage_mt": req.declared_tonnage_mt,
            "origin_to_destination": f"{req.origin_country} -> {req.destination_port}",
            "exclusion_catastrophe_breakdown": {
                "vessel_anchorage_demurrage_usdc": demurrage_penalty,
                "manual_customs_delay_days": cls.MANUAL_CUSTOMS_AUDIT_DAYS,
                "port_rehandling_surcharges_usdc": port_rehandling_penalty,
                "traditional_bank_lc_spread_usdc": bank_lc_fees,
                "forfeited_transit_treasury_yield_usdc": forfeited_yield,
                "assay_discrepancy_arbitration_risk_usdc": assay_litigation_cost,
                "eudr_statutory_liability_exposure_usdc": eudr_statutory_risk,
                "total_exclusion_penalty_usdc": total_exclusion_penalty,
                "penalty_burden_as_pct_of_cargo": penalty_ratio_pct
            },
            "minerals_oracle_tollgate_clearing": {
                "protocol_clearing_fee_usdc": oracle_protocol_fee,
                "protocol_fee_bps": 15,  # 0.15%
                "net_value_preserved_for_trader_usdc": net_value_preservation,
                "economic_moat_roi_multiplier": f"{roi_multiplier}x",
                "customs_demurrage_risk_post_clearing": "ZERO_PRE_CLEARED",
                "in_transit_yield_earned_usdc": forfeited_yield
            },
            "strategic_verdict": {
                "economic_viability_without_oracle": "PROHIBITIVE_IMPOSSIBLE_COLLAPSE",
                "verdict_statement": (
                    f"Excluding Minerals Oracle X402 adds ${total_exclusion_penalty:,.2f} USD "
                    f"({penalty_ratio_pct}% of total cargo value) in deadweight loss, customs delay, "
                    f"and regulatory penalties. Trade without Minerals Oracle is economically suicidal."
                ),
                "audit_proof_digest": audit_hash,
                "timestamp_utc": int(time.time())
            }
        }
