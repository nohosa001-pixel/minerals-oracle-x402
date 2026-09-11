from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field


# =====================================================================
# 1. CORE COMPLIANCE ENUMS
# =====================================================================

class MineralType(str, Enum):
    NICKEL_MHP = "NICKEL_MHP"                           # Mixed Hydroxide Precipitate (Indonesia/Australia)
    LITHIUM_HYDROXIDE = "LITHIUM_HYDROXIDE"             # Battery Grade Hydroxide (Chile/Australia)
    LITHIUM_CARBONATE = "LITHIUM_CARBONATE"             # Battery Grade Carbonate (Chile/Argentina)
    COBALT_HYDROXIDE = "COBALT_HYDROXIDE"               # Crude Cobalt Hydroxide (DRC)
    COPPER_CATHODE = "COPPER_CATHODE"                   # LME Grade A Electrolytic Copper Cathode 99.99% (Chile/Peru)
    COPPER_CONCENTRATE = "COPPER_CONCENTRATE"           # Flotation Copper Concentrate 26-30% Cu (Chile/Peru)
    SILVER_DORE = "SILVER_DORE"                         # Unrefined Silver Doré Bar (Mexico/Peru)
    SILVER_POWDER_SOLAR_PV = "SILVER_POWDER_SOLAR_PV"   # High-Purity 99.99% TOPCon Solar PV Silver Paste (Mexico/Peru)
    NATURAL_GRAPHITE = "NATURAL_GRAPHITE"               # Spherical Coated Natural Graphite (Mozambique/China)
    SYNTHETIC_GRAPHITE = "SYNTHETIC_GRAPHITE"           # Synthetic Anode Graphite (China)
    MANGANESE_SULFATE = "MANGANESE_SULFATE"             # High Purity Sulfate (South Africa/Gabon)
    NEODYMIUM_DYSPROSIUM = "NEODYMIUM_DYSPROSIUM"       # Rare Earth Permanent Magnet Metals (Australia/China)
    ANTIMONY_TRIOXIDE = "ANTIMONY_TRIOXIDE"             # Flame Retardant & Electro-additive (China/Bolivia)
    LITHIUM_BLACK_MASS = "LITHIUM_BLACK_MASS"           # Shredded battery black mass containing lithium (US BIS regulated)
    NICKEL_COBALT_BLACK_MASS = "NICKEL_COBALT_BLACK_MASS" # Recycled Ni/Co black mass (US BIS export restricted)
    TUNGSTEN_SCRAP = "TUNGSTEN_SCRAP"                   # Recycled tungsten scrap (US BIS export restricted)


class SourceCountry(str, Enum):
    IDN = "IDN"   # Indonesia
    COD = "COD"   # Democratic Republic of the Congo (DRC)
    CHL = "CHL"   # Chile
    ARG = "ARG"   # Argentina
    AUS = "AUS"   # Australia
    BRA = "BRA"   # Brazil
    CHN = "CHN"   # China
    ZAF = "ZAF"   # South Africa
    USA = "USA"   # United States of America
    MEX = "MEX"   # Mexico (World #1 Silver Producer)
    PER = "PER"   # Peru (Top Copper & Silver Producer)


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
    us_bis_scrap_export_license: Optional[str] = Field(None, description="US BIS 15 CFR 744 special export license for black mass / tungsten scrap")
    china_extraterritorial_tech_clearance: Optional[str] = Field(None, description="China MOFCOM approval for extraterritorial SX refining tech utilization")
    chile_cochilco_export_id: Optional[str] = Field(None, description="Chile COCHILCO copper export registration & quota clearance")
    mexico_se_mining_concession: Optional[str] = Field(None, description="Mexico Secretaría de Economía mining concession title ID")
    peru_ingemmet_concession_id: Optional[str] = Field(None, description="Peru INGEMMET public mining registry concession ID")


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
    csddd_audit_hash: Optional[str] = Field(None, description="EU CSDDD supply chain human rights and environmental audit SHA-256 hash")


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
    cbam_scope1_emissions_kg_co2e: Optional[float] = Field(None, description="Direct Scope 1 emissions in kg CO2e per kg mineral")
    cbam_scope2_emissions_kg_co2e: Optional[float] = Field(None, description="Indirect Scope 2 electricity emissions in kg CO2e per kg mineral")
    cbam_scope3_emissions_kg_co2e: Optional[float] = Field(None, description="Upstream/downstream Scope 3 emissions in kg CO2e per kg mineral")
    cbam_declaration_id: Optional[str] = Field(None, description="EU CBAM Definitive Period registry declaration reference")
    solvent_extraction_tech_origin: Optional[str] = Field("DOMESTIC", description="Origin of SX technology: DOMESTIC, WESTERN, CHINA_LICENSED, CHINA_UNLICENSED")
    chinese_tech_dependency_pct: float = Field(0.0, ge=0.0, le=100.0, description="Percentage dependency on Chinese proprietary SX/smelting technology/catalysts")
    mofcom_extraterritorial_clearance_id: Optional[str] = Field(None, description="China MOFCOM dual-use extraterritorial technology export authorization ID")
    substitute_western_tech_certified: bool = Field(False, description="Certified availability and operational deployment of non-Chinese Western alternative SX/refining technology")
    sulfuric_acid_input_metric_tons: Optional[float] = Field(None, description="Sulfuric acid (H2SO4) input in metric tons for copper leach/smelting")
    sulfuric_acid_discrepancy_pct: Optional[float] = Field(None, description="Discrepancy % from stoichiometric sulfuric acid requirement (max allowable 5.0%)")
    hvdc_grade_copper_certified: Optional[bool] = Field(None, description="True if copper cathode meets ASTM B115 Grade 1 (99.9935% Cu) for HVDC cables")
    solar_pv_topcon_silver_certified: Optional[bool] = Field(None, description="True if silver powder/paste meets 99.99% purity for N-type TOPCon solar PV cells")


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
    is_recycled_black_mass: bool = Field(False, description="True if cargo batch originates from shredded battery black mass or secondary scrap")
    us_bis_export_authorized: bool = Field(True, description="True if authorized under US BIS 15 CFR 744 scrap retention rules")
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
    us_bis_scrap_retention_cleared: bool = Field(True, description="Compliant with US BIS 15 CFR 744 battery scrap retention mandate (Trap 13)")
    china_tech_jurisdiction_cleared: bool = Field(True, description="Compliant with China Extraterritorial SX refining tech rules (Trap 14)")
    china_tech_licensing_cleared: bool = Field(True, description="Compliant with China Extraterritorial Tech Licensing Jurisdiction (Trap 15)")
    cbam_definitive_period_verified: bool = Field(True, description="Verified under EU CBAM Definitive Period Scope 1-3 rules")
    downstream_cbam_scope3_cleared: bool = Field(True, description="Compliant with EU CBAM 2028 downstream finished/machinery product rules")
    csddd_due_diligence_verified: bool = Field(True, description="Compliant with EU CSDDD human rights and environmental due diligence audit")
    copper_hvdc_certified: Optional[bool] = Field(None, description="Certified for AI Data Center & HVDC Power Grid infrastructure")
    silver_solar_pv_cleared: Optional[bool] = Field(None, description="Certified for N-type TOPCon high-efficiency solar PV cells")
    zkp_privacy_sealed: bool = Field(True, description="Commercial pricing & supplier contracts blinded via ZKP")
    gotcha_defenses_applied: List[str] = Field(default_factory=list, description="List of 16-trap defense rules applied")
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


# =====================================================================
# 6. DEDICATED LITHIUM SPODUMENE ORIGIN PROVENANCE SCHEMAS
# =====================================================================

class LithiumOriginVerifyRequest(BaseModel):
    trace_id: str = Field(..., description="Unique traceability ID (e.g. LIT-AU-2026-X091)")
    product: str = Field("Lithium Hydroxide Monohydrate", description="Refined product form: Lithium Hydroxide, Lithium Carbonate, Spodumene Concentrate")
    mine_name: str = Field(..., description="Name of hard-rock mine (e.g. Greenbushes Lithium Mine, Pilgangoora)")
    mine_country: str = Field("AU", description="ISO alpha-2 country of extraction (AU default)")
    coordinates: List[float] = Field(..., min_length=2, max_length=2, description="[Latitude, Longitude] of extraction centroid")
    minedex_tenement_id: Optional[str] = Field(None, description="Western Australia DMIRS MINEDEX tenement ID (e.g., M01/03)")
    spodumene_tonnage_extracted: float = Field(..., gt=0, description="Gross run-of-mine or SC6 spodumene input in metric tons")
    spodumene_grade_pct: float = Field(6.0, ge=1.0, le=10.0, description="Spodumene Li2O concentrate grade percentage (standard 6.0%)")
    refinery_facility: str = Field(..., description="Name of refining or chemical conversion plant")
    refinery_country: str = Field("AU", description="ISO alpha-2 country of the refinery plant (e.g. AU, US, CHN)")
    refined_output_tonnage: float = Field(..., gt=0, description="Finished lithium product output in metric tons")
    refinery_feoc_equity_pct: float = Field(0.0, ge=0.0, le=100.0, description="Covered nation entity equity/voting share in refinery")
    satellite_vegetation_index: Optional[float] = Field(None, description="Sentinel-2 NDVI for the extraction boundary (typically < 0.2 in active pit)")
    sar_backscatter_db: Optional[float] = Field(None, description="Sentinel-1 SAR C-band backscatter in dB")
    agent_address: Optional[str] = Field(None, description="Calling agent Polygon wallet address for receipt generation")


class ExtractionOriginEvidence(BaseModel):
    mine_name: str
    country: str
    minedex_tenement_id: str
    coordinates: List[float]
    geofence_distance_km: float
    geofence_passed: bool
    satellite_evidence: Dict[str, Any]


class MassBalanceAuditEvidence(BaseModel):
    spodumene_input_metric_tons: float
    refined_output_metric_tons: float
    theoretical_required_spodumene_tons: float
    discrepancy_pct: float
    is_stoichiometrically_sound: bool


class LithiumAuditVerdict(BaseModel):
    ira_compliant: bool = Field(..., description="Eligible for US IRA 30D $7,500 clean vehicle credit")
    crma_origin_eligible: bool = Field(..., description="Eligible for EU Critical Raw Materials Act & Battery Passport")
    feoc_risk_detected: bool = Field(..., description="True if refined in China or >=25% covered nation equity")
    confidence_score: float = Field(..., ge=0.0, le=100.0, description="Algorithmic confidence rating (0-100)")
    defenses_applied: List[str] = Field(default_factory=list)


class LithiumOriginVerifyResponse(BaseModel):
    status: str = "success"
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    trace_id: str
    product: str
    extraction_origin: ExtractionOriginEvidence
    processing_route: List[Dict[str, Any]]
    mass_balance_audit: MassBalanceAuditEvidence
    audit_verdict: LithiumAuditVerdict
    onchain_proof: str
    timestamp: str


# =====================================================================
# 7. DEDICATED INDONESIAN NICKEL MHP PROVENANCE SCHEMAS
# =====================================================================

class NickelOriginVerifyRequest(BaseModel):
    trace_id: str = Field(..., description="Unique traceability batch identifier (e.g. NIC-IDN-2026-MHP01)")
    product: str = Field("Nickel Mixed Hydroxide Precipitate (MHP)", description="Beneficiated intermediate product form (MHP or Ferronickel)")
    concession_name: str = Field(..., description="Mining concession / IUP name (e.g. Morowali Concession, Weda Bay, Sorowako)")
    coordinates: List[float] = Field(..., min_length=2, max_length=2, description="[Latitude, Longitude] of extraction centroid")
    simbara_ntpn: str = Field(..., description="Indonesia Ministry of Energy (ESDM) SIMBARA/e-PNBP payment code (NTPN)")
    dhe_forex_deposit_ref: Optional[str] = Field(None, description="Bank Indonesia 30% export forex deposit receipt reference (DHE BI)")
    limonite_ore_input_tons: float = Field(..., gt=0, description="Gross wet/dry laterite limonite ore input in metric tons")
    ore_grade_ni_pct: float = Field(1.35, ge=0.5, le=3.0, description="Limonite ore nickel content % (standard 1.2% ~ 1.5%)")
    hpal_refinery_name: str = Field(..., description="High Pressure Acid Leach (HPAL) facility name (e.g. QMB New Energy, Huayue)")
    mhp_output_tons: float = Field(..., gt=0, description="Refined MHP product yield in metric tons")
    mhp_grade_ni_pct: float = Field(38.5, ge=30.0, le=45.0, description="MHP nickel metal content % (standard ~38% ~ 40%)")
    captive_coal_power: bool = Field(False, description="True if HPAL plant runs on dedicated captive coal-fired power (EU CBAM risk)")
    feoc_equity_pct: float = Field(0.0, ge=0.0, le=100.0, description="Covered nation entity equity/voting share in smelter JV")
    agent_address: Optional[str] = Field(None, description="Calling agent Polygon wallet address for receipt generation")


class NickelConcessionEvidence(BaseModel):
    concession_name: str
    region: str
    coordinates: List[float]
    geofence_distance_km: float
    geofence_passed: bool
    simbara_ntpn_verified: bool
    dhe_forex_verified: bool


class HPALMassBalanceEvidence(BaseModel):
    limonite_input_tons: float
    mhp_output_tons: float
    theoretical_required_ore_tons: float
    discrepancy_pct: float
    is_stoichiometrically_sound: bool
    hpal_recovery_yield_pct: float


class NickelAuditVerdict(BaseModel):
    simbara_export_cleared: bool = Field(..., description="Inaportnet export clearance legally cleared via SIMBARA NTPN")
    wto_ds592_compliant: bool = Field(..., description="Beneficiated MHP compliant with WTO DS592 domestic processing rules")
    cbam_carbon_ready: bool = Field(..., description="Free of captive coal power; eligible for EU Battery Regulation")
    ira_feoc_compliant: bool = Field(..., description="Covered nation equity < 25.0%; eligible for US IRA 30D credit")
    confidence_score: float = Field(..., ge=0.0, le=100.0, description="Algorithmic confidence rating (0-100)")
    defenses_applied: List[str] = Field(default_factory=list)


class NickelOriginVerifyResponse(BaseModel):
    status: str = "success"
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    trace_id: str
    product: str
    extraction_concession: NickelConcessionEvidence
    refining_facility: Dict[str, Any]
    hpal_mass_balance: HPALMassBalanceEvidence
    audit_verdict: NickelAuditVerdict
    onchain_proof: str
    timestamp: str


# =====================================================================
# 8. DEDICATED DRC COBALT HYDROXIDE PROVENANCE SCHEMAS
# =====================================================================

class CobaltOriginVerifyRequest(BaseModel):
    trace_id: str = Field(..., description="Unique traceability batch identifier (e.g. COB-COD-2026-HYD01)")
    product: str = Field("Crude Cobalt Hydroxide", description="Beneficiated intermediate product form")
    concession_name: str = Field(..., description="Mining concession name (e.g. Tenke Fungurume, Kamoto Copper Company, Mutanda Mining)")
    province: str = Field("Lualaba", description="DRC Province (e.g. Lualaba, Haut-Katanga)")
    coordinates: List[float] = Field(..., min_length=2, max_length=2, description="[Latitude, Longitude] centroid of extraction pit")
    mine_type: str = Field("LSM", description="Extraction scale: Large-Scale Mining ('LSM') or Artisanal & Small-scale ('ASM')")
    ceec_seal_id: str = Field(..., description="DRC CEEC (Centre d'Expertise) tamper-proof barcode seal / export certificate")
    egc_custody_ref: Optional[str] = Field(None, description="Entreprise Générale du Cobalt (EGC) custody reference if ASM involvement")
    asm_comingled: bool = Field(False, description="True if uncertified artisanal ore was co-mingled into industrial lot (Trap 1 risk)")
    zero_child_labor_audit_ref: Optional[str] = Field(None, description="Independent ILO 138/182 zero child labor verification certificate hash/ID")
    heterogenite_ore_input_tons: float = Field(..., gt=0, description="Gross heterogenite/copper-cobalt ore input in metric tons")
    ore_grade_co_pct: float = Field(1.50, ge=0.2, le=10.0, description="Cobalt grade in run-of-mine ore % (standard 1.0% ~ 2.5%)")
    refinery_name: str = Field(..., description="Refinery / hydrometallurgical leaching plant name")
    refinery_country: str = Field("COD", description="Country of primary refining (e.g. COD, FIN, CHN)")
    rmi_rmap_smelter_id: Optional[str] = Field(None, description="Responsible Minerals Initiative (RMI) RMAP audited smelter ID")
    cobalt_hydroxide_output_tons: float = Field(..., gt=0, description="Refined crude cobalt hydroxide output in metric tons")
    hydroxide_grade_co_pct: float = Field(30.0, ge=15.0, le=45.0, description="Cobalt metal content % in hydroxide (standard ~30.0%)")
    feoc_equity_pct: float = Field(0.0, ge=0.0, le=100.0, description="Covered nation entity equity/voting share in operator (cap < 25%)")
    agent_address: Optional[str] = Field(None, description="Calling agent Polygon wallet address for receipt generation")


class CobaltConcessionEvidence(BaseModel):
    concession_name: str
    province: str
    coordinates: List[float]
    geofence_distance_km: float
    geofence_passed: bool
    mine_type: str
    ceec_seal_verified: bool
    egc_custody_verified: bool
    child_labor_audit_verified: bool


class CobaltMassBalanceEvidence(BaseModel):
    heterogenite_input_tons: float
    hydroxide_output_tons: float
    theoretical_required_ore_tons: float
    discrepancy_pct: float
    is_stoichiometrically_sound: bool
    hydrometallurgical_recovery_pct: float


class CobaltAuditVerdict(BaseModel):
    ceec_export_cleared: bool = Field(..., description="Cleared under DRC Mining Code Loi n° 18/001 via CEEC tamper-proof seal")
    asm_segregated: bool = Field(..., description="Free of uncontrolled artisanal co-mingling; compliant with OECD Annex II Red Flags")
    rmi_rmap_certified: bool = Field(..., description="Smelter holds active RMI Responsible Minerals Assurance Process certification")
    child_labor_free: bool = Field(..., description="Certified zero child labor under ILO Conventions 138 & 182")
    ira_feoc_compliant: bool = Field(..., description="Covered nation equity < 25.0%; eligible for US IRA 30D tax credit")
    confidence_score: float = Field(..., ge=0.0, le=100.0, description="Algorithmic confidence rating (0-100)")
    defenses_applied: List[str] = Field(default_factory=list)


class CobaltOriginVerifyResponse(BaseModel):
    status: str = "success"
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    trace_id: str
    product: str
    extraction_concession: CobaltConcessionEvidence
    refining_facility: Dict[str, Any]
    mass_balance_audit: CobaltMassBalanceEvidence
    audit_verdict: CobaltAuditVerdict
    onchain_proof: str
    timestamp: str


# =====================================================================
# 9. COMPOSITE BATTERY PASSPORT & MULTI-MINERAL INTEGRITY SCHEMAS
# =====================================================================

class CompositeBatteryVerifyRequest(BaseModel):
    battery_pack_id: str = Field(..., description="Unique EV battery pack or cell batch serial (e.g. BATT-NCM811-2026-PACK01)")
    cell_chemistry: str = Field("NCM811", description="Cathode active material chemistry (e.g. NCM811, NCM622, NCM523)")
    pack_capacity_kwh: float = Field(84.0, gt=0, description="Gross battery pack capacity in kilowatt-hours (kWh)")
    lithium_lot: LithiumOriginVerifyRequest = Field(..., description="Australian Spodumene Lithium Hydroxide lot data")
    nickel_lot: NickelOriginVerifyRequest = Field(..., description="Indonesian Nickel MHP lot data")
    cobalt_lot: CobaltOriginVerifyRequest = Field(..., description="DRC Katanga Cobalt Hydroxide lot data")
    agent_address: Optional[str] = Field(None, description="Requesting OEM/tier-1 buyer Polygon wallet address")


class CompositeBatteryAuditVerdict(BaseModel):
    ira_30d_tax_credit_eligible: bool = Field(..., description="Eligible for US IRA Section 30D $7,500 clean vehicle credit ($3,750 mineral portion)")
    ira_critical_mineral_fta_ratio_pct: float = Field(..., ge=0.0, le=100.0, description="Calculated % of critical mineral procurement value originating from US FTA partner countries (threshold >= 50%)")
    eu_battery_passport_approved: bool = Field(..., description="Eligible for EU Battery Regulation 2023/1542 mandatory passport registration")
    blended_carbon_footprint_kg_per_kwh: float = Field(..., ge=0.0, description="Blended cradle-to-gate Scope 1-3 carbon footprint (kg CO2e / kWh)")
    composite_confidence_score: float = Field(..., ge=0.0, le=100.0, description="Composite algorithmic confidence rating (0-100)")
    lithium_cleared: bool
    nickel_cleared: bool
    cobalt_cleared: bool
    feoc_taint_detected: bool = Field(..., description="True if any component mineral carries >=25% covered nation equity/control")
    cbam_carbon_penalty_alert: bool = Field(..., description="True if any processing step (e.g. nickel captive coal) incurs EU CBAM carbon tariff liabilities")
    composite_defenses_applied: List[str] = Field(default_factory=list)


class CompositeBatteryVerifyResponse(BaseModel):
    status: str = "success"
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    battery_pack_id: str
    cell_chemistry: str
    pack_capacity_kwh: float
    merkle_root: str
    lithium_summary: Dict[str, Any]
    nickel_summary: Dict[str, Any]
    cobalt_summary: Dict[str, Any]
    composite_verdict: CompositeBatteryAuditVerdict
    master_onchain_proof: str
    timestamp: str


# =====================================================================
# 8. COPPER (HVDC & AI DATA CENTER GRID) SCHEMAS
# =====================================================================

class CopperOriginVerifyRequest(BaseModel):
    lot_id: str = Field(..., description="Unique enterprise copper lot identifier")
    mine_concession_name: str = Field("CHUQUICAMATA", description="Canonical mine concession: CHUQUICAMATA, EL_TENIENTE, ANDINA, ESCONDIDA, LOS_PELAMBRES, CERRO_VERDE")
    extraction_coordinates: Tuple[float, float] = Field(..., description="(lat, lon) centroid coordinates")
    source_country: SourceCountry = Field(SourceCountry.CHL, description="Country of extraction")
    feedstock_concentrate_tons: float = Field(..., gt=0, description="Copper flotation concentrate feed in metric tons")
    concentrate_grade_cu_pct: float = Field(28.0, ge=10.0, le=45.0, description="Copper concentrate assay grade % (default 28.0% Cu)")
    sulfuric_acid_input_tons: float = Field(..., gt=0, description="Actual sulfuric acid (H2SO4) consumed in metric tons")
    refined_copper_cathode_tons: float = Field(..., gt=0, description="Refined Grade A copper cathode output in metric tons")
    copper_cathode_purity_pct: float = Field(99.9935, ge=99.0, le=100.0, description="Cathode assay purity % (ASTM B115 Grade 1 requires 99.9935%)")
    cochilco_export_clearance_id: Optional[str] = Field(None, description="Chile COCHILCO export quota and registration ID")
    hvdc_cable_spec_compliant: bool = Field(True, description="True if certified for AI Data Center HVDC power grid transmission")
    feoc_shareholding_pct: float = Field(0.0, ge=0.0, le=100.0, description="Covered nation equity shareholding %")
    agent_address: Optional[str] = Field(None, description="Buyer agent Polygon wallet address")


class CopperAuditVerdict(BaseModel):
    geofence_verified: bool
    stoichiometric_mass_balance_passed: bool
    sulfuric_acid_ratio_passed: bool
    cochilco_cleared: bool
    hvdc_grid_certified: bool
    feoc_cleared: bool
    confidence_score: float = Field(..., ge=0.0, le=100.0)
    defenses_applied: List[str] = Field(default_factory=list)


class CopperOriginVerifyResponse(BaseModel):
    status: str = "success"
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    lot_id: str
    extraction_origin: Dict[str, Any]
    mass_balance_audit: Dict[str, Any]
    verdict: CopperAuditVerdict
    onchain_proof: str
    timestamp: str


# =====================================================================
# 9. SILVER (N-TYPE TOPCON SOLAR PV PASTE) SCHEMAS
# =====================================================================

class SilverOriginVerifyRequest(BaseModel):
    lot_id: str = Field(..., description="Unique enterprise silver batch identifier")
    mine_concession_name: str = Field("TERRONERA", description="Canonical mine concession: TERRONERA, FRESNILLO, ANTAMINA, UCHUCCHACUA, LOS_PELAMBRES")
    extraction_coordinates: Tuple[float, float] = Field(..., description="(lat, lon) centroid coordinates")
    source_country: SourceCountry = Field(SourceCountry.MEX, description="Country of extraction")
    feedstock_dore_or_ore_kg: float = Field(..., gt=0, description="Unrefined Doré bullion or high-grade ore input in kg")
    feedstock_silver_grade_pct: float = Field(75.0, ge=10.0, le=98.0, description="Doré bullion silver content % (default 75.0% Ag)")
    refined_solar_powder_kg: float = Field(..., gt=0, description="Finished electrolytic silver powder/paste yield in kg")
    refined_purity_pct: float = Field(99.99, ge=95.0, le=100.0, description="Refined silver assay purity % (Solar PV paste requires >= 99.99%)")
    lbma_good_delivery_ref: Optional[str] = Field(None, description="LBMA Good Delivery ref or accredited refiner license ID")
    conflict_free_asm_verified: bool = Field(True, description="Verified free from illegal artisanal laundering or cartel supply")
    topcon_pv_grade_compliant: bool = Field(True, description="Certified for N-type TOPCon / HJT solar cell metallization paste")
    feoc_shareholding_pct: float = Field(0.0, ge=0.0, le=100.0, description="Covered nation equity shareholding %")
    agent_address: Optional[str] = Field(None, description="Buyer agent Polygon wallet address")


class SilverAuditVerdict(BaseModel):
    geofence_verified: bool
    refining_mass_balance_passed: bool
    topcon_solar_pv_certified: bool
    conflict_free_asm_passed: bool
    lbma_cleared: bool
    feoc_cleared: bool
    confidence_score: float = Field(..., ge=0.0, le=100.0)
    defenses_applied: List[str] = Field(default_factory=list)


class SilverOriginVerifyResponse(BaseModel):
    status: str = "success"
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    lot_id: str
    extraction_origin: Dict[str, Any]
    mass_balance_audit: Dict[str, Any]
    verdict: SilverAuditVerdict
    onchain_proof: str
    timestamp: str





