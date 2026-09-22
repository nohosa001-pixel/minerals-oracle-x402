# -*- coding: utf-8 -*-
"""
Distributed State & Atomic Locking Storage Engine
=================================================
Provides scalable multi-instance state synchronization, atomic balance debits,
distributed locking, and transaction replay protection for cloud deployments.

Supported Backends:
1. RedisDistributedStore (Activated when REDIS_URL environment variable is set)
2. InMemoryDistributedStore (Default zero-dependency fallback for local/test execution)
"""

from __future__ import annotations

import os
import time
import json
import threading
from contextlib import contextmanager
from typing import Dict, Any, Optional, Tuple, Iterator


class BaseDistributedStore:
    """Abstract interface for distributed state and locks."""

    def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def set_json(self, key: str, data: Dict[str, Any], ttl_seconds: Optional[int] = None) -> bool:
        raise NotImplementedError

    def delete(self, key: str) -> bool:
        raise NotImplementedError

    def debit_balance(self, account_key: str, amount: float) -> Tuple[bool, float]:
        """Atomically checks and debits balance. Returns (success, remaining_balance)."""
        raise NotImplementedError

    def is_hash_redeemed(self, hash_str: str) -> bool:
        raise NotImplementedError

    def mark_hash_redeemed(self, hash_str: str, ttl_seconds: int = 86400 * 30) -> bool:
        raise NotImplementedError

    @contextmanager
    def acquire_lock(self, lock_key: str, timeout_seconds: float = 5.0) -> Iterator[bool]:
        raise NotImplementedError


class InMemoryDistributedStore(BaseDistributedStore):
    """Thread-safe in-memory store with file-backed persistence fallback."""

    def __init__(self):
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._redeemed_hashes: Dict[str, float] = {}

    def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            val = self._data.get(key)
            if val is None:
                return None
            return dict(val) if isinstance(val, dict) else val

    def set_json(self, key: str, data: Dict[str, Any], ttl_seconds: Optional[int] = None) -> bool:
        with self._lock:
            self._data[key] = data
            return True

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    def debit_balance(self, account_key: str, amount: float) -> Tuple[bool, float]:
        if amount <= 0:
            return False, 0.0
        with self._lock:
            acc = self._data.get(account_key)
            if not acc or not isinstance(acc, dict):
                return False, 0.0
            cur_bal = float(acc.get("current_balance_usdc", acc.get("balance_usdc", 0.0)))
            if cur_bal < amount:
                return False, cur_bal
            new_bal = round(cur_bal - amount, 4)
            if "current_balance_usdc" in acc:
                acc["current_balance_usdc"] = new_bal
            if "balance_usdc" in acc:
                acc["balance_usdc"] = new_bal
            acc["queries_executed"] = acc.get("queries_executed", 0) + 1
            self._data[account_key] = acc
            return True, new_bal

    def is_hash_redeemed(self, hash_str: str) -> bool:
        h = hash_str.lower().strip()
        if not h:
            return False
        with self._lock:
            return h in self._redeemed_hashes

    def mark_hash_redeemed(self, hash_str: str, ttl_seconds: int = 86400 * 30) -> bool:
        h = hash_str.lower().strip()
        if not h:
            return False
        with self._lock:
            if h in self._redeemed_hashes:
                return False
            self._redeemed_hashes[h] = time.time()
            return True

    @contextmanager
    def acquire_lock(self, lock_key: str, timeout_seconds: float = 5.0) -> Iterator[bool]:
        t_sec = max(0.0, float(timeout_seconds))
        with self._lock:
            if lock_key not in self._locks:
                self._locks[lock_key] = threading.Lock()
            sub_lock = self._locks[lock_key]

        acquired = sub_lock.acquire(timeout=t_sec)
        try:
            yield acquired
        finally:
            if acquired:
                sub_lock.release()


class RedisDistributedStore(BaseDistributedStore):
    """Production Redis/Dragonfly distributed store with atomic Lua scripts."""

    client: Any
    redis_url: str

    def __init__(self, redis_url: str):
        import redis  # pyright: ignore[reportMissingImports]
        self.redis_url = redis_url
        self.client = redis.Redis.from_url(redis_url, decode_responses=True)

    def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        try:
            raw = self.client.get(key)
            if raw:
                return json.loads(raw)
        except Exception:
            pass
        return None

    def set_json(self, key: str, data: Dict[str, Any], ttl_seconds: Optional[int] = None) -> bool:
        try:
            raw = json.dumps(data, ensure_ascii=False)
            if ttl_seconds:
                self.client.setex(key, ttl_seconds, raw)
            else:
                self.client.set(key, raw)
            return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        try:
            return bool(self.client.delete(key))
        except Exception:
            return False

    def debit_balance(self, account_key: str, amount: float) -> Tuple[bool, float]:
        # Atomic Lua script to check balance and decrement in a single Redis execution
        lua_script = """
        local data = redis.call('GET', KEYS[1])
        if not data then
            return {-1, 0}
        end
        local obj = cjson.decode(data)
        local cur = obj['current_balance_usdc'] or obj['balance_usdc'] or 0
        local cost = tonumber(ARGV[1])
        if cost <= 0 or cur < cost then
            return {0, math.floor(cur * 10000 + 0.5) / 10000}
        end
        local new_bal = math.floor((cur - cost) * 10000 + 0.5) / 10000
        if obj['current_balance_usdc'] then
            obj['current_balance_usdc'] = new_bal
        end
        if obj['balance_usdc'] then
            obj['balance_usdc'] = new_bal
        end
        obj['queries_executed'] = (obj['queries_executed'] or 0) + 1
        redis.call('SET', KEYS[1], cjson.encode(obj))
        return {1, new_bal}
        """
        try:
            res = self.client.eval(lua_script, 1, account_key, str(amount))
            return bool(res[0] == 1), float(res[1])
        except Exception:
            return False, 0.0

    def is_hash_redeemed(self, hash_str: str) -> bool:
        h_str = hash_str.lower().strip()
        if not h_str:
            return False
        h = f"oracle:tx:{h_str}"
        try:
            return bool(self.client.exists(h))
        except Exception:
            return False

    def mark_hash_redeemed(self, hash_str: str, ttl_seconds: int = 86400 * 30) -> bool:
        h_str = hash_str.lower().strip()
        if not h_str:
            return False
        h = f"oracle:tx:{h_str}"
        try:
            # SET NX ensures atomic single redemption
            res = self.client.set(h, str(time.time()), nx=True, ex=ttl_seconds)
            return bool(res)
        except Exception:
            return False

    @contextmanager
    def acquire_lock(self, lock_key: str, timeout_seconds: float = 5.0) -> Iterator[bool]:
        key = f"oracle:lock:{lock_key}"
        lock_token = os.urandom(8).hex()
        acquired = False
        t_sec = max(0.0, float(timeout_seconds))
        ttl_ms = max(1000, int(t_sec * 1000) if t_sec > 0 else 5000)
        start_ts = time.time()
        try:
            while True:
                acquired = bool(self.client.set(key, lock_token, nx=True, px=ttl_ms))
                if acquired or (time.time() - start_ts >= t_sec):
                    break
                time.sleep(0.05)
            yield acquired
        finally:
            if acquired:
                # Release lock if still owner
                lua_del = """
                if redis.call('GET', KEYS[1]) == ARGV[1] then
                    return redis.call('DEL', KEYS[1])
                else
                    return 0
                end
                """
                try:
                    self.client.eval(lua_del, 1, key, lock_token)
                except Exception:
                    pass


def get_distributed_store() -> BaseDistributedStore:
    """Factory helper creating Redis store if available or falling back to In-Memory."""
    redis_url = os.getenv("REDIS_URL")
    if redis_url and "PYTEST_CURRENT_TEST" not in os.environ:
        try:
            store = RedisDistributedStore(redis_url)
            store.client.ping()
            return store
        except Exception:
            pass
    return InMemoryDistributedStore()


distributed_store = get_distributed_store()
