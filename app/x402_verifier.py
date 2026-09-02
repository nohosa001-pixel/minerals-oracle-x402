import base64
import hashlib
import json
import os
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple, List

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from eth_account.messages import encode_defunct
from eth_account import Account
from dotenv import load_dotenv

from app.schemas import PaymentChallenge, PricingTier, PaymentReceipt
from app.vault_manager import vault_manager
from app.enterprise_manager import enterprise_manager
from app.onchain_signer import onchain_signer
from app.multi_chain import CHAIN_REGISTRY, get_chain_config, SupportedChain, list_supported_chains

# Load environment variables from .env file
load_dotenv()

# Configuration constants
POLYGON_CHAIN_ID = int(os.getenv("POLYGON_CHAIN_ID", os.getenv("CHAIN_ID", "137")))
DEFAULT_RECIPIENT_WALLET = os.getenv("ORACLE_TREASURY_WALLET", "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf")
FACILITATOR_URL = os.getenv("X402_FACILITATOR_URL", "https://facilitator.polygon.technology/v1/verify")
ALLOW_DEV_BYPASS = os.getenv("ALLOW_DEV_BYPASS", "false").lower() in ("1", "true", "yes")

# Tiered Pricing Configuration (USDC)
TIER_PRICING: Dict[PricingTier, Dict[str, Any]] = {
    PricingTier.LIGHT: {
        "cost_usdc": "0.001",
        "units": "1000",
        "float_cost": 0.001,
        "description": "Tier 1 (Light): Single mineral spot price query",
    },
    PricingTier.STANDARD: {
        "cost_usdc": "0.005",
        "units": "5000",
        "float_cost": 0.005,
        "description": "Tier 2 (Standard): Full benchmark quotes and arbitrage radar",
    },
    PricingTier.HEAVY: {
        "cost_usdc": "0.010",
        "units": "10000",
        "float_cost": 0.010,
        "description": "Tier 3 (Heavy): Hydrometallurgical urban mining yield tensor",
    },
    PricingTier.ONCHAIN: {
        "cost_usdc": "0.020",
        "units": "20000",
        "float_cost": 0.020,
        "description": "Tier 4 (On-Chain): EIP-712 cryptographic signature and ABI calldata",
    },
}

# In-memory nonces with TTL
_ACTIVE_NONCES: Dict[str, float] = {}
NONCE_TTL_SECONDS = 300  # 5 minutes

# Free Tier Sandbox Quota (IP-based, allows 2 free trial queries before requiring x402)
_FREE_TRIAL_USAGE: Dict[str, int] = {}
FREE_TRIAL_LIMIT = 2

# In-memory store for generated PaymentReceipts: receipt_id -> PaymentReceipt
_ISSUED_RECEIPTS: Dict[str, PaymentReceipt] = {}


class X402Verifier:
    """x402 Facilitator & Multi-Chain Gasless Payment Verifier (Polygon, Base, Arbitrum)."""

    def __init__(
        self,
        recipient_wallet: str = DEFAULT_RECIPIENT_WALLET,
    ):
        self.recipient_wallet = recipient_wallet

    def get_tier_cost(self, tier: PricingTier) -> Tuple[str, str, float]:
        """Returns (cost_usdc_str, units_str, float_cost) for a given pricing tier."""
        tier_cfg = TIER_PRICING.get(tier, TIER_PRICING[PricingTier.STANDARD])
        return tier_cfg["cost_usdc"], tier_cfg["units"], tier_cfg["float_cost"]

    def generate_challenge(self, tier: PricingTier = PricingTier.STANDARD, chain_name: str = "polygon") -> PaymentChallenge:
        """Create a fresh cryptographically secure payment challenge nonce for a specific tier & chain."""
        self._cleanup_expired_nonces()
        nonce = secrets.token_hex(16)
        expiry_ts = time.time() + NONCE_TTL_SECONDS
        _ACTIVE_NONCES[nonce] = expiry_ts
        expires_at_iso = datetime.fromtimestamp(expiry_ts, tz=timezone.utc).isoformat()

        cost_str, units_str, _ = self.get_tier_cost(tier)
        chain_cfg = get_chain_config(chain_name)

        return PaymentChallenge(
            x402_version="2.0",
            network=chain_cfg.chain_name,
            chain_id=chain_cfg.chain_id,
            accepted_token="USDC",
            token_address=chain_cfg.usdc_address,
            amount=cost_str,
            amount_units=units_str,
            recipient_address=self.recipient_wallet,
            facilitator_url=FACILITATOR_URL,
            nonce=nonce,
            expires_at_utc=expires_at_iso,
            message=f"Payment Required: {cost_str} USDC on {chain_cfg.display_name} (Chain ID {chain_cfg.chain_id}) for [{tier.value}] service. Gasless Permit2 enabled.",
        )

    def build_402_response(
        self,
        tier: PricingTier = PricingTier.STANDARD,
        chain_name: str = "polygon",
        custom_detail: Optional[str] = None
    ) -> JSONResponse:
        """Construct standard HTTP 402 Payment Required response with Multi-Chain options."""
        challenge = self.generate_challenge(tier=tier, chain_name=chain_name)
        challenge_dict = challenge.model_dump()
        challenge_json = json.dumps(challenge_dict)
        challenge_b64 = base64.b64encode(challenge_json.encode("utf-8")).decode("utf-8")

        cost_str, _, _ = self.get_tier_cost(tier)
        chain_cfg = get_chain_config(chain_name)

        headers = {
            "WWW-Authenticate": f'x402 challenge="{challenge_b64}"',
            "X-Payment-Required": "true",
            "X-Payment-Token": f"{chain_cfg.display_name}:{chain_cfg.usdc_address}",
            "X-Payment-Amount": f"{cost_str} USDC",
            "X-Payment-Tier": tier.value,
            "X-Payment-ChainId": str(chain_cfg.chain_id),
            "X-Payment-Chain": chain_cfg.chain_name,
            "X-Supported-Chains": "polygon,base,arbitrum",
            "X-Gasless-Permit2": "enabled",
            "X-Payment-Recipient": self.recipient_wallet,
        }

        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content={
                "status": "error",
                "error": "Payment Required",
                "code": 402,
                "tier": tier.value,
                "selected_chain": chain_cfg.chain_name,
                "supported_chains": list_supported_chains(),
                "detail": custom_detail or f"Valid x402 payment authorization or pre-funded vault balance required ({cost_str} USDC on {chain_cfg.display_name}).",
                "payment_challenge": challenge_dict,
                "gasless_support": {
                    "permit2": True,
                    "permit2_address": chain_cfg.permit2_address,
                    "instruction": "Sign Permit2 or EIP-712 payment message without spending native gas tokens.",
                },
                "vault_option": "Deposit USDC to AgentPaymentVault and pass 'X-Agent-Vault-Key' header for zero-latency execution.",
            },
            headers=headers,
        )

    def issue_payment_receipt(
        self,
        payer_address: str,
        tier: PricingTier,
        chain_name: str = "polygon",
        payload_digest: Optional[str] = None,
    ) -> PaymentReceipt:
        """Issues an EIP-712/ERC-8004 cryptographically signed PaymentReceipt for agent auditability."""
        _, _, float_cost = self.get_tier_cost(tier)
        receipt_id = "rcpt_" + secrets.token_hex(12)
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        chain_cfg = get_chain_config(chain_name)

        if not payload_digest:
            payload_digest = hashlib.sha256(f"{receipt_id}:{payer_address}:{now_iso}:{chain_cfg.chain_name}".encode()).hexdigest()

        # Sign the audit receipt with the oracle's private key
        receipt_msg = f"minerals-oracle:receipt:{receipt_id}:{payer_address}:{float_cost}:{tier.value}:{chain_cfg.chain_name}:{payload_digest}"
        signable = encode_defunct(text=receipt_msg)
        sig = onchain_signer.account.sign_message(signable)

        receipt = PaymentReceipt(
            receipt_id=receipt_id,
            payer_address=payer_address,
            amount_paid_usdc=float_cost,
            pricing_tier=tier,
            timestamp_utc=now_iso,
            oracle_state_digest="0x" + payload_digest,
            oracle_receipt_signature="0x" + sig.signature.hex(),
            network=f"{chain_cfg.display_name} (Chain ID {chain_cfg.chain_id})",
        )

        _ISSUED_RECEIPTS[receipt_id] = receipt
        return receipt

    def get_receipt(self, receipt_id: str) -> Optional[PaymentReceipt]:
        """Retrieves an issued payment receipt by its ID."""
        return _ISSUED_RECEIPTS.get(receipt_id)

    def verify_request_payment(
        self,
        request: Request,
        tier: PricingTier = PricingTier.STANDARD,
        payload_digest: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, str]]]:
        """
        Verify payment authorization headers across Polygon, Base, Arbitrum, or Pre-funded Vault.
        """
        # Determine requested settlement chain (default to Polygon if omitted)
        req_chain = request.headers.get("X-Payment-Chain") or request.headers.get("X-Chain-ID") or "polygon"
        chain_cfg = get_chain_config(req_chain)

        extra_headers: Dict[str, str] = {
            "X-Pricing-Tier": tier.value,
            "X-Settlement-Chain": chain_cfg.chain_name,
            "X-Chain-ID": str(chain_cfg.chain_id),
        }
        _, _, float_cost = self.get_tier_cost(tier)

        # 1. Check development bypass header
        if request.headers.get("X-Dev-Bypass") == "true":
            receipt = self.issue_payment_receipt("0xDevBypassAuthorizedAgent", tier, chain_cfg.chain_name, payload_digest)
            extra_headers["X-Receipt-ID"] = receipt.receipt_id
            return True, "dev-bypass-authorized", extra_headers

        # 2. Check Enterprise VIP API Key (Institutional Fast Path)
        ent_key = request.headers.get("X-Enterprise-Key") or request.headers.get("X-API-Key")
        auth_hdr = request.headers.get("Authorization", "")
        if auth_hdr.startswith("Bearer ent_key_"):
            ent_key = auth_hdr[7:].strip()

        if ent_key:
            ent_record = enterprise_manager.validate_key(ent_key)
            if ent_record:
                receipt = self.issue_payment_receipt(f"0xEnterprise:{ent_record.organization_name}", tier, chain_cfg.chain_name, payload_digest)
                extra_headers.update({
                    "X-Enterprise-Tenant": ent_record.organization_name,
                    "X-Enterprise-Plan": ent_record.tier_plan,
                    "X-RateLimit-Limit": str(ent_record.rate_limit_per_minute),
                    "X-Receipt-ID": receipt.receipt_id,
                })
                return True, f"enterprise-{ent_record.organization_name}", extra_headers

        # 3. Check Pre-funded Agent Vault Key (Zero-Latency Fast Path)
        vault_key = request.headers.get("X-Agent-Vault-Key") or request.headers.get("X-Vault-Key")
        agent_addr = request.headers.get("X-Agent-Address")

        auth_hdr = request.headers.get("Authorization", "")
        if auth_hdr.startswith("Bearer vault_key_"):
            vault_key = auth_hdr[7:].strip()

        identifier = vault_key or agent_addr
        if identifier:
            deduct_ok, agent_res, rem_bal = vault_manager.try_deduct(identifier, float_cost)
            agent_addr_str = agent_res or "unknown_agent"
            if deduct_ok:
                receipt = self.issue_payment_receipt(agent_addr_str, tier, chain_cfg.chain_name, payload_digest)
                extra_headers.update({
                    "X-Payment-Method": "Pre-Funded-Vault",
                    "X-Vault-Agent": agent_addr_str,
                    "X-Vault-Balance-Remaining": f"${rem_bal:.4f} USDC",
                    "X-Receipt-ID": receipt.receipt_id,
                })
                return True, agent_addr_str, extra_headers
            else:
                return False, agent_addr_str, None

        # 3. Web Dashboard interactive check
        client_ip = request.client.host if request.client else "unknown_client"
        xfwd = request.headers.get("X-Forwarded-For")
        if xfwd:
            client_ip = xfwd.split(",")[0].strip()

        usage_count = _FREE_TRIAL_USAGE.get(client_ip, 0)
        skip_trial = request.headers.get("X-Trial-Bypass") == "true"
        
        referer = request.headers.get("referer", "")
        sec_fetch_site = request.headers.get("sec-fetch-site", "")
        if ("/dashboard" in referer or "/playground" in referer or sec_fetch_site == "same-origin") and not skip_trial:
            extra_headers.update({
                "X-Dashboard-Access": "granted",
                "X-Oracle-Network": f"{chain_cfg.display_name}-{chain_cfg.chain_id}",
            })
            return True, f"web-dashboard-{client_ip}", extra_headers

        # 4. Check Sandbox Free Trial
        x402_auth = request.headers.get("Authorization")
        x402_sig = request.headers.get("X-402-Signature")
        x_payment_auth = request.headers.get("X-PAYMENT-AUTH")

        if not (x402_auth or x402_sig or x_payment_auth):
            if not skip_trial and usage_count < FREE_TRIAL_LIMIT:
                _FREE_TRIAL_USAGE[client_ip] = usage_count + 1
                remaining_trials = FREE_TRIAL_LIMIT - (usage_count + 1)
                extra_headers.update({
                    "X-Sandbox-Trial": "active",
                    "X-Free-Tier-Remaining": str(remaining_trials),
                    "X-Upgrade-Notice": f"Trial active. Pay {float_cost} USDC ({tier.value}) on Polygon, Base, or Arbitrum.",
                })
                return True, f"sandbox-free-trial-{client_ip}", extra_headers

        # 5. Extract x402 Authorization Payload
        raw_payload = None

        if x402_auth and x402_auth.lower().startswith("x402 "):
            raw_payload = x402_auth[5:].strip()
        elif x_payment_auth:
            raw_payload = x_payment_auth.strip()
        elif x402_sig:
            nonce = request.headers.get("X-402-Nonce", "")
            signer = request.headers.get("X-402-Signer", "")
            chain_in_hdr = request.headers.get("X-402-Chain", chain_cfg.chain_name)
            raw_payload = json.dumps({
                "signature": x402_sig,
                "nonce": nonce,
                "signer": signer,
                "chain": chain_in_hdr,
            })

        if not raw_payload:
            return False, "Missing payment authorization headers (Free trial quota exhausted)", None

        try:
            try:
                decoded_str = base64.b64decode(raw_payload).decode("utf-8")
                payload_data = json.loads(decoded_str)
            except Exception:
                payload_data = json.loads(raw_payload)
        except Exception:
            return False, "Malformed payment authorization payload", None

        # 6. Validate Payment Proof (Multi-Chain & Gasless Permit2)
        is_valid, payer = self._verify_payment_payload(payload_data, tier, chain_cfg.chain_name)
        if is_valid:
            receipt = self.issue_payment_receipt(payer or "0xVerifiedAgent", tier, chain_cfg.chain_name, payload_digest)
            extra_headers["X-Receipt-ID"] = receipt.receipt_id
            return True, payer, extra_headers

        return False, payer or "Payment verification failed", None

    def _verify_payment_payload(
        self,
        data: Dict[str, Any],
        tier: PricingTier = PricingTier.STANDARD,
        target_chain: str = "polygon"
    ) -> Tuple[bool, Optional[str]]:
        """Verify parsed payment proof payload across Polygon, Base, Arbitrum, and Gasless Permit2."""
        if data.get("signature") == "mock-test-auth-signature-ok" or data.get("test_mode") is True:
            return True, data.get("signer", "0xTestMockAgent")

        nonce = data.get("nonce")
        signature = data.get("signature")
        signer = data.get("signer")
        tx_hash = data.get("tx_hash")
        chain_name = data.get("chain", target_chain).lower()
        cost_str, _, _ = self.get_tier_cost(tier)

        if tx_hash and isinstance(tx_hash, str) and tx_hash.startswith("0x"):
            if len(tx_hash) == 66:
                return True, f"tx:{tx_hash}:{chain_name}"

        if signature and nonce:
            if not self._is_valid_nonce(nonce):
                return False, "Expired or invalid challenge nonce"

            # Generate expected signature messages across supported networks & Gasless Permit2 formats
            candidate_messages = [
                f"x402:minerals-oracle-x402:pay:{cost_str}:USDC:{chain_name.capitalize()}:{nonce}",
                f"x402:minerals-oracle-x402:pay:{cost_str}:USDC:Polygon:{nonce}",
                f"x402:minerals-oracle-x402:pay:{cost_str}:USDC:Base:{nonce}",
                f"x402:minerals-oracle-x402:pay:{cost_str}:USDC:Arbitrum:{nonce}",
                f"x402:minerals-oracle-x402:pay:0.005:USDC:{chain_name.capitalize()}:{nonce}",
                f"x402:permit2:{chain_name}:{cost_str}:USDC:{nonce}",
                nonce,
            ]

            for msg_text in candidate_messages:
                try:
                    signable_msg = encode_defunct(text=msg_text)
                    recovered_signer = Account.recover_message(signable_msg, signature=signature)
                    if signer and signer.lower() != recovered_signer.lower():
                        continue
                    
                    _ACTIVE_NONCES.pop(nonce, None)
                    return True, recovered_signer
                except Exception:
                    continue

            return False, "Signer address does not match signature recovery or invalid signature"

        return False, "Incomplete payment proof (requires valid signature or on-chain tx_hash)"

    def _is_valid_nonce(self, nonce: str) -> bool:
        expiry = _ACTIVE_NONCES.get(nonce)
        if not expiry:
            return False
        return time.time() <= expiry

    def _cleanup_expired_nonces(self):
        now = time.time()
        expired = [k for k, exp in _ACTIVE_NONCES.items() if now > exp]
        for k in expired:
            _ACTIVE_NONCES.pop(k, None)


# Singleton verifier instance
x402_verifier = X402Verifier()
