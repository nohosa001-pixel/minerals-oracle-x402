# -*- coding: utf-8 -*-
"""
A2A Webhook Push Dispatcher & Event Notification Engine
======================================================
Enables event-driven, zero-polling bilateral trade notifications
for autonomous AI agents (ElizaOS, AutoGen, LangChain).

Features:
- Webhook registration for agent EVM addresses
- Cryptographic HMAC-SHA256 payload signatures (X-Oracle-Webhook-Signature)
- Event filtering (deal.proposed, deal.dual_signed, deal.rejected, deal.cancelled, ebl.verified)
- Non-blocking async background delivery with timeout and retry protection
"""

from __future__ import annotations

import os
import json
import time
import hmac
import hashlib
import secrets
import threading
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from pydantic import BaseModel, Field, field_validator
import httpx
from web3 import Web3


class AgentWebhookRegistrationRequest(BaseModel):
    agent_address: str = Field(..., description="Agent EVM address (0x...) or '*' for broadcast")
    callback_url: str = Field(..., description="HTTP/HTTPS webhook callback endpoint")
    subscribed_events: List[str] = Field(
        default=["*"],
        description="Event types to subscribe to (e.g. ['deal.proposed', 'deal.dual_signed'])"
    )
    webhook_secret: Optional[str] = Field(
        default=None,
        description="Optional shared secret for HMAC-SHA256 signing (auto-generated if omitted)"
    )

    @field_validator("agent_address")
    @classmethod
    def validate_agent_address(cls, v: str) -> str:
        s = v.strip()
        if s != "*" and not Web3.is_address(s):
            raise ValueError(f"Invalid agent EVM address format: '{s}'")
        return s.lower()

    @field_validator("callback_url")
    @classmethod
    def validate_callback_url(cls, v: str) -> str:
        s = v.strip()
        if not (s.startswith("http://") or s.startswith("https://")):
            raise ValueError(f"callback_url must start with 'http://' or 'https://', got: '{s}'")
        return s


class AgentWebhookRegistrationResponse(BaseModel):
    status: str = "success"
    webhook_id: str
    agent_address: str
    callback_url: str
    subscribed_events: List[str]
    webhook_secret: str
    created_at_utc: str


class WebhookEventPayload(BaseModel):
    event_id: str
    event_type: str
    timestamp_utc: str
    target_agent_address: str
    data: Dict[str, Any]


class WebhookManager:
    """Thread-safe event webhook manager and async HTTP push dispatcher."""

    _instance: Optional["WebhookManager"] = None
    _lock: threading.Lock
    _webhooks: Dict[str, Dict[str, Any]]
    _storage_path: Path

    def __new__(cls) -> "WebhookManager":
        if cls._instance is None:
            cls._instance = super(WebhookManager, cls).__new__(cls)
            cls._instance._lock = threading.Lock()
            cls._instance._webhooks = {}
            cls._instance._storage_path = (
                Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                / "logs"
                / "webhooks.json"
            )
            cls._instance._load_from_disk()
        return cls._instance

    def _save_to_disk(self) -> None:
        if "PYTEST_CURRENT_TEST" in os.environ:
            return
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(self._webhooks, f, indent=2)
        except Exception:
            pass

    def _load_from_disk(self) -> None:
        if "PYTEST_CURRENT_TEST" in os.environ:
            return
        try:
            if self._storage_path.exists():
                with open(self._storage_path, "r", encoding="utf-8") as f:
                    self._webhooks = json.load(f)
        except Exception:
            self._webhooks = {}

    def register_webhook(self, req: AgentWebhookRegistrationRequest) -> AgentWebhookRegistrationResponse:
        """Registers a new webhook subscriber for an agent EVM address."""
        agent_addr = req.agent_address.lower()
        webhook_id = f"whk_{secrets.token_hex(12)}"
        secret = req.webhook_secret or f"whsec_{secrets.token_hex(20)}"
        now_utc = datetime.now(timezone.utc).isoformat()

        with self._lock:
            webhook_entry = {
                "webhook_id": webhook_id,
                "agent_address": agent_addr,
                "callback_url": req.callback_url,
                "subscribed_events": req.subscribed_events,
                "webhook_secret": secret,
                "created_at_utc": now_utc,
                "active": True,
            }
            self._webhooks[webhook_id] = webhook_entry
            self._save_to_disk()

        return AgentWebhookRegistrationResponse(
            status="success",
            webhook_id=webhook_id,
            agent_address=agent_addr,
            callback_url=req.callback_url,
            subscribed_events=req.subscribed_events,
            webhook_secret=secret,
            created_at_utc=now_utc,
        )

    def unregister_webhook(self, webhook_id: str) -> bool:
        """Removes a registered webhook."""
        with self._lock:
            if webhook_id in self._webhooks:
                del self._webhooks[webhook_id]
                self._save_to_disk()
                return True
            return False

    def list_webhooks_for_agent(self, agent_address: str) -> List[Dict[str, Any]]:
        """Retrieves all active webhooks for a given agent EVM address."""
        addr = agent_address.lower()
        with self._lock:
            return [
                dict(entry) for entry in self._webhooks.values()
                if entry["agent_address"] == addr and entry.get("active", True)
            ]

    def compute_signature(self, payload_bytes: bytes, secret: str) -> str:
        """Computes HMAC-SHA256 signature for webhook payload authentication."""
        return "sha256=" + hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    async def _send_webhook_http(
        self,
        callback_url: str,
        secret: str,
        payload_dict: Dict[str, Any],
        max_retries: int = 2,
    ) -> bool:
        """Asynchronously dispatches webhook payload over HTTP with HMAC signature."""
        payload_bytes = json.dumps(payload_dict, ensure_ascii=False).encode("utf-8")
        signature = self.compute_signature(payload_bytes, secret)

        headers = {
            "Content-Type": "application/json",
            "X-Oracle-Webhook-Signature": signature,
            "X-Oracle-Event-Type": payload_dict["event_type"],
            "X-Oracle-Event-Id": payload_dict["event_id"],
            "User-Agent": "Minerals-Oracle-X402-Webhook/2.0",
        }

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=4.0, follow_redirects=True) as client:
                    resp = await client.post(callback_url, content=payload_bytes, headers=headers)
                    if resp.status_code in (200, 201, 202, 204):
                        return True
            except Exception:
                pass
            if attempt < max_retries:
                await asyncio.sleep(0.1 * (2 ** attempt))
        return False

    def dispatch_event(
        self,
        event_type: str,
        target_agent_address: str,
        data: Dict[str, Any],
    ) -> List[str]:
        """
        Dispatches event to matching registered webhooks in background.
        Returns list of matched webhook IDs.
        """
        target_addr = target_agent_address.lower()
        event_id = f"evt_{secrets.token_hex(12)}"
        now_utc = datetime.now(timezone.utc).isoformat()

        payload = WebhookEventPayload(
            event_id=event_id,
            event_type=event_type,
            timestamp_utc=now_utc,
            target_agent_address=target_addr,
            data=data,
        ).model_dump()

        matched_webhooks: List[Tuple[str, str, str]] = []

        with self._lock:
            for whk in self._webhooks.values():
                if not whk.get("active", True):
                    continue
                if whk["agent_address"] == target_addr or whk["agent_address"] == "*":
                    subs = whk.get("subscribed_events", ["*"])
                    if "*" in subs or event_type in subs:
                        matched_webhooks.append((whk["webhook_id"], whk["callback_url"], whk["webhook_secret"]))

        if not matched_webhooks:
            return []

        # Dispatch async task if event loop is available
        for wid, cb_url, sec in matched_webhooks:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._send_webhook_http(cb_url, sec, payload))
            except RuntimeError:
                # No active event loop in current thread; execute in daemon thread
                def _bg(url=cb_url, secret=sec):
                    asyncio.run(self._send_webhook_http(url, secret, payload))
                threading.Thread(target=_bg, daemon=True).start()

        return [w[0] for w in matched_webhooks]


def get_webhook_manager() -> WebhookManager:
    """Factory helper for singleton WebhookManager."""
    return WebhookManager()


webhook_manager = get_webhook_manager()
