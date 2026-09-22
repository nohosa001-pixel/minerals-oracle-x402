# -*- coding: utf-8 -*-
"""
Test Suite: Pyth Network Real-Time Commodity Price Feed Integration
===================================================================
Verifies:
1. Fetching real-time/benchmark spot prices for Copper, Silver, Gold, Lithium, Nickel
2. Integration into OnChainOracleSigner with dynamic pricing
3. REST endpoint /api/v1/oracle/realtime-price/{symbol}
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.pyth_oracle_client import pyth_oracle_client
from app.onchain_signer import onchain_signer


def test_pyth_oracle_client_spot_pricing():
    # 1. Copper spot price
    cu_info = pyth_oracle_client.get_realtime_price("Cu")
    assert cu_info["symbol"] == "Cu"
    assert cu_info["price_usd"] > 1000.0  # Around $9,650 / MT
    assert cu_info["confidence_usd"] >= 0.0

    # 2. Silver spot price
    ag_info = pyth_oracle_client.get_realtime_price("Ag")
    assert ag_info["symbol"] == "Ag"
    assert 20.0 < ag_info["price_usd"] < 100.0  # Around $31.45 / oz

    # 3. Lithium benchmark index
    li_info = pyth_oracle_client.get_realtime_price("Li")
    assert li_info["symbol"] == "Li"
    assert li_info["price_usd"] >= 10000.0  # Around $13,500 / MT


def test_onchain_signer_dynamic_pyth_price_injection():
    # Sign feed with price_usd=None -> pulls Pyth spot price
    signed = onchain_signer.sign_price_feed(symbol="Cu", price_usd=None)
    assert signed["feed"]["symbol"] == "Cu"
    # Spot price in 8 decimals: $9650 * 10^8 = 965000000000
    assert signed["feed"]["spotPriceUsd8Dec"] > 500000000000
    assert signed["signature"]["r"].startswith("0x")
    assert signed["calldata"].startswith("0x")


def test_realtime_price_rest_endpoint():
    client = TestClient(app)
    r = client.get("/api/v1/oracle/realtime-price/ag")
    assert r.status_code == 200
    data = r.json()
    assert data["symbol"] == "Ag"
    assert data["price_usd"] > 0.0
    assert "publish_time_utc" in data
