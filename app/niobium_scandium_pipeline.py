"""
Niobium & Scandium Defense Strategic Materials Provenance Pipeline.
Validates extraction and refining of Ferroniobium (FeNb 65%) and Scandium Oxide (Sc2O3 99.5%)
for defense superalloys, hypersonic materials, aerospace Al-Sc alloys, and SOFC fuel cells.
Enforces GIS Geofencing (NioCorp Elk Creek, CBMM Araxá, Niobec), ASTM A550/ISO 5483 assay standards,
US NDAA Section 848 defense eligibility, and US DOE Title XVII & EXIM loan guarantee compliance.
"""

import math
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional, List

from app.schemas import (
    NiobiumScandiumOriginVerifyRequest,
    NiobiumScandiumOriginVerifyResponse,
    NiobiumScandiumAuditVerdict,
    MineralType,
    SourceCountry,
)
from app.onchain_signer import onchain_signer


CANONICAL_NIOBIUM_SCANDIUM_TENEMENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "ELK_CREEK": {
        "canonical_name": "NioCorp Elk Creek Critical Minerals Project",
        "operator": "NioCorp Developments Ltd (NASDAQ: NB / Traxys 100% Commercial Offtake / US DOE & EXIM Strategic Site)",
        "coordinates": (40.274, -96.183),
        "concession_id": "USA-NE-ELKCREEK-01",
        "max_geofence_radius_km": 25.0,
        "region": "Johnson County, Nebraska, USA",
        "country": "USA",
    },
    "ARAXA": {
        "canonical_name": "CBMM Araxá Niobium Complex",
        "operator": "Companhia Brasileira de Metalurgia e Mineração (CBMM)",
        "coordinates": (-19.645, -46.940),
        "concession_id": "BRA-MG-ARAXA-01",
        "max_geofence_radius_km": 30.0,
        "region": "Minas Gerais, Brazil",
        "country": "BRA",
    },
    "NIOBEC": {
        "canonical_name": "Niobec Underground Niobium Mine",
        "operator": "Magris Performance Materials Inc",
        "coordinates": (48.533, -71.150),
        "concession_id": "CAN-QC-NIOBEC-01",
        "max_geofence_radius_km": 20.0,
        "region": "Quebec, Canada",
        "country": "CAN",
    },
}


class NiobiumScandiumPipeline:
    """Enterprise verification pipeline for defense/aerospace Niobium & Scandium procurement."""

    def __init__(self):
        self.tenements = CANONICAL_NIOBIUM_SCANDIUM_TENEMENT_REGISTRY

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
        return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    def verify_origin(self, request: NiobiumScandiumOriginVerifyRequest) -> NiobiumScandiumOriginVerifyResponse:
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
                reasons.append(f"Strategic mineral centroid geofenced near {matched_t['canonical_name']} ({distance_km:.2f} km)")
            else:
                geofence_verified = False
                distance_km = nearest_dist
                is_compliant = False
                reasons.append(f"Concession {request.tenement_id} not registered in Allied Niobium/Scandium Registry ({distance_km:.2f} km)")
        else:
            distance_km = self._haversine_distance(request.latitude, request.longitude, tenement["coordinates"][0], tenement["coordinates"][1])
            if distance_km <= tenement["max_geofence_radius_km"]:
                geofence_verified = True
                reasons.append(f"Extraction point validated within {tenement['canonical_name']} ({distance_km:.2f} km <= {tenement['max_geofence_radius_km']} km)")
            else:
                geofence_verified = False
                is_compliant = False
                reasons.append(f"Coordinates deviate {distance_km:.2f} km from certified perimeter")

        # 2. Commodity Grade / Purity Assay Check
        grade_assay_certified = True
        comm_type = str(request.commodity_type).upper()
        if "SCANDIUM" in comm_type or "SC2O3" in comm_type:
            # Scandium Oxide >= 99.5%
            if request.sc2o3_purity_pct < 99.5:
                grade_assay_certified = False
                is_compliant = False
                reasons.append(f"Scandium Oxide purity {request.sc2o3_purity_pct:.2f}% below aerospace specification standard (99.50%)")
            else:
                reasons.append(f"Scandium Oxide purity {request.sc2o3_purity_pct:.2f}% certified high-purity aerospace grade")
        else:
            # Ferroniobium FeNb >= 65.0% (ASTM A550 / ISO 5483 Standard Grade)
            if request.fe_nb_grade_pct < 65.0:
                grade_assay_certified = False
                is_compliant = False
                reasons.append(f"Ferroniobium Nb content {request.fe_nb_grade_pct:.2f}% below ASTM A550 standard grade (65.00%)")
            else:
                reasons.append(f"Ferroniobium Nb content {request.fe_nb_grade_pct:.2f}% certified defense superalloy grade (ASTM A550)")

        # 3. Defense Procurement & Strategic Loan Eligibility
        defense_eligible = request.ndaa_defense_procurement_eligible and geofence_verified
        if not defense_eligible:
            reasons.append("Ineligible for US DoD military hardware procurement under NDAA Section 848 (covered nation origin risk)")
        else:
            reasons.append("US DoD NDAA Section 848 & Title III Defense Production Act non-covered nation certified")

        doe_exim_eligible = request.doe_exim_loan_eligible and geofence_verified
        if doe_exim_eligible:
            reasons.append("Pre-qualified for US DOE Title XVII clean energy loan & US EXIM Bank critical mineral debt facility")

        confidence_score = 98.0 if is_compliant else (50.0 if geofence_verified else 20.0)
        status_str = "COMPLIANT_CERTIFIED" if is_compliant else "NON_COMPLIANT_REJECTED"

        verdict = NiobiumScandiumAuditVerdict(
            is_compliant=is_compliant,
            status=status_str,
            geofence_verified=geofence_verified,
            distance_to_concession_km=round(distance_km, 2),
            grade_assay_certified=grade_assay_certified,
            defense_procurement_eligible=defense_eligible,
            doe_exim_loan_eligible=doe_exim_eligible,
            confidence_score=confidence_score,
            reasons=reasons,
        )

        now_utc = datetime.now(timezone.utc).isoformat()
        proof_data = f"{request.batch_id}|{request.tenement_id}|{request.commodity_type}|{status_str}|{verdict.confidence_score}|{now_utc}"
        proof_hash = "0x" + hashlib.sha256(proof_data.encode("utf-8")).hexdigest()

        # Generate onchain signature
        onchain_sig, signer_addr = onchain_signer.sign_attestation(proof_hash)

        return NiobiumScandiumOriginVerifyResponse(
            status="success",
            batch_id=request.batch_id,
            commodity_type=str(request.commodity_type),
            audit_verdict=verdict,
            proof_hash=proof_hash,
            onchain_signature=onchain_sig,
            signed_by=signer_addr,
            timestamp=now_utc,
        )


niobium_scandium_pipeline = NiobiumScandiumPipeline()
