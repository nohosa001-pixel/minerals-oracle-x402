"""
Minerals & Battery Passport Fast Verifier powered by Gemini Decisions API (gemini-decision-1).
Evaluates ESG audit PDFs, RMAP smelter certificates, and battery chemistry dossiers
in ~150-250ms with zero output tokens.
"""

import os
import time
from typing import Any, Dict, List, Optional

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


class MineralsDecisionsVerifier:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model = "gemini-decision-1"
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not HAS_GENAI or not self.api_key:
            return None
        self._client = genai.Client(
            api_key=self.api_key,
            http_options={"api_version": "v1beta"},
        )
        return self._client

    def fast_verify(
        self,
        document_text: Optional[str] = None,
        file_uri: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Evaluate ESG/RMAP/Battery Passport compliance in a single forward pass."""
        start_t = time.perf_counter()
        client = self._get_client()

        if client is None or not hasattr(client, "decisions"):
            return {
                "engine": "deterministic_fallback",
                "decisions_api_active": False,
                "passport_eligible": False,
                "reason": "GEMINI_API_KEY missing or google-genai<3.5.0",
                "latency_ms": round((time.perf_counter() - start_t) * 1000.0, 2),
            }

        inputs: List[Dict[str, Any]] = []
        if document_text:
            inputs.append({"type": "text", "text": document_text})
        if file_uri:
            item: Dict[str, Any] = {"type": "file", "uri": file_uri}
            if mime_type:
                item["mime_type"] = mime_type
            inputs.append(item)

        if not inputs:
            return {
                "engine": self.model,
                "decisions_api_active": True,
                "passport_eligible": False,
                "reason": "Empty mineral dossier input",
                "latency_ms": round((time.perf_counter() - start_t) * 1000.0, 2),
            }

        questions = {
            "is_rmap_conformant": {
                "type": "noul",
                "instructions": "Does the document confirm Responsible Minerals Assurance Process (RMAP) or RMI conformant smelter/refiner status?",
            },
            "is_conflict_free": {
                "type": "noul",
                "instructions": "Does the evidence verify conflict-free and forced-labor-free mineral sourcing (OECD Due Diligence / EU Battery Reg)?",
            },
            "has_carbon_footprint": {
                "type": "noul",
                "instructions": "Does the dossier disclose cradle-to-gate carbon footprint or Scope 1/2/3 emissions?",
            },
            "chemistry_profile": {
                "type": "choice",
                "instructions": "Identify the primary battery chemistry or mineral supply chain profile.",
                "criteria": {
                    "NCM811": "High-nickel Nickel-Cobalt-Manganese (NCM811 / NCM) battery supply chain.",
                    "NCA": "Nickel-Cobalt-Aluminum (NCA) battery supply chain.",
                    "LFP": "Lithium Iron Phosphate (LFP) battery supply chain.",
                    "SOLID_STATE": "All-Solid-State Battery (ASB / Solid-State) or sulfide electrolyte supply chain.",
                    "RAW_MINERAL": "General critical mineral (Lithium, Cobalt, Nickel, Copper, Graphite, Rare Earth) without specific cell chemistry.",
                },
            },
            "esg_compliance_score": {
                "type": "score",
                "instructions": "Rate the overall EU Battery Passport & ESG audit readiness of this dossier.",
                "criteria": [
                    "Non-compliant: missing smelter origin, ESG audit, or conflict-free attestation.",
                    "Partial: valid origin or chemistry, missing carbon footprint or third-party RMAP sign-off.",
                    "Full EU Battery Passport ready: verified RMAP, conflict-free, carbon footprint, and traceable origin.",
                ],
            },
        }

        try:
            res = client.decisions.create(
                model=self.model,
                input=inputs,
                questions=questions,
            )
            elapsed_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
            ans = res.answers

            rmap = float(getattr(ans.get("is_rmap_conformant"), "noul", 0.0))
            conflict_free = float(getattr(ans.get("is_conflict_free"), "noul", 0.0))
            carbon = float(getattr(ans.get("has_carbon_footprint"), "noul", 0.0))
            chem = getattr(ans.get("chemistry_profile"), "choice", "RAW_MINERAL")
            esg_score = float(getattr(ans.get("esg_compliance_score"), "score", 0.0))

            eligible = rmap >= 0.6 and conflict_free >= 0.6

            return {
                "engine": self.model,
                "decisions_api_active": True,
                "passport_eligible": eligible,
                "chemistry_profile": chem,
                "esg_compliance_score": round(esg_score, 4),
                "checks": {
                    "is_rmap_conformant": round(rmap, 4),
                    "is_conflict_free": round(conflict_free, 4),
                    "has_carbon_footprint": round(carbon, 4),
                },
                "output_tokens_used": 0,
                "latency_ms": elapsed_ms,
            }
        except Exception as exc:
            return {
                "engine": "deterministic_fallback",
                "decisions_api_active": False,
                "passport_eligible": False,
                "reason": str(exc),
                "latency_ms": round((time.perf_counter() - start_t) * 1000.0, 2),
            }


minerals_decisions_verifier = MineralsDecisionsVerifier()
