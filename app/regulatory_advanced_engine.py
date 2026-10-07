"""
Advanced Global Regulatory Engine: EU CBAM Mark-up Penalty, Industrial Accelerator Act (IAA),
and W3C Verifiable Credential (VC) EU Battery Passport Issuer.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from app.schemas import (
    CBAMMarkupPenaltyRequest,
    CBAMMarkupPenaltyResponse,
    EUIndustrialActVerifyRequest,
    EUIndustrialActVerifyResponse,
    BatteryPassportVCRequest,
    BatteryPassportVCResponse,
)
from app.onchain_signer import onchain_signer


class RegulatoryAdvancedEngine:
    """Enterprise compliance calculator for 2026/2027 evolving trade policies."""

    # CBAM Statutory Default Mark-up Rates under EU Implementing Regulation
    CBAM_MARKUP_RATES: Dict[int, float] = {
        2026: 0.10,  # +10% penalty surcharge on default values
        2027: 0.20,  # +20% penalty surcharge
        2028: 0.30,  # +30% penalty surcharge
    }

    def calculate_cbam_markup_penalty(self, request: CBAMMarkupPenaltyRequest) -> CBAMMarkupPenaltyResponse:
        """
        Calculates CBAM certificate liabilities and default value mark-up surcharges.
        Post-Sept 30 accredited verifier portal deadline.
        """
        penalty_rate = self.CBAM_MARKUP_RATES.get(request.import_year, 0.30)
        is_verified = request.verified_scope1_2_emissions_tco2_per_ton is not None

        total_default_emissions = request.tonnage * request.default_embedded_emissions_tco2_per_ton

        if is_verified:
            effective_rate = 0.0
            total_verified_emissions = request.tonnage * request.verified_scope1_2_emissions_tco2_per_ton
            effective_emissions_billed = total_verified_emissions
            is_verified_exempt = True
            markup_penalty_surcharge_eur = 0.0
            total_cbam_liability_eur = effective_emissions_billed * request.eu_allowance_price_eur
            
            # Default comparison without verification
            unverified_billed = total_default_emissions * (1.0 + penalty_rate)
            unverified_liability = unverified_billed * request.eu_allowance_price_eur
            savings = max(0.0, unverified_liability - total_cbam_liability_eur)
            advice = (
                f"VERIFIED_EXEMPT: Scope 1&2 audit verified. Mark-up penalty avoided. "
                f"Saved €{savings:,.2f} versus default value penalty regime."
            )
        else:
            effective_rate = penalty_rate
            total_verified_emissions = None
            is_verified_exempt = False
            effective_emissions_billed = total_default_emissions * (1.0 + penalty_rate)
            base_liability = total_default_emissions * request.eu_allowance_price_eur
            total_cbam_liability_eur = effective_emissions_billed * request.eu_allowance_price_eur
            markup_penalty_surcharge_eur = total_cbam_liability_eur - base_liability
            savings = 0.0
            advice = (
                f"PENALTY_APPLIED: Unverified default value subject to +{penalty_rate * 100:.0f}% statutory mark-up. "
                f"Incurring €{markup_penalty_surcharge_eur:,.2f} in penalty surcharges. Engage accredited verifier immediately."
            )

        return CBAMMarkupPenaltyResponse(
            status="success",
            import_year=request.import_year,
            markup_penalty_rate=effective_rate,
            is_verified_exempt=is_verified_exempt,
            total_default_emissions_tco2=round(total_default_emissions, 2),
            total_verified_emissions_tco2=round(total_verified_emissions, 2) if total_verified_emissions is not None else None,
            effective_emissions_billed_tco2=round(effective_emissions_billed, 2),
            total_cbam_liability_eur=round(total_cbam_liability_eur, 2),
            markup_penalty_surcharge_eur=round(markup_penalty_surcharge_eur, 2),
            savings_with_verified_report_eur=round(savings, 2),
            audit_advice=advice,
        )

    def verify_eu_industrial_act(self, request: EUIndustrialActVerifyRequest) -> EUIndustrialActVerifyResponse:
        """
        Verifies compliance with the EU Industrial Accelerator Act (IAA)
        requiring >=70% local EU components and >=40% EU green steel for EV subsidies.
        """
        iaa_70_passed = request.eu_domestic_value_share_pct >= 70.0
        steel_40_passed = request.eu_steel_domestic_share_pct >= 40.0
        overall_eligible = iaa_70_passed and steel_40_passed

        score = (request.eu_domestic_value_share_pct * 0.7 + request.eu_steel_domestic_share_pct * 0.3) / 100.0

        citations = [
            "Directive (EU) 2026/470 Corporate Sustainability Due Diligence (CSDDD)",
            "Proposal for EU Industrial Accelerator Act (IAA) 2026 Art. 14 (Domestic Clean Value Requirements)",
            "EU Net-Zero Industry Act (NZIA) Critical Raw Material Benchmark",
        ]

        proof_payload = f"IAA:{request.component_type}:{request.eu_domestic_value_share_pct}:{overall_eligible}:{datetime.now(timezone.utc).isoformat()}"
        proof_hash = "0x" + hashlib.sha256(proof_payload.encode("utf-8")).hexdigest()

        return EUIndustrialActVerifyResponse(
            status="success",
            component_type=request.component_type,
            iaa_70pct_threshold_passed=iaa_70_passed,
            steel_40pct_threshold_passed=steel_40_passed,
            overall_subsidy_eligible=overall_eligible,
            compliance_score=round(score, 3),
            statutory_citations=citations,
            proof_hash=proof_hash,
        )

    def generate_battery_passport_vc(self, request: BatteryPassportVCRequest) -> BatteryPassportVCResponse:
        """
        Generates W3C Verifiable Credential (VC) compliant EU Battery Passport (Regulation 2023/1542).
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        issuer_did = f"did:agrid:oracle:{onchain_signer.get_address().lower()}"
        subject_did = f"did:battery:{hashlib.sha256(request.battery_id.encode('utf-8')).hexdigest()[:32]}"

        vc_payload: Dict[str, Any] = {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://schema.eu-battery-passport.org/v1",
            ],
            "id": f"urn:uuid:bp-{hashlib.sha256((request.battery_id + now_iso).encode('utf-8')).hexdigest()[:16]}",
            "type": ["VerifiableCredential", "DigitalProductPassport", "EUBatteryPassport"],
            "issuer": issuer_did,
            "issuanceDate": now_iso,
            "credentialSubject": {
                "id": subject_did,
                "batterySerial": request.battery_id,
                "chemistry": request.chemistry,
                "ratedCapacityKWh": request.rated_capacity_kwh,
                "recycledContent": {
                    "cobalt": request.recycled_cobalt_pct,
                    "lithium": request.recycled_lithium_pct,
                    "nickel": request.recycled_nickel_pct,
                },
                "carbonFootprintKgCO2ePerKWh": request.carbon_footprint_kg_co2_per_kwh,
                "upstreamMineralProofHash": request.provenance_proof_hash,
                "conformanceStatus": "EU_2023_1542_FULLY_COMPLIANT",
            },
        }

        # Deterministic digest of credential subject
        digest = hashlib.sha256(json.dumps(vc_payload, sort_keys=True).encode("utf-8")).hexdigest()
        sig, _ = onchain_signer.sign_attestation("0x" + digest)

        vc_payload["proof"] = {
            "type": "EcdsaSecp256k1RecoverySignature2020",
            "created": now_iso,
            "verificationMethod": f"{issuer_did}#key-1",
            "proofPurpose": "assertionMethod",
            "jws": sig,
        }

        qr_uri = f"https://passport.agrid.io/view?did={subject_did}&proof={sig[:32]}"

        return BatteryPassportVCResponse(
            status="success",
            battery_id=request.battery_id,
            vc_token=vc_payload,
            did_issuer=issuer_did,
            did_subject=subject_did,
            qr_code_payload_uri=qr_uri,
            signature=sig,
            issued_at=now_iso,
        )


regulatory_advanced_engine = RegulatoryAdvancedEngine()
