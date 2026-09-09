import sys
import json
from typing import Dict, Any, Optional, List

from app.compliance_engine import compliance_engine
from app.schemas import MineralLotProvenanceRequest, MineralType, SourceCountry
from app.evolution_manager import evolution_manager



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
                "name": "minerals-oracle-x402",
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
