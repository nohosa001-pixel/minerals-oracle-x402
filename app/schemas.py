from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class CommoditySymbol(str, Enum):
    AG = "Ag"       # Silver
    PT = "Pt"       # Platinum
    CU = "Cu"       # Copper
    LI = "Li"       # Lithium Carbonate / Hydroxide
    NDDY = "NdDy"   # Neodymium-Dysprosium (Rare Earths)


class PriceUnit(str, Enum):
    USD_PER_TROY_OZ = "USD/troy_oz"
    USD_PER_GRAM = "USD/g"
    USD_PER_KG = "USD/kg"
    USD_PER_METRIC_TON = "USD/mt"
    USD_PER_LB = "USD/lb"


class ScrapCategory(str, Enum):
    EV_BATTERY_BLACK_MASS = "EV_BATTERY_BLACK_MASS"
    AUTO_CATALYST_CERAMIC = "AUTO_CATALYST_CERAMIC"
    E_WASTE_HIGH_GRADE_PCB = "E_WASTE_HIGH_GRADE_PCB"
    WIND_EV_PERMANENT_MAGNETS = "WIND_EV_PERMANENT_MAGNETS"


class MineralQuote(BaseModel):
    symbol: CommoditySymbol = Field(..., description="Commodity symbol")
    name: str = Field(..., description="Full descriptive name")
    spot_price_usd: float = Field(..., description="Spot reference price in USD")
    unit: PriceUnit = Field(..., description="Primary price unit")
    secondary_prices: Dict[str, float] = Field(default_factory=dict, description="Normalized prices in alternative units")
    bid: float = Field(..., description="Current market bid")
    ask: float = Field(..., description="Current market ask")
    change_24h_pct: float = Field(..., description="24 hour price change percentage")
    benchmark_exchange: str = Field(..., description="Primary benchmark venue (e.g. COMEX, LME, SMM, Fastmarkets)")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Oracle composite confidence score (0.0 - 1.0)")
    timestamp_utc: str = Field(..., description="ISO 8601 UTC timestamp")
    attestation_hash: str = Field(..., description="Cryptographic SHA-256 integrity digest of the quote payload")


class PriceFeedResponse(BaseModel):
    oracle: str = "minerals-oracle-x402"
    version: str = "1.1.0"
    network: str = "Polygon (Chain ID 137)"
    generated_at_utc: str
    quotes: Dict[str, MineralQuote]
    signature: Optional[str] = Field(None, description="Oracle signer signature if enabled")


class ArbitrageSpread(BaseModel):
    symbol: CommoditySymbol
    primary_exchange: str
    primary_price_usd: float
    secondary_exchange: str
    secondary_price_usd: float
    spread_usd: float
    spread_basis_points: float
    arbitrage_direction: str
    estimated_freight_and_tariff_usd: float
    net_arbitrage_margin_usd: float
    is_arbitrage_profitable: bool


class SpreadsResponse(BaseModel):
    oracle: str = "minerals-oracle-x402"
    timestamp_utc: str
    spreads: List[ArbitrageSpread]


class ScrapYieldItem(BaseModel):
    mineral_symbol: str
    mineral_name: str
    assay_grade_pct: Optional[float] = Field(None, description="Assay grade percentage (if applicable)")
    assay_grade_ppm: Optional[float] = Field(None, description="Assay grade parts-per-million (if applicable)")
    contained_weight_kg: float = Field(..., description="Total contained metal weight in kg")
    recovery_rate_pct: float = Field(..., description="Process recovery efficiency %")
    payable_weight_kg: float = Field(..., description="Payable/recoverable weight in kg")
    payable_weight_troy_oz: Optional[float] = Field(None, description="Payable weight in troy ounces (for PMs)")
    benchmark_unit_price_usd: float = Field(..., description="Underlying mineral price per kg or oz")
    gross_payable_value_usd: float = Field(..., description="Gross recoverable dollar value for this mineral")


class UrbanMiningRequest(BaseModel):
    scrap_category: ScrapCategory = Field(
        default=ScrapCategory.E_WASTE_HIGH_GRADE_PCB,
        description="Urban mining feedstock category (e.g. E_WASTE_HIGH_GRADE_PCB, EV_BATTERY_BLACK_MASS, AUTO_CATALYST_CERAMIC, WIND_EV_PERMANENT_MAGNETS)",
        examples=["E_WASTE_HIGH_GRADE_PCB", "EV_BATTERY_BLACK_MASS"]
    )
    quantity_metric_tons: float = Field(
        default=1.0,
        gt=0,
        description="Total feedstock weight in metric tons",
        examples=[1.0, 5.0]
    )
    target_yield_currency: str = Field(
        default="USDC",
        description="Settlement denomination currency (default: 'USDC')",
        examples=["USDC"]
    )
    custom_assay_overrides: Optional[Dict[str, float]] = Field(
        None,
        description="Optional custom assay grades to override standard defaults (e.g. {'Au': 250, 'Ag': 1300, 'Cu': 17.5} or {'Li': 4.5, 'Co': 12.0})",
        examples=[{"Au": 250.0, "Cu": 17.0}]
    )
    refining_cost_per_ton_usd: Optional[float] = Field(
        None,
        description="Custom refining & toll treatment charge per metric ton (USD). If omitted, default benchmark is used."
    )
    recovery_efficiency_factor: Optional[float] = Field(
        1.0,
        ge=0.5,
        le=1.5,
        description="Refinery efficiency multiplier (1.0 = 100% of benchmark recovery)"
    )


class UrbanMiningResponse(BaseModel):
    oracle: str = "minerals-oracle-x402"
    timestamp_utc: str
    scrap_category: ScrapCategory
    input_quantity_metric_tons: float
    target_yield_currency: str = "USDC"
    mineral_breakdown: List[ScrapYieldItem]
    total_gross_payable_usd: float
    total_treatment_and_refining_charges_usd: float
    net_settlement_value_usd: float
    net_value_per_ton_usd: float
    recovery_rates_tensor: Dict[str, float] = Field(
        default_factory=dict,
        description="Element-wise hydrometallurgical recovery rates tensor (%)"
    )
    refinery_compliance_flags: Dict[str, Any] = Field(
        default_factory=lambda: {
            "oecd_due_diligence_compliant": True,
            "eu_battery_regulation_2023_1542_ready": True,
            "basel_convention_transboundary_scrap_cleared": True,
            "esg_carbon_offset_intensity_kg_co2_per_ton": -420.0
        },
        description="Global refinery compliance and regulatory ESG attestation flags"
    )
    benchmarks_applied: Dict[str, float]
    attestation_hash: str


class PaymentChallenge(BaseModel):
    x402_version: str = "1.0"
    network: str = "polygon"
    chain_id: int = 137
    accepted_token: str = "USDC"
    token_address: str = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"
    amount: str = "0.005"
    amount_units: str = "5000"  # 0.005 USDC (6 decimals)
    recipient_address: str
    facilitator_url: str
    nonce: str
    expires_at_utc: str
    message: str = "Payment Required: 0.005 USDC on Polygon (Chain ID 137) to access Critical Raw Minerals Oracle feed"


class MCPToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class MCPToolCallResponse(BaseModel):
    content: List[Dict[str, Any]]
    isError: bool = False


class AlphaSignalItem(BaseModel):
    symbol: str
    name: str
    spot_price_usd: float
    unit: str
    primary_venue: str
    arbitrage_detected: bool
    estimated_margin_bps: float
    teaser_message: str


class AlphaSignalsSummary(BaseModel):
    oracle: str = "minerals-oracle-x402"
    status: str = "operational"
    timestamp_utc: str
    network: str = "Polygon (Chain ID 137)"
    free_tier_status: str = "PUBLIC_REALTIME_ALPHA_TEASER"
    arbitrage_opportunities_active: int
    highest_profit_commodity: str
    signals: List[AlphaSignalItem]
    unlock_instruction: str = (
        "Pay 0.005 USDC on Polygon (Chain ID 137) via x402 protocol at /api/v1/oracle/prices or "
        "/api/v1/oracle/spreads to obtain complete EIP-712 certified quotes, net logistics formulas, and scrap matrices."
    )


class PricingTier(str, Enum):
    LIGHT = "LIGHT"         # $0.001 USDC (Single price / basic ping)
    STANDARD = "STANDARD"   # $0.005 USDC (Full price feed / arbitrage radar)
    HEAVY = "HEAVY"         # $0.010 USDC (Hydrometallurgical scrap yield tensor)
    ONCHAIN = "ONCHAIN"     # $0.020 USDC (EIP-712 smart contract signed calldata)


class PaymentReceipt(BaseModel):
    receipt_id: str = Field(..., description="Unique cryptographic payment receipt ID (e.g. rcpt_...)")
    payer_address: str = Field(..., description="Agent or user wallet address that authorized the payment")
    amount_paid_usdc: float = Field(..., description="Amount paid in USDC")
    pricing_tier: PricingTier = Field(..., description="Service tier consumed")
    timestamp_utc: str = Field(..., description="ISO 8601 UTC timestamp of execution")
    oracle_state_digest: str = Field(..., description="Cryptographic SHA-256 digest of the payload provided")
    oracle_receipt_signature: str = Field(..., description="ECDSA signature proving payment settlement")
    network: str = "Polygon (Chain ID 137)"


class VaultDepositRequest(BaseModel):
    agent_address: str = Field(..., description="Checksummed Polygon wallet address of the agent")
    amount_usdc: float = Field(..., gt=0, description="Amount of USDC to deposit (e.g. 10.0, 50.0)")
    tx_hash: Optional[str] = Field(None, description="Optional on-chain Polygon transaction hash")


class VaultBalanceResponse(BaseModel):
    agent_address: str
    balance_usdc: float
    total_deposited_usdc: float
    total_consumed_usdc: float
    session_key: str
    query_count: int
    last_active_utc: str


