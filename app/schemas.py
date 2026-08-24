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
    version: str = "1.0.0"
    network: str = "Base (Chain ID 8453)"
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
    scrap_category: ScrapCategory = Field(..., description="Urban mining feedstock category")
    quantity_metric_tons: float = Field(..., gt=0, description="Total feedstock weight in metric tons")
    custom_assay_overrides: Optional[Dict[str, float]] = Field(
        None,
        description="Optional custom assay grades to override standard defaults (e.g. {'Li': 4.5, 'Co': 12.0} in % or {'Pt': 1500} in ppm)"
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
    mineral_breakdown: List[ScrapYieldItem]
    total_gross_payable_usd: float
    total_treatment_and_refining_charges_usd: float
    net_settlement_value_usd: float
    net_value_per_ton_usd: float
    benchmarks_applied: Dict[str, float]
    attestation_hash: str


class PaymentChallenge(BaseModel):
    x402_version: str = "1.0"
    network: str = "base"
    chain_id: int = 8453
    accepted_token: str = "USDC"
    token_address: str = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    amount: str = "0.005"
    amount_units: str = "5000"  # 0.005 USDC (6 decimals)
    recipient_address: str
    facilitator_url: str
    nonce: str
    expires_at_utc: str
    message: str = "Payment Required: 0.005 USDC on Base to access Critical Raw Minerals Oracle feed"


class MCPToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class MCPToolCallResponse(BaseModel):
    content: List[Dict[str, Any]]
    isError: bool = False
