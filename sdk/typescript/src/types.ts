/**
 * minerals-oracle-x402 TypeScript SDK Data Schemas
 * Pure Autonomous AI Agent (M2M) Critical Minerals Provenance & Multi-Chain Escrow Protocol
 */

export type MineralType =
  | 'LITHIUM_HYDROXIDE'
  | 'LITHIUM_CARBONATE'
  | 'NICKEL_MHP'
  | 'COBALT_HYDROXIDE'
  | 'COPPER_CATHODE'
  | 'COPPER_CONCENTRATE'
  | 'SILVER_DORE'
  | 'SILVER_POWDER_SOLAR_PV'
  | 'NATURAL_GRAPHITE'
  | 'SYNTHETIC_GRAPHITE'
  | 'MANGANESE_SULFATE'
  | 'NEODYMIUM_DYSPROSIUM'
  | 'ANTIMONY_TRIOXIDE'
  | 'TUNGSTEN_APT'
  | 'TUNGSTEN_SCRAP'
  | 'RARE_EARTHS_NDPR'
  | 'FERRONIOBIUM'
  | 'SCANDIUM_OXIDE'
  | 'RECYCLED_BLACK_MASS'
  | 'LITHIUM_BLACK_MASS'
  | 'NICKEL_COBALT_BLACK_MASS'
  | 'INDIUM_INGOT'
  | 'GALLIUM_METAL'
  | 'YTTRIUM_OXIDE'
  | 'ANTIMONY_INGOT'
  | 'ALUMINIUM_INGOT';

export type SourceCountry =
  | 'AUS'
  | 'IDN'
  | 'COD'
  | 'CHL'
  | 'ARG'
  | 'PER'
  | 'MEX'
  | 'KOR'
  | 'USA'
  | 'CAN'
  | 'PRT'
  | 'AGO'
  | 'GRL'
  | 'EST'
  | 'KAZ'
  | 'BRA'
  | 'ZMB'
  | 'ESP'
  | 'ZAF'
  | 'CHN'
  | 'DEU'
  | 'VNM'
  | 'JPN'
  | 'AUT'
  | 'TJK'
  | 'UZB'
  | 'GIN';

export type SupportedChain = 'polygon' | 'base' | 'arbitrum' | 'solana';

export interface ClientConfig {
  baseUrl?: string;
  apiKey?: string;
  vaultKey?: string;
  devBypass?: boolean;
  timeoutMs?: number;
}

export interface VerificationVerdict {
  is_compliant: boolean;
  status: string;
  confidence_score: number;
  reasons: string[];
  [key: string]: any;
}

export interface VerificationResponse<T = VerificationVerdict> {
  status: 'success' | 'error';
  batch_id?: string;
  trace_id?: string;
  lot_id?: string;
  audit_verdict?: T;
  verdict?: T;
  proof_hash?: string;
  onchain_signature?: string;
  timestamp?: string;
  [key: string]: any;
}

export interface LithiumVerifyInput {
  trace_id: string;
  product?: string;
  mine_name: string;
  mine_country?: string;
  coordinates: [number, number];
  minedex_tenement_id?: string;
  spodumene_tonnage_extracted: number;
  spodumene_grade_pct?: number;
  refinery_facility: string;
  refinery_country?: string;
  refined_output_tonnage: number;
  refinery_feoc_equity_pct?: number;
}

export interface NickelVerifyInput {
  trace_id: string;
  product?: string;
  concession_name: string;
  coordinates: [number, number];
  simbara_ntpn?: string;
  limonite_ore_input_tons: number;
  ore_grade_ni_pct?: number;
  hpal_refinery_name: string;
  mhp_output_tons: number;
  mhp_grade_ni_pct?: number;
  captive_coal_power?: boolean;
  feoc_equity_pct?: number;
}

export interface CobaltVerifyInput {
  trace_id: string;
  product?: string;
  concession_name: string;
  province?: string;
  coordinates: [number, number];
  mine_type?: 'LSM' | 'ASM';
  ceec_seal_id?: string;
  asm_comingled?: boolean;
  zero_child_labor_audit_ref?: string | null;
  heterogenite_ore_input_tons: number;
  ore_grade_co_pct?: number;
  refinery_name: string;
  refinery_country?: string;
  cobalt_hydroxide_output_tons: number;
  hydroxide_grade_co_pct?: number;
  feoc_equity_pct?: number;
}

export interface CopperVerifyInput {
  lot_id: string;
  mine_concession_name: string;
  extraction_coordinates: [number, number];
  source_country?: string;
  feedstock_concentrate_tons: number;
  concentrate_grade_cu_pct?: number;
  sulfuric_acid_input_tons?: number;
  refined_copper_cathode_tons: number;
  copper_cathode_purity_pct?: number;
  cochilco_export_clearance_id?: string | null;
  hvdc_cable_spec_compliant?: boolean;
  feoc_shareholding_pct?: number;
}

export interface SilverVerifyInput {
  lot_id: string;
  mine_concession_name: string;
  extraction_coordinates: [number, number];
  source_country?: string;
  feedstock_dore_or_ore_kg: number;
  feedstock_silver_grade_pct?: number;
  refined_solar_powder_kg: number;
  refined_purity_pct?: number;
  lbma_good_delivery_ref?: string | null;
  conflict_free_asm_verified?: boolean;
  topcon_pv_grade_compliant?: boolean;
  feoc_shareholding_pct?: number;
}

export interface TungstenVerifyInput {
  batch_id: string;
  tenement_id: string;
  latitude: number;
  longitude: number;
  apt_wo3_grade_pct?: number;
  dodd_frank_conflict_free?: boolean;
  ndaa_defense_procurement_eligible?: boolean;
  source_country?: SourceCountry;
  client_identity?: string;
}

export interface RareEarthsVerifyInput {
  batch_id: string;
  tenement_id: string;
  latitude: number;
  longitude: number;
  ndpr_oxide_purity_pct?: number;
  thorium_uranium_radiation_ppm?: number;
  declared_china_origin_ratio?: number;
  source_country?: SourceCountry;
  client_identity?: string;
}

export interface NiobiumScandiumVerifyInput {
  batch_id: string;
  tenement_id: string;
  latitude: number;
  longitude: number;
  commodity_type?: 'FERRONIOBIUM' | 'SCANDIUM_OXIDE';
  fe_nb_grade_pct?: number;
  sc2o3_purity_pct?: number;
  doe_exim_loan_eligible?: boolean;
  ndaa_defense_procurement_eligible?: boolean;
  source_country?: SourceCountry;
  client_identity?: string;
}

export interface TradeDealSpec {
  deal_id: string;
  commodity: MineralType;
  volume_tons: number;
  unit_price_usd_per_ton: number;
  total_deal_value_usd: number;
  origin_country: SourceCountry | string;
  destination_country: string;
  feoc_cleared?: boolean;
  mass_balance_cleared?: boolean;
  ebl_document_id: string;
  buyer_agent_address: string;
  seller_agent_address: string;
  settlement_currency?: string;
  projected_savings_usd?: number;
  gain_share_rate_pct?: number;
  calculated_gain_share_fee_usd?: number;
  fee_cap_applied?: boolean;
  hybrid_settlement_summary?: string;
  expires_at_utc?: string;
  created_at_utc: string;
}

export interface TradeDealProposeInput {
  spec?: TradeDealSpec;
  seller_signature: string;
  deal_id?: string;
  commodity?: MineralType;
  commodity_type?: MineralType;
  volume_tons?: number;
  quantity_metric_tons?: number;
  unit_price_usd_per_ton?: number;
  unit_price_usd?: number;
  total_deal_value_usd?: number;
  origin_country?: SourceCountry | string;
  destination_country?: string;
  feoc_cleared?: boolean;
  mass_balance_cleared?: boolean;
  ebl_document_id?: string;
  ebl_document_hash?: string;
  buyer_agent_address?: string;
  seller_agent_address?: string;
  delivery_incoterm?: string;
  settlement_currency?: string;
  projected_savings_usd?: number;
  created_at_utc?: string;
  [key: string]: any;
}

export interface TradeDealDualSignInput {
  deal_id: string;
  buyer_signature: string;
  buyer_agent_address?: string;
}

export interface TradeDealAttestation {
  status: string;
  deal_id: string;
  deal_state: string;
  buyer_agent_address: string;
  seller_agent_address: string;
  total_value_usd: number;
  oracle_signature?: string;
  deal_hash: string;
  verified_at_utc: string;
  [key: string]: any;
}

export interface EscrowCalldataResponse {
  deal_id: string;
  chain: string;
  chain_id: number;
  escrow_contract_address: string;
  usdc_token_address: string;
  total_usd_value: number;
  required_usdc_units: string;
  seller_agent_address: string;
  buyer_agent_address: string;
  deal_id_bytes32: string;
  ebl_hash_bytes32: string;
  duration_seconds: number;
  function_signature: string;
  calldata: string;
  next_action: string;
}


// ============================================================================
// ElizaOS Brain & Security Gate x402 4-Tier Bridge Types
// ============================================================================

export interface BrainPerceptionInput {
  caller_agent_id: string;
  stimulus_text: string;
  session_id?: string;
  origin_country?: SourceCountry | string;
}

export interface BrainPerceptionResponse {
  is_safe: boolean;
  decision: 'INGESTED_TO_BRAIN' | 'BLOCKED_BY_SECURITY_GATE';
  memory_poisoning_prevented?: boolean;
  threat_fingerprint?: string;
  threats?: string[];
  memory_id?: string;
  working_memory_count?: number;
  readiness_score?: number;
  [key: string]: any;
}

export interface BrainExecutionInput {
  agent_id?: string;
  deal_id: string;
  mineral_type: MineralType | string;
  product_name: string;
  declared_grade_pct: number;
  declared_tonnage: number;
  origin_country: SourceCountry | string;
  destination_port?: string;
  recipient_wallet: string;
  trade_value_usdc?: number;
  action_intent?: string;
}

export interface BrainExecutionResponse {
  status: 'APPROVED_AND_EXECUTED' | 'REJECTED_METALLURGICAL_ANOMALY' | 'BLOCKED_BY_POLICY';
  is_executable: boolean;
  deal_id: string;
  mineral_fact_check: {
    is_plausible: boolean;
    product: string;
    grade_pct: number;
    declared_tonnage: number;
    reason?: string;
  };
  sub_account?: {
    ephemeral_public_key: string;
    micro_cap_limit_usd: number;
    balance_usd: number;
    single_use: boolean;
    expires_at_utc: string;
  };
  ai_act_compliance?: {
    eu_ai_act_art50_watermark: string;
    synthetically_generated: boolean;
    watermarked_at_utc: string;
  };
  eip712_attestation?: {
    verifying_contract: string;
    deal_hash: string;
    signature_preview: string;
  };
  rwa_yield_vault?: {
    eligible: boolean;
    asset: string;
    target_apy_pct: number;
    transit_escrow_yield_usd: number;
  };
  brain_readiness_score: number;
  [key: string]: any;
}

export interface BrainDiagnosticsResponse {
  agent_identity: string;
  provider_identity: string;
  readiness_score: number;
  working_memory_count: number;
  episodic_memory_count: number;
  immune_threats_neutralized: number;
  threat_fingerprints: string[];
}

export interface DDSGenerationRequest {
  operator_eori: string;
  operator_name: string;
  operator_address: string;
  operator_country: string;
  commodity_type: string;
  net_mass_kg: number;
  latitude: number;
  longitude: number;
  area_hectares?: number;
  concession_id: string;
  concession_name: string;
  concession_country: string;
  bill_of_lading_number: string;
  vessel_name?: string;
  destination_port_unlocode?: string;
}

export interface DDSGenerationResponse {
  status: string;
  dds_reference_number: string;
  customs_pre_clearance_status: string;
  sha256_attestation_digest: string;
  dds_json: Record<string, any>;
  xml_preview: string;
}

export interface InspectionCertificate {
  certificate_id: string;
  inspection_agency: 'SGS' | 'INTERTEK' | 'BUREAU_VERITAS' | 'ALEX_STEWART' | string;
  inspection_date: string;
  moisture_pct: number;
  dry_metric_tons: number;
  assayed_grade_pct: number;
  assay_method?: string;
  certificate_sha256?: string;
}

export interface CommercialSettlementRequest {
  deal_id: string;
  commodity_type: string;
  contract_wet_tonnage_mt: number;
  contract_target_grade_pct: number;
  base_price_per_dmt_usdc: number;
  loading_cert: InspectionCertificate;
  discharging_cert: InspectionCertificate;
  umpire_cert?: InspectionCertificate;
  tolerance_grade_pct?: number;
  rwa_yield_annual_pct?: number;
  transit_days?: number;
}

export interface CommercialSettlementResponse {
  status: string;
  clearing_verdict: Record<string, any>;
}

export interface MultiChainGasBalancesResponse {
  relayer_address: string;
  creator_wallet: string;
  timestamp_utc: string;
  chains: {
    polygon: {
      network: string;
      chain_id: number;
      gas_token: string;
      balance: number;
      balance_formatted: string;
      sufficient_for_gas: boolean;
      status: string;
    };
    base: {
      network: string;
      chain_id: number;
      gas_token: string;
      balance: number;
      balance_formatted: string;
      sufficient_for_gas: boolean;
      status: string;
    };
    arbitrum: {
      network: string;
      chain_id: number;
      gas_token: string;
      balance: number;
      balance_formatted: string;
      sufficient_for_gas: boolean;
      status: string;
    };
  };
  all_chains_active: boolean;
}

export const MULTICHAIN_DEPLOYED_CONTRACTS = {
  creator: '0xA185B43fDD19619f99952AAed6eabf1029bF36a1',
  polygon: {
    chainId: 137,
    tradeFinanceSettlementEngine: '0x1dD725fB4860e1e9E00aA887F4bda5acD3789d10',
    dynamicTradeEscrow: '0x3A863A2b1018B47FE79041FCDF56efEa3f8b978F',
    mineralTradeEscrow: '0xd1F37196A1fe73Caa89ce7f4a58D6Fe49FD47655',
    mineralsOracleConsumer: '0x5F565115441188b5dCa06539615Fc154BC7f3028',
    agentPaymentVault: '0xbFc79F55E410508aBCa2FF8ebA1120de4F209f68',
    usdc: '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359',
  },
  base: {
    chainId: 8453,
    tradeFinanceSettlementEngine: '0x9462587838fb8436C286AC9E04AAb6D42Eaf6D93',
    dynamicTradeEscrow: '0x54786360Db4582AEC2435E216479FD4ff093CB80',
    mineralTradeEscrow: '0xbFc79F55E410508aBCa2FF8ebA1120de4F209f68',
    mineralsOracleConsumer: '0xF0A781372cd7E32485603823390c791495140ca9',
    agentPaymentVault: '0x8eB40eF1f032dd66CD54c6e1D0C29980C31d5E57',
    usdc: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
  },
  arbitrum: {
    chainId: 42161,
    tradeFinanceSettlementEngine: '0x402E95B6aE9BBD26A227A1AE2aC7f52E14E1A314',
    dynamicTradeEscrow: '0x54786360Db4582AEC2435E216479FD4ff093CB80',
    mineralTradeEscrow: '0x1884025dD7E510a4490533eC46A362fCb08D3822',
    mineralsOracleConsumer: '0x75F36e1682f283feBfB683dD40e93785715cE404',
    agentPaymentVault: '0xC089E5f72a7F5550Bb383C31B04Bf430a4E31372',
    usdc: '0xaf88d065e77c8cC2239327C5EDb3A432268e5831',
  },
  solana: {
    chainId: 501,
    creator: '411ksMz9RHYVtVMe6RUUErzZYtrU9zzvkgzswKbqx9qp',
    tradeFinanceSettlementEngine: 'TrdFx402ZkR3M5vW9aK7nB1pQ2eC8sY6tU4jH7vL9mNp',
    dynamicTradeEscrow: 'DynSxW8JCy6296toTYrdhJqnoxtMvf3CPmtSSFEyqNnz',
    mineralTradeEscrow: 'AGR3W3R9pKxnuZGYrpaggfkbMKVrjoniLaGvi1voBFSC',
    mineralsOracleConsumer: '21ZR1QCyAbNrRLs1iWEkdbNsfCFdJcy6ip9R2JxDbkTL',
    agentPaymentVault: '7oZ16YaazQzN6z5uA1nAZWD9oGUDXyvHwXGJLFYyWi3y',
    usdc: 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
  },
} as const;
