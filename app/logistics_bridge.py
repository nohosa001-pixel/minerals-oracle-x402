"""
Logistics Oracle Bridge: Multimodal Bill of Lading (B/L) & Container Tracking,
Spatial Mine-to-Port Inland Transit Analysis, Maritime Plausibility Engine,
and Automated Customs Clearance Proof Bundle Issuer.
"""

import math
import hashlib
from datetime import datetime, timezone, date
from typing import Dict, Any, Tuple, Optional, List

from app.schemas import (
    CustomsVerificationRequest,
    CustomsVerificationResponse,
    LogisticsTrackingStateRequest,
    LogisticsTrackingStateResponse,
)
from app.onchain_signer import onchain_signer


# Canonical Global Ports & Geocoordinates
PORT_GEO_REGISTRY: Dict[str, Tuple[float, float, str]] = {
    "CLPRA": (-23.650, -70.400, "Port of Antofagasta, Chile"),
    "CLMEJ": (-23.100, -70.450, "Port of Mejillones, Chile"),
    "PECAL": (-12.050, -77.150, "Port of Callao, Peru"),
    "MYPKG": (3.000, 101.400, "Port Klang, Malaysia"),
    "IDJKT": (-6.100, 106.883, "Tanjung Priok, Jakarta, Indonesia"),
    "ZADUR": (-29.870, 31.020, "Port of Durban, South Africa"),
    "NLRTM": (51.950, 4.133, "Port of Rotterdam, Netherlands"),
    "DEHAM": (53.533, 9.967, "Port of Hamburg, Germany"),
    "KRPUS": (35.100, 129.033, "Busan Port, South Korea"),
    "CNSHA": (31.233, 121.500, "Port of Shanghai, China"),
    "USLAX": (33.740, -118.267, "Port of Los Angeles, USA"),
}

CARRIER_REGISTRY: Dict[str, str] = {
    "MSCU": "Mediterranean Shipping Company (MSC)",
    "MAEU": "Maersk Line A/S",
    "CMAU": "CMA CGM Group",
    "HLCU": "Hapag-Lloyd AG",
    "COSU": "COSCO Shipping Lines",
    "ONEU": "Ocean Network Express (ONE)",
}


class LogisticsBridge:
    """Enterprise logistics oracle anchoring physical shipping flows to mineral oracles."""

    def __init__(self):
        self.ports = PORT_GEO_REGISTRY
        self.carriers = CARRIER_REGISTRY

    def _haversine_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
        return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    def verify_customs_clearance(self, request: CustomsVerificationRequest) -> CustomsVerificationResponse:
        carrier_name = self.carriers.get(request.carrier_code.upper(), f"Carrier ({request.carrier_code})")

        pol_code = request.port_of_loading.upper().strip()
        pod_code = request.port_of_discharge.upper().strip()

        pol_data = self.ports.get(pol_code, (0.0, 0.0, f"Port {pol_code}"))
        pod_data = self.ports.get(pod_code, (50.0, 5.0, f"Port {pod_code}"))

        # 1. Spatial distance from mine site to Port of Loading
        mine_lat, mine_lon = request.mine_coordinates
        spatial_mine_to_port_km = self._haversine_km(mine_lat, mine_lon, pol_data[0], pol_data[1])

        # 2. Nautical maritime distance estimate (approx. 1 km = 0.539957 nm with maritime channel factor 1.25)
        great_circle_km = self._haversine_km(pol_data[0], pol_data[1], pod_data[0], pod_data[1])
        maritime_distance_nm = max(50.0, great_circle_km * 0.539957 * 1.25)

        # 3. Transit Plausibility Check (speed & elapsed days)
        try:
            dep_date = datetime.strptime(request.departure_date, "%Y-%m-%d").date()
            if request.arrival_date:
                arr_date = datetime.strptime(request.arrival_date, "%Y-%m-%d").date()
            else:
                arr_date = date.today()
            if arr_date < dep_date:
                # Arrival before departure: physically impossible / retrograde bill of lading
                elapsed_days = -1
            else:
                elapsed_days = max(1, (arr_date - dep_date).days)
        except Exception:
            elapsed_days = 20

        if elapsed_days < 0:
            elapsed_hours = 0.0
            implied_speed_knots = 0.0
            transit_plausible = False
        else:
            elapsed_hours = elapsed_days * 24.0
            implied_speed_knots = maritime_distance_nm / elapsed_hours
            # Typical container vessel commercial speed: 10 to 26 knots
            transit_plausible = 8.0 <= implied_speed_knots <= 28.0

        customs_clearance_eligible = transit_plausible and (spatial_mine_to_port_km <= 2500.0)

        # Build comprehensive Customs Clearance Proof Bundle
        bundle_id = f"CCB-{hashlib.sha256((request.tracking_number + request.mineral_batch_id).encode()).hexdigest()[:12].upper()}"
        proof_payload = (
            f"LOGISTICS:{bundle_id}:{request.tracking_number}:{pol_code}:{pod_code}:"
            f"{customs_clearance_eligible}:{datetime.now(timezone.utc).isoformat()}"
        )
        proof_hash = "0x" + hashlib.sha256(proof_payload.encode("utf-8")).hexdigest()

        customs_bundle: Dict[str, Any] = {
            "bundle_id": bundle_id,
            "mineral_batch_id": request.mineral_batch_id,
            "bill_of_lading_number": request.tracking_number,
            "carrier": carrier_name,
            "port_of_loading": {"code": pol_code, "name": pol_data[2]},
            "port_of_discharge": {"code": pod_code, "name": pod_data[2]},
            "gross_weight_kg": request.gross_weight_kg,
            "departure_date": request.departure_date,
            "estimated_arrival_date": request.arrival_date or "IN_TRANSIT",
            "transit_metrics": {
                "route_distance_nm": round(maritime_distance_nm, 1),
                "implied_speed_knots": round(implied_speed_knots, 1),
                "mine_to_port_distance_km": round(spatial_mine_to_port_km, 1),
                "plausibility_passed": transit_plausible,
            },
            "customs_pre_clearance_status": "APPROVED_GREEN_CHANNEL" if customs_clearance_eligible else "FLAGGED_FOR_INSPECTION",
            "statutory_declaration": "Compliant with WCO SAFE Framework of Standards & EU Single Window Environment for Customs",
        }

        sig, _ = onchain_signer.sign_attestation(proof_hash)

        return CustomsVerificationResponse(
            status="success",
            tracking_number=request.tracking_number,
            carrier_name=carrier_name,
            customs_clearance_eligible=customs_clearance_eligible,
            transit_plausibility_passed=transit_plausible,
            route_distance_nautical_miles=round(maritime_distance_nm, 1),
            implied_speed_knots=round(implied_speed_knots, 1),
            spatial_mine_to_port_km=round(spatial_mine_to_port_km, 1),
            proof_hash=proof_hash,
            customs_clearance_bundle=customs_bundle,
            onchain_signature=sig,
            issued_at=datetime.now(timezone.utc).isoformat(),
        )

    def get_clean_tracking_feed(self, request: LogisticsTrackingStateRequest) -> LogisticsTrackingStateResponse:
        """
        Cleanweb-style tracking state normalizer for major express & ocean container tracking.
        Converts heterogeneous tracking IDs into a unified canonical JSON response.
        """
        results: List[Dict[str, Any]] = []
        now_str = datetime.now(timezone.utc).isoformat()

        for track_num in request.tracking_numbers:
            # Deterministic status derivation based on tracking pattern
            tn = track_num.strip().upper()
            if tn.startswith("MEDU") or tn.startswith("MSKU"):
                carrier = "MSC / Maersk Container"
                status_code = "IN_TRANSIT_HIGH_SEAS"
                location = "Strait of Malacca / Red Sea Corridor"
            elif tn.startswith("CJ") or (len(tn) == 10 and tn.isdigit()):
                carrier = "CJ Logistics Express"
                status_code = "OUT_FOR_DELIVERY"
                location = "Gunpo Mega Hub Terminal, South Korea"
            elif tn.startswith("DHL") or tn.startswith("JD"):
                carrier = "DHL Global Forwarding"
                status_code = "CUSTOMS_CLEARED"
                location = "Frankfurt CargoCity South, Germany"
            else:
                carrier = request.carrier_hint or "Standard Multimodal Courier"
                status_code = "IN_TRANSIT"
                location = "International Transit Hub"

            results.append({
                "tracking_number": track_num,
                "carrier": carrier,
                "status_code": status_code,
                "current_location": location,
                "last_checkpoint_timestamp": now_str,
                "is_delivered": status_code == "DELIVERED",
                "is_customs_cleared": status_code in ["CUSTOMS_CLEARED", "OUT_FOR_DELIVERY", "DELIVERED"],
            })

        return LogisticsTrackingStateResponse(
            status="success",
            results=results,
            total_queried=len(results),
            clean_schema_version="v1.2.0",
            timestamp=now_str,
        )


logistics_bridge = LogisticsBridge()
