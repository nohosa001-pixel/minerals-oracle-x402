"""
High-Frequency WebSocket Streaming Connection Manager for Minerals Oracle x402.
Broadcasts real-time physical commodity ticks, cross-market arbitrage spreads, and urban mining events to AI agents.
"""

import asyncio
import json
import logging
import time
from typing import List, Dict, Any, Set
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("WebSocketManager")


class OracleWebSocketManager:
    """Manages active streaming WebSocket connections for enterprise AI quant agents."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.total_messages_streamed: int = 0
        self.started_at_unix: float = time.time()

    async def connect(self, websocket: WebSocket, client_id: str = "anonymous_agent"):
        """Accepts and registers an incoming agent WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Agent connected to real-time oracle stream: {client_id} (Total: {len(self.active_connections)})")

    def disconnect(self, websocket: WebSocket):
        """Removes a disconnected agent WebSocket."""
        self.active_connections.discard(websocket)

    async def broadcast_tick(self, payload: Dict[str, Any]):
        """Broadcasts a real-time price/spread update to all subscribed agents."""
        if not self.active_connections:
            return

        message_str = json.dumps(payload)
        dead_connections = []

        for conn in list(self.active_connections):
            try:
                await conn.send_text(message_str)
                self.total_messages_streamed += 1
            except Exception:
                dead_connections.append(conn)

        for dead in dead_connections:
            self.disconnect(dead)


# Singleton manager instance
ws_manager = OracleWebSocketManager()
