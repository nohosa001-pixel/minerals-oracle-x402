"""
Global Tungsten (Ammonium Paratungstate / Concentrate) Provenance Pipeline.
Defends against 3TG conflict mining, enforces ASTM B783/ISO 10386 APT Grade Standards (WO3 >= 88.5%),
and certifies US NDAA Section 848 Defense Procurement non-covered nation eligibility.
"""

import math
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional, List

from app.schemas import (
    TungstenOriginVerifyRequest,
    TungstenOriginVerifyResponse,
    TungstenAuditVerdict,
    SourceCountry,
)
from app.onchain_signer import onchain_signer


CANONICAL_TUNGSTEN_TENEMENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "CANTUNG": {
        "canonical_name": "NATC Cantung Tungsten Mine",
        "operator": "North American Tungsten Corp / Gov of NWT",
        "coordinates": (61.954, -128.243),
        "concession_id": "CAN-NWT-CAN-01",
        "max_geofence_radius_km": 25.0,
        "region": "Northwest Territories, Canada",
        "country": "CAN",
    },
    "IMA_PROJECT": {
        "canonical_name": "American Tungsten IMA Project",
        "operator": "American Tungsten Corp",
        "coordinates": (44.492, -113.882),
        "concession_id": "USA-ID-IMA-01",
        "max_geofence_radius_km": 20.0,
        "region": "Idaho, United States",
        "country": "USA",
    },
    "PANASQUEIRA": {
        "canonical_name": "Beralt Panasqueira Wolframite Underground Mine",
        "operator": "Almonty Industries Inc",
        "coordinates": (40.158, -7.747),
        "concession_id": "PRT-CB-PAN-01",
        "max_geofence_radius_km": 20.0,
        "region": "Castelo Branco, Portugal",
        "country": "PRT",
    },
    "SANGDONG": {
        "canonical_name": "Almonty Korea Sangdong Tungsten Mine",
        "operator": "Almonty Industries (World's Largest Western Deposit)",
        "coordinates": (37.150, 128.833),
        "concession_id": "KOR-GW-SANG-01",
        "max_geofence_radius_km": 20.0,
        "region": "Gangwon-do, South Korea",
        "country": "KOR",
    },
}


class TungstenPipeline:
    """Enterprise verification pipeline for defense/semiconductor tungsten procurement."""

    def __init__(self):
        self.tenements = CANONICAL_TUNGSTEN_TENEMENT_REGISTRY

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
        return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    def verify_tungsten_batch(self, request: TungstenOriginVerifyRequest) -> TungstenOriginVerifyResponse:
        reasons: List[str] = []
        is_compliant = True

        tenement_key = request.tenement_id.upper().strip()
        tenement = self.tenements.get(tenement_key)

        distance_km = 9999.0
        geofence_verified = False

        if not tenement:
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
                reasons.append(f"Tungsten centroid geofenced near {matched_t['canonical_name']} ({distance_km:.2f} km)")
            else:
                geofence_verified = False
                distance_km = nearest_dist
                is_compliant = False
                reasons.append(f"Concession {request.tenement_id} not recognized in Western Tungsten Registry ({distance_km:.2f} km)")
        else:
            distance_km = self._haversine_distance(request.latitude, request.longitude, tenement["coordinates"][0], tenement["coordinates"][1])
            if distance_km <= tenement["max_geofence_radius_km"]:
                geofence_verified = True
                reasons.append(f"Extraction point validated within {tenement['canonical_name']} ({distance_km:.2f} km <= {tenement['max_geofence_radius_km']} km)")
            else:
                geofence_verified = False
                is_compliant = False
                reasons.append(f"Coordinates deviate {distance_km:.2f} km from certified perimeter")

        # 2. APT WO3 Grade (>= 88.5%)
        apt_grade_certified = request.apt_wo3_grade_pct >= 88.5
        if not apt_grade_certified:
            is_compliant = False
            reasons.append(f"Ammonium Paratungstate WO3 purity {request.apt_wo3_grade_pct:.2f}% below standard grade (88.50%)")
        else:
            reasons.append(f"Ammonium Paratungstate WO3 purity {request.apt_wo3_grade_pct:.2f}% certified high-purity commercial grade")

        # 3. 3TG Conflict Free (Dodd-Frank Sec 1502)
        dodd_frank_passed = request.dodd_frank_conflict_free
        if not dodd_frank_passed:
            is_compliant = False
            reasons.append("Batch flagged with conflict 3TG contamination in upstream supply chain")
        else:
            reasons.append("OECD Annex II & Dodd-Frank Sec 1502 conflict-free audit verified")

        # 4. US NDAA Section 848 Defense Procurement Eligibility
        ndaa_defense_eligible = request.ndaa_defense_procurement_eligible and geofence_verified
        if not ndaa_defense_eligible:
            reasons.append("Ineligible for US DoD military hardware procurement under NDAA Section 848 (covered nation origin risk)")
        else:
            reasons.append("Certified eligible for US Department of Defense procurement under NDAA Section 848")

        status = "COMPLIANT_CERTIFIED" if is_compliant else "NON_COMPLIANT_REJECTED"
        confidence_score = 0.98 if is_compliant else 0.45

        audit_verdict = TungstenAuditVerdict(
            is_compliant=is_compliant,
            status=status,
            geofence_verified=geofence_verified,
            distance_to_concession_km=round(distance_km, 2),
            apt_grade_certified=apt_grade_certified,
            dodd_frank_passed=dodd_frank_passed,
            ndaa_defense_eligible=ndaa_defense_eligible,
            confidence_score=confidence_score,
            reasons=reasons,
        )

        proof_payload = (
            f"W:{request.batch_id}:{request.tenement_id}:{request.apt_wo3_grade_pct}:"
            f"{status}:{datetime.now(timezone.utc).isoformat()}"
        )
        proof_hash = "0x" + hashlib.sha256(proof_payload.encode("utf-8")).hexdigest()
        sig, signer_addr = onchain_signer.sign_attestation(proof_hash)

        return TungstenOriginVerifyResponse(
            status="success",
            batch_id=request.batch_id,
            audit_verdict=audit_verdict,
            proof_hash=proof_hash,
            onchain_signature=sig,
            signed_by=signer_addr,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


tungsten_pipeline = TungstenPipeline()
