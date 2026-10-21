#!/usr/bin/env python3
"""
Main entry point for Minerals Oracle MCP Server & Web API.
- Stdio MCP mode (default for Glama, Claude Desktop, Cursor): Speaks JSON-RPC 2.0 over stdin/stdout.
- HTTP API mode (for Cloud Run / Web clients): Runs FastAPI with uvicorn.
"""
import os
import sys
from pathlib import Path

# Ensure project root is first in sys.path so local app/ package takes precedence
_PROJECT_ROOT = str(Path(__file__).resolve().parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from app.mcp_stdio import main as stdio_main


def main():
    if "--http" in sys.argv:
        import uvicorn
        port = int(os.getenv("PORT", "8000"))
        host = os.getenv("HOST", "0.0.0.0")
        uvicorn.run("app.main:app", host=host, port=port)
    else:
        # Standard MCP stdio mode for Glama inspector and LLM agent clients
        stdio_main()


if __name__ == "__main__":
    main()
