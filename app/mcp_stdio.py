import sys
import json
from typing import Dict, Any, Optional, List

from app.feed_engine import feed_engine
from app.schemas import CommoditySymbol, UrbanMiningRequest



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
                "version": "1.1.0"
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
                    "name": "get_mineral_prices",
                    "description": "Retrieve real-time certified spot prices and unit conversions for critical raw minerals: Neodymium/Dysprosium (NdDy), Lithium (Li), Copper (Cu), Silver (Ag), Platinum (Pt). Free tier sandbox available.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "mineral_type": {
                                "type": "string",
                                "enum": ["Neodymium", "Lithium", "Dysprosium", "Copper", "Silver", "Platinum", "ALL"],
                                "default": "Neodymium",
                                "description": "Specific mineral name or symbol preset (default: 'Neodymium')"
                            }
                        }
                    }
                },
                {
                    "name": "get_arbitrage_spreads",
                    "description": "Calculate locational basis spreads and arbitrage yields across major global venues (COMEX vs LME Copper, COMEX vs LBMA Silver, Fastmarkets vs SMM Lithium).",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "calculate_urban_mining_value",
                    "description": "Evaluate gross payable mineral value, recovery rates tensor, and net settlement value in USDC after refining charges (TC/RC) for recyclable scrap (E-Waste PCBs, EV Battery Black Mass, Auto Catalysts, Permanent Magnets).",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "scrap_category": {
                                "type": "string",
                                "enum": [
                                    "E_WASTE_HIGH_GRADE_PCB",
                                    "EV_BATTERY_BLACK_MASS",
                                    "AUTO_CATALYST_CERAMIC",
                                    "WIND_EV_PERMANENT_MAGNETS"
                                ],
                                "default": "E_WASTE_HIGH_GRADE_PCB",
                                "description": "Feedstock category of the recyclable scrap batch (default: 'E_WASTE_HIGH_GRADE_PCB')"
                            },
                            "quantity_metric_tons": {
                                "type": "number",
                                "description": "Total metric tons of feedstock batch to process (default: 1.0)",
                                "default": 1.0
                            },
                            "target_yield_currency": {
                                "type": "string",
                                "description": "Settlement currency (default: 'USDC')",
                                "default": "USDC"
                            },
                            "recovery_efficiency_factor": {
                                "type": "number",
                                "description": "Hydrometallurgical extraction efficiency factor (0.8 ~ 1.1)",
                                "default": 1.0
                            }
                        },
                        "required": ["scrap_category", "quantity_metric_tons"]
                    }
                },
                {
                    "name": "get_onchain_signed_feed",
                    "description": "Generate an EIP-712 cryptographically signed price feed payload and raw ABI calldata (v, r, s) to update or consume price data directly in Solidity smart contracts on Polygon (Chain ID 137 / Amoy).",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "enum": ["Cu", "Li", "Ag", "Pt", "NdDy"],
                                "default": "Cu",
                                "description": "Commodity symbol to sign (default: 'Cu')"
                            }
                        },
                        "required": ["symbol"]
                    }
                }
            ]
        }
    }


def handle_tool_call(req_id: Any, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if name == "get_mineral_prices":
        mineral_type = args.get("mineral_type", "ALL") if args else "ALL"
        alias_map = {
            "Neodymium": CommoditySymbol.NDDY,
            "Dysprosium": CommoditySymbol.NDDY,
            "NdDy": CommoditySymbol.NDDY,
            "Lithium": CommoditySymbol.LI,
            "Li": CommoditySymbol.LI,
            "Copper": CommoditySymbol.CU,
            "Cu": CommoditySymbol.CU,
            "Silver": CommoditySymbol.AG,
            "Ag": CommoditySymbol.AG,
            "Platinum": CommoditySymbol.PT,
            "Pt": CommoditySymbol.PT,
        }
        if mineral_type in alias_map:
            data = feed_engine.get_single_quote(alias_map[mineral_type]).model_dump()
        else:
            data = feed_engine.get_all_quotes().model_dump()
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(data, indent=2)}]
            }
        }
    elif name == "get_arbitrage_spreads":
        data = feed_engine.get_arbitrage_spreads().model_dump()
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(data, indent=2)}]
            }
        }
    elif name == "calculate_urban_mining_value":
        try:
            # Apply defaults if arguments are missing
            if "scrap_category" not in args:
                args["scrap_category"] = "E_WASTE_HIGH_GRADE_PCB"
            if "quantity_metric_tons" not in args:
                args["quantity_metric_tons"] = 1.0
            req_model = UrbanMiningRequest(**args)
            data = feed_engine.calculate_urban_mining(req_model).model_dump()
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(data, indent=2)}]
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                    "isError": True
                }
            }
    elif name == "get_onchain_signed_feed":
        try:
            from app.onchain_signer import onchain_signer
            symbol = args.get("symbol", "Cu")
            alias_map = {
                "Cu": CommoditySymbol.CU, "Copper": CommoditySymbol.CU,
                "Li": CommoditySymbol.LI, "Lithium": CommoditySymbol.LI,
                "Ag": CommoditySymbol.AG, "Silver": CommoditySymbol.AG,
                "Pt": CommoditySymbol.PT, "Platinum": CommoditySymbol.PT,
                "NdDy": CommoditySymbol.NDDY, "Neodymium": CommoditySymbol.NDDY
            }
            sym_enum = alias_map.get(symbol, CommoditySymbol.CU)
            quote = feed_engine.get_single_quote(sym_enum)
            signed_payload = onchain_signer.sign_price_feed(sym_enum.value, quote.spot_price_usd)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(signed_payload, indent=2)}]
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                    "isError": True
                }
            }
    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method or tool '{name}' not found"
            }
        }


def main():
    """Reads JSON-RPC 2.0 MCP messages from stdin and outputs to stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception as e:
            err_resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()
            continue

        req_id = req.get("id")
        method = req.get("method", "")
        params = req.get("params", {})

        if method == "initialize":
            resp = handle_initialize(req_id)
        elif method == "notifications/initialized" or method == "initialized":
            continue  # Notification, no response
        elif method == "ping":
            resp = {"jsonrpc": "2.0", "id": req_id, "result": {}}
        elif method == "tools/list":
            resp = handle_tools_list(req_id)
        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})
            resp = handle_tool_call(req_id, tool_name, tool_args)
        else:
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method '{method}' not implemented"}
            }

        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()

