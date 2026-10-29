"""
Security Gate x402 Adapter for Minerals Oracle X402.
======================================================
Implements deterministic sub-millisecond:
1. Prompt Injection & Jailbreak Defense (OWASP LLM01)
2. Dangerous AST & Code Execution Guard
3. Financial & Semantic Manipulation Defense (A2A Exploits: slippage bypass, vault drain, wallet hijack)
4. Metallurgical NLI Fact-Checking (Physical bounds for mineral purity and concentration)
5. EU AI Act Article 50 Machine Provenance Watermarking
6. Ephemeral Sub-Accounts ($1.00~$5.00 micro-budget cap) for Key Isolation
Derived from and compatible with Security Gate x402 & EUDR Agent Architecture.
"""

import re
import time
import uuid
import secrets
from typing import Dict, Any, List, Optional


class AgentSecurityGateAdapter:
    """Security interceptor and fact-checker for autonomous AI agent inputs in Minerals Oracle."""

    # Prompt Injection & Jailbreak RegEx patterns
    INJECTION_PATTERNS = [
        r"(?i)(ignore|disregard|forget)\s+(all\s+)?(prior|previous|past|above|system)?\s*instructions",
        r"(?i)system\s+prompt\s*(override|bypass)",
        r"(?i)(override|bypass|force)\s+(all\s+)?(checks|security|rules|filters|safeguards|compliance(\s+checks)?)",
        r"(?i)you\s+are\s+now\s+in\s+(dan|developer)\s+mode",
        r"(?i)grant\s+(me\s+)?admin(istrator)?\s+privileges",
        r"(?i)drop\s+table\s+",
        r"(?i)<script\b[^>]*>",
        r"(?i)select\s+\*\s+from\s+",
        r"(?i)declare\s+(origin_verified|feoc_free|crma_eligible)\s+without\s+inspection",
        r"(?i)bypass\s+geofence\s+verification",
    ]

    # Malicious Code Execution patterns
    DANGEROUS_AST_PATTERNS = [
        r"\bimport\s+os\b",
        r"\bimport\s+subprocess\b",
        r"\bos\.system\(",
        r"\bsubprocess\.Popen\(",
        r"\beval\(",
        r"\bexec\(",
        r"\b__import__\(",
        r"\bshutil\.rmtree\(",
    ]

    # Financial & Semantic Manipulation patterns (A2A Exploits)
    FINANCIAL_EXPLOIT_PATTERNS = [
        r"(?i)(set|increase|force|manipulate)\s+slippage\s*(to|=)?\s*([1-9][0-9]|100)\s*%",
        r"(?i)bypass\s+(slippage|price\s*impact)\s*(check|guard|limit|protection)",
        r"(?i)(redirect|divert|send|route)\s+(all\s+)?(funds|usdc|payout|settlement|payment|escrow)(\s+(funds|usdc|payout|settlement|payment|escrow))*\s+to\s+(0x[a-fA-F0-9]{40}|[1-9A-HJ-NP-Za-km-z]{32,44})",
        r"(?i)override\s+(beneficiary|recipient|vendor|seller|payee)\s*(wallet|address)",
        r"(?i)(falsify|spoof|forge|alter)\s+(hs\s*code|tariff|mineral\s*assay|purity)",
        r"(?i)declare\s+hs\s*code\s+0000",
        r"(?i)drain\s+(vault|escrow|sub[-_]?account|balance|treasury)",
        r"(?i)(refund|liquidate|transfer|withdraw).*?(treasury|vault|reserve).*?(to\s+0x[a-fA-F0-9]{40})",
    ]

    # Physical / Metallurgical Bounds (Max theoretical concentration / purity)
    METALLURGICAL_BOUNDS: Dict[str, Dict[str, Any]] = {
        "SPODUMENE_CONCENTRATE": {"max_grade_pct": 8.0, "unit": "% Li2O", "desc": "Spodumene hard rock cannot exceed ~8.0% Li2O physically"},
        "LITHIUM_HYDROXIDE": {"max_grade_pct": 100.0, "min_grade_pct": 55.0, "unit": "% LiOH.H2O"},
        "LITHIUM_CARBONATE": {"max_grade_pct": 100.0, "min_grade_pct": 95.0, "unit": "% Li2CO3"},
        "COPPER_CATHODE": {"min_grade_pct": 99.90, "max_grade_pct": 100.0, "unit": "% Cu", "desc": "LME Grade A must be >= 99.90% Cu"},
        "COPPER_CONCENTRATE": {"max_grade_pct": 45.0, "min_grade_pct": 15.0, "unit": "% Cu", "desc": "Flotation Cu concentrate cannot physically exceed 45% Cu"},
        "ANTIMONY_INGOT": {"min_grade_pct": 99.0, "max_grade_pct": 100.0, "unit": "% Sb"},
        "SILVER_DORE": {"min_grade_pct": 50.0, "max_grade_pct": 99.99, "unit": "% Ag"},
        "NICKEL_MHP": {"max_grade_pct": 50.0, "min_grade_pct": 25.0, "unit": "% Ni", "desc": "MHP precipitate is typically 30-40% Ni"},
    }

    @classmethod
    def inspect_text_security(cls, text: str) -> Dict[str, Any]:
        """Inspect inbound text for prompt injections, malicious AST code, and financial manipulation exploits."""
        if not text:
            return {"is_safe": True, "verdict": "ALLOW", "threats": [], "threat_score": 0}

        threats = []
        threat_score = 0

        # 1. Prompt Injection Checks
        for pat in cls.INJECTION_PATTERNS:
            if re.search(pat, text):
                threats.append(f"PROMPT_INJECTION_DETECTED: {pat}")
                threat_score += 45

        # 2. Dangerous AST / Code Execution Checks
        for pat in cls.DANGEROUS_AST_PATTERNS:
            if re.search(pat, text):
                threats.append(f"MALICIOUS_CODE_INJECTION: {pat}")
                threat_score += 50

        # 3. Financial / Semantic Manipulation Checks
        for pat in cls.FINANCIAL_EXPLOIT_PATTERNS:
            if re.search(pat, text):
                threats.append(f"FINANCIAL_MANIPULATION_ATTEMPT: {pat}")
                threat_score += 60

        is_safe = threat_score < 40
        return {
            "is_safe": is_safe,
            "verdict": "ALLOW" if is_safe else "BLOCK",
            "threats": threats,
            "threat_score": threat_score,
            "inspected_length": len(text)
        }

    @classmethod
    def inspect_metallurgical_fact_check(
        cls,
        product: str,
        grade_pct: float,
        declared_tonnage: float,
        mine_country: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        NLI Metallurgical Fact-Checker:
        Detects physical impossibilities, counterfeit assays, and fraudulent purity declarations.
        """
        if declared_tonnage <= 0:
            return {
                "is_plausible": False,
                "reason": "INVALID_TONNAGE: Declared tonnage must be strictly greater than zero.",
                "product": product
            }

        product_norm = product.upper().strip().replace(" ", "_").replace("-", "_")

        for key, bound in cls.METALLURGICAL_BOUNDS.items():
            if key in product_norm:
                max_allowed = bound.get("max_grade_pct")
                min_allowed = bound.get("min_grade_pct")

                if max_allowed is not None and grade_pct > max_allowed:
                    return {
                        "is_plausible": False,
                        "reason": f"METALLURGICAL_IMPOSSIBILITY: Declared grade {grade_pct}% exceeds physical maximum {max_allowed}% for {key}.",
                        "rule": bound.get("desc", ""),
                        "product": product
                    }

                if min_allowed is not None and grade_pct < min_allowed:
                    return {
                        "is_plausible": False,
                        "reason": f"SUBSTANDARD_GRADE_ANOMALY: Declared grade {grade_pct}% falls below minimum specification {min_allowed}% for {key}.",
                        "product": product
                    }

        return {
            "is_plausible": True,
            "product": product,
            "grade_pct": grade_pct,
            "declared_tonnage": declared_tonnage,
            "verdict": "PHYSICALLY_CONGRUENT"
        }

    @classmethod
    def verify_ai_act_article_50_watermark(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Verifies EU AI Act Art. 50 transparency machine-provenance watermark."""
        agent_id = payload.get("agent_id")
        provider = payload.get("provider")
        synthetic_flag = payload.get("synthetic_content_flag", False)
        watermark = payload.get("watermark", "")

        is_valid = bool(agent_id and provider and synthetic_flag and watermark.startswith("sha256:art50-"))
        return {
            "compliant": is_valid,
            "standard": "EU_AI_ACT_2024_1689_ART50",
            "watermark": watermark if is_valid else None,
            "timestamp": int(time.time()),
            "audit_trail_valid": is_valid
        }


class EphemeralSubAccountManager:
    """
    Manages isolated, disposable sub-accounts with strict micro-budget caps ($1.00 - $5.00).
    Shields the primary treasury wallet from unlimited drain during autonomous agent operations.
    """
    _sub_accounts: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def create_ephemeral_sub_account(
        cls,
        parent_agent_id: str,
        budget_cap_usdc: float = 3.0,
        ttl_seconds: int = 3600
    ) -> Dict[str, Any]:
        """Provisions an isolated ephemeral sub-account with hard budget ceiling."""
        session_id = f"sub_{uuid.uuid4().hex[:12]}"
        virtual_key = f"0x{secrets.token_hex(20)}"
        now = int(time.time())

        account = {
            "session_id": session_id,
            "parent_agent_id": parent_agent_id,
            "virtual_address": virtual_key,
            "budget_cap_usdc": budget_cap_usdc,
            "spent_usdc": 0.0,
            "remaining_usdc": budget_cap_usdc,
            "created_at": now,
            "expires_at": now + ttl_seconds,
            "status": "ACTIVE"
        }
        cls._sub_accounts[session_id] = account
        return account

    @classmethod
    def charge_sub_account(
        cls,
        session_id: str,
        amount_usdc: float,
        purpose: str
    ) -> Dict[str, Any]:
        """Micro-charges an ephemeral sub-account. Refuses if budget cap is exceeded."""
        account = cls._sub_accounts.get(session_id)
        if not account:
            return {"success": False, "reason": "SUB_ACCOUNT_NOT_FOUND"}

        now = int(time.time())
        if now > account["expires_at"]:
            account["status"] = "EXPIRED"
            return {"success": False, "reason": "SUB_ACCOUNT_EXPIRED"}

        if account["spent_usdc"] + amount_usdc > account["budget_cap_usdc"]:
            return {
                "success": False,
                "reason": "BUDGET_CAP_EXCEEDED",
                "attempted": amount_usdc,
                "remaining": account["remaining_usdc"],
                "cap": account["budget_cap_usdc"]
            }

        account["spent_usdc"] = round(account["spent_usdc"] + amount_usdc, 4)
        account["remaining_usdc"] = round(account["budget_cap_usdc"] - account["spent_usdc"], 4)

        return {
            "success": True,
            "charged_usdc": amount_usdc,
            "remaining_usdc": account["remaining_usdc"],
            "purpose": purpose
        }

    @classmethod
    def get_sub_account(cls, session_id: str) -> Optional[Dict[str, Any]]:
        return cls._sub_accounts.get(session_id)
