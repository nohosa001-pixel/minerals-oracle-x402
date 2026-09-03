"""
Test suite verifying Korea Investment & Securities (KIS)
strict 1-token-per-day enforcement, GCS persistent caching, and redundant issuance rejection.
"""

import json
import os
import time
import pytest
from unittest.mock import patch, MagicMock

from app.kis_client import KoreaInvestmentFuturesClient


def test_kis_reuses_valid_cached_token(tmp_path):
    """Verify that a valid token in cache file is reused without making any network request."""
    cache_file = tmp_path / ".kis_token_cache.json"
    
    client = KoreaInvestmentFuturesClient()
    client._cache_file = str(cache_file)
    client._gcs_bucket = ""  # isolate from GCS
    
    # Pre-populate valid cache
    valid_data = {
        "cred_hash": client._get_credentials_hash(),
        "access_token": "TEST_VALID_CACHED_TOKEN_123",
        "token_type": "Bearer",
        "expires_at": time.time() + 80000,
        "issued_at_timestamp": time.time() - 3600,  # issued 1 hr ago
        "issued_at_utc": "2026-09-03T10:00:00Z",
    }
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(valid_data, f)

    client._access_token = None
    client._token_expires_at = 0.0

    with patch("httpx.Client.post") as mock_post:
        token = client.get_access_token()
        assert token == "TEST_VALID_CACHED_TOKEN_123"
        # Network call to tokenP MUST NOT be made!
        mock_post.assert_not_called()


def test_kis_rejects_duplicate_issuance_within_23h(tmp_path):
    """
    Verify that even if memory token is cleared or expires_at is tampered,
    if issued_at is less than 23 hours ago, it strictly avoids issuing a new token.
    """
    cache_file = tmp_path / ".kis_token_cache.json"
    
    client = KoreaInvestmentFuturesClient()
    client._cache_file = str(cache_file)
    client._gcs_bucket = ""
    client._access_token = None
    client._token_expires_at = 0.0

    # Token issued 4 hours ago, but slightly expired local clock
    cached_data = {
        "cred_hash": client._get_credentials_hash(),
        "access_token": "EXISTING_STRICT_24H_TOKEN_ABC",
        "token_type": "Bearer",
        "expires_at": time.time() + 100,  # low remaining
        "issued_at_timestamp": time.time() - 14400,  # 4 hours ago
        "issued_at_utc": "2026-09-03T07:00:00Z",
    }
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cached_data, f)

    with patch("httpx.Client.post") as mock_post:
        token = client.get_access_token()
        # Must return the existing token to uphold KIS 1-per-day rule
        assert token == "EXISTING_STRICT_24H_TOKEN_ABC"
        mock_post.assert_not_called()


def test_kis_saves_issued_at_timestamp(tmp_path):
    """Verify that when a token is newly saved, issued_at_timestamp is preserved."""
    cache_file = tmp_path / ".kis_token_cache.json"
    
    client = KoreaInvestmentFuturesClient()
    client._cache_file = str(cache_file)
    client._gcs_bucket = ""

    client._save_token_to_cache("NEW_MOCK_TOKEN_XYZ", 86400)
    
    assert os.path.exists(cache_file)
    with open(cache_file, "r", encoding="utf-8") as f:
        saved = json.load(f)
    assert saved["access_token"] == "NEW_MOCK_TOKEN_XYZ"
    assert "issued_at_timestamp" in saved
    assert time.time() - saved["issued_at_timestamp"] < 5.0
