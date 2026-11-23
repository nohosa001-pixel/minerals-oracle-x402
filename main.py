#!/usr/bin/env python3
"""
Minerals Oracle x402 — Thin Client CLI Entrypoint (v2.0.0)
Delegates directly to the remote hosted Minerals Oracle x402 Cloud Run API via mcp_server.
"""
import json
import sys
import httpx

from mcp_server import get_base_url, main as mcp_stdio_main


def main() -> None:
    if "--health" in sys.argv:
        r = httpx.get(f"{get_base_url()}/health", timeout=10.0)
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
        return
    if "--x402" in sys.argv:
        r = httpx.get(f"{get_base_url()}/.well-known/x402", timeout=10.0)
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
        return
    mcp_stdio_main()


if __name__ == "__main__":
    main()
