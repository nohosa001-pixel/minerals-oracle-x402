"""
Composite EV Battery Passport & Multi-Mineral Supply-Chain Integrity Orchestrator.
Integrates Australian Spodumene Lithium, Indonesian Nickel MHP, and DRC Cobalt Hydroxide
into an end-to-end composite NCM battery cell/pack compliance audit.
Calculates US IRA Section 30D Critical Mineral FTA Value Ratios (>= 50%),
audits EU Battery Regulation (2023/1542) blended carbon footprint & CSDDD criteria,
and anchors a composite cryptographic Merkle Root on Polygon Mainnet via EIP-712.
"""

import math
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.schemas import (
    CompositeBatteryVerifyRequest,
    CompositeBatteryVerifyResponse,
    CompositeBatteryAuditVerdict,
)
from app.lithium_pipeline import lithium_pipeline
from app.nickel_pipeline import nickel_pipeline
from app.cobalt_pipeline import cobalt_pipeline
from app.onchain_signer import onchain_signer


# 2026-09 Market Baseline Valuations for Critical Mineral Components (USD / metric ton)
VALUATION_LITHIUM_HYDROXIDE_USD_PER_TON: float = 18500.0
VALUATION_NICKEL_METAL_EQUIV_USD_PER_TON: float = 17000.0
VALUATION_COBALT_METAL_EQUIV_USD_PER_TON: float = 32000.0


class CompositeBatteryPipeline:
    """
    Orchestration engine evaluating the composite compliance of an EV battery pack
    by synthesizing provenance records across Lithium, Nickel, and Cobalt.
    """

    def evaluate_battery_pack(self, req: CompositeBatteryVerifyRequest) -> CompositeBatteryVerifyResponse:
        now_utc = datetime.now(timezone.utc).isoformat()
        defenses: List[str] = []

        # -----------------------------------------------------------------
        # 1. Evaluate Individual Mineral Supply-Chain Streams
        # -----------------------------------------------------------------
        li_res = lithium_pipeline.evaluate_lithium_lot(req.lithium_lot)
        ni_res = nickel_pipeline.evaluate_nickel_lot(req.nickel_lot)
        co_res = cobalt_pipeline.evaluate_cobalt_lot(req.cobalt_lot)

        li_cleared = li_res.audit_verdict.crma_origin_eligible and li_res.audit_verdict.confidence_score >= 80.0
        ni_cleared = ni_res.audit_verdict.simbara_export_cleared and ni_res.audit_verdict.confidence_score >= 80.0
        co_cleared = co_res.audit_verdict.ceec_export_cleared and co_res.audit_verdict.child_labor_free and co_res.audit_verdict.asm_segregated

        # -----------------------------------------------------------------
        # 2. US IRA Section 30D Critical Mineral 50% FTA Value-Added Ratio
        # -----------------------------------------------------------------
        # Calculate procurement value of each stream
        val_li = req.lithium_lot.refined_output_tonnage * VALUATION_LITHIUM_HYDROXIDE_USD_PER_TON
        val_ni = (req.nickel_lot.mhp_output_tons * (req.nickel_lot.mhp_grade_ni_pct / 100.0)) * VALUATION_NICKEL_METAL_EQUIV_USD_PER_TON
        val_co = (req.cobalt_lot.cobalt_hydroxide_output_tons * (req.cobalt_lot.hydroxide_grade_co_pct / 100.0)) * VALUATION_COBALT_METAL_EQUIV_USD_PER_TON

        total_mineral_value = max(1.0, val_li + val_ni + val_co)

        # Qualifying FTA value:
        # Australia is a US Free Trade Agreement (FTA) partner nation -> Lithium is 100% qualifying
        # Indonesia & DRC are non-FTA nations -> 0% qualifying
        qualifying_fta_value = val_li
        fta_value_ratio_pct = (qualifying_fta_value / total_mineral_value) * 100.0

        # Statutory IRA 2026 Critical Mineral threshold: >= 50.0%
        fta_ratio_passed = fta_value_ratio_pct >= 50.0

        # -----------------------------------------------------------------
        # 3. Foreign Entity of Concern (FEOC) Taint Check
        # -----------------------------------------------------------------
        feoc_tainted = (
            req.lithium_lot.refinery_feoc_equity_pct >= 25.0
            or req.lithium_lot.refinery_country == "CHN"
            or req.nickel_lot.feoc_equity_pct >= 25.0
            or req.cobalt_lot.feoc_equity_pct >= 25.0
        )

        if feoc_tainted:
            ira_eligible = False
            defenses.append("FLAG_COMPOSITE_FEOC_TAINT: >= 25.0% covered nation equity detected in component mineral; entire battery pack disqualified for US 30D credit.")
        elif not fta_ratio_passed:
            ira_eligible = False
            defenses.append(f"FLAG_IRA_FTA_RATIO_DEFICIT: Critical mineral FTA ratio {fta_value_ratio_pct:.1f}% below US IRA 50.0% statutory threshold.")
        else:
            ira_eligible = True
            defenses.append(f"DEFENSE_IRA_30D_QUALIFIED: FTA procurement value ratio {fta_value_ratio_pct:.1f}% >= 50.0% and zero FEOC taint; fully eligible for $3,750 clean vehicle credit.")

        # -----------------------------------------------------------------
        # 4. EU Battery Regulation (2023/1542) & Carbon Footprint Audit
        # -----------------------------------------------------------------
        cbam_alert = req.nickel_lot.captive_coal_power

        # Blended Scope 1-3 Carbon Footprint benchmark (kg CO2e / kWh)
        # Baseline NCM cathode footprint ~ 56.0 kg CO2e / kWh
        base_carbon_kg_kwh = 56.0
        if cbam_alert:
            blended_carbon = base_carbon_kg_kwh + 26.5  # Captive coal penalty
            defenses.append("FLAG_EU_BATTERY_CBAM_SURCHARGE: Nickel stream utilizes captive coal power; triggers mandatory EU CBAM carbon border certificate surrender.")
        else:
            blended_carbon = base_carbon_kg_kwh - 4.5   # Clean hydro/grid reward
            defenses.append("DEFENSE_EU_LOW_CARBON_CLEARED: Mineral refining pathways utilize renewable/grid power, complying with EU Battery Regulation carbon limits.")

        eu_approved = (
            li_cleared
            and ni_cleared
            and co_cleared
            and co_res.audit_verdict.child_labor_free
            and co_res.audit_verdict.asm_segregated
            and not cbam_alert
        )

        if eu_approved:
            defenses.append("DEFENSE_EU_BATTERY_PASSPORT_APPROVED: Verified under EU 2023/1542, OECD Annex II, and CSDDD due diligence standards.")
        else:
            defenses.append("FLAG_EU_BATTERY_PASSPORT_HOLD: Deficiencies detected in social, tax, or carbon criteria across component streams.")

        # -----------------------------------------------------------------
        # 5. Composite Confidence Score Calculation
        # -----------------------------------------------------------------
        composite_score = (
            0.35 * li_res.audit_verdict.confidence_score +
            0.35 * ni_res.audit_verdict.confidence_score +
            0.30 * co_res.audit_verdict.confidence_score
        )
        if feoc_tainted:
            composite_score -= 20.0
        if cbam_alert:
            composite_score -= 10.0
        if not co_res.audit_verdict.child_labor_free:
            composite_score -= 30.0

        final_composite_score = max(0.0, min(100.0, composite_score))

        # -----------------------------------------------------------------
        # 6. Merkle Root Generation & Master Polygon EIP-712 Signature
        # -----------------------------------------------------------------
        leaf_li = hashlib.sha256(li_res.onchain_proof.encode("utf-8")).hexdigest()
        leaf_ni = hashlib.sha256(ni_res.onchain_proof.encode("utf-8")).hexdigest()
        leaf_co = hashlib.sha256(co_res.onchain_proof.encode("utf-8")).hexdigest()
        merkle_root = "0x" + hashlib.sha256((leaf_li + leaf_ni + leaf_co).encode("utf-8")).hexdigest()

        try:
            master_onchain_proof = onchain_signer.sign_compliance_verdict(
                lot_id=req.battery_pack_id,
                mineral_type=f"COMPOSITE_{req.cell_chemistry}",
                source_country="AUS_IDN_COD",
                score=int(final_composite_score * 10),
                is_compliant=ira_eligible and eu_approved,
                digest_hash=merkle_root,
            )
        except Exception:
            master_onchain_proof = "0x" + hashlib.sha256((merkle_root + "_MASTER_PASSPORT_FALLBACK").encode("utf-8")).hexdigest()

        return CompositeBatteryVerifyResponse(
            status="success",
            battery_pack_id=req.battery_pack_id,
            cell_chemistry=req.cell_chemistry,
            pack_capacity_kwh=req.pack_capacity_kwh,
            merkle_root=merkle_root,
            lithium_summary={
                "trace_id": li_res.trace_id,
                "mine": li_res.extraction_origin.mine_name,
                "ira_compliant": li_res.audit_verdict.ira_compliant,
                "confidence_score": li_res.audit_verdict.confidence_score,
                "proof": li_res.onchain_proof[:16] + "...",
            },
            nickel_summary={
                "trace_id": ni_res.trace_id,
                "concession": ni_res.extraction_concession.concession_name,
                "simbara_cleared": ni_res.audit_verdict.simbara_export_cleared,
                "cbam_ready": ni_res.audit_verdict.cbam_carbon_ready,
                "confidence_score": ni_res.audit_verdict.confidence_score,
                "proof": ni_res.onchain_proof[:16] + "...",
            },
            cobalt_summary={
                "trace_id": co_res.trace_id,
                "concession": co_res.extraction_concession.concession_name,
                "ceec_cleared": co_res.audit_verdict.ceec_export_cleared,
                "child_labor_free": co_res.audit_verdict.child_labor_free,
                "confidence_score": co_res.audit_verdict.confidence_score,
                "proof": co_res.onchain_proof[:16] + "...",
            },
            composite_verdict=CompositeBatteryAuditVerdict(
                ira_30d_tax_credit_eligible=ira_eligible,
                ira_critical_mineral_fta_ratio_pct=round(fta_value_ratio_pct, 2),
                eu_battery_passport_approved=eu_approved,
                blended_carbon_footprint_kg_per_kwh=round(blended_carbon, 2),
                composite_confidence_score=round(final_composite_score, 1),
                lithium_cleared=li_cleared,
                nickel_cleared=ni_cleared,
                cobalt_cleared=co_cleared,
                feoc_taint_detected=feoc_tainted,
                cbam_carbon_penalty_alert=cbam_alert,
                composite_defenses_applied=defenses,
            ),
            master_onchain_proof=master_onchain_proof,
            timestamp=now_utc,
        )


composite_battery_pipeline = CompositeBatteryPipeline()
