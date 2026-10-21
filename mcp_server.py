#!/usr/bin/env python3
"""
MCP Server entrypoint for Minerals Oracle x402.
Standard stdio JSON-RPC 2.0 protocol handler for Glama, Claude Desktop, Cursor, and uvx.
"""
import sys
from pathlib import Path

# Ensure project root is first in sys.path so local app/ package takes precedence
_PROJECT_ROOT = str(Path(__file__).resolve().parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from app.mcp_stdio import main

if __name__ == "__main__":
    main()
