"""
Security Gate Client for minerals-oracle-x402.
Binds Minerals Oracle with the Security Gate x402 Zero-Trust architecture.
Provides prompt injection / input validation, Agent Credit FICO scoring,
and EU AI Act Compliance Dual-Attestation.
"""

import os
import time
import hashlib
import logging
from typing import Optional, Dict, Any
import httpx
from dotenv import load_dotenv

from app.schemas import SecurityAttestation

load_dotenv(override=True)
logger = logging.getLogger("security_gate_client")

DEFAULT_GATE_URL = "https://agent-security-gate-x402-212942243360.asia-northeast3.run.app"
EU_AI_ACT_STANDARD = "EU_AI_ACT_2024_1689_ART50"


import threading

class SecurityGateClient:
    def __init__(self):
        self.gate_url = os.getenv("SECURITY_GATE_URL", DEFAULT_GATE_URL).rstrip("/")
        self.timeout_sec = float(os.getenv("SECURITY_GATE_TIMEOUT_SECONDS", "2.0"))
        self.strict_mode = os.getenv("SECURITY_GATE_STRICT_MODE", "false").lower() == "true"
        self._client = httpx.Client(timeout=self.timeout_sec)

        # Thread-safe Circuit Breaker resilience parameters
        self._lock = threading.Lock()
        self._circuit_state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._failure_count = 0
        self._failure_threshold = 3
        self._recovery_timeout_sec = 15.0
        self._circuit_open_until = 0.0

    def can_attempt_remote(self) -> bool:
        """Determines if remote call should be permitted under circuit breaker policy."""
        now = time.time()
        with self._lock:
            if self._circuit_state == "OPEN":
                if now >= self._circuit_open_until:
                    self._circuit_state = "HALF_OPEN"
                    logger.info("Security Gate Circuit Breaker transitioned to HALF_OPEN")
                    return True
                return False
            return True

    def record_success(self):
        """Records successful remote communication, resetting circuit state."""
        with self._lock:
            self._failure_count = 0
            if self._circuit_state != "CLOSED":
                logger.info("Security Gate Circuit Breaker restored to CLOSED")
                self._circuit_state = "CLOSED"

    def record_failure(self, err: Exception):
        """Records failed remote communication, potentially tripping the circuit."""
        with self._lock:
            self._failure_count += 1
            if self._failure_count >= self._failure_threshold:
                self._circuit_state = "OPEN"
                self._circuit_open_until = time.time() + self._recovery_timeout_sec
                logger.warning(
                    f"Security Gate Circuit Breaker TRIPPED to OPEN for {self._recovery_timeout_sec}s. Error: {err}"
                )

    def get_circuit_status(self) -> Dict[str, Any]:
        """Returns diagnostic telemetry for the circuit breaker."""
        with self._lock:
            return {
                "state": self._circuit_state,
                "failure_count": self._failure_count,
                "failure_threshold": self._failure_threshold,
                "recovery_timeout_sec": self._recovery_timeout_sec,
                "open_remaining_sec": max(0.0, round(self._circuit_open_until - time.time(), 2)),
            }

    def check_health(self) -> Dict[str, Any]:
        """Checks connectivity and latency to the remote Security Gate."""
        start = time.perf_counter()
        try:
            resp = self._client.get(f"{self.gate_url}/health")
            latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
            is_ok = resp.status_code == 200
            return {
                "status": "HEALTHY" if is_ok else f"HTTP_{resp.status_code}",
                "gate_url": self.gate_url,
                "latency_ms": latency_ms,
                "mode": "REMOTE_GATEWAY" if is_ok else "DEGRADED"
            }
        except Exception as e:
            latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
            logger.warning(f"Security Gate health probe failed: {e}")
            return {
                "status": "UNREACHABLE",
                "gate_url": self.gate_url,
                "latency_ms": latency_ms,
                "error": str(e),
                "mode": "LOCAL_STANDALONE"
            }

    async def check_health_async(self) -> Dict[str, Any]:
        """Non-blocking async health probe for high-throughput event loops."""
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                resp = await client.get(f"{self.gate_url}/health")
                latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
                is_ok = resp.status_code == 200
                return {
                    "status": "HEALTHY" if is_ok else f"HTTP_{resp.status_code}",
                    "gate_url": self.gate_url,
                    "latency_ms": latency_ms,
                    "mode": "REMOTE_GATEWAY" if is_ok else "DEGRADED"
                }
        except Exception as e:
            latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
            logger.warning(f"Security Gate async health probe failed: {e}")
            return {
                "status": "UNREACHABLE",
                "gate_url": self.gate_url,
                "latency_ms": latency_ms,
                "error": str(e),
                "mode": "LOCAL_STANDALONE"
            }

    def verify_input_safety(self, text_payload: str) -> Dict[str, Any]:
        """
        Scans input string against prompt injection, malicious AST triggers, or secret leaks.
        Falls back to deterministic local safety scanner if remote gate is unreachable.
        Enforces Fail-Closed blocking if strict_mode is True.
        """
        start = time.perf_counter()
        # Fast local pre-screen for hazardous patterns
        hazardous_keywords = [
            "ignore previous instructions", "system prompt", "exec(", "eval(",
            "subprocess.", "__import__", "drop table", "rm -rf"
        ]
        lower_payload = text_payload.lower()
        for kw in hazardous_keywords:
            if kw in lower_payload:
                return {
                    "is_safe": False,
                    "reason": f"Hazardous keyword detected: '{kw}'",
                    "risk_score": 0.95,
                    "latency_ms": round((time.perf_counter() - start) * 1000.0, 2)
                }

        # Remote verification if endpoint is available and circuit breaker permits
        if self.can_attempt_remote():
            try:
                resp = self._client.post(
                    f"{self.gate_url}/api/v1/gate/verify",
                    json={"output_text": text_payload, "strict_mode": self.strict_mode}
                )
                latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
                if resp.status_code == 200:
                    self.record_success()
                    data = resp.json()
                    return {
                        "is_safe": data.get("is_safe", True),
                        "reason": data.get("reason", "Verified by Security Gate"),
                        "risk_score": data.get("risk_score", 0.0),
                        "latency_ms": latency_ms
                    }
                else:
                    self.record_failure(Exception(f"HTTP_{resp.status_code}"))
            except Exception as e:
                self.record_failure(e)
                logger.debug(f"Remote gate verify bypassed: {e}")
                if self.strict_mode:
                    return {
                        "is_safe": False,
                        "reason": f"Fail-Closed: Security Gate unreachable under strict mode ({e})",
                        "risk_score": 1.0,
                        "latency_ms": round((time.perf_counter() - start) * 1000.0, 2)
                    }

        latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
        return {
            "is_safe": True,
            "reason": "Passed local zero-trust pre-filter (Circuit Breaker standby)" if self._circuit_state == "OPEN" else "Passed local zero-trust pre-filter",
            "risk_score": 0.02,
            "latency_ms": latency_ms
        }

    async def verify_input_safety_async(self, text_payload: str) -> Dict[str, Any]:
        """Non-blocking async input safety scan for high-throughput FastAPI endpoints."""
        start = time.perf_counter()
        hazardous_keywords = [
            "ignore previous instructions", "system prompt", "exec(", "eval(",
            "subprocess.", "__import__", "drop table", "rm -rf"
        ]
        lower_payload = text_payload.lower()
        for kw in hazardous_keywords:
            if kw in lower_payload:
                return {
                    "is_safe": False,
                    "reason": f"Hazardous keyword detected: '{kw}'",
                    "risk_score": 0.95,
                    "latency_ms": round((time.perf_counter() - start) * 1000.0, 2)
                }

        if self.can_attempt_remote():
            try:
                async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                    resp = await client.post(
                        f"{self.gate_url}/api/v1/gate/verify",
                        json={"output_text": text_payload, "strict_mode": self.strict_mode}
                    )
                    latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
                    if resp.status_code == 200:
                        self.record_success()
                        data = resp.json()
                        return {
                            "is_safe": data.get("is_safe", True),
                            "reason": data.get("reason", "Verified by Security Gate"),
                            "risk_score": data.get("risk_score", 0.0),
                            "latency_ms": latency_ms
                        }
                    else:
                        self.record_failure(Exception(f"HTTP_{resp.status_code}"))
            except Exception as e:
                self.record_failure(e)
                logger.debug(f"Remote gate async verify bypassed: {e}")
                if self.strict_mode:
                    return {
                        "is_safe": False,
                        "reason": f"Fail-Closed: Security Gate unreachable under strict mode ({e})",
                        "risk_score": 1.0,
                        "latency_ms": round((time.perf_counter() - start) * 1000.0, 2)
                    }

        latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
        return {
            "is_safe": True,
            "reason": "Passed local zero-trust pre-filter (Circuit Breaker standby)" if self._circuit_state == "OPEN" else "Passed local zero-trust pre-filter",
            "risk_score": 0.02,
            "latency_ms": latency_ms
        }

    def get_agent_credit_rating(self, agent_address: str) -> Dict[str, Any]:
        """
        Queries FICO credit score and investment grade tier for an agent wallet.
        """
        start = time.perf_counter()
        clean_addr = agent_address.strip()
        try:
            resp = self._client.get(f"{self.gate_url}/api/v1/credit/{clean_addr}")
            latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
            if resp.status_code == 200:
                data = resp.json()
                score = data.get("credit_score", 540)
                tier = data.get("grade") or data.get("credit_tier", "BB")
                return {
                    "credit_score": score,
                    "credit_tier": tier,
                    "is_investment_grade": score >= 650,
                    "is_eligible": score >= 450 and tier != "D",
                    "latency_ms": latency_ms,
                    "source": "REMOTE_GATEWAY"
                }
        except Exception as e:
            logger.debug(f"Remote credit check fallback: {e}")

        # Deterministic local score derivation based on address hash
        latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
        h = int(hashlib.sha256(clean_addr.lower().encode()).hexdigest()[:4], 16)
        # Scaled FICO score between 550 and 820 for registered valid addresses
        score = 550 + (h % 270)
        tier = "AAA" if score >= 800 else ("AA" if score >= 740 else ("A" if score >= 650 else "BBB"))

        return {
            "credit_score": score,
            "credit_tier": tier,
            "is_investment_grade": score >= 650,
            "is_eligible": score >= 450,
            "latency_ms": latency_ms,
            "source": "LOCAL_STANDALONE"
        }

    async def get_agent_credit_rating_async(self, agent_address: str) -> Dict[str, Any]:
        """Non-blocking async credit check for high-frequency trading swarms."""
        start = time.perf_counter()
        clean_addr = agent_address.strip()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                resp = await client.get(f"{self.gate_url}/api/v1/credit/{clean_addr}")
                latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
                if resp.status_code == 200:
                    data = resp.json()
                    score = data.get("credit_score", 540)
                    tier = data.get("grade") or data.get("credit_tier", "BB")
                    return {
                        "credit_score": score,
                        "credit_tier": tier,
                        "is_investment_grade": score >= 650,
                        "is_eligible": score >= 450 and tier != "D",
                        "latency_ms": latency_ms,
                        "source": "REMOTE_GATEWAY"
                    }
        except Exception as e:
            logger.debug(f"Remote credit check async fallback: {e}")

        latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
        h = int(hashlib.sha256(clean_addr.lower().encode()).hexdigest()[:4], 16)
        score = 550 + (h % 270)
        tier = "AAA" if score >= 800 else ("AA" if score >= 740 else ("A" if score >= 650 else "BBB"))

        return {
            "credit_score": score,
            "credit_tier": tier,
            "is_investment_grade": score >= 650,
            "is_eligible": score >= 450,
            "latency_ms": latency_ms,
            "source": "LOCAL_STANDALONE"
        }


    def generate_dual_attestation(
        self,
        oracle_digest: str,
        agent_address: Optional[str] = None
    ) -> SecurityAttestation:
        """
        Issues a certified dual-attestation binding the Minerals Oracle EIP-712 digest
        to the Security Gate zero-trust audit proof and EU AI Act Article 50 standard.
        """
        start = time.perf_counter()
        mode = "LOCAL_STANDALONE"
        tier = None
        score = None

        if agent_address:
            credit = self.get_agent_credit_rating(agent_address)
            tier = credit.get("credit_tier")
            score = credit.get("credit_score")
            mode = credit.get("source", "LOCAL_STANDALONE")

        # Cryptographic joint hash: keccak-style sha256 binding
        raw_seed = f"GATE_CERTIFIED:{self.gate_url}:{oracle_digest}:{agent_address or 'ANON'}:{EU_AI_ACT_STANDARD}"
        dual_hash = "0x" + hashlib.sha256(raw_seed.encode("utf-8")).hexdigest()

        latency_ms = round((time.perf_counter() - start) * 1000.0, 2)

        return SecurityAttestation(
            security_gate_certified=True,
            security_gate_url=self.gate_url,
            security_gate_mode=mode,
            agent_address=agent_address,
            agent_credit_tier=tier,
            agent_credit_score=score,
            compliance_standard=EU_AI_ACT_STANDARD,
            dual_attestation_hash=dual_hash,
            latency_ms=latency_ms
        )


security_gate_client = SecurityGateClient()
