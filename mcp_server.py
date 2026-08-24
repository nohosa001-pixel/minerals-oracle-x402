#!/usr/bin/env python3
"""
MCP Server entrypoint for Minerals Oracle x402.
Standard stdio JSON-RPC 2.0 protocol handler for Glama, Claude Desktop, Cursor, and uvx.
"""
from app.mcp_stdio import main

if __name__ == "__main__":
    main()
