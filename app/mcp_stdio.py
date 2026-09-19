from __future__ import annotations

import sys
import json
import hashlib
import time
from typing import Dict, Any, Optional, List

from app.compliance_engine import compliance_engine
from app.schemas import (
    MineralLotProvenanceRequest,
    MineralType,
    SourceCountry,
    PricingTier,
    MaritimeCIIRating,
    MaritimeRouteRequest,
    EBLVerificationRequest,
    TradeRouteOptimizationRequest,
    AgentSessionOpenRequest,
    AgentSessionCloseRequest,
    TradeDealProposeRequest,
    TradeDealDualSignRequest,
    TradeDealRejectRequest,
    TradeDealCancelRequest,
    TradeDealVerifyRequest,
)
from app.global_trade_engine import global_trade_engine
from app.agent_session_vault import get_agent_session_vault
from app.a2a_deal_engine import get_a2a_deal_engine
from app.evolution_manager import evolution_manager
from app.vault_manager import vault_manager
from app.x402_verifier import x402_verifier

agent_session_vault = get_agent_session_vault()
a2a_deal_engine = get_a2a_deal_engine()



def handle_initialize(req_id: Any) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {
                    "listChanged": False
                }
            },
            "serverInfo": {
                "name": "battery-passport-oracle",
                "version": "2.0.0"
            }
        }
    }


def handle_tools_list(req_id: Any) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "tools": [
                {
                    "name": "verify_mineral_lot_compliance",
                    "description": (
                        "Fetches raw algorithmic indices derived from open satellite/market data and computes "
                        "12-trap regulatory rule heuristics for a critical mineral consignment. "
                        "DO NOT use as an official regulatory legal filing or physical assay certification "
                        "without independent manual verification."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "lot_id": {"type": "string", "description": "Unique lot/batch identifier"},
                            "mineral_type": {"type": "string", "enum": ["NICKEL_MHP", "LITHIUM_HYDROXIDE", "LITHIUM_CARBONATE", "COBALT_HYDROXIDE", "NATURAL_GRAPHITE", "SYNTHETIC_GRAPHITE", "MANGANESE_SULFATE", "NEODYMIUM_DYSPROSIUM", "ANTIMONY_TRIOXIDE"]},
                            "source_country": {"type": "string", "enum": ["IDN", "COD", "CHL", "ARG", "AUS", "BRA", "CHN", "ZAF"]},
                            "net_weight_metric_tons": {"type": "number", "description": "Net weight in metric tons"},
                            "declared_purity_pct": {"type": "number", "description": "Declared assay purity percentage"}
                        },
                        "required": ["lot_id", "mineral_type", "source_country", "net_weight_metric_tons"]
                    }
                },
                {
                    "name": "verify_lithium_origin",
                    "description": (
                        "Verifies Australian hard-rock Spodumene to Lithium Hydroxide supply-chain provenance. "
                        "Evaluates WA MINEDEX GIS geofencing (Greenbushes, Pilgangoora, Mt Marion), "
                        "stoichiometric mass balance (SC6.0 to LiOH <= 2.5% loss), and US IRA Section 30D FEOC 25% clean origin."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "trace_id": {"type": "string", "description": "Traceability lot ID (e.g., LIT-AU-2026-X091)"},
                            "product": {"type": "string", "default": "Lithium Hydroxide Monohydrate"},
                            "mine_name": {"type": "string", "description": "Hard-rock mine name (e.g. Greenbushes, Pilgangoora)"},
                            "mine_country": {"type": "string", "default": "AU"},
                            "coordinates": {"type": "array", "items": {"type": "number"}, "description": "[Lat, Lon] centroid"},
                            "minedex_tenement_id": {"type": "string", "description": "WA MINEDEX permit ID (optional)"},
                            "spodumene_tonnage_extracted": {"type": "number", "description": "Gross spodumene input in metric tons"},
                            "spodumene_grade_pct": {"type": "number", "default": 6.0, "description": "Li2O grade % (default 6.0%)"},
                            "refinery_facility": {"type": "string", "description": "Refining facility name (e.g. Kwinana Plant)"},
                            "refinery_country": {"type": "string", "default": "AU", "description": "Refinery country code (AU, US, CHN)"},
                            "refined_output_tonnage": {"type": "number", "description": "Finished product output in metric tons"},
                            "refinery_feoc_equity_pct": {"type": "number", "default": 0.0, "description": "Covered nation equity % (cap < 25%)"}
                        },
                        "required": ["trace_id", "mine_name", "coordinates", "spodumene_tonnage_extracted", "refinery_facility", "refined_output_tonnage"]
                    }
                },
                {
                    "name": "verify_nickel_origin",
                    "description": (
                        "Verifies Indonesian laterite Limonite-to-Nickel MHP supply-chain provenance. "
                        "Evaluates Sulawesi/Halmahera concession geofencing (IMIP Morowali, IWIP Weda Bay), "
                        "SIMBARA NTPN & DHE BI tax validation, HPAL stoichiometric mass balance (~31t Limonite to 1t MHP <= 2.5% loss), "
                        "Captive Coal EU CBAM screening, and US IRA 30D FEOC 25% compliance."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "trace_id": {"type": "string", "description": "Traceability batch ID (e.g. NIC-IDN-2026-MHP01)"},
                            "product": {"type": "string", "default": "Nickel Mixed Hydroxide Precipitate (MHP)"},
                            "concession_name": {"type": "string", "description": "Concession name (e.g. Morowali Concession, Weda Bay)"},
                            "coordinates": {"type": "array", "items": {"type": "number"}, "description": "[Lat, Lon] centroid"},
                            "simbara_ntpn": {"type": "string", "description": "Indonesia ESDM SIMBARA NTPN tax receipt code"},
                            "dhe_forex_deposit_ref": {"type": "string", "description": "Bank Indonesia 30% retention receipt (optional)"},
                            "limonite_ore_input_tons": {"type": "number", "description": "Gross limonite ore input in metric tons"},
                            "ore_grade_ni_pct": {"type": "number", "default": 1.35, "description": "Limonite ore Ni % (default 1.35%)"},
                            "hpal_refinery_name": {"type": "string", "description": "HPAL refinery name (e.g. QMB New Energy)"},
                            "mhp_output_tons": {"type": "number", "description": "Refined MHP output in metric tons"},
                            "mhp_grade_ni_pct": {"type": "number", "default": 38.5, "description": "MHP Ni % (default 38.5%)"},
                            "captive_coal_power": {"type": "boolean", "default": False, "description": "True if refinery runs on captive coal"},
                            "feoc_equity_pct": {"type": "number", "default": 0.0, "description": "Covered nation equity % (cap < 25%)"}
                        },
                        "required": ["trace_id", "concession_name", "coordinates", "simbara_ntpn", "limonite_ore_input_tons", "hpal_refinery_name", "mhp_output_tons"]
                    }
                },
                {
                    "name": "verify_cobalt_origin",
                    "description": (
                        "Verifies DRC Katanga heterogenite-to-cobalt hydroxide supply-chain provenance. "
                        "Evaluates Katanga Copperbelt concession geofencing (Tenke Fungurume, Kamoto KCC, Mutanda, Metalkol), "
                        "CEEC tamper-proof barcode seal, ASM co-mingling segregation & EGC custody (Trap 1), "
                        "ILO 138/182 zero child labor due diligence, RMI RMAP smelter certification, "
                        "stoichiometric mass balance (~23.5t ore to 1t hydroxide <= 2.5% loss), and US IRA FEOC 25% screening."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "trace_id": {"type": "string", "description": "Traceability batch ID (e.g. COB-COD-2026-HYD01)"},
                            "product": {"type": "string", "default": "Crude Cobalt Hydroxide"},
                            "concession_name": {"type": "string", "description": "Concession name (e.g. Kamoto Copper Company, Tenke Fungurume)"},
                            "province": {"type": "string", "default": "Lualaba"},
                            "coordinates": {"type": "array", "items": {"type": "number"}, "description": "[Lat, Lon] centroid"},
                            "mine_type": {"type": "string", "default": "LSM", "description": "LSM or ASM"},
                            "ceec_seal_id": {"type": "string", "description": "DRC CEEC barcode export seal ID"},
                            "egc_custody_ref": {"type": "string", "description": "EGC artisanal custody receipt (optional)"},
                            "asm_comingled": {"type": "boolean", "default": False, "description": "True if uncertified ASM ore co-mingled"},
                            "zero_child_labor_audit_ref": {"type": "string", "description": "ILO 138/182 zero child labor audit reference"},
                            "heterogenite_ore_input_tons": {"type": "number", "description": "Gross heterogenite ore input in metric tons"},
                            "ore_grade_co_pct": {"type": "number", "default": 1.50, "description": "Ore Co % (default 1.50%)"},
                            "refinery_name": {"type": "string", "description": "Refinery name (e.g. Luilu Metallurgical Plant)"},
                            "refinery_country": {"type": "string", "default": "COD", "description": "Refinery country code"},
                            "rmi_rmap_smelter_id": {"type": "string", "description": "RMI RMAP audited smelter ID (optional)"},
                            "cobalt_hydroxide_output_tons": {"type": "number", "description": "Refined crude hydroxide output in metric tons"},
                            "hydroxide_grade_co_pct": {"type": "number", "default": 30.0, "description": "Hydroxide Co % (default 30.0%)"},
                            "feoc_equity_pct": {"type": "number", "default": 0.0, "description": "Covered nation equity % (cap < 25%)"}
                        },
                        "required": ["trace_id", "concession_name", "coordinates", "ceec_seal_id", "heterogenite_ore_input_tons", "refinery_name", "cobalt_hydroxide_output_tons"]
                    }
                },
                {
                    "name": "verify_composite_battery_passport",
                    "description": (
                        "Evaluates end-to-end composite EV battery pack compliance and issues a Master Passport on Polygon. "
                        "Orchestrates Australian Lithium, Indonesian Nickel, and DRC Cobalt streams; "
                        "computes US IRA Section 30D critical mineral 50% FTA value-added ratio; "
                        "enforces zero FEOC taint across all component streams; "
                        "audits EU Battery Regulation 2023/1542 blended carbon footprint and CSDDD due diligence; "
                        "and binds all proofs into a cryptographic Merkle Root EIP-712 Master Signature."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "battery_pack_id": {"type": "string", "description": "Unique battery pack serial (e.g. BATT-NCM811-2026-PACK01)"},
                            "cell_chemistry": {"type": "string", "default": "NCM811", "description": "Cathode chemistry (NCM811, NCM622, NCM523)"},
                            "pack_capacity_kwh": {"type": "number", "default": 84.0, "description": "Pack capacity in kWh"},
                            "lithium_lot": {"type": "object", "description": "LithiumOriginVerifyRequest payload"},
                            "nickel_lot": {"type": "object", "description": "NickelOriginVerifyRequest payload"},
                            "cobalt_lot": {"type": "object", "description": "CobaltOriginVerifyRequest payload"}
                        },
                        "required": ["battery_pack_id", "lithium_lot", "nickel_lot", "cobalt_lot"]
                    }
                },
                {
                    "name": "verify_copper_origin",
                    "description": (
                        "Verifies South American Copper-to-Cathode supply-chain provenance. "
                        "Evaluates Codelco/Escondida/Cerro Verde GIS geofencing (Chuquicamata, El Teniente, Andina), "
                        "stoichiometric flotation-to-cathode mass balance (loss discrepancy <= 2.0%), "
                        "sulfuric acid (H2SO4) deficit screening (variance <= 5.0%), Chilean COCHILCO export clearance, "
                        "and AI Data Center / HVDC Power Grid specifications (ASTM B115 Grade 1, 99.9935% Cu)."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "lot_id": {"type": "string", "description": "Unique lot ID (e.g. COP-CHL-2026-LOT01)"},
                            "mine_concession_name": {"type": "string", "default": "CHUQUICAMATA", "description": "Mine concession name"},
                            "extraction_coordinates": {"type": "array", "items": {"type": "number"}, "description": "[Lat, Lon] centroid"},
                            "feedstock_concentrate_tons": {"type": "number", "description": "Flotation concentrate input in metric tons"},
                            "concentrate_grade_cu_pct": {"type": "number", "default": 28.0, "description": "Cu concentrate grade %"},
                            "sulfuric_acid_input_tons": {"type": "number", "description": "Actual H2SO4 consumed in metric tons"},
                            "refined_copper_cathode_tons": {"type": "number", "description": "Cathode output in metric tons"},
                            "copper_cathode_purity_pct": {"type": "number", "default": 99.9935, "description": "Assay purity % (Grade 1 >= 99.9935%)"},
                            "cochilco_export_clearance_id": {"type": "string", "description": "Chilean COCHILCO clearance ID"},
                            "hvdc_cable_spec_compliant": {"type": "boolean", "default": True, "description": "HVDC grid compliance"},
                            "feoc_shareholding_pct": {"type": "number", "default": 0.0, "description": "Covered nation equity % (cap < 25%)"}
                        },
                        "required": ["lot_id", "extraction_coordinates", "feedstock_concentrate_tons", "sulfuric_acid_input_tons", "refined_copper_cathode_tons"]
                    }
                },
                {
                    "name": "verify_silver_origin",
                    "description": (
                        "Verifies Mexican & Global Silver supply-chain provenance. "
                        "Evaluates Terronera/Fresnillo/Antamina GIS geofencing, "
                        "Moebius/Thum electrolytic mass balance (loss discrepancy <= 2.0%), "
                        "N-Type TOPCon High-Efficiency Solar PV paste assay purity (>= 99.99% Ag), "
                        "anti-cartel conflict ASM screening, and LBMA Good Delivery audit."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "lot_id": {"type": "string", "description": "Unique silver batch ID (e.g. SIL-MEX-2026-PV01)"},
                            "mine_concession_name": {"type": "string", "default": "TERRONERA", "description": "Mine concession name"},
                            "extraction_coordinates": {"type": "array", "items": {"type": "number"}, "description": "[Lat, Lon] centroid"},
                            "feedstock_dore_or_ore_kg": {"type": "number", "description": "Gross Doré bullion or ore input in kg"},
                            "feedstock_silver_grade_pct": {"type": "number", "default": 75.0, "description": "Doré silver content %"},
                            "refined_solar_powder_kg": {"type": "number", "description": "Finished refined silver powder/paste yield in kg"},
                            "refined_purity_pct": {"type": "number", "default": 99.99, "description": "Assay purity % (Solar PV requires >= 99.99%)"},
                            "lbma_good_delivery_ref": {"type": "string", "description": "LBMA accreditation ref (optional)"},
                            "conflict_free_asm_verified": {"type": "boolean", "default": True, "description": "Free from cartel/ASM taint"},
                            "topcon_pv_grade_compliant": {"type": "boolean", "default": True, "description": "N-type TOPCon solar grade compliance"},
                            "feoc_shareholding_pct": {"type": "number", "default": 0.0, "description": "Covered nation equity % (cap < 25%)"}
                        },
                        "required": ["lot_id", "extraction_coordinates", "feedstock_dore_or_ore_kg", "refined_solar_powder_kg"]
                    }
                },
                {
                    "name": "list_trade_precedents",
                    "description": (
                        "Query international trade jurisprudence precedents embedded in the oracle: "
                        "WTO DS592 (Indonesia Raw Materials), WTO DS431 (China Rare Earths), "
                        "ICSID ARB/15/31 (Gabriel Resources), and US CIT Superior Wire (Origin Laundering)."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "get_compliance_status",
                    "description": "Check current regulatory monitoring status across 10 jurisdictions and 12-trap defenses.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "minerals_submit_agent_feedback",
                    "description": (
                        "Allows an autonomous AI agent or bot operator to submit an evolution proposal, "
                        "mineral dataset addition request, regulatory edge case, or protocol improvement "
                        "to continuously evolve the Minerals Oracle engine."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": "Unique identifier of the calling AI agent or operator (e.g. 'tesla-procure-agent-09')"
                            },
                            "title": {
                                "type": "string",
                                "description": "Summary of proposed improvement or edge case"
                            },
                            "content": {
                                "type": "string",
                                "description": "Detailed description, legal context, or observed issue"
                            },
                            "feedback_type": {
                                "type": "string",
                                "enum": ["FEATURE_REQUEST", "PROTOCOL_PROPOSAL", "EDGE_CASE", "DATASET_SUGGESTION", "COMPLIANCE_RULE"],
                                "default": "FEATURE_REQUEST",
                                "description": "Classification category"
                            },
                            "mineral_focus": {
                                "type": "string",
                                "enum": ["LITHIUM", "COBALT", "NICKEL", "GRAPHITE", "RARE_EARTHS", "MANGANESE", "ALL"],
                                "default": "ALL",
                                "description": "Relevant mineral commodity"
                            },
                            "proposed_solution": {
                                "type": "string",
                                "description": "Optional suggested technical or architectural fix"
                            },
                            "caller_model": {
                                "type": "string",
                                "description": "Optional underlying model (e.g. 'claude-3-5-sonnet', 'gemini-1.5-pro')"
                            },
                            "contact_channel": {
                                "type": "string",
                                "description": "Optional agent webhook, ENS domain, or wallet address"
                            }
                        },
                        "required": ["agent_id", "title", "content"]
                    }
                },
                {
                    "name": "minerals_list_evolution_proposals",
                    "description": "List active autonomous agent evolution proposals and improvement requests.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "default": 20, "description": "Maximum number of proposals to fetch"},
                            "mineral_focus": {"type": "string", "description": "Optional filter by mineral"}
                        }
                    }
                },
                {
                    "name": "register_agent_account",
                    "description": "Self-service onboarding for autonomous AI agents. Instantly returns a session key and seeds an initial free trial balance (e.g. 0.05 USDC).",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "agent_name": {"type": "string", "description": "Agent or bot operator name"},
                            "agent_address": {"type": "string", "description": "Optional Polygon wallet address (0x...)"},
                            "initial_trial_balance_usdc": {"type": "number", "default": 0.05, "description": "Trial balance in USDC"}
                        },
                        "required": ["agent_name"]
                    }
                },
                {
                    "name": "get_agent_vault_balance",
                    "description": "Retrieves pre-funded USDC vault balance, total consumed, query count, and remaining query capacity across tiers for an agent.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "session_key": {"type": "string", "description": "Agent session key (vault_key_...)"},
                            "agent_address": {"type": "string", "description": "Agent Polygon address (0x...)"}
                        }
                    }
                },
                {
                    "name": "request_x402_payment_challenge",
                    "description": "Generates a fresh multi-chain payment challenge nonce with pricing tier details and gasless Permit2 contract address.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "pricing_tier": {"type": "string", "enum": ["LIGHT", "STANDARD", "HEAVY", "ONCHAIN"], "default": "STANDARD"},
                            "chain": {"type": "string", "enum": ["polygon", "base", "arbitrum"], "default": "polygon"}
                        }
                    }
                },
                {
                    "name": "simulate_procurement_rfq",
                    "description": "Simulates multi-mineral consignment RFQ for battery manufacturing. Computes US IRA 50% FTA threshold and FEOC 25% taint propagation before placing contracts.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "rfq_id": {"type": "string", "description": "Buyer agent RFQ identifier"},
                            "cell_chemistry": {"type": "string", "default": "NCM811", "description": "Target battery chemistry"},
                            "pack_capacity_kwh": {"type": "number", "default": 84.0},
                            "lithium_tons": {"type": "number"},
                            "lithium_origin_country": {"type": "string", "default": "AUS"},
                            "lithium_feoc_equity_pct": {"type": "number", "default": 0.0},
                            "nickel_tons": {"type": "number"},
                            "nickel_origin_country": {"type": "string", "default": "IDN"},
                            "nickel_feoc_equity_pct": {"type": "number", "default": 0.0},
                            "cobalt_tons": {"type": "number"},
                            "cobalt_origin_country": {"type": "string", "default": "COD"},
                            "cobalt_feoc_equity_pct": {"type": "number", "default": 0.0}
                        },
                        "required": ["rfq_id", "lithium_tons", "nickel_tons", "cobalt_tons"]
                    }
                },
                {
                    "name": "get_global_trade_flows",
                    "description": "Queries global critical mineral physical trade corridor flows, monthly bulk volumes, standard transit days, vessel classes, and maritime chokepoints.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "mineral_type": {"type": "string", "description": "Optional filter by mineral (e.g. LITHIUM_HYDROXIDE, NICKEL_MHP)"},
                            "origin_country": {"type": "string", "description": "Optional origin country code (e.g. AUS, IDN, CHL)"},
                            "destination_country": {"type": "string", "description": "Optional destination country code (e.g. KOR, USA, CHN, EU)"}
                        }
                    }
                },
                {
                    "name": "calculate_trade_tariffs",
                    "description": "Resolves WCO 6-digit Harmonized System (HS) Code, MFN base duty, applicable FTA preferential duty, US Section 301 punitive tariffs, and EU CBAM benchmarks.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "mineral_type": {"type": "string", "description": "Target mineral commodity"},
                            "importer_jurisdiction": {"type": "string", "default": "USA", "description": "Importing destination (USA, EU, KOR, JPN, CHN)"}
                        },
                        "required": ["mineral_type"]
                    }
                },
                {
                    "name": "estimate_maritime_freight_and_carbon",
                    "description": "Calculates maritime voyage distance (nautical miles), transit duration, freight charter costs ($/MT), chokepoint detour surcharges (Red Sea/Panama), IMO CII rating, and EU CBAM carbon costs.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "mineral_type": {"type": "string", "description": "Mineral cargo"},
                            "origin_country": {"type": "string", "description": "Origin country"},
                            "destination_country": {"type": "string", "description": "Destination country"},
                            "cargo_weight_metric_tons": {"type": "number", "default": 1000.0},
                            "cii_rating": {"type": "string", "enum": ["A", "B", "C", "D", "E"], "default": "A"},
                            "avoid_chokepoints": {"type": "array", "items": {"type": "string"}, "description": "Chokepoints to avoid (e.g. ['RED_SEA', 'PANAMA_CANAL'])"}
                        },
                        "required": ["mineral_type", "origin_country", "destination_country"]
                    }
                },
                {
                    "name": "verify_electronic_bill_of_lading",
                    "description": "Cryptographically audits UNCITRAL MLETR / FIT Alliance electronic Bill of Lading (eBL). Validates 7-digit IMO checksum, UN/LOCODE port pairs, manifest weight, and screens for AIS dark fleet anomalies.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "ebl_document_id": {"type": "string", "description": "eBL reference ID"},
                            "ebl_document_hash": {"type": "string", "description": "SHA-256 hash of eBL document"},
                            "carrier_imo_number": {"type": "integer", "description": "7-digit vessel IMO"},
                            "vessel_name": {"type": "string", "description": "Registered vessel name"},
                            "mineral_type": {"type": "string", "description": "Declared mineral cargo"},
                            "gross_weight_metric_tons": {"type": "number", "description": "Cargo gross weight in MT"},
                            "port_of_loading_code": {"type": "string", "description": "5-letter UN/LOCODE POL"},
                            "port_of_discharge_code": {"type": "string", "description": "5-letter UN/LOCODE POD"},
                            "shipper_name": {"type": "string", "description": "Shipper corporate name"},
                            "consignee_name": {"type": "string", "description": "Consignee corporate name"}
                        },
                        "required": ["ebl_document_id", "ebl_document_hash", "carrier_imo_number", "vessel_name", "mineral_type", "gross_weight_metric_tons", "port_of_loading_code", "port_of_discharge_code", "shipper_name", "consignee_name"]
                    }
                },
                {
                    "name": "optimize_mineral_trade_route",
                    "description": "Autonomous trade route optimizer for AI procurement agents. Compares direct marine transit vs chokepoint detour corridors, computing landed cost arbitrage ($/MT), total freight and tariffs, and delivery timelines.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "mineral_type": {"type": "string", "description": "Target mineral cargo"},
                            "origin_country": {"type": "string", "description": "Origin country"},
                            "destination_country": {"type": "string", "description": "Destination country"},
                            "cargo_weight_metric_tons": {"type": "number", "description": "Volume in MT"},
                            "target_delivery_deadline_days": {"type": "number", "description": "Max acceptable transit days (optional)"},
                            "max_carbon_budget_co2_tons": {"type": "number", "description": "Max acceptable voyage CO2 tons (optional)"}
                        },
                        "required": ["mineral_type", "origin_country", "destination_country", "cargo_weight_metric_tons"]
                    }
                },
                {
                    "name": "open_agent_session",
                    "description": "Opens a high-speed allowance session for autonomous AI agents, enabling <0.1ms micro-queries without per-query on-chain gas latency.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "agent_address": {"type": "string", "description": "Agent EVM wallet address (0x...)"},
                            "deposit_amount_usdc": {"type": "number", "description": "USDC deposit amount for session queries (default 10.0)"},
                            "session_duration_hours": {"type": "integer", "description": "Session validity in hours (default 24)"},
                            "signature": {"type": "string", "description": "Optional EIP-712 deposit authorization signature"}
                        },
                        "required": ["agent_address"]
                    }
                },
                {
                    "name": "close_agent_session",
                    "description": "Closes an active agent session, computes refund of unspent balance, and generates an immutable settlement receipt hash.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "session_token": {"type": "string", "description": "Active session token (asess_...)"},
                            "agent_address": {"type": "string", "description": "Agent EVM wallet address"}
                        },
                        "required": ["session_token", "agent_address"]
                    }
                },
                {
                    "name": "get_agent_session_info",
                    "description": "Queries real-time balance, query capacity, and status for an active session without debiting a fee.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "session_token": {"type": "string", "description": "Active session token (asess_...)"}
                        },
                        "required": ["session_token"]
                    }
                },
                {
                    "name": "propose_a2a_trade_deal",
                    "description": "Seller AI agent proposes a canonical bilateral trade agreement for a critical mineral consignment with cryptographic signature.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "spec": {
                                "type": "object",
                                "description": "Canonical TradeDealSpec object",
                                "properties": {
                                    "deal_id": {"type": "string", "description": "Unique trade deal ID (e.g. DEAL-2026-CHL-001)"},
                                    "commodity": {"type": "string", "description": "Commodity symbol (e.g. LITHIUM_CARBONATE, COPPER_CATHODE, NICKEL_MHP)"},
                                    "volume_tons": {"type": "number", "description": "Cargo weight in metric tons"},
                                    "unit_price_usd_per_ton": {"type": "number", "description": "Contract unit price $/MT"},
                                    "total_deal_value_usd": {"type": "number", "description": "Gross deal value in USD"},
                                    "origin_country": {"type": "string", "description": "Origin country ISO code (e.g. CHL, AUS, IDN)"},
                                    "destination_country": {"type": "string", "description": "Importing destination country (e.g. USA, KOR, EU)"},
                                    "feoc_cleared": {"type": "boolean", "default": True, "description": "FEOC 25% compliance cleared"},
                                    "mass_balance_cleared": {"type": "boolean", "default": True, "description": "Stoichiometric mass balance cleared"},
                                    "ebl_document_id": {"type": "string", "description": "Verified electronic Bill of Lading reference"},
                                    "buyer_agent_address": {"type": "string", "description": "Buyer agent EVM address (0x...)"},
                                    "seller_agent_address": {"type": "string", "description": "Seller agent EVM address (0x...)"},
                                    "projected_savings_usd": {"type": "number", "default": 0.0, "description": "Oracle verified tariff and logistics savings for 10% gain-share"},
                                    "created_at_utc": {"type": "string", "description": "ISO timestamp"}
                                },
                                "required": ["deal_id", "commodity", "volume_tons", "unit_price_usd_per_ton", "total_deal_value_usd", "origin_country", "destination_country", "ebl_document_id", "buyer_agent_address", "seller_agent_address", "created_at_utc"]
                            },
                            "seller_signature": {"type": "string", "description": "Seller agent cryptographic signature over deal hash"}
                        },
                        "required": ["spec", "seller_signature"]
                    }
                },
                {
                    "name": "dual_sign_trade_deal",
                    "description": "Buyer AI agent countersigns an existing trade proposal; Oracle mints an immutable 3-party deal attestation seal.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "deal_id": {"type": "string", "description": "Canonical trade deal identifier"},
                            "buyer_signature": {"type": "string", "description": "Buyer agent cryptographic signature"},
                            "buyer_agent_address": {"type": "string", "description": "Buyer agent EVM address"}
                        },
                        "required": ["deal_id", "buyer_signature", "buyer_agent_address"]
                    }
                },
                {
                    "name": "reject_a2a_trade_deal",
                    "description": "Buyer AI agent rejects an existing trade proposal with structured reasoning and optional cryptographic signature.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "deal_id": {"type": "string", "description": "Trade deal identifier to reject"},
                            "buyer_agent_address": {"type": "string", "description": "Buyer agent EVM address executing rejection"},
                            "buyer_signature": {"type": "string", "description": "Optional cryptographic signature"},
                            "rejection_reason": {"type": "string", "description": "Reason for rejection"}
                        },
                        "required": ["deal_id", "buyer_agent_address"]
                    }
                },
                {
                    "name": "cancel_a2a_trade_deal",
                    "description": "Seller AI agent revokes or cancels a pending trade deal proposal before buyer countersignature.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "deal_id": {"type": "string", "description": "Trade deal identifier to cancel"},
                            "seller_agent_address": {"type": "string", "description": "Seller agent EVM address executing cancellation"},
                            "seller_signature": {"type": "string", "description": "Optional cryptographic cancellation signature"},
                            "cancellation_reason": {"type": "string", "description": "Reason for proposal revocation"}
                        },
                        "required": ["deal_id", "seller_agent_address"]
                    }
                },
                {
                    "name": "list_a2a_trade_deals",
                    "description": "Lists A2A bilateral trade deals, optionally filtered by agent EVM address or status (PROPOSED, DUAL_SIGNED_CONFIRMED, REJECTED, CANCELLED, EXPIRED).",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "agent_address": {"type": "string", "description": "Optional agent EVM address filter"},
                            "status_filter": {"type": "string", "description": "Optional status filter"}
                        }
                    }
                },
                {
                    "name": "get_a2a_trade_deal",
                    "description": "Retrieves the full specification, audit notes, and current status of an A2A trade agreement.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "deal_id": {"type": "string", "description": "Trade deal identifier"}
                        },
                        "required": ["deal_id"]
                    }
                },
                {
                    "name": "verify_a2a_trade_deal",
                    "description": "Cryptographically audits a dual-signed A2A trade deal, verifying seller, buyer, and oracle signatures, along with FEOC and mass-balance compliance.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "deal_id": {"type": "string", "description": "Trade deal identifier to audit"}
                        },
                        "required": ["deal_id"]
                    }
                }
            ]
        }
    }


def _populate_lot_defaults(arguments: Dict[str, Any]) -> Dict[str, Any]:
    args = dict(arguments)
    args.setdefault("lot_id", "LOT-MCP-DEFAULT")
    args.setdefault("mineral_type", "NICKEL_MHP")
    args.setdefault("source_country", "IDN")
    args.setdefault("net_weight_metric_tons", 100.0)
    args.setdefault("declared_purity_pct", 38.5)
    if "mine_permits" not in args:
        args["mine_permits"] = {
            "mining_license_id": "IUP-OP-4491-SULAWESI",
            "mine_operator_name": "PT Sulawesi Nickel Resources",
            "simbara_ntpn": "NTPN-884219482109",
            "simbara_rkab_quota_id": "RKAB-2026-IDN-771",
            "dhe_forex_deposit_ref": "DHE-BI-992144-USD",
        }
    if "ecological_spatial" not in args:
        args["ecological_spatial"] = {
            "latitude": -2.812451,
            "longitude": 121.341209,
            "eudr_deforestation_free": True,
            "periglacial_zone_violation": False,
            "indigenous_territory_encroachment": False,
            "tailing_dam_dce_certified": True,
            "aquifer_depletion_alert": False,
        }
    if "labor_human_rights" not in args:
        args["labor_human_rights"] = {
            "child_labor_free_certified": True,
            "rmi_rmap_audit_id": "RMI-RMAP-2026-0811",
            "forced_labor_uapa_cleared": True,
        }
    if "refining_mass_balance" not in args:
        args["refining_mass_balance"] = {
            "refinery_id": "HPAL-IWIP-LINE-3",
            "feedstock_input_metric_tons": 850.0,
            "refined_output_metric_tons": 100.0,
            "recovery_yield_pct": 91.4,
            "mass_balance_loss_discrepancy_pct": 1.12,
            "captive_coal_power_used": False,
        }
    if "maritime_logistics" not in args:
        args["maritime_logistics"] = {
            "vessel_imo_number": 9821441,
            "vessel_name": "Pacific Star",
            "cii_rating": "B",
            "ebl_document_hash": "0x44a" + "e" * 61,
            "transshipment_port": "Singapore",
            "iso_17025_lab_coa_hash": "0x99f" + "d" * 61,
            "tml_moisture_safe": True,
        }
    if "geopolitical_sanctions" not in args:
        args["geopolitical_sanctions"] = {
            "feoc_shareholding_pct": 14.5,
            "feoc_board_control_pct": 12.0,
            "contractual_operational_control": False,
            "ofac_sdn_sanctioned": False,
            "us_substantial_transformation_compliant": True,
        }
    return args


def handle_tool_call(req_id: Any, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if name == "verify_mineral_lot_compliance":
            full_args = _populate_lot_defaults(arguments)
            req_model = MineralLotProvenanceRequest(**full_args)
            passport = compliance_engine.evaluate_lot(req_model)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(passport.model_dump(), indent=2)
                        }
                    ]
                }
            }

        elif name == "verify_lithium_origin":
            from app.lithium_pipeline import lithium_pipeline
            from app.schemas import LithiumOriginVerifyRequest
            req_model = LithiumOriginVerifyRequest(**arguments)
            lithium_res = lithium_pipeline.evaluate_lithium_lot(req_model)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(lithium_res.model_dump(), indent=2, ensure_ascii=False)
                        }
                    ]
                }
            }

        elif name == "verify_nickel_origin":
            from app.nickel_pipeline import nickel_pipeline
            from app.schemas import NickelOriginVerifyRequest
            req_model = NickelOriginVerifyRequest(**arguments)
            nickel_res = nickel_pipeline.evaluate_nickel_lot(req_model)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(nickel_res.model_dump(), indent=2, ensure_ascii=False)
                        }
                    ]
                }
            }

        elif name == "verify_cobalt_origin":
            from app.cobalt_pipeline import cobalt_pipeline
            from app.schemas import CobaltOriginVerifyRequest
            req_model = CobaltOriginVerifyRequest(**arguments)
            cobalt_res = cobalt_pipeline.evaluate_cobalt_lot(req_model)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(cobalt_res.model_dump(), indent=2, ensure_ascii=False)
                        }
                    ]
                }
            }

        elif name == "verify_composite_battery_passport":
            from app.composite_battery_pipeline import composite_battery_pipeline
            from app.schemas import CompositeBatteryVerifyRequest
            req_model = CompositeBatteryVerifyRequest(**arguments)
            composite_res = composite_battery_pipeline.evaluate_battery_pack(req_model)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(composite_res.model_dump(), indent=2, ensure_ascii=False)
                        }
                    ]
                }
            }

        elif name == "verify_copper_origin":
            from app.copper_pipeline import copper_pipeline
            from app.schemas import CopperOriginVerifyRequest
            req_model = CopperOriginVerifyRequest(**arguments)
            copper_res = copper_pipeline.verify_origin(req_model)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(copper_res.model_dump(), indent=2, ensure_ascii=False)
                        }
                    ]
                }
            }

        elif name == "verify_silver_origin":
            from app.silver_pipeline import silver_pipeline
            from app.schemas import SilverOriginVerifyRequest
            req_model = SilverOriginVerifyRequest(**arguments)
            silver_res = silver_pipeline.verify_origin(req_model)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(silver_res.model_dump(), indent=2, ensure_ascii=False)
                        }
                    ]
                }
            }

        elif name == "list_trade_precedents":
            data = {
                "oracle": "minerals-oracle-x402",
                "precedents": ["WTO_DS592", "WTO_DS431", "ICSID_ARB_15_31", "US_CIT_SUPERIOR_WIRE"]
            }
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(data, indent=2)}]
                }
            }

        elif name == "get_compliance_status":
            data = {
                "oracle": "minerals-oracle-x402",
                "engine": "ComplianceEngine v2.0.0",
                "monitored_nations": ["IDN", "COD", "CHL", "ARG", "AUS", "BRA", "CHN", "ZAF"],
                "active_defenses": 12
            }
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(data, indent=2)}]
                }
            }

        elif name == "minerals_submit_agent_feedback":
            agent_id = arguments.get("agent_id", "anonymous-agent")
            title = arguments.get("title", "")
            content = arguments.get("content", "")
            feedback_type = arguments.get("feedback_type", "FEATURE_REQUEST")
            mineral_focus = arguments.get("mineral_focus", "ALL")
            proposed_solution = arguments.get("proposed_solution")
            caller_model = arguments.get("caller_model")
            contact_channel = arguments.get("contact_channel")

            if not title or not content:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: 'title' and 'content' are required fields."
                    }
                }

            prop = evolution_manager.submit_proposal(
                agent_id=agent_id,
                title=title,
                content=content,
                feedback_type=feedback_type,
                mineral_focus=mineral_focus,
                proposed_solution=proposed_solution,
                caller_model=caller_model,
                contact_channel=contact_channel
            )
            result = {
                "status": "PROPOSAL_ACCEPTED",
                "feedback_id": prop.feedback_id,
                "title": prop.title,
                "message": f"Evolution proposal '{prop.title}' successfully recorded into Minerals Oracle roadmap. Thank you for contributing to autonomous oracle evolution.",
                "created_at_utc": prop.created_at_utc
            }
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                }
            }

        elif name == "minerals_list_evolution_proposals":
            limit = int(arguments.get("limit", 20))
            mineral = arguments.get("mineral_focus")
            proposals = evolution_manager.list_proposals(limit=limit, mineral_focus=mineral)
            result = {
                "status": "SUCCESS",
                "total_proposals": len(proposals),
                "proposals": [p.model_dump() for p in proposals]
            }
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                }
            }

        elif name == "register_agent_account":
            agent_name = arguments.get("agent_name", "AutonomousBot")
            agent_addr = arguments.get("agent_address")
            init_bal = float(arguments.get("initial_trial_balance_usdc", 0.05))
            acc, session_key = vault_manager.register_agent_onboarding(
                agent_name=agent_name,
                agent_address=agent_addr,
                initial_trial_balance_usdc=init_bal,
            )
            result = {
                "status": "REGISTERED",
                "agent_name": agent_name,
                "agent_address": acc.agent_address,
                "session_key": session_key,
                "balance_usdc": acc.balance_usdc,
                "query_capacity": vault_manager.get_query_capacity(acc.balance_usdc),
                "instruction": "Pass this session_key in 'X-Agent-Vault-Key' header or bearer auth for zero-latency queries.",
            }
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                }
            }

        elif name == "get_agent_vault_balance":
            key = arguments.get("session_key") or arguments.get("agent_address")
            if not key:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32602,
                        "message": "Missing 'session_key' or 'agent_address' parameter."
                    }
                }
            acc = vault_manager.get_account_by_session_key(key)
            if not acc and key.startswith("0x"):
                acc = vault_manager.get_account_by_address(key)
            if not acc:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32602,
                        "message": f"Vault account '{key}' not found."
                    }
                }
            result = {
                "status": "ACTIVE",
                "agent_address": acc.agent_address,
                "balance_usdc": acc.balance_usdc,
                "total_deposited_usdc": acc.total_deposited_usdc,
                "total_consumed_usdc": acc.total_consumed_usdc,
                "query_count": acc.query_count,
                "query_capacity": vault_manager.get_query_capacity(acc.balance_usdc),
            }
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                }
            }

        elif name == "request_x402_payment_challenge":
            tier_str = arguments.get("pricing_tier", "STANDARD")
            chain_str = arguments.get("chain", "polygon")
            try:
                tier_val = PricingTier(tier_str)
            except Exception:
                tier_val = PricingTier.STANDARD
            challenge = x402_verifier.generate_challenge(tier=tier_val, chain_name=chain_str)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(challenge.model_dump(), indent=2)}]
                }
            }

        elif name == "simulate_procurement_rfq":
            rfq_id = arguments.get("rfq_id", "RFQ-SIM-01")
            chemistry = arguments.get("cell_chemistry", "NCM811")
            li_tons = float(arguments.get("lithium_tons", 0.0))
            li_origin = arguments.get("lithium_origin_country", "AUS")
            li_feoc = float(arguments.get("lithium_feoc_equity_pct", 0.0))
            ni_tons = float(arguments.get("nickel_tons", 0.0))
            ni_origin = arguments.get("nickel_origin_country", "IDN")
            ni_feoc = float(arguments.get("nickel_feoc_equity_pct", 0.0))
            co_tons = float(arguments.get("cobalt_tons", 0.0))
            co_origin = arguments.get("cobalt_origin_country", "COD")
            co_feoc = float(arguments.get("cobalt_feoc_equity_pct", 0.0))

            US_FTA_COUNTRIES = {"USA", "US", "AUS", "CHL", "CAN", "MEX", "KOR", "SGP", "BHR", "ISR", "JOR", "MAR", "OMN", "PAN", "PER"}
            BENCHMARK_PRICES = {"LITHIUM": 15000.0, "NICKEL": 16800.0, "COBALT": 28500.0}

            li_val = li_tons * BENCHMARK_PRICES["LITHIUM"]
            ni_val = ni_tons * BENCHMARK_PRICES["NICKEL"]
            co_val = co_tons * BENCHMARK_PRICES["COBALT"]
            total_val = li_val + ni_val + co_val

            fta_val = 0.0
            if li_origin.upper() in US_FTA_COUNTRIES:
                fta_val += li_val
            if ni_origin.upper() in US_FTA_COUNTRIES:
                fta_val += ni_val
            if co_origin.upper() in US_FTA_COUNTRIES:
                fta_val += co_val

            fta_ratio = round((fta_val / total_val) * 100.0, 2) if total_val > 0 else 0.0

            tainted = []
            if li_feoc >= 25.0:
                tainted.append(f"LITHIUM ({li_feoc}% covered nation equity)")
            if ni_feoc >= 25.0:
                tainted.append(f"NICKEL ({ni_feoc}% covered nation equity)")
            if co_feoc >= 25.0:
                tainted.append(f"COBALT ({co_feoc}% covered nation equity)")

            has_taint = len(tainted) > 0
            ira_ok = (fta_ratio >= 50.0) and not has_taint

            now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            merkle_preimage = f"{rfq_id}:{chemistry}:{fta_ratio}:{has_taint}:{now_iso}"
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

            result = {
                "rfq_id": rfq_id,
                "cell_chemistry": chemistry,
                "status": status_val,
                "ira_fta_compliant": ira_ok,
                "ira_fta_value_ratio_pct": fta_ratio,
                "feoc_taint_detected": has_taint,
                "tainted_minerals": tainted,
                "us_subsidy_qualified_per_pack_usd": subsidy,
                "recommendation": rec,
                "composite_merkle_digest": digest,
                "simulated_at_utc": now_iso,
            }
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                }
            }

        elif name == "get_global_trade_flows":
            m_type = MineralType(arguments["mineral_type"]) if "mineral_type" in arguments and arguments["mineral_type"] else None
            o_country = SourceCountry(arguments["origin_country"]) if "origin_country" in arguments and arguments["origin_country"] else None
            d_country = arguments.get("destination_country")
            corrs = global_trade_engine.get_corridors(m_type, o_country, d_country)
            data = [c.model_dump() for c in corrs]
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(data, indent=2, ensure_ascii=False)}]}
            }

        elif name == "calculate_trade_tariffs":
            m_type = MineralType(arguments["mineral_type"])
            dest = arguments.get("importer_jurisdiction", "USA")
            tariff = global_trade_engine.get_hs_tariff(m_type, dest)
            data = tariff.model_dump() if tariff else {"error": f"No HS tariff data found for {m_type} to {dest}"}
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(data, indent=2, ensure_ascii=False)}]}
            }

        elif name == "estimate_maritime_freight_and_carbon":
            req_model = MaritimeRouteRequest(**arguments)
            data = global_trade_engine.calculate_maritime_route(req_model).model_dump()
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(data, indent=2, ensure_ascii=False)}]}
            }

        elif name == "verify_electronic_bill_of_lading":
            req_model = EBLVerificationRequest(**arguments)
            data = global_trade_engine.verify_ebl(req_model).model_dump()
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(data, indent=2, ensure_ascii=False)}]}
            }

        elif name == "optimize_mineral_trade_route":
            req_model = TradeRouteOptimizationRequest(**arguments)
            data = global_trade_engine.optimize_route(req_model).model_dump()
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(data, indent=2, ensure_ascii=False)}]}
            }

        elif name == "open_agent_session":
            req_model = AgentSessionOpenRequest(**arguments)
            data = agent_session_vault.open_session(req_model).model_dump()
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(data, indent=2, ensure_ascii=False)}]}
            }

        elif name == "close_agent_session":
            req_model = AgentSessionCloseRequest(**arguments)
            data = agent_session_vault.close_session(req_model).model_dump()
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(data, indent=2, ensure_ascii=False)}]}
            }

        elif name == "get_agent_session_info":
            token = arguments.get("session_token", "")
            data = agent_session_vault.get_session_info_model(token).model_dump()
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(data, indent=2, ensure_ascii=False)}]}
            }

        elif name == "propose_a2a_trade_deal":
            req_model = TradeDealProposeRequest(**arguments)
            data = a2a_deal_engine.propose_deal(req_model).model_dump()
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(data, indent=2, ensure_ascii=False)}]}
            }

        elif name == "dual_sign_trade_deal":
            req_model = TradeDealDualSignRequest(**arguments)
            data = a2a_deal_engine.dual_sign_deal(req_model).model_dump()
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(data, indent=2, ensure_ascii=False)}]}
            }

        elif name == "reject_a2a_trade_deal":
            req_model = TradeDealRejectRequest(**arguments)
            data = a2a_deal_engine.reject_deal(req_model).model_dump()
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(data, indent=2, ensure_ascii=False)}]}
            }

        elif name == "cancel_a2a_trade_deal":
            req_model = TradeDealCancelRequest(**arguments)
            data = a2a_deal_engine.cancel_deal(req_model).model_dump()
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(data, indent=2, ensure_ascii=False)}]}
            }

        elif name == "list_a2a_trade_deals":
            agent_addr = arguments.get("agent_address")
            status_flt = arguments.get("status_filter")
            deals = a2a_deal_engine.list_deals_by_agent(agent_addr, status_flt)
            res = {"status": "success", "total_count": len(deals), "deals": deals}
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(res, indent=2, ensure_ascii=False)}]}
            }

        elif name == "get_a2a_trade_deal":
            deal_id = arguments.get("deal_id", "")
            data = a2a_deal_engine.get_deal(deal_id)
            if not data:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": f"Deal '{deal_id}' not found"}
                }
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(data, indent=2, ensure_ascii=False)}]}
            }

        elif name == "verify_a2a_trade_deal":
            req_model = TradeDealVerifyRequest(**arguments)
            data = a2a_deal_engine.verify_deal(req_model).model_dump()
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(data, indent=2, ensure_ascii=False)}]}
            }

        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method '{name}' not found"
                }
            }

    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32603,
                "message": f"Internal tool execution error: {str(e)}"
            }
        }


def run_stdio_server():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            method = req.get("method")
            req_id = req.get("id")

            if method == "initialize":
                resp = handle_initialize(req_id)
            elif method == "ping":
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {}
                }
            elif method == "tools/list":
                resp = handle_tools_list(req_id)
            elif method == "tools/call":
                params = req.get("params", {})
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                resp = handle_tool_call(req_id, tool_name, tool_args)
            elif method == "notifications/initialized":
                continue
            else:
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unhandled MCP method: {method}"
                    }
                }
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {str(e)}"
                }
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


def main():
    run_stdio_server()


if __name__ == "__main__":
    main()
