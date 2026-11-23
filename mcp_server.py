#!/usr/bin/env python3
"""
Minerals Oracle x402 — Thin MCP Stdio Client (v2.0.0)
Zero server-side core logic bundled. Proxies JSON-RPC 2.0 MCP calls directly to the
hosted Minerals Oracle x402 Cloud Run endpoint with x402 USDC payment header forwarding.
"""
import json
import os
import sys
from typing import Any, Dict, Optional

import httpx

DEFAULT_ORACLE_URL = "https://minerals-oracle-x402-212942243360.asia-northeast3.run.app"


def get_base_url() -> str:
    return os.getenv("MINERALS_ORACLE_URL", DEFAULT_ORACLE_URL).rstrip("/")


def _auth_headers() -> Dict[str, str]:
    headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "User-Agent": "minerals-oracle-x402-thin-client/2.0.0",
    }
    vault_key = os.getenv("MINERALS_VAULT_KEY") or os.getenv("X_AGENT_VAULT_KEY")
    if vault_key:
        headers["X-Agent-Vault-Key"] = vault_key
    ent_key = os.getenv("MINERALS_ENTERPRISE_KEY") or os.getenv("X_ENTERPRISE_KEY")
    if ent_key:
        headers["X-Enterprise-Key"] = ent_key
    x402_auth = os.getenv("X402_AUTHORIZATION")
    if x402_auth:
        headers["Authorization"] = x402_auth
    return headers


def handle_jsonrpc(req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    method = req.get("method", "")
    req_id = req.get("id")
    params = req.get("params") or {}
    base = get_base_url()

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "minerals-oracle-x402", "version": "2.0.0"},
            },
        }

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        try:
            r = httpx.get(f"{base}/mcp/tools", headers=_auth_headers(), timeout=15.0)
            data = r.json()
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": data.get("tools", [])}}
        except Exception as exc:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(exc)}}

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments") or {}
        try:
            r = httpx.post(
                f"{base}/mcp/invoke",
                headers=_auth_headers(),
                json={"name": tool_name, "arguments": arguments},
                timeout=30.0,
            )
            if r.status_code == 402:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps({"http_status": 402, "payment_required": r.json()}, ensure_ascii=False)}],
                        "isError": True,
                    },
                }
            r.raise_for_status()
            return {"jsonrpc": "2.0", "id": req_id, "result": r.json()}
        except Exception as exc:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(exc)}}

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}


def main() -> None:
    """Run MCP stdio JSON-RPC 2.0 proxy loop."""
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as exc:
            resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"Parse error: {exc}"}}
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
            continue

        resp = handle_jsonrpc(req)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
