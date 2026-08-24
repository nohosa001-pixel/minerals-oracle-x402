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
                "version": "1.0.0"
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
                    "description": "Retrieve real-time certified spot prices for critical raw minerals (Silver, Platinum, Copper, Lithium, NdDy Rare Earths) with unit conversions (USD/oz, USD/kg, USD/mt).",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
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
                    "description": "Evaluate gross payable mineral value and net settlement value after refining charges (TC/RC) for recyclable scrap (EV Battery Black Mass, Auto Catalysts, E-Waste PCB, Permanent Magnets).",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "scrap_category": {
                                "type": "string",
                                "enum": [
                                    "EV_BATTERY_BLACK_MASS",
                                    "AUTO_CATALYST_CERAMIC",
                                    "E_WASTE_HIGH_GRADE_PCB",
                                    "WIND_EV_PERMANENT_MAGNETS"
                                ],
                                "description": "Feedstock category of the recyclable scrap batch"
                            },
                            "quantity_metric_tons": {
                                "type": "number",
                                "description": "Total metric tons of feedstock batch to process",
                                "default": 1.0
                            },
                            "recovery_efficiency_factor": {
                                "type": "number",
                                "description": "Hydrometallurgical extraction efficiency factor (0.8 ~ 1.1)",
                                "default": 1.0
                            }
                        },
                        "required": ["scrap_category", "quantity_metric_tons"]
                    }
                }
            ]
        }
    }


def handle_tool_call(req_id: Any, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if name == "get_mineral_prices":
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

