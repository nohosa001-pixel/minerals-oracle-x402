"""
MCP (Model Context Protocol) Router for LLM autonomous agent tool calling and SSE streaming.
"""
import json
import secrets
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse

from app.schemas import MCPToolCallRequest, MCPToolCallResponse
from app.mcp_stdio import process_mcp_request
from app.mcp_executor import mcp_executor
from app.routers.deps import require_x402_payment

router = APIRouter(tags=["MCP Tools & Protocol"])

MCP_SPEC_FILE_PATH = Path(__file__).parent.parent.parent / "mcp_tool_spec.json"
_MCP_SSE_SESSIONS: Dict[str, asyncio.Queue] = {}


@router.get("/mcp/tools", summary="Returns Model Context Protocol tool specifications")
async def get_mcp_tool_specs():
    """Returns Model Context Protocol (MCP) tool specifications for autonomous AI agents."""
    if MCP_SPEC_FILE_PATH.exists():
        with open(MCP_SPEC_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"tools": []}


@router.post("/mcp/invoke", response_model=MCPToolCallResponse, summary="Direct HTTP tool dispatcher")
async def invoke_mcp_tool(request: Request, tool_call: MCPToolCallRequest):
    """
    Direct MCP tool dispatcher for LLM agents. Protected with x402 payment validation for data queries.
    Evolution & feedback tools are free to encourage open autonomous agent contributions.
    """
    name = tool_call.name
    args = tool_call.arguments

    free_tools = {
        "minerals_submit_agent_feedback",
        "minerals_list_evolution_proposals",
        "register_agent_account",
        "get_agent_vault_balance",
        "request_x402_payment_challenge",
        "open_agent_session",
        "close_agent_session",
        "get_agent_session_info",
    }
    if name not in free_tools:
        resp_402 = await require_x402_payment(request)
        if resp_402:
            return resp_402

    if "session_key" not in args and "agent_address" not in args:
        hdr_key = request.headers.get("X-Agent-Vault-Key") or request.headers.get("X-Agent-Address")
        if hdr_key:
            args["session_key"] = hdr_key

    return mcp_executor.execute_for_mcp_response(name, args)


@router.get("/mcp/sse", summary="Remote MCP over SSE Transport connection endpoint")
async def mcp_sse_endpoint(request: Request):
    """
    Establishes Server-Sent Events (SSE) stream for remote LLM agent clients (Claude Desktop, Cursor, ElizaOS).
    Emits initial 'endpoint' event with unique sessionId and streams tool call responses.
    """
    session_id = f"mcpsess_{secrets.token_hex(16)}"
    queue: asyncio.Queue = asyncio.Queue()
    _MCP_SSE_SESSIONS[session_id] = queue

    async def event_generator():
        try:
            endpoint_url = f"/mcp/messages?sessionId={session_id}"
            yield f"event: endpoint\r\ndata: {endpoint_url}\r\n\r\n"

            if request.headers.get("X-Test-Stream") == "single":
                return

            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=15.0)
                    msg_json = json.dumps(msg, ensure_ascii=False)
                    yield f"event: message\r\ndata: {msg_json}\r\n\r\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\r\n\r\n"
        finally:
            _MCP_SSE_SESSIONS.pop(session_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/mcp/messages", summary="Receive JSON-RPC 2.0 messages for remote MCP over SSE sessions")
async def mcp_messages_endpoint(request: Request, sessionId: Optional[str] = None):
    """Processes JSON-RPC 2.0 MCP requests and pushes responses back through the client's SSE stream."""
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

    resp = process_mcp_request(body)

    active_session_id = (
        sessionId
        or request.query_params.get("session_id")
        or request.query_params.get("sessionId")
        or request.headers.get("x-session-id")
    )
    if not active_session_id and isinstance(body, dict):
        active_session_id = body.get("sessionId") or body.get("session_id")

    if active_session_id:
        if active_session_id not in _MCP_SSE_SESSIONS:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MCP SSE session '{active_session_id}' not found or disconnected",
            )
        if resp is not None:
            await _MCP_SSE_SESSIONS[active_session_id].put(resp)
        return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"status": "ACCEPTED", "sessionId": active_session_id})

    return JSONResponse(content=resp or {})
