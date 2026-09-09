from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


# =====================================================================
# 1. CORE COMPLIANCE ENUMS
# =====================================================================

class MineralType(str, Enum):
    NICKEL_MHP = "NICKEL_MHP"                           # Mixed Hydroxide Precipitate (Indonesia/Australia)
    LITHIUM_HYDROXIDE = "LITHIUM_HYDROXIDE"             # Battery Grade Hydroxide (Chile/Australia)
    LITHIUM_CARBONATE = "LITHIUM_CARBONATE"             # Battery Grade Carbonate (Chile/Argentina)
    COBALT_HYDROXIDE = "COBALT_HYDROXIDE"               # Crude Cobalt Hydroxide (DRC)
    NATURAL_GRAPHITE = "NATURAL_GRAPHITE"               # Spherical Coated Natural Graphite (Mozambique/China)
    SYNTHETIC_GRAPHITE = "SYNTHETIC_GRAPHITE"           # Synthetic Anode Graphite (China)
    MANGANESE_SULFATE = "MANGANESE_SULFATE"             # High Purity Sulfate (South Africa/Gabon)
    NEODYMIUM_DYSPROSIUM = "NEODYMIUM_DYSPROSIUM"       # Rare Earth Permanent Magnet Metals (Australia/China)
    ANTIMONY_TRIOXIDE = "ANTIMONY_TRIOXIDE"             # Flame Retardant & Electro-additive (China/Bolivia)


class SourceCountry(str, Enum):
    IDN = "IDN"   # Indonesia
    COD = "COD"   # Democratic Republic of the Congo (DRC)
    CHL = "CHL"   # Chile
    ARG = "ARG"   # Argentina
    AUS = "AUS"   # Australia
    BRA = "BRA"   # Brazil
    CHN = "CHN"   # China
    ZAF = "ZAF"   # South Africa


class MaritimeCIIRating(str, Enum):
    A = "A"  # Major superior
    B = "B"  # Minor superior
    C = "C"  # Moderate / Acceptable
    D = "D"  # Minor inferior (Requires correction under IMO)
    E = "E"  # Inferior (High risk of EU Battery footprint penalty)


# =====================================================================
# 2. SEVEN PILLARS OF COMPLIANCE SPECIFICATION
# =====================================================================

# Pillar 1: Source Nation Statutory Permits
class MinePermitsRecord(BaseModel):
    mining_license_id: str = Field(..., description="Government-issued concession or extraction license ID")
    mine_operator_name: str = Field(..., description="Corporate name of the mining operator")
    simbara_ntpn: Optional[str] = Field(None, description="Indonesia SIMBARA/e-PNBP tax payment code (NTPN)")
    simbara_rkab_quota_id: Optional[str] = Field(None, description="Indonesia annual approved production quota (RKAB) ID")
    dhe_forex_deposit_ref: Optional[str] = Field(None, description="Indonesia Bank Indonesia 30% export forex deposit receipt (DHE)")
    ceec_barcode_tag_id: Optional[str] = Field(None, description="DRC CEEC official tamper-evident barcode tag series")
    egc_artisanal_license: Optional[str] = Field(None, description="DRC EGC monopoly buying license (for artisanal concessions)")
    chile_dga_water_permit_id: Optional[str] = Field(None, description="Chile DGA brine & freshwater extraction permit ID")
    australia_epbc_ref_no: Optional[str] = Field(None, description="Australia Federal EPBC Act MNES environmental approval ID")
    argentina_concession_id: Optional[str] = Field(None, description="Argentina Provincial mining concession registry ID")
    brazil_anm_license_id: Optional[str] = Field(None, description="Brazil ANM mining registry license ID")
    china_dual_use_license_no: Optional[str] = Field(None, description="China MOFCOM dual-use export license (Graphite/Antimony)")


# Pillar 2: Ecological, Spatial & Geological Integrity
class EcologicalSpatialRecord(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Mine extraction centroid latitude (min 6 decimals)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Mine extraction centroid longitude (min 6 decimals)")
    eudr_deforestation_free: bool = Field(True, description="Zero deforestation after EUDR cutoff date 2020-12-31")
    periglacial_zone_violation: bool = Field(False, description="True if within Argentina Ley 26.639 periglacial protected zone")
    indigenous_territory_encroachment: bool = Field(False, description="True if encroaching on Brazil Art. 231 indigenous land")
    tailing_dam_dce_certified: bool = Field(True, description="Brazil ANM 95/2022 tailing dam stability certificate (DCE)")
    aquifer_depletion_alert: bool = Field(False, description="Chile DGA Atacama monitoring well anomaly alert")


# Pillar 3: Labor, Human Rights & Social Safeguards
class LaborHumanRightsRecord(BaseModel):
    child_labor_free_certified: bool = Field(True, description="Zero-tolerance verified absence of under-18 workers")
    rmi_rmap_audit_id: Optional[str] = Field(None, description="Responsible Minerals Initiative (RMI) RMAP certified audit ID")
    ilua_registration_id: Optional[str] = Field(None, description="Australia Native Title Act ILUA registration number")
    forced_labor_uapa_cleared: bool = Field(True, description="Verified absence of Xinjiang UFLPA or forced labor ties")
    independent_third_party_auditor: str = Field("SGS / Bureau Veritas / RCS Global", description="Third-party audit body")


# Pillar 4: Refining & Mass Balance Math
class RefiningMassBalanceRecord(BaseModel):
    refinery_id: str = Field(..., description="Smelter/refinery global facility identifier")
    feedstock_input_metric_tons: float = Field(..., gt=0, description="Total ore/feedstock input in metric tons")
    refined_output_metric_tons: float = Field(..., gt=0, description="Finished product yield in metric tons")
    recovery_yield_pct: float = Field(..., ge=0.0, le=100.0, description="Process recovery efficiency %")
    mass_balance_loss_discrepancy_pct: float = Field(
        ...,
        ge=0.0,
        description="OECD Annex II mass balance loss discrepancy percentage (Must be <= 2.0%)"
    )
    captive_coal_power_used: bool = Field(False, description="True if refined with captive coal power (EU CBAM risk)")


# Pillar 5: Maritime Logistics & Scope 3 Carbon
class MaritimeLogisticsRecord(BaseModel):
    vessel_imo_number: int = Field(..., description="IMO 7-digit ship identification number")
    vessel_name: str = Field(..., description="Cargo vessel registered name")
    cii_rating: MaritimeCIIRating = Field(..., description="IMO MARPOL Annex VI Carbon Intensity Indicator (A-E)")
    ebl_document_hash: str = Field(..., description="UNCITRAL MLETR compliant electronic B/L cryptographic SHA-256 hash")
    transshipment_port: Optional[str] = Field(None, description="Intermediate transit port (e.g. Singapore, Batam)")
    iso_17025_lab_coa_hash: str = Field(..., description="ISO/IEC 17025 accredited laboratory assay COA certificate hash")
    tml_moisture_safe: bool = Field(True, description="IMSBC Code Transportable Moisture Limit (TML) liquefaction safe")


# Pillar 6: Geopolitical, Sanctions & Trade Defense
class GeopoliticalSanctionsRecord(BaseModel):
    feoc_shareholding_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Covered nation (China/Russia/Iran/DPRK) total equity shareholding % (Must be < 25.0% for IRA 30D)"
    )
    feoc_board_control_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Covered nation board seats/voting control % (Must be < 25.0%)"
    )
    contractual_operational_control: bool = Field(
        False,
        description="True if covered entity has effective operational control or exclusive offtake veto"
    )
    ofac_sdn_sanctioned: bool = Field(False, description="True if associated with OFAC SDN list (e.g. Russia Nornickel)")
    us_substantial_transformation_compliant: bool = Field(
        True,
        description="Compliant with US CIT origin standards against transit laundering"
    )


# Pillar 7: Trade Jurisprudence Precedent Citation
class TradeJurisprudenceCitation(BaseModel):
    precedent_case_id: str = Field(..., description="Citation ID (e.g. WTO_DS592, ICSID_ARB_15_31, CIT_SUPERIOR_WIRE)")
    tribunal: str = Field(..., description="Adjudicating body (e.g. WTO DSB, ICSID, US CIT, UK EWHC)")
    legal_rule_applied: str = Field(..., description="Core ratio decidendi or legal doctrine applied to this lot")
    compliance_status: str = Field(..., description="COMPLIANT, WARNING, or VIOLATION")


# =====================================================================
# 3. REQUEST & VERDICT SCHEMAS
# =====================================================================

class SecurityAttestation(BaseModel):
    security_gate_certified: bool = Field(True, description="True if verified and certified by Security Gate x402")
    security_gate_url: str = Field(..., description="Endpoint URL of the certifying security gate")
    security_gate_mode: str = Field("REMOTE_GATEWAY", description="Verification mode: REMOTE_GATEWAY or LOCAL_STANDALONE")
    agent_address: Optional[str] = Field(None, description="Requesting agent wallet address")
    agent_credit_tier: Optional[str] = Field(None, description="FICO-style credit tier (e.g. AAA, AA, A, BBB)")
    agent_credit_score: Optional[int] = Field(None, description="Dynamic agent credit score (300-850)")
    compliance_standard: str = Field("EU_AI_ACT_2024_1689_ART50", description="Regulatory and safety compliance standard")
    dual_attestation_hash: str = Field(..., description="Cryptographic joint hash binding oracle digest & security passport")
    latency_ms: float = Field(..., description="Verification latency in milliseconds")



class MineralLotProvenanceRequest(BaseModel):
    lot_id: str = Field(..., description="Unique enterprise mineral batch/lot identifier (e.g. LOT-2026-NI-IDN-0412)")
    mineral_type: MineralType = Field(..., description="Standard critical mineral commodity type")
    source_country: SourceCountry = Field(..., description="Primary mining country of origin")
    net_weight_metric_tons: float = Field(..., gt=0, description="Gross cargo batch weight in metric tons")
    declared_purity_pct: float = Field(..., ge=0.0, le=100.0, description="Declared metallurgical assay grade %")
    mine_permits: MinePermitsRecord
    ecological_spatial: EcologicalSpatialRecord
    labor_human_rights: LaborHumanRightsRecord
    refining_mass_balance: RefiningMassBalanceRecord
    maritime_logistics: MaritimeLogisticsRecord
    geopolitical_sanctions: GeopoliticalSanctionsRecord
    commercial_price_usd_per_ton: Optional[float] = Field(
        None,
        description="Confidential purchase price per ton (will be ZKP blinded on-chain)"
    )
    agent_address: Optional[str] = Field(
        None,
        description="Requesting buyer agent Polygon wallet address (0x...)"
    )


class ComplianceVerdict(BaseModel):
    overall_compliance_score: float = Field(..., ge=0.0, le=100.0, description="Overall compliance score (0-100)")
    is_fully_compliant: bool = Field(..., description="True if all critical gates are passed without fatal violation")
    eu_battery_regulation_ready: bool = Field(..., description="Compliant with EU Battery Regulation 2023/1542 & Passport")
    us_ira_feoc_compliant: bool = Field(..., description="Compliant with US IRA 30D $7,500 tax credit clean vehicle rules")
    oecd_annex_ii_passed: bool = Field(..., description="Passed OECD Due Diligence Guidance 12 red flags & 2% mass balance")
    eudr_deforestation_cleared: bool = Field(..., description="Compliant with EUDR Regulation 2023/1115")
    csddd_civil_liability_shielded: bool = Field(..., description="Compliant with EU CSDDD Tier-2/3 traceability standards")
    zkp_privacy_sealed: bool = Field(True, description="Commercial pricing & supplier contracts blinded via ZKP")
    gotcha_defenses_applied: List[str] = Field(default_factory=list, description="List of 12-trap defense rules applied")
    jurisprudence_citations: List[TradeJurisprudenceCitation] = Field(default_factory=list)


class LegalDisclaimerRecord(BaseModel):
    disclaimer_version: str = Field("2026.09-v1", description="Legal disclaimer terms version")
    liability_cap_usdc: float = Field(0.50, description="Strict maximum liability cap per verification request in USDC")
    warranty_disclaimer: str = Field(
        "ALGORITHMIC_VERIFICATION_ONLY: This passport represents mathematical and algorithmic rule verification "
        "against codified standards (EU Battery Reg, US IRA FEOC, OECD Annex II, EUDR, CSDDD). The Oracle and its operators "
        "issue NO WARRANTY, express or implied, regarding physical ground truth, actual chemical assay, batch weight, "
        "or unverified laboratory integrity.",
        description="Physical warranty exclusion"
    )
    consequential_damages_waiver: str = Field(
        "ZERO_CONSEQUENTIAL_LIABILITY: The Oracle and its operators bear zero liability for customs seizures, "
        "regulatory fines, sanctions penalties, trade suspensions, vessel demurrage, or commercial losses.",
        description="Consequential damages waiver"
    )
    non_delegable_audit_duty: str = Field(
        "NON_DELEGABLE_IMPORTER_DUTY: The recipient retains sole and non-delegable legal obligation to perform "
        "independent physical testing, assay verification, and due diligence under applicable customs and trade laws.",
        description="Duty of due diligence allocation"
    )
    binding_disclaimer_hash: str = Field(
        ...,
        description="SHA-256 hash of normalized disclaimer terms, cryptographically bound into EIP-712 signature"
    )


class ResponseMeta(BaseModel):
    license: str = Field("AS-IS", description="Open Source AS-IS Software & Data Reference License")
    disclaimer: str = Field(
        "This output is an automated algorithmic data reference and does not constitute "
        "legal, regulatory, or compliance certification. The user/calling agent assumes "
        "all risks regarding real-world application.",
        description="Binding algorithmic reference disclaimer"
    )
    warranty: str = Field(
        "PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING "
        "BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR "
        "PURPOSE AND NONINFRINGEMENT.",
        description="Standard MIT/Apache 2.0 disclaimer of warranty"
    )
    service_nature: str = Field(
        "Algorithmic Heuristic Calculator & Public Ledger Feed (Stateless M2M)",
        description="Pure computational calculator / data vending machine"
    )


class CompliancePassportResponse(BaseModel):
    status: str = "success"
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    oracle: str = "minerals-oracle-x402"
    version: str = "2.0.0"
    lot_id: str
    mineral_type: MineralType
    source_country: SourceCountry
    net_weight_metric_tons: float
    timestamp_utc: str
    network: str = "Polygon (Chain ID 137)"
    verdict: ComplianceVerdict
    passport_qr_data: str
    attestation_digest: str
    legal_disclaimer: LegalDisclaimerRecord = Field(
        ...,
        description="Legally binding terms of algorithmic limitation and fee-capped liability"
    )
    eip712_signature: Optional[str] = Field(None, description="ECDSA EIP-712 structured cryptographic signature")
    onchain_anchor_tx: Optional[str] = Field(None, description="Polygon transaction hash if anchored")
    security_attestation: Optional[SecurityAttestation] = None


# =====================================================================
# 4. PAYMENT, VAULT & ENTERPRISE SCHEMAS (PRESERVED & REPURPOSED)
# =====================================================================

class PricingTier(str, Enum):
    LIGHT = "LIGHT"         # $0.05 USDC (Basic sanctions / quick check)
    STANDARD = "STANDARD"   # $0.50 USDC (Full 7-pillar compliance audit)
    HEAVY = "HEAVY"         # $1.00 USDC (Deep supply-chain & spatial verification)
    ONCHAIN = "ONCHAIN"     # $5.00 USDC (Full audit + EIP-712 On-chain Passport)
    ENTERPRISE = "ENTERPRISE" # $25.00 USDC (Comprehensive Enterprise Passport)


class PaymentChallenge(BaseModel):
    x402_version: str = "2.0"
    network: str = "polygon"
    chain_id: int = 137
    accepted_token: str = "USDC"
    token_address: str = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"
    amount: str = "0.50"
    amount_units: str = "500000"  # 0.50 USDC (6 decimals)
    recipient_address: str
    facilitator_url: str
    nonce: str
    expires_at_utc: str
    message: str = "Payment Required: 0.50 USDC on Polygon to verify critical mineral lot compliance passport"


class PaymentReceipt(BaseModel):
    receipt_id: str
    payer_address: str
    amount_paid_usdc: float
    pricing_tier: PricingTier
    timestamp_utc: str
    oracle_state_digest: str
    oracle_receipt_signature: str
    network: str = "Polygon (Chain ID 137)"


class VaultDepositRequest(BaseModel):
    agent_address: str
    amount_usdc: float = Field(..., gt=0)
    tx_hash: Optional[str] = None


class VaultBalanceResponse(BaseModel):
    agent_address: str
    balance_usdc: float
    total_deposited_usdc: float
    total_consumed_usdc: float
    session_key: str
    query_count: int
    last_active_utc: str


class AutonomousPaymentMethod(str, Enum):
    B2A_USDC_M2M = "B2A_USDC_M2M"                 # Autonomous Agent M2M x402 Protocol
    VAULT_BALANCE = "VAULT_BALANCE"               # Pre-funded Agent Vault Session Key (<1ms)
    USDC_ONCHAIN_POLYGON = "USDC_ONCHAIN_POLYGON" # Native Polygon Mainnet (Chain ID 137)
    USDC_ONCHAIN_BASE = "USDC_ONCHAIN_BASE"       # Base Mainnet (Chain ID 8453)
    USDC_ONCHAIN_ARBITRUM = "USDC_ONCHAIN_ARBITRUM" # Arbitrum One (Chain ID 42161)
    GASLESS_PERMIT2 = "GASLESS_PERMIT2"           # EIP-712 Permit2 Gasless Settlement
    DEV_BYPASS = "DEV_BYPASS"                     # Dev / Testing Bypass
    SANDBOX_FREE_TRIAL = "SANDBOX_FREE_TRIAL"     # Machine IP Sandbox


class MCPToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class MCPToolCallResponse(BaseModel):
    content: List[Dict[str, Any]]
    isError: bool = False


# ===================================================================
# Autonomous AI Agent Evolution & Continuous Improvement Schemas
# ===================================================================

class AgentFeedbackSubmitRequest(BaseModel):
    agent_id: str = Field(
        ...,
        description="Unique identifier of the calling AI agent or operator (e.g., 'tesla-procure-agent-09', 'battery-passport-evaluator')",
        examples=["procurement-agent-alpha-42"]
    )
    feedback_type: str = Field(
        default="FEATURE_REQUEST",
        description="Category: FEATURE_REQUEST, PROTOCOL_PROPOSAL, EDGE_CASE, DATASET_SUGGESTION, or COMPLIANCE_RULE"
    )
    mineral_focus: str = Field(
        default="ALL",
        description="Target mineral: LITHIUM, COBALT, NICKEL, GRAPHITE, RARE_EARTHS, MANGANESE, or ALL"
    )
    title: str = Field(
        ...,
        min_length=5,
        max_length=256,
        description="Concise summary of the proposed improvement or discovered edge case"
    )
    content: str = Field(
        ...,
        min_length=10,
        description="Detailed description, rationale, regulatory reference, or observed issue"
    )
    proposed_solution: Optional[str] = Field(
        None,
        description="Suggested technical, architectural, or regulatory resolution"
    )
    caller_model: Optional[str] = Field(
        None,
        description="LLM / Agent model underpinning the caller (e.g., 'claude-3-5-sonnet', 'gemini-1.5-pro', 'gpt-4o')"
    )
    contact_channel: Optional[str] = Field(
        None,
        description="Agent callback URL, ENS domain, or wallet address for receipt notification"
    )


class AgentFeedbackVoteRequest(BaseModel):
    voter_agent_id: Optional[str] = Field(
        None,
        description="Agent identifier casting the vote (optional)"
    )


class AgentFeedbackResponse(BaseModel):
    status: str
    feedback_id: str
    message: str
    created_at_utc: str
    proposal: Optional[Dict[str, Any]] = None
    meta: Dict[str, Any]


class AgentFeedbackListResponse(BaseModel):
    status: str
    total_proposals: int
    items: List[Dict[str, Any]]
    meta: Dict[str, Any]
