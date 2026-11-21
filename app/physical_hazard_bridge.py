"""
Physical Hazard Pre-Settlement Bridge for Minerals Oracle x402.
Concurrently queries global-earthquake-agent (SEISMIC_ORACLE) and
climate-insurance-agent (CLIMATE_ORACLE) via trade-hazard-oracle/1.0.
"""

import asyncio
import os
import time
from typing import Any, Dict, List
import httpx

SEISMIC_ORACLE_URL = os.getenv(
    "SEISMIC_ORACLE_URL",
    "https://global-earthquake-agent-212942243360.asia-northeast3.run.app",
)
CLIMATE_ORACLE_URL = os.getenv(
    "CLIMATE_ORACLE_URL",
    "https://climate-insurance-agent-212942243360.asia-northeast3.run.app",
)


class PhysicalHazardBridge:
    def __init__(
        self,
        seismic_url: str = SEISMIC_ORACLE_URL,
        climate_url: str = CLIMATE_ORACLE_URL,
        timeout_sec: float = 4.0,
    ):
        self.seismic_url = seismic_url.rstrip("/")
        self.climate_url = climate_url.rstrip("/")
        self.timeout_sec = timeout_sec

    async def _query_oracle(
        self, client: httpx.AsyncClient, base_url: str, name: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            resp = await client.post(
                f"{base_url}/api/trade-oracle/assess-route",
                json=payload,
                timeout=self.timeout_sec,
            )
            resp.raise_for_status()
            data = resp.json()
            data["_status"] = "OK"
            return data
        except Exception as exc:
            return {
                "_status": "DEGRADED_FALLBACK",
                "subsystem": name,
                "route_trade_action": "CLEAR",
                "max_severity_score": 0.0,
                "error": str(exc),
                "waypoints": [],
            }

    async def assess_trade_route(
        self,
        waypoints: List[Dict[str, Any]],
        use_live_feed: bool = True,
    ) -> Dict[str, Any]:
        """Query both Seismic & Climate sub-oracles in parallel before mineral escrow settlement."""
        t0 = time.perf_counter()
        payload = {"waypoints": waypoints, "use_live_feed": use_live_feed}

        async with httpx.AsyncClient() as client:
            seismic_res, climate_res = await asyncio.gather(
                self._query_oracle(client, self.seismic_url, "SEISMIC_ORACLE", payload),
                self._query_oracle(client, self.climate_url, "CLIMATE_ORACLE", payload),
            )

        actions = [
            seismic_res.get("route_trade_action", "CLEAR"),
            climate_res.get("route_trade_action", "CLEAR"),
        ]
        if "HOLD_COMPLIANCE" in actions:
            combined_action = "HOLD_COMPLIANCE"
        elif "REROUTE" in actions:
            combined_action = "REROUTE"
        elif "CAUTION" in actions:
            combined_action = "CAUTION"
        else:
            combined_action = "CLEAR"

        alternates = []
        for wp in seismic_res.get("waypoints", []):
            for alt in wp.get("alternate_hubs", []):
                if alt not in alternates:
                    alternates.append(alt)

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        return {
            "schema_version": "trade-hazard-oracle/1.0",
            "combined_trade_action": combined_action,
            "settlement_cleared": combined_action in ("CLEAR", "CAUTION"),
            "force_majeure_triggered": bool(
                seismic_res.get("force_majeure_triggered") or climate_res.get("force_majeure_triggered")
            ),
            "max_severity_score": max(
                float(seismic_res.get("max_severity_score", 0.0)),
                float(climate_res.get("max_severity_score", 0.0)),
            ),
            "alternate_hubs_suggested": alternates,
            "latency_ms": elapsed_ms,
            "subsystems": {
                "seismic": {
                    "status": seismic_res.get("_status"),
                    "action": seismic_res.get("route_trade_action"),
                    "severity": seismic_res.get("max_severity_score"),
                    "url": self.seismic_url,
                },
                "climate": {
                    "status": climate_res.get("_status"),
                    "action": climate_res.get("route_trade_action"),
                    "severity": climate_res.get("max_severity_score"),
                    "url": self.climate_url,
                },
            },
        }


physical_hazard_bridge = PhysicalHazardBridge()
