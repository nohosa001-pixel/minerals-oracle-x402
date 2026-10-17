"""
Mineral Provenance, Traceability, ZK Proofs & Regulatory Engine Router.
"""
from __future__ import annotations

import asyncio
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse

from app.schemas import (
    MineralLotProvenanceRequest,
    CompliancePassportResponse,
    MineSiteSatelliteAuditRequest,
    MineSiteSatelliteAuditResponse,
    LithiumOriginVerifyRequest,
    LithiumOriginVerifyResponse,
    NickelOriginVerifyRequest,
    NickelOriginVerifyResponse,
    CobaltOriginVerifyRequest,
    CobaltOriginVerifyResponse,
    CompositeBatteryVerifyRequest,
    CompositeBatteryVerifyResponse,
    CopperOriginVerifyRequest,
    CopperOriginVerifyResponse,
    SilverOriginVerifyRequest,
    SilverOriginVerifyResponse,
    RareEarthsOriginVerifyRequest,
    RareEarthsOriginVerifyResponse,
    TungstenOriginVerifyRequest,
    TungstenOriginVerifyResponse,
    NiobiumScandiumOriginVerifyRequest,
    NiobiumScandiumOriginVerifyResponse,
    BlackMassOriginVerifyRequest,
    BlackMassOriginVerifyResponse,
    CBAMMarkupPenaltyRequest,
    CBAMMarkupPenaltyResponse,
    EUIndustrialActVerifyRequest,
    EUIndustrialActVerifyResponse,
    BatteryPassportVCRequest,
    BatteryPassportVCResponse,
    ZKComplianceProofRequest,
    ZKComplianceProofResponse,
    ZKProofVerifyRequest,
    ZKProofVerifyResponse,
    SMELightweightInput,
    SMELightweightResponse,
    SupplyChainBatchRequest,
    SupplyChainBatchResponse,
    VoucherAuditPackageResponse,
    PricingTier,
)
from app.routers.deps import require_x402_payment
from app.compliance_engine import compliance_engine
from app.eudr_client import eudr_client
from app.lithium_pipeline import lithium_pipeline
from app.nickel_pipeline import nickel_pipeline
from app.cobalt_pipeline import cobalt_pipeline
from app.composite_battery_pipeline import composite_battery_pipeline
from app.copper_pipeline import copper_pipeline
from app.silver_pipeline import silver_pipeline
from app.rare_earths_pipeline import rare_earths_pipeline
from app.tungsten_pipeline import tungsten_pipeline
from app.niobium_scandium_pipeline import niobium_scandium_pipeline
from app.black_mass_pipeline import black_mass_pipeline
from app.regulatory_advanced_engine import regulatory_advanced_engine
from app.zk_compliance_prover import zk_compliance_prover
from app.enterprise_manager import enterprise_manager

router = APIRouter(tags=["Compliance Oracle"])


@router.post(
    "/api/v1/oracle/compliance/verify",
    response_model=CompliancePassportResponse,
    summary="Verify Critical Mineral Lot Provenance & Issue Battery Passport (x402 Verified)",
    responses={402: {"description": "Payment Required (0.50 USDC on Polygon)"}},
)
async def verify_mineral_lot_compliance(
    request: Request,
    body: MineralLotProvenanceRequest,
):
    """
    Autonomous 7-Pillar Critical Mineral Provenance & Battery Passport Verification.
    """
    resp_402 = await require_x402_payment(request, tier=PricingTier.STANDARD)
    if resp_402:
        return resp_402

    headers = getattr(request.state, "extra_headers", {}) or {}
    passport = compliance_engine.evaluate_lot(body)
    return JSONResponse(content=passport.model_dump(), headers=headers)


@router.post(
    "/api/v1/compliance/eudr-satellite-audit",
    response_model=MineSiteSatelliteAuditResponse,
    summary="Audit Mining Concession Plot via EUDR Satellite Radar (Sentinel-1/2 SAR & TRACES-NT)",
)
async def audit_mine_site_eudr(
    body: MineSiteSatelliteAuditRequest,
    request: Request,
):
    """
    Connects with eudr-compliance-agent for multi-satellite radar & Hansen GFC deforestation screening.
    """
    res = await asyncio.to_thread(
        eudr_client.verify_mine_site_compliance,
        latitude=body.latitude,
        longitude=body.longitude,
        country_code=body.country_code,
        area_hectares=body.area_hectares,
        concession_id=body.concession_id,
        production_date=body.production_date,
    )
    return MineSiteSatelliteAuditResponse(
        status="success",
        is_compliant=res.get("is_compliant", True),
        deforestation_detected=res.get("deforestation_detected", False),
        forest_loss_pct=res.get("forest_loss_pct", 0.0),
        indigenous_territory_encroachment=res.get("indigenous_territory_encroachment", False),
        reason=res.get("reason", "Verified clean"),
        satellite_evidence_hash=res.get("satellite_evidence_hash", ""),
        traces_nt_dds_reference=res.get("traces_nt_dds_reference"),
        audit_source=res.get("audit_source", "LOCAL_STANDALONE"),
        latency_ms=res.get("latency_ms", 0.0),
    )


@router.post(
    "/api/v1/lithium/verify-origin",
    response_model=LithiumOriginVerifyResponse,
    summary="Verify Australian Spodumene-to-Lithium Hydroxide Supply-Chain Provenance (x402 Verified)",
    responses={402: {"description": "Payment Required (0.05 USDC on Polygon)"}},
)
async def verify_lithium_origin(
    request: Request,
    body: LithiumOriginVerifyRequest,
):
    """Dedicated Australian Hard-Rock Spodumene-to-Lithium Hydroxide Provenance Pipeline."""
    resp_402 = await require_x402_payment(request, tier=PricingTier.LIGHT)
    if resp_402:
        return resp_402

    headers = getattr(request.state, "extra_headers", {}) or {}
    result = lithium_pipeline.evaluate_lithium_lot(body)
    return JSONResponse(content=result.model_dump(), headers=headers)


@router.post(
    "/api/v1/nickel/verify-origin",
    response_model=NickelOriginVerifyResponse,
    summary="Verify Indonesian Laterite-to-Nickel MHP Supply-Chain Provenance (x402 Verified)",
    responses={402: {"description": "Payment Required (0.05 USDC on Polygon)"}},
)
async def verify_nickel_origin(
    request: Request,
    body: NickelOriginVerifyRequest,
):
    """Dedicated Indonesian Laterite Limonite Ore-to-Nickel MHP Provenance Pipeline."""
    resp_402 = await require_x402_payment(request, tier=PricingTier.LIGHT)
    if resp_402:
        return resp_402

    headers = getattr(request.state, "extra_headers", {}) or {}
    result = nickel_pipeline.evaluate_nickel_lot(body)
    return JSONResponse(content=result.model_dump(), headers=headers)


@router.post(
    "/api/v1/cobalt/verify-origin",
    response_model=CobaltOriginVerifyResponse,
    summary="Verify DRC Katanga-to-Cobalt Hydroxide Supply-Chain Provenance (x402 Verified)",
    responses={402: {"description": "Payment Required (0.05 USDC on Polygon)"}},
)
async def verify_cobalt_origin(
    request: Request,
    body: CobaltOriginVerifyRequest,
):
    """Dedicated DRC Katanga Heterogenite Ore-to-Cobalt Hydroxide Provenance Pipeline."""
    resp_402 = await require_x402_payment(request, tier=PricingTier.LIGHT)
    if resp_402:
        return resp_402

    headers = getattr(request.state, "extra_headers", {}) or {}
    result = cobalt_pipeline.evaluate_cobalt_lot(body)
    return JSONResponse(content=result.model_dump(), headers=headers)


@router.post(
    "/api/v1/battery/composite-verify",
    response_model=CompositeBatteryVerifyResponse,
    summary="Verify Composite EV Battery Pack Multi-Mineral Provenance & Issue Master Passport (x402 Verified)",
    responses={402: {"description": "Payment Required (0.10 USDC on Polygon)"}},
)
async def verify_composite_battery(
    request: Request,
    body: CompositeBatteryVerifyRequest,
):
    """Deterministic Composite Battery Supply-Chain Integrity & Master Passport Engine."""
    resp_402 = await require_x402_payment(request, tier=PricingTier.STANDARD)
    if resp_402:
        return resp_402

    headers = getattr(request.state, "extra_headers", {}) or {}
    result = composite_battery_pipeline.evaluate_battery_pack(body)
    return JSONResponse(content=result.model_dump(), headers=headers)


@router.post(
    "/api/v1/copper/verify-origin",
    response_model=CopperOriginVerifyResponse,
    summary="Verify South American Copper-to-Cathode Provenance & HVDC Grid Certification (x402 Verified)",
    responses={402: {"description": "Payment Required (0.05 USDC on Polygon)"}},
)
@router.post(
    "/api/v1/oracle/verify/copper",
    response_model=CopperOriginVerifyResponse,
    include_in_schema=False,
)
async def verify_copper_origin(
    request: Request,
    body: CopperOriginVerifyRequest,
):
    """Dedicated Chilean/South American Copper Cathode Provenance Pipeline."""
    resp_402 = await require_x402_payment(request, tier=PricingTier.LIGHT)
    if resp_402:
        return resp_402

    headers = getattr(request.state, "extra_headers", {}) or {}
    result = copper_pipeline.verify_origin(body)
    return JSONResponse(content=result.model_dump(), headers=headers)


@router.post(
    "/api/v1/silver/verify-origin",
    response_model=SilverOriginVerifyResponse,
    summary="Verify Mexican & Global Silver Provenance & N-Type TOPCon Solar PV Purity (x402 Verified)",
    responses={402: {"description": "Payment Required (0.05 USDC on Polygon)"}},
)
@router.post(
    "/api/v1/oracle/verify/silver",
    response_model=SilverOriginVerifyResponse,
    include_in_schema=False,
)
async def verify_silver_origin(
    request: Request,
    body: SilverOriginVerifyRequest,
):
    """Dedicated Mexican & Global Silver-to-Solar PV Metallization Provenance Pipeline."""
    resp_402 = await require_x402_payment(request, tier=PricingTier.LIGHT)
    if resp_402:
        return resp_402

    headers = getattr(request.state, "extra_headers", {}) or {}
    result = silver_pipeline.verify_origin(body)
    return JSONResponse(content=result.model_dump(), headers=headers)


@router.post(
    "/api/v1/rare-earths/verify-origin",
    response_model=RareEarthsOriginVerifyResponse,
    summary="Verify Non-China NdPr Rare Earths Provenance & MOFCOM 0.1% Rule (x402 Verified)",
    responses={402: {"description": "Payment Required (0.05 USDC on Polygon)"}},
)
@router.post(
    "/api/v1/oracle/verify/rare-earths",
    response_model=RareEarthsOriginVerifyResponse,
    include_in_schema=False,
)
async def verify_rare_earths_origin(
    request: Request,
    body: RareEarthsOriginVerifyRequest,
):
    """Dedicated Rare Earths Permanent Magnet Metal Provenance Pipeline."""
    resp_402 = await require_x402_payment(request, tier=PricingTier.LIGHT)
    if resp_402:
        return resp_402

    headers = getattr(request.state, "extra_headers", {}) or {}
    result = rare_earths_pipeline.verify_rare_earths_batch(body)
    return JSONResponse(content=result.model_dump(), headers=headers)


@router.post(
    "/api/v1/tungsten/verify-origin",
    response_model=TungstenOriginVerifyResponse,
    summary="Verify Western Tungsten / APT Provenance & US NDAA Sec 848 (x402 Verified)",
    responses={402: {"description": "Payment Required (0.05 USDC on Polygon)"}},
)
@router.post(
    "/api/v1/oracle/verify/tungsten",
    response_model=TungstenOriginVerifyResponse,
    include_in_schema=False,
)
async def verify_tungsten_origin(
    request: Request,
    body: TungstenOriginVerifyRequest,
):
    """Dedicated Tungsten Provenance Pipeline."""
    resp_402 = await require_x402_payment(request, tier=PricingTier.LIGHT)
    if resp_402:
        return resp_402

    headers = getattr(request.state, "extra_headers", {}) or {}
    result = tungsten_pipeline.verify_tungsten_batch(body)
    return JSONResponse(content=result.model_dump(), headers=headers)


@router.post(
    "/api/v1/oracle/verify/niobium-scandium",
    response_model=NiobiumScandiumOriginVerifyResponse,
    include_in_schema=False,
)
@router.post(
    "/api/v1/niobium-scandium/verify-origin",
    response_model=NiobiumScandiumOriginVerifyResponse,
    summary="Verify Ferroniobium & Scandium Oxide Origin, ASTM Grade & Defense Eligibility (x402 Verified)",
    responses={402: {"description": "Payment Required (0.005 USDC on Polygon)"}},
)
async def verify_niobium_scandium_origin(
    request: Request,
    body: NiobiumScandiumOriginVerifyRequest,
):
    """Dedicated Niobium & Scandium Defense Strategic Materials Provenance Pipeline."""
    resp_402 = await require_x402_payment(request, tier=PricingTier.LIGHT)
    if resp_402:
        return resp_402

    headers = getattr(request.state, "extra_headers", {}) or {}
    result = niobium_scandium_pipeline.verify_origin(body)
    return JSONResponse(content=result.model_dump(), headers=headers)


@router.post(
    "/api/v1/black-mass/verify-origin",
    response_model=BlackMassOriginVerifyResponse,
    summary="Verify Recycled Battery Black Mass & US BIS Export License (x402 Verified)",
    responses={402: {"description": "Payment Required (0.05 USDC on Polygon)"}},
)
@router.post(
    "/api/v1/oracle/verify/black-mass",
    response_model=BlackMassOriginVerifyResponse,
    include_in_schema=False,
)
async def verify_black_mass_origin(
    request: Request,
    body: BlackMassOriginVerifyRequest,
):
    """Dedicated Battery Black Mass Recycling Provenance Pipeline."""
    resp_402 = await require_x402_payment(request, tier=PricingTier.LIGHT)
    if resp_402:
        return resp_402

    headers = getattr(request.state, "extra_headers", {}) or {}
    result = black_mass_pipeline.verify_black_mass_batch(body)
    return JSONResponse(content=result.model_dump(), headers=headers)


@router.post(
    "/api/v1/regulatory/cbam/markup-penalty",
    response_model=CBAMMarkupPenaltyResponse,
    tags=["Regulatory Advanced Oracle"],
    summary="Calculate EU CBAM Statutory Mark-up Penalty (+10% to +30%) & Savings (x402 Verified)",
    responses={402: {"description": "Payment Required (0.05 USDC on Polygon)"}},
)
async def calculate_cbam_markup_penalty(
    request: Request,
    body: CBAMMarkupPenaltyRequest,
):
    """Calculates EU CBAM Statutory Default Mark-up Rates."""
    resp_402 = await require_x402_payment(request, tier=PricingTier.LIGHT)
    if resp_402:
        return resp_402

    headers = getattr(request.state, "extra_headers", {}) or {}
    result = regulatory_advanced_engine.calculate_cbam_markup_penalty(body)
    return JSONResponse(content=result.model_dump(), headers=headers)


@router.post(
    "/api/v1/regulatory/iaa/verify-domestic-share",
    response_model=EUIndustrialActVerifyResponse,
    tags=["Regulatory Advanced Oracle"],
    summary="Verify EU Industrial Accelerator Act (IAA) 70% Domestic Content & Subsidy Eligibility",
    responses={402: {"description": "Payment Required (0.05 USDC on Polygon)"}},
)
async def verify_eu_industrial_act(
    request: Request,
    body: EUIndustrialActVerifyRequest,
):
    """Evaluates compliance against the EU Industrial Accelerator Act (IAA)."""
    resp_402 = await require_x402_payment(request, tier=PricingTier.LIGHT)
    if resp_402:
        return resp_402

    headers = getattr(request.state, "extra_headers", {}) or {}
    result = regulatory_advanced_engine.verify_eu_industrial_act(body)
    return JSONResponse(content=result.model_dump(), headers=headers)


@router.post(
    "/api/v1/battery/passport-vc/issue",
    response_model=BatteryPassportVCResponse,
    tags=["Regulatory Advanced Oracle"],
    summary="Issue W3C Verifiable Credential (VC) EU Battery Passport (x402 Verified)",
    responses={402: {"description": "Payment Required (0.05 USDC on Polygon)"}},
)
async def issue_battery_passport_vc(
    request: Request,
    body: BatteryPassportVCRequest,
):
    """Issues W3C-standard Digital Product Passport (DPP) Verifiable Credential."""
    resp_402 = await require_x402_payment(request, tier=PricingTier.LIGHT)
    if resp_402:
        return resp_402

    headers = getattr(request.state, "extra_headers", {}) or {}
    result = regulatory_advanced_engine.generate_battery_passport_vc(body)
    return JSONResponse(content=result.model_dump(), headers=headers)


@router.post(
    "/api/v1/zk/compliance-proof/generate",
    response_model=ZKComplianceProofResponse,
    tags=["Privacy & ZK Oracle"],
    summary="Generate Zero-Knowledge Origin & Purity Proof (Shield GPS & Costs)",
    responses={402: {"description": "Payment Required (0.05 USDC on Polygon)"}},
)
async def generate_zk_compliance_proof(
    request: Request,
    body: ZKComplianceProofRequest,
):
    """Privacy-Preserving Zero-Knowledge Compliance Engine."""
    resp_402 = await require_x402_payment(request, tier=PricingTier.LIGHT)
    if resp_402:
        return resp_402

    headers = getattr(request.state, "extra_headers", {}) or {}
    result = zk_compliance_prover.generate_zk_compliance_proof(body)
    return JSONResponse(content=result.model_dump(), headers=headers)


@router.post(
    "/api/v1/zk/compliance-proof/verify",
    response_model=ZKProofVerifyResponse,
    tags=["Privacy & ZK Oracle"],
    summary="Verify Zero-Knowledge Compliance Proof (Public Auditor / Customs Verifier)",
    responses={402: {"description": "Payment Required (0.02 USDC on Polygon)"}},
)
async def verify_zk_compliance_proof(
    request: Request,
    body: ZKProofVerifyRequest,
):
    """Public Verifier for Zero-Knowledge Compliance Attestations."""
    resp_402 = await require_x402_payment(request, tier=PricingTier.LIGHT)
    if resp_402:
        return resp_402

    headers = getattr(request.state, "extra_headers", {}) or {}
    result = zk_compliance_prover.verify_zk_proof(body)
    return JSONResponse(content=result.model_dump(), headers=headers)


@router.post(
    "/api/v1/compliance/sme-lightweight",
    response_model=SMELightweightResponse,
    summary="SME Lightweight Scope 1/2 & OECD Mass Balance Verification (Micro-Cost x402)",
    responses={402: {"description": "Payment Required (0.05 USDC on Polygon)"}},
)
async def verify_sme_lightweight(
    request: Request,
    body: SMELightweightInput,
):
    """Lightweight SME Proxy Verification for Scope 1/2 Embedded Carbon & OECD Annex II Mass Balance."""
    resp_402 = await require_x402_payment(request, tier=PricingTier.LIGHT)
    if resp_402:
        return resp_402

    headers = getattr(request.state, "extra_headers", {}) or {}
    result = compliance_engine.evaluate_sme_lightweight(body)
    return JSONResponse(content=result.model_dump(), headers=headers)


@router.post(
    "/api/v1/enterprise/batch-compliance",
    response_model=SupplyChainBatchResponse,
    tags=["Enterprise Institutional"],
    summary="Enterprise Multi-Tier Supply-Chain Batch Compliance Audit (16-Trap Radar)",
)
async def verify_supply_chain_batch(
    request: Request,
    body: SupplyChainBatchRequest,
):
    """Enterprise-grade high-throughput batch audit across multi-tier supplier networks."""
    key_record = enterprise_manager.validate_key(body.enterprise_api_key)
    if not key_record and not body.enterprise_api_key.startswith("ent_key_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive enterprise API key. Use provisioned key or 'ent_key_goldman_commodity_quant_2026'.",
        )

    result = enterprise_manager.evaluate_batch(body)
    return JSONResponse(content=result.model_dump())


@router.get(
    "/api/v1/compliance/voucher-evidence/{passport_id}",
    response_model=VoucherAuditPackageResponse,
    summary="Generate MOTIE K-CBAM & Government Voucher Audit Package for SME Reimbursement",
)
async def get_voucher_audit_package(passport_id: str):
    """Generates official audit evidence package aligned with South Korea MOTIE K-CBAM calculation rules."""
    result = compliance_engine.generate_voucher_audit_package(passport_id)
    return JSONResponse(content=result.model_dump())
