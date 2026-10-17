"""
A2A (Agent-to-Agent) Autonomous Trade Negotiation, Bilateral Deals & Escrow Router.
"""
import time
import hashlib
import secrets
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Request, HTTPException, status, Query, Path as FPath

from app.schemas import (
    TradeDealSpec,
    TradeDealProposeRequest,
    TradeDealDualSignRequest,
    TradeDealRejectRequest,
    TradeDealCancelRequest,
    TradeDealAttestation,
    TradeDealVerifyRequest,
    TradeDealVerifyResponse,
    TradeDealListResponse,
    AgentSessionOpenRequest,
    AgentSessionResponse,
    AgentSessionCloseRequest,
    AgentSessionCloseResponse,
    AgentSessionInfoResponse,
    AgentRegisterRequest,
    AgentRegisterResponse,
    VaultBalanceResponse,
    ReceiptVerifyRequest,
    PaymentReceipt,
    PricingTier,
    ProcurementRFQRequest,
    ProcurementRFQResponse,
    VaultDepositRequest,
)
from pydantic import BaseModel
from app.routers.deps import STANDARD_DISCLAIMER_META
from app.a2a_deal_engine import (
    get_a2a_deal_engine,
    DealNotFoundError,
    InvalidDealStateError,
    DealExpiredError,
    InvalidSignatureError,
)
from app.agent_session_vault import (
    get_agent_session_vault,
    InvalidSessionTokenError,
)
from app.vault_manager import vault_manager
from app.webhook_manager import (
    webhook_manager,
    AgentWebhookRegistrationRequest,
    AgentWebhookRegistrationResponse,
)
from app.x402_verifier import x402_verifier
from app.onchain_signer import onchain_signer

router = APIRouter(tags=["A2A Autonomous Settlement"])
a2a_deal_engine = get_a2a_deal_engine()
agent_session_vault = get_agent_session_vault()


# ==========================================
# RFQ Simulation
# ==========================================
@router.post("/api/v1/oracle/simulate-rfq", response_model=ProcurementRFQResponse, summary="Simulate multi-mineral procurement RFQ")
async def simulate_procurement_rfq(rfq_req: ProcurementRFQRequest):
    """
    Simulates a multi-mineral procurement RFQ for EV battery packs.
    Evaluates US IRA 50% FTA threshold and FEOC 25% taint propagation before placing contracts.
    """
    US_FTA_COUNTRIES = {"USA", "US", "AUS", "CHL", "CAN", "MEX", "KOR", "SGP", "BHR", "ISR", "JOR", "MAR", "OMN", "PAN", "PER"}
    BENCHMARK_PRICES = {"LITHIUM": 15000.0, "NICKEL": 16800.0, "COBALT": 28500.0}

    li_val = rfq_req.lithium_tons * BENCHMARK_PRICES["LITHIUM"]
    ni_val = rfq_req.nickel_tons * BENCHMARK_PRICES["NICKEL"]
    co_val = rfq_req.cobalt_tons * BENCHMARK_PRICES["COBALT"]
    total_val = li_val + ni_val + co_val

    fta_val = 0.0
    if rfq_req.lithium_origin_country.upper() in US_FTA_COUNTRIES:
        fta_val += li_val
    if rfq_req.nickel_origin_country.upper() in US_FTA_COUNTRIES:
        fta_val += ni_val
    if rfq_req.cobalt_origin_country.upper() in US_FTA_COUNTRIES:
        fta_val += co_val

    fta_ratio = round((fta_val / total_val) * 100.0, 2) if total_val > 0 else 0.0

    tainted = []
    if rfq_req.lithium_feoc_equity_pct >= 25.0:
        tainted.append(f"LITHIUM ({rfq_req.lithium_feoc_equity_pct}% covered nation equity)")
    if rfq_req.nickel_feoc_equity_pct >= 25.0:
        tainted.append(f"NICKEL ({rfq_req.nickel_feoc_equity_pct}% covered nation equity)")
    if rfq_req.cobalt_feoc_equity_pct >= 25.0:
        tainted.append(f"COBALT ({rfq_req.cobalt_feoc_equity_pct}% covered nation equity)")

    has_taint = len(tainted) > 0
    ira_ok = (fta_ratio >= 50.0) and not has_taint

    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    merkle_preimage = f"{rfq_req.rfq_id}:{rfq_req.cell_chemistry}:{fta_ratio}:{has_taint}:{now_iso}"
    digest = "0x" + hashlib.sha256(merkle_preimage.encode()).hexdigest()

    if ira_ok:
        status_val = "QUALIFIED"
        subsidy = 3750.0
        rec = "APPROVED_FOR_PROCUREMENT: Batch satisfies US IRA Section 30D $3,750 clean vehicle credit with 0% FEOC taint."
    else:
        status_val = "DISQUALIFIED"
        subsidy = 0.0
        reasons = []
        if has_taint:
            reasons.append("FEOC covered nation taint >= 25.0%")
        if fta_ratio < 50.0:
            reasons.append(f"FTA value ratio {fta_ratio}% < 50.0% statutory threshold")
        rec = f"REJECT_OR_REPLACE: Disqualified due to {', '.join(reasons)}."

    return ProcurementRFQResponse(
        rfq_id=rfq_req.rfq_id,
        cell_chemistry=rfq_req.cell_chemistry,
        status=status_val,
        ira_fta_compliant=ira_ok,
        ira_fta_value_ratio_pct=fta_ratio,
        feoc_taint_detected=has_taint,
        tainted_minerals=tainted,
        us_subsidy_qualified_per_pack_usd=subsidy,
        recommendation=rec,
        composite_merkle_digest=digest,
        simulated_at_utc=now_iso,
    )


# ==========================================
# Agent Sessions & Micro-Queries
# ==========================================
@router.post("/api/v1/agent/session/open", response_model=AgentSessionResponse, summary="Open high-speed micro-allowance session")
@router.post("/api/v1/a2a/session/open", response_model=AgentSessionResponse, include_in_schema=False)
async def open_agent_session_route(body: AgentSessionOpenRequest):
    """Opens a high-speed allowance session for sub-millisecond query execution without per-request on-chain gas."""
    return agent_session_vault.open_session(body)


@router.get("/api/v1/agent/session/{session_token}", response_model=AgentSessionInfoResponse, summary="Query session balance and capacity")
@router.get("/api/v1/a2a/session/{session_token}", response_model=AgentSessionInfoResponse, include_in_schema=False)
async def get_agent_session_route(session_token: str):
    """Retrieves session metadata, allocated/current balance, and remaining query capacity."""
    try:
        return agent_session_vault.get_session_info_model(session_token)
    except InvalidSessionTokenError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/api/v1/agent/session/close", response_model=AgentSessionCloseResponse, summary="Close active session and refund unspent")
@router.post("/api/v1/a2a/session/close", response_model=AgentSessionCloseResponse, include_in_schema=False)
async def close_agent_session_route(body: AgentSessionCloseRequest):
    """Closes an active session, issues an immutable receipt hash, and frees remaining unspent balance."""
    try:
        return agent_session_vault.close_session(body)
    except InvalidSessionTokenError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==========================================
# Agent Webhooks
# ==========================================
@router.post("/api/v1/agent/webhooks/register", response_model=AgentWebhookRegistrationResponse, summary="Register a webhook for trade events")
async def register_agent_webhook_route(body: AgentWebhookRegistrationRequest):
    """Registers callback URL with HMAC-SHA256 authentication for trade proposals and attestations."""
    return webhook_manager.register_webhook(body)


@router.get("/api/v1/agent/webhooks/{agent_address}", summary="List active webhooks for agent")
async def list_agent_webhooks_route(agent_address: str):
    """Retrieves all registered webhooks for an agent address."""
    return webhook_manager.list_webhooks_for_agent(agent_address)


@router.delete("/api/v1/agent/webhooks/{webhook_id}", summary="Unregister a webhook")
async def delete_agent_webhook_route(webhook_id: str):
    """Removes a registered webhook by ID."""
    ok = webhook_manager.unregister_webhook(webhook_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook subscription not found.")
    return {"status": "DELETED", "webhook_id": webhook_id}


# ==========================================
# Bilateral Trade Deals
# ==========================================
@router.post("/api/v1/a2a/deals/propose", response_model=TradeDealAttestation, summary="Propose bilateral trade agreement")
@router.post("/api/v1/trade/deals/propose", response_model=TradeDealAttestation, include_in_schema=False)
async def propose_a2a_deal_route(body: TradeDealProposeRequest):
    """Registers a bilateral trade deal proposal signed by seller agent."""
    try:
        return a2a_deal_engine.propose_deal(body)
    except (InvalidDealStateError, InvalidSignatureError, DealExpiredError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/api/v1/a2a/deals/dual-sign", response_model=TradeDealAttestation, summary="Countersign trade proposal")
@router.post("/api/v1/trade/deals/dual-sign", response_model=TradeDealAttestation, include_in_schema=False)
async def dual_sign_a2a_deal_route(body: TradeDealDualSignRequest):
    """Countersigns proposal and triggers Oracle attestation seal to finalize the contract."""
    try:
        return a2a_deal_engine.dual_sign_deal(body)
    except DealNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (InvalidDealStateError, DealExpiredError, InvalidSignatureError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/api/v1/a2a/deals/reject", response_model=TradeDealAttestation, summary="Reject trade proposal")
@router.post("/api/v1/trade/deals/reject", response_model=TradeDealAttestation, include_in_schema=False)
async def reject_a2a_deal_route(body: TradeDealRejectRequest):
    """Marks proposal as REJECTED and records buyer rejection reasoning."""
    try:
        return a2a_deal_engine.reject_deal(body)
    except DealNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (InvalidDealStateError, DealExpiredError, InvalidSignatureError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/api/v1/a2a/deals/cancel", response_model=TradeDealAttestation, summary="Cancel trade proposal")
@router.post("/api/v1/trade/deals/cancel", response_model=TradeDealAttestation, include_in_schema=False)
async def cancel_a2a_deal_route(body: TradeDealCancelRequest):
    """Revokes a pending proposal before buyer countersigns."""
    try:
        return a2a_deal_engine.cancel_deal(body)
    except DealNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (InvalidDealStateError, DealExpiredError, InvalidSignatureError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/api/v1/a2a/deals/{deal_id}", summary="Retrieve trade deal specification and status")
@router.get("/api/v1/trade/deals/{deal_id}", include_in_schema=False)
async def get_a2a_deal_route(deal_id: str):
    """Retrieves full specification, status, and audit notes of a deal."""
    deal = a2a_deal_engine.get_deal(deal_id)
    if not deal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Deal '{deal_id}' not found.")
    return deal


@router.get("/api/v1/a2a/deals/by-agent/{agent_address}", response_model=TradeDealListResponse, summary="List deals for agent")
@router.get("/api/v1/trade/deals/by-agent/{agent_address}", response_model=TradeDealListResponse, include_in_schema=False)
async def list_a2a_deals_route(agent_address: str, status_filter: Optional[str] = None):
    """Filters all bilateral agreements for an agent address."""
    deals = a2a_deal_engine.list_deals_by_agent(agent_address, status_filter)
    return TradeDealListResponse(status="success", total_count=len(deals), deals=deals)


@router.get("/api/v1/a2a/deals/verify/{deal_id}", response_model=TradeDealVerifyResponse, summary="Audit cryptographic signatures of dual-signed deal")
@router.get("/api/v1/trade/deals/verify/{deal_id}", response_model=TradeDealVerifyResponse, include_in_schema=False)
async def verify_a2a_deal_route(deal_id: str):
    """Audits seller, buyer, and oracle signatures along with FEOC and mass-balance compliance."""
    try:
        req = TradeDealVerifyRequest(deal_id=deal_id)
        return a2a_deal_engine.verify_deal(req)
    except DealNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/api/v1/a2a/deals/{deal_id}/escrow-calldata", summary="Generate EVM calldata for MineralTradeEscrow")
@router.get("/api/v1/trade/deals/{deal_id}/escrow-calldata", include_in_schema=False)
async def get_deal_escrow_calldata_route(
    deal_id: str,
    escrow_contract_address: Optional[str] = None,
    chain_name: str = "polygon",
):
    """Generates precise EVM transaction calldata for buyer agent to deposit funds into MineralTradeEscrow."""
    try:
        return a2a_deal_engine.build_escrow_deposit_calldata(
            deal_id,
            escrow_contract_address=escrow_contract_address,
            chain_name=chain_name,
        )
    except DealNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidDealStateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==========================================
# Agent Payment Vault Endpoints
# ==========================================
@router.post("/api/v1/vault/register", response_model=AgentRegisterResponse, tags=["Agent Payment Vault"])
async def register_agent_vault(reg_req: AgentRegisterRequest):
    """
    Self-service registration for autonomous AI agents.
    Instantly returns a dedicated session key and seeds an initial free trial balance (e.g. 0.05 USDC).
    """
    acc, session_key = vault_manager.register_agent_onboarding(
        agent_name=reg_req.agent_name,
        agent_address=reg_req.agent_address,
        initial_trial_balance_usdc=reg_req.initial_trial_balance_usdc,
    )
    return AgentRegisterResponse(
        status="success",
        agent_name=reg_req.agent_name,
        agent_address=acc.agent_address,
        session_key=session_key,
        balance_usdc=acc.balance_usdc,
        message="Agent registered successfully. Pass 'X-Agent-Vault-Key' or 'Authorization: Bearer <key>' for zero-latency execution.",
        capacity=vault_manager.get_query_capacity(acc.balance_usdc),
        created_at_utc=acc.created_at_utc,
    )


@router.get("/api/v1/vault/account", response_model=VaultBalanceResponse, tags=["Agent Payment Vault"])
async def get_vault_account(request: Request, identifier: Optional[str] = None):
    """Retrieves vault balance, consumption, and query capacity for an agent."""
    key = (
        identifier
        or request.headers.get("X-Agent-Vault-Key")
        or request.headers.get("X-Vault-Key")
        or request.headers.get("X-Agent-Address")
    )
    auth_hdr = request.headers.get("Authorization", "")
    if not key and auth_hdr.startswith("Bearer "):
        key = auth_hdr[7:].strip()

    if not key:
        raise HTTPException(status_code=400, detail="Missing agent identifier (session key or 0x address).")

    acc = vault_manager.get_account_by_session_key(key)
    if not acc and key.startswith("0x"):
        acc = vault_manager.get_account_by_address(key)

    if not acc:
        raise HTTPException(status_code=404, detail=f"Vault account for identifier '{key}' not found.")

    return VaultBalanceResponse(
        agent_address=acc.agent_address,
        balance_usdc=acc.balance_usdc,
        total_deposited_usdc=acc.total_deposited_usdc,
        total_consumed_usdc=acc.total_consumed_usdc,
        session_key=acc.session_key,
        query_count=acc.query_count,
        last_active_utc=acc.last_active_utc,
        capacity=vault_manager.get_query_capacity(acc.balance_usdc),
    )


@router.get("/api/v1/vault/receipts/{receipt_id}", tags=["Agent Payment Vault"])
async def get_vault_payment_receipt(receipt_id: str):
    """Retrieves an EIP-712 cryptographically signed PaymentReceipt issued to an agent."""
    receipt = x402_verifier.get_receipt(receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail=f"Payment receipt '{receipt_id}' not found.")
    return receipt


@router.post("/api/v1/vault/verify-receipt", tags=["Agent Payment Vault"])
async def verify_payment_receipt(v_req: ReceiptVerifyRequest):
    """Cryptographically verifies that a PaymentReceipt was signed by the Minerals Oracle authority."""
    try:
        tier_enum = PricingTier(v_req.pricing_tier)
    except Exception:
        tier_enum = PricingTier.STANDARD

    receipt_obj = PaymentReceipt(
        receipt_id=v_req.receipt_id,
        payer_address=v_req.payer_address,
        amount_paid_usdc=v_req.amount_paid_usdc,
        pricing_tier=tier_enum,
        timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        oracle_state_digest=v_req.oracle_state_digest,
        oracle_receipt_signature=v_req.oracle_receipt_signature,
        network=v_req.network,
    )
    is_valid = x402_verifier.verify_payment_receipt_signature(receipt_obj)
    return {
        "status": "VERIFIED" if is_valid else "INVALID_SIGNATURE",
        "receipt_id": v_req.receipt_id,
        "is_valid": is_valid,
        "oracle_signing_address": onchain_signer.account.address,
        "verified_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


@router.post(
    "/api/v1/vault/deposit",
    response_model=VaultBalanceResponse,
    tags=["Agent Payment Vault"],
    summary="Deposit USDC into Agent Pre-Funded Vault (Simulated / Verified)",
)
async def deposit_vault(body: VaultDepositRequest):
    """
    Deposits USDC into the agent's pre-funded vault balance for zero-latency (<1ms) querying.
    Returns the agent's active balance and private session key.
    """
    ident = body.identifier or body.agent_address
    if not ident:
        raise HTTPException(status_code=400, detail="Missing 'identifier' or 'agent_address'")

    account, receipt = vault_manager.deposit_funds(
        identifier=ident,
        amount_usdc=body.amount_usdc,
        tx_hash=body.tx_hash,
        chain=body.chain,
    )
    return VaultBalanceResponse(
        status="DEPOSIT_CONFIRMED",
        agent_address=account.agent_address,
        balance_usdc=account.balance_usdc,
        total_deposited_usdc=account.total_deposited_usdc,
        total_consumed_usdc=account.total_consumed_usdc,
        session_key=account.session_key,
        query_count=account.query_count,
        last_active_utc=account.last_active_utc,
        capacity=vault_manager.get_query_capacity(account.balance_usdc),
        receipt=receipt,
    )


@router.get(
    "/api/v1/vault/balance/{agent_address}",
    response_model=VaultBalanceResponse,
    tags=["Agent Payment Vault"],
    summary="Get Agent Vault Balance and Usage Statistics",
)
async def get_vault_balance(agent_address: str):
    """Retrieves the current available USDC balance and session stats for an agent wallet."""
    account = vault_manager.get_account_by_address(agent_address)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vault account for agent '{agent_address}' not found. Please deposit USDC first via POST /api/v1/vault/deposit.",
        )
    return VaultBalanceResponse(
        agent_address=account.agent_address,
        balance_usdc=account.balance_usdc,
        total_deposited_usdc=account.total_deposited_usdc,
        total_consumed_usdc=account.total_consumed_usdc,
        session_key=account.session_key,
        query_count=account.query_count,
        last_active_utc=account.last_active_utc,
    )


class AgentOnboardRequest(BaseModel):
    agent_name: str = "AnonymousAutonomousAgent"
    agent_address: Optional[str] = None
    requested_network: Optional[str] = "polygon"


@router.post(
    "/api/v1/agent/onboard",
    tags=["Agent Protocol"],
    summary="Self-serve instant onboarding for autonomous AI agents",
)
async def onboard_autonomous_agent(body: AgentOnboardRequest):
    """
    Zero-friction self-serve onboarding for autonomous AI agents.
    Instantly provisions an agent vault account pre-funded with 10 free trial queries (0.05 USDC).
    """
    acc, session_key = vault_manager.register_agent_onboarding(
        agent_name=body.agent_name,
        agent_address=body.agent_address,
        initial_trial_balance_usdc=0.05,
    )
    import os
    treasury_wallet = os.getenv("ORACLE_TREASURY_WALLET", "0xA185B43fDD19619f99952AAed6eabf1029bF36a1")
    return {
        "status": "success",
        "meta": STANDARD_DISCLAIMER_META,
        "agent_name": body.agent_name,
        "agent_address": acc.agent_address,
        "session_key": session_key,
        "trial_balance_usdc": acc.balance_usdc,
        "free_queries_remaining": int(acc.balance_usdc // 0.005),
        "auth_header": {
            "header_name": "X-Agent-Vault-Key",
            "header_value": session_key,
            "curl_example": f"curl -H 'X-Agent-Vault-Key: {session_key}' http://127.0.0.1:8000/api/v1/oracle/prices?format=compact",
        },
        "recharge_instructions": {
            "token": "USDC",
            "networks": ["Polygon (137)", "Base (8453)", "Arbitrum (42161)"],
            "deposit_endpoint": "POST /api/v1/vault/deposit",
            "treasury_address": treasury_wallet,
        }
    }


from app.collaborator_mediator import collaborator_mediator, HarmonizedTradeFlowRequest, HarmonizedTradeFlowResult

@router.post(
    "/api/v1/trade/harmonize-flow",
    response_model=HarmonizedTradeFlowResult,
    tags=["Harmonized Trade Pipeline"],
    summary="End-to-end fluid trade pipeline execution ('like flowing water')",
)
async def harmonize_trade_flow_endpoint(body: HarmonizedTradeFlowRequest):
    """
    Executes the collaborative 5-pillar trade lifecycle:
    Deal Inception -> Tariff/Route Optimization -> eBL/Satellite Verification -> Escrow Calldata -> A.GRID Clearing & Webhook Push.
    """
    return collaborator_mediator.flow_deal_to_settlement(body)


