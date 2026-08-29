"""
Agent Payment Vault Manager for Minerals Oracle x402.
Maintains in-memory and on-chain pre-funded agent USDC balances for zero-latency (<1ms) querying.
"""

import os
import time
import secrets
import threading
from typing import Dict, Any, Optional, Tuple, List
from pydantic import BaseModel
from web3 import Web3


class AgentVaultAccount(BaseModel):
    agent_address: str
    balance_usdc: float
    total_deposited_usdc: float
    total_consumed_usdc: float
    session_key: str
    created_at_utc: str
    last_active_utc: str
    query_count: int = 0


class VaultManager:
    """Thread-safe manager for pre-funded agent payment vault accounts."""

    def __init__(self):
        self._lock = threading.Lock()
        # agent_address (checksummed) -> AgentVaultAccount
        self._accounts: Dict[str, AgentVaultAccount] = {}
        # session_key -> agent_address
        self._session_index: Dict[str, str] = {}
        
        # Pre-seed a sandbox agent vault for local testing / demo
        self._seed_demo_account()

    def _seed_demo_account(self):
        demo_addr = Web3.to_checksum_address("0x70997970C51812dc3A010C7d01b50e0d17dc79C8")
        demo_key = "vault_key_demo_agent_sandbox_2026"
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        acc = AgentVaultAccount(
            agent_address=demo_addr,
            balance_usdc=25.00,  # $25.00 USDC pre-funded
            total_deposited_usdc=25.00,
            total_consumed_usdc=0.0,
            session_key=demo_key,
            created_at_utc=now_iso,
            last_active_utc=now_iso,
            query_count=0,
        )
        self._accounts[demo_addr] = acc
        self._session_index[demo_key] = demo_addr

    def deposit(self, agent_address: str, amount_usdc: float) -> AgentVaultAccount:
        """Deposits USDC into an agent's pre-funded vault balance."""
        if amount_usdc <= 0:
            raise ValueError("Deposit amount must be positive.")

        chk_addr = Web3.to_checksum_address(agent_address)
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        with self._lock:
            if chk_addr in self._accounts:
                acc = self._accounts[chk_addr]
                acc.balance_usdc = round(acc.balance_usdc + amount_usdc, 6)
                acc.total_deposited_usdc = round(acc.total_deposited_usdc + amount_usdc, 6)
                acc.last_active_utc = now_iso
            else:
                session_key = "vault_key_" + secrets.token_hex(16)
                acc = AgentVaultAccount(
                    agent_address=chk_addr,
                    balance_usdc=round(amount_usdc, 6),
                    total_deposited_usdc=round(amount_usdc, 6),
                    total_consumed_usdc=0.0,
                    session_key=session_key,
                    created_at_utc=now_iso,
                    last_active_utc=now_iso,
                    query_count=0,
                )
                self._accounts[chk_addr] = acc
                self._session_index[session_key] = chk_addr

            return acc

    def get_account_by_address(self, agent_address: str) -> Optional[AgentVaultAccount]:
        """Retrieves vault account by wallet address."""
        chk_addr = Web3.to_checksum_address(agent_address)
        with self._lock:
            return self._accounts.get(chk_addr)

    def get_account_by_session_key(self, session_key: str) -> Optional[AgentVaultAccount]:
        """Retrieves vault account by session key header."""
        with self._lock:
            addr = self._session_index.get(session_key)
            if addr and addr in self._accounts:
                return self._accounts[addr]
            return None

    def try_deduct(self, identifier: str, amount_usdc: float) -> Tuple[bool, Optional[str], float]:
        """
        Attempts to deduct amount_usdc from an agent's vault balance in sub-millisecond time.
        Identifier can be either a checksummed wallet address or a session key.
        Returns: (success, reason_or_agent_addr, remaining_balance)
        """
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._lock:
            # Check by session key first
            addr = self._session_index.get(identifier)
            if not addr and identifier.startswith("0x"):
                try:
                    addr = Web3.to_checksum_address(identifier)
                except Exception:
                    addr = None

            if not addr or addr not in self._accounts:
                return False, "Vault account not found", 0.0

            acc = self._accounts[addr]
            if acc.balance_usdc < amount_usdc:
                return False, f"Insufficient vault balance (Current: ${acc.balance_usdc:.4f} USDC, Required: ${amount_usdc:.4f})", acc.balance_usdc

            acc.balance_usdc = round(acc.balance_usdc - amount_usdc, 6)
            acc.total_consumed_usdc = round(acc.total_consumed_usdc + amount_usdc, 6)
            acc.query_count += 1
            acc.last_active_utc = now_iso

            return True, acc.agent_address, acc.balance_usdc


# Singleton instance
vault_manager = VaultManager()
