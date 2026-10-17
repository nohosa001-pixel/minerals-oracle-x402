"""
Global Trade, Logistics, Maritime Route & CBAM Router.
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.schemas import (
    MineralType,
    SourceCountry,
    TradeCorridorFlow,
    HSCodeTariffInfo,
    MaritimeRouteRequest,
    MaritimeRouteResponse,
    EBLVerificationRequest,
    EBLVerificationResponse,
    TradeRouteOptimizationRequest,
    TradeRouteOptimizationResponse,
    CustomsVerificationRequest,
    CustomsVerificationResponse,
    LogisticsTrackingStateResponse,
    PricingTier,
    LogisticsTrackingStateRequest,
)
from app.routers.deps import require_x402_payment
from app.global_trade_engine import global_trade_engine
from app.logistics_bridge import logistics_bridge
from fastapi import Request

router = APIRouter(tags=["Global Trade & Logistics"])


@router.get("/api/v1/trade/flows", response_model=List[TradeCorridorFlow], summary="Global trade corridor flows")
@router.get("/api/v1/trade/corridors", response_model=List[TradeCorridorFlow], summary="Global trade corridor flows (Alias)")
async def get_trade_flows(
    mineral_type: Optional[MineralType] = None,
    origin_country: Optional[SourceCountry] = None,
    destination_country: Optional[str] = None,
):
    """
    Returns global critical mineral physical trade corridor flows, monthly bulk tonnages,
    standard transit days, vessel classes, and maritime chokepoints.
    """
    return global_trade_engine.get_corridors(
        mineral_type=mineral_type,
        origin_country=origin_country,
        destination_country=destination_country,
    )


@router.post("/api/v1/trade/tariffs", response_model=HSCodeTariffInfo, summary="Resolve HS tariff and trade barriers")
async def get_trade_tariffs(
    mineral_type: MineralType,
    importer_jurisdiction: str = "USA",
):
    """
    Resolves WCO 6-digit Harmonized System (HS) Code, general MFN duty rate,
    applicable FTA preferential duty rate, US Section 301 punitive tariff, and EU CBAM benchmarks.
    """
    tariff = global_trade_engine.get_hs_tariff(mineral_type, importer_jurisdiction)
    if not tariff:
        raise HTTPException(status_code=404, detail="Tariff line not found.")
    return tariff


@router.post("/api/v1/trade/maritime-route", response_model=MaritimeRouteResponse, summary="Calculate maritime transit and CII carbon")
async def calculate_maritime_route(route_req: MaritimeRouteRequest):
    """
    Calculates maritime voyage distance (nautical miles), transit duration,
    freight charter costs, chokepoint detour surcharges, IMO CII rating, and EU CBAM costs.
    """
    return global_trade_engine.calculate_maritime_route(route_req)


@router.post("/api/v1/trade/verify-ebl", response_model=EBLVerificationResponse, summary="Verify UNCITRAL MLETR electronic Bill of Lading")
async def verify_electronic_bill_of_lading(ebl_req: EBLVerificationRequest):
    """
    Cryptographically audits UNCITRAL MLETR / FIT Alliance electronic Bill of Lading (eBL).
    Validates 7-digit IMO checksum, UN/LOCODE port pairs, manifest weight, and screens for AIS dark fleet anomalies.
    """
    return global_trade_engine.verify_ebl(ebl_req)


@router.post("/api/v1/trade/optimize-route", response_model=TradeRouteOptimizationResponse, summary="Optimize mineral trade route")
async def optimize_mineral_trade_route(opt_req: TradeRouteOptimizationRequest):
    """
    Autonomous trade route optimizer for AI procurement agents.
    Compares direct marine transit vs chokepoint detour corridors, computing landed cost arbitrage.
    """
    return global_trade_engine.optimize_route(opt_req)


@router.get("/api/v1/trade/cbam-liability", summary="Calculate EU CBAM carbon liability")
def calculate_cbam_liability_endpoint(
    mineral_type: str = Query(..., description="Commodity type (e.g. LITHIUM_HYDROXIDE, NICKEL_MHP)"),
    cargo_weight_metric_tons: float = Query(..., ge=0.1, description="Shipment volume in MT"),
    importer_jurisdiction: str = Query(default="EU", description="Importing territory (e.g. EU, US, JP)"),
):
    """Calculates embedded CO2 tonnage and financial CBAM carbon import certificate liability."""
    m_enum = None
    for member in MineralType:
        if member.value == mineral_type or member.name == mineral_type:
            m_enum = member
            break
    if m_enum is None:
        u = mineral_type.upper()
        if "LITH" in u:
            m_enum = MineralType.LITHIUM_HYDROXIDE
        elif "NICK" in u:
            m_enum = MineralType.NICKEL_MHP
        elif "COB" in u:
            m_enum = MineralType.COBALT_HYDROXIDE
        elif "COP" in u:
            m_enum = MineralType.COPPER_CATHODE
        else:
            m_enum = MineralType.LITHIUM_CARBONATE

    res = global_trade_engine.calculate_cbam_liability(
        mineral_type=m_enum,
        cargo_weight_metric_tons=cargo_weight_metric_tons,
        importer_jurisdiction=importer_jurisdiction,
    )
    return JSONResponse(content=res)


@router.post(
    "/api/v1/logistics/customs-clearance/verify",
    response_model=CustomsVerificationResponse,
    summary="Anchors ocean carrier B/L to mineral batch and issues Customs Clearance Proof Bundle",
)
@router.post(
    "/api/v1/logistics/customs-clearance-verify",
    response_model=CustomsVerificationResponse,
    summary="Anchors ocean carrier B/L to mineral batch and issues Customs Clearance Proof Bundle (Alias)",
    responses={402: {"description": "Payment Required (0.05 USDC on Polygon)"}},
)
async def verify_customs_clearance_endpoint(
    body: CustomsVerificationRequest,
    request: Request = None,
):
    """Validates international container/BOL transit and issues customs clearance attestation bundle."""
    if request:
        resp_402 = await require_x402_payment(request, tier=PricingTier.LIGHT)
        if resp_402:
            return resp_402
        headers = getattr(request.state, "extra_headers", {}) or {}
        result = logistics_bridge.verify_customs_clearance(body)
        return JSONResponse(content=result.model_dump(), headers=headers)
    return logistics_bridge.verify_customs_clearance(body)


@router.post(
    "/api/v1/logistics/clean-tracking-feed",
    response_model=LogisticsTrackingStateResponse,
    summary="Normalized Multi-Carrier Tracking Feed (Express & Ocean Containers)",
    responses={402: {"description": "Payment Required (0.02 USDC on Polygon)"}},
)
async def get_clean_tracking_feed_endpoint(
    body: LogisticsTrackingStateRequest,
    request: Request = None,
):
    """Cleanweb Tracking Engine for Autonomous Trade Agents."""
    if request:
        resp_402 = await require_x402_payment(request, tier=PricingTier.LIGHT)
        if resp_402:
            return resp_402
        headers = getattr(request.state, "extra_headers", {}) or {}
        result = logistics_bridge.get_clean_tracking_feed(body)
        return JSONResponse(content=result.model_dump(), headers=headers)
    return logistics_bridge.get_clean_tracking_feed(body)


@router.get(
    "/api/v1/logistics/tracking/{tracking_number}/status",
    response_model=LogisticsTrackingStateResponse,
    summary="Query real-time customs & carrier logistics tracking status",
)
def get_logistics_tracking_status(tracking_number: str):
    """Retrieves carrier API tracking status, inland-port linkage, and customs milestone history."""
    state = logistics_bridge.get_tracking_state(tracking_number)
    if not state:
        raise HTTPException(
            status_code=404,
            detail=f"Tracking number '{tracking_number}' not found in active logistics cache.",
        )
    return state
