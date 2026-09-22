# -*- coding: utf-8 -*-
"""
Test Suite: Distributed State & Atomic Locking Storage Layer
============================================================
Verifies:
1. InMemoryDistributedStore CRUD and atomic operations
2. Distributed locking context manager
3. Transaction hash replay attack prevention
"""

import pytest

from app.distributed_store import (
    InMemoryDistributedStore,
    distributed_store,
    get_distributed_store,
)


def test_distributed_store_atomic_balance_debit():
    store = InMemoryDistributedStore()
    account_key = "session:test_sess_001"

    # Set initial account balance
    store.set_json(account_key, {
        "session_token": "test_sess_001",
        "current_balance_usdc": 1.0,
        "queries_executed": 0,
    })

    # Debit 0.05 USDC
    ok, rem_bal = store.debit_balance(account_key, 0.05)
    assert ok is True
    assert rem_bal == 0.95

    # Debit remaining 0.95 USDC
    ok2, rem_bal2 = store.debit_balance(account_key, 0.95)
    assert ok2 is True
    assert rem_bal2 == 0.0

    # Debit exceeding balance -> must fail
    ok3, rem_bal3 = store.debit_balance(account_key, 0.05)
    assert ok3 is False
    assert rem_bal3 == 0.0


def test_distributed_store_replay_hash_deduplication():
    store = InMemoryDistributedStore()
    tx_hash = "0x" + "c" * 64

    assert store.is_hash_redeemed(tx_hash) is False
    # First redemption succeeds
    assert store.mark_hash_redeemed(tx_hash) is True
    assert store.is_hash_redeemed(tx_hash) is True
    # Second redemption attempt fails (Replay blocked)
    assert store.mark_hash_redeemed(tx_hash) is False


def test_distributed_store_lock_acquisition():
    store = InMemoryDistributedStore()
    with store.acquire_lock("agent_settlement_001", timeout_seconds=1.0) as acquired:
        assert acquired is True
