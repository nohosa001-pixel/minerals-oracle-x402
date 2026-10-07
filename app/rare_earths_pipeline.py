"""
Global Rare Earth Elements (NdPr / Dy / Tb) Provenance & Export Control Compliance Pipeline.
Integrates Non-China Tenement GIS Geofencing (Mt Weld, Mountain Pass, Nechalacho, Longonjo),
IAEA Radiation Byproduct Safety (Thorium/Uranium limits), High-Purity Assay (>=99.5% NdPr Oxide),
and China MOFCOM Notice 61 '0.1% Extraterritorial Export Control' (D-35 / Nov 10 rule) compliance.
"""

import math
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional, List

from app.schemas import (
    RareEarthsOriginVerifyRequest,
    RareEarthsOriginVerifyResponse,
    RareEarthsAuditVerdict,
    SourceCountry,
)
from app.onchain_signer import onchain_signer


CANONICAL_RARE_EARTHS_TENEMENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "MT_WELD": {
        "canonical_name": "Lynas Mt Weld Rare Earths Mine",
        "operator": "Lynas Rare Earths Ltd (World's #1 Non-China Producer)",
        "coordinates": (-28.868, 122.500),
        "concession_id": "AUS-WA-MTWELD-01",
        "max_geofence_radius_km": 30.0,
        "region": "Western Australia",
        "country": "AUS",
    },
    "MOUNTAIN_PASS": {
        "canonical_name": "MP Materials Mountain Pass Mine",
        "operator": "MP Materials Corp",
        "coordinates": (35.483, -115.533),
        "concession_id": "USA-CA-MTPASS-01",
        "max_geofence_radius_km": 25.0,
        "region": "California, United States",
        "country": "USA",
    },
    "NECHALACHO": {
        "canonical_name": "Nechalacho Rare Earth Elements Project",
        "operator": "Vital Metals / Cheetah Resources",
        "coordinates": (62.110, -112.590),
        "concession_id": "CAN-NWT-NECH-01",
        "max_geofence_radius_km": 20.0,
        "region": "Northwest Territories, Canada",
        "country": "CAN",
    },
    "LONGONJO": {
        "canonical_name": "Pensana Longonjo Rare Earths Project",
        "operator": "Pensana Plc",
        "coordinates": (-12.910, 15.250),
        "concession_id": "AGO-HUAM-LONG-01",
        "max_geofence_radius_km": 25.0,
        "region": "Huambo, Angola",
        "country": "AGO",
    },
}


class RareEarthsPipeline:
    """Enterprise verification pipeline for critical NdPr magnet materials and MOFCOM 0.1% rule."""

    def __init__(self):
        self.tenements = CANONICAL_RARE_EARTHS_TENEMENT_REGISTRY

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
        return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    def verify_rare_earths_batch(self, request: RareEarthsOriginVerifyRequest) -> RareEarthsOriginVerifyResponse:
        reasons: List[str] = []
        is_compliant = True

        tenement_key = request.tenement_id.upper().strip()
        tenement = self.tenements.get(tenement_key)

        distance_km = 9999.0
        geofence_verified = False

        if not tenement:
            # Fallback search by coordinates
            nearest_dist = 99999.0
            matched_t = None
            for t_data in self.tenements.values():
                d = self._haversine_distance(request.latitude, request.longitude, t_data["coordinates"][0], t_data["coordinates"][1])
                if d < nearest_dist:
                    nearest_dist = d
                    matched_t = t_data
            if matched_t and nearest_dist <= matched_t["max_geofence_radius_km"]:
                geofence_verified = True
                distance_km = nearest_dist
                reasons.append(f"Centroid geofenced near {matched_t['canonical_name']} ({distance_km:.2f} km)")
            else:
                geofence_verified = False
                distance_km = nearest_dist
                is_compliant = False
                reasons.append(f"Tenement {request.tenement_id} not registered in non-China canonical registry (distance: {distance_km:.2f} km)")
        else:
            distance_km = self._haversine_distance(request.latitude, request.longitude, tenement["coordinates"][0], tenement["coordinates"][1])
            if distance_km <= tenement["max_geofence_radius_km"]:
                geofence_verified = True
                reasons.append(f"Concession geofenced inside {tenement['canonical_name']} ({distance_km:.2f} km <= {tenement['max_geofence_radius_km']} km)")
            else:
                geofence_verified = False
                is_compliant = False
                reasons.append(f"Extraction coordinates deviate {distance_km:.2f} km from authorized boundary")

        # 2. NdPr Oxide Purity (>= 99.5%)
        purity_certified = request.ndpr_oxide_purity_pct >= 99.5
        if not purity_certified:
            is_compliant = False
            reasons.append(f"NdPr Oxide assay purity {request.ndpr_oxide_purity_pct:.2f}% below automotive magnet benchmark (99.50%)")
        else:
            reasons.append(f"NdPr Oxide assay purity {request.ndpr_oxide_purity_pct:.2f}% meets sintered NdFeB magnet grade")

        # 3. Radiation Safety (Thorium/Uranium residue <= 500 ppm)
        radiation_passed = request.thorium_uranium_radiation_ppm <= 500.0
        if not radiation_passed:
            is_compliant = False
            reasons.append(f"Radionuclide Th+U level {request.thorium_uranium_radiation_ppm:.1f} ppm exceeds IAEA limit (500 ppm)")
        else:
            reasons.append(f"Radionuclide Th+U level {request.thorium_uranium_radiation_ppm:.1f} ppm verified safe")

        # 4. MOFCOM Notice 61 '0.1% Rule' (D-35 Threshold)
        # Declared ratio must be strictly < 0.001 (0.1%)
        mofcom_china_content_passed = request.declared_china_origin_ratio < 0.001
        if not mofcom_china_content_passed:
            is_compliant = False
            reasons.append(
                f"China origin content {request.declared_china_origin_ratio * 100:.3f}% exceeds China MOFCOM Notice 61 threshold (0.100%). "
                "Subject to extraterritorial export embargo!"
            )
        else:
            reasons.append(
                f"China origin content {request.declared_china_origin_ratio * 100:.3f}% strictly below 0.100% threshold. "
                "Safe from Chinese MOFCOM extraterritorial export restrictions."
            )

        status = "COMPLIANT_CERTIFIED" if is_compliant else "NON_COMPLIANT_REJECTED"
        confidence_score = 0.99 if is_compliant else 0.40

        audit_verdict = RareEarthsAuditVerdict(
            is_compliant=is_compliant,
            status=status,
            geofence_verified=geofence_verified,
            distance_to_concession_km=round(distance_km, 2),
            purity_certified=purity_certified,
            radiation_safety_passed=radiation_passed,
            mofcom_china_content_passed=mofcom_china_content_passed,
            china_content_ratio=round(request.declared_china_origin_ratio, 6),
            mofcom_rule_d35_eligible=mofcom_china_content_passed,
            confidence_score=confidence_score,
            reasons=reasons,
        )

        # Cryptographic Proof Hash
        proof_payload = (
            f"RE:{request.batch_id}:{request.tenement_id}:{request.ndpr_oxide_purity_pct}:"
            f"{request.declared_china_origin_ratio}:{status}:{datetime.now(timezone.utc).isoformat()}"
        )
        proof_hash = "0x" + hashlib.sha256(proof_payload.encode("utf-8")).hexdigest()

        # ECDSA Onchain Signature
        sig, signer_addr = onchain_signer.sign_attestation(proof_hash)

        return RareEarthsOriginVerifyResponse(
            status="success",
            batch_id=request.batch_id,
            audit_verdict=audit_verdict,
            proof_hash=proof_hash,
            onchain_signature=sig,
            signed_by=signer_addr,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


rare_earths_pipeline = RareEarthsPipeline()
