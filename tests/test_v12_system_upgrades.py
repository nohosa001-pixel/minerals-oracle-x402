# -*- coding: utf-8 -*-
"""
Tests for Minerals Oracle v1.2.0 System Upgrades
================================================
Validates:
1. Version bump and packaging configuration (v1.2.0, Redis dependency).
2. Multi-Oracle Consensus Medianizer (Pyth + Statutory benchmarks).
3. EU ETS Carbon price feed and CBAM carbon border tax calculation.
4. Security Gate Circuit Breaker fault-tolerance & state transitions.
5. Prometheus /metrics endpoint and new HTTP API routes.
6. MineralTradeEscrow.sol milestone-based escrow contract artifacts.
"""

import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.pyth_oracle_client import pyth_oracle_client, FALLBACK_BENCHMARKS
from app.global_trade_engine import global_trade_engine
from app.schemas import MineralType
from app.security_gate_client import SecurityGateClient


client = TestClient(app)


def test_v12_version_and_packaging():
    """Validates pyproject.toml contains version 1.2.1 and required dependencies."""
    with open("pyproject.toml", "r", encoding="utf-8") as f:
        content = f.read()
    assert 'version = "1.2.1"' in content
    assert '"redis>=5.0.0"' in content


def test_carbon_and_eu_ets_oracle_feed():
    """Validates Carbon & EU ETS allowance benchmark resolution."""
    res_carbon = pyth_oracle_client.get_realtime_price("CARBON")
    assert res_carbon["symbol"] == "CARBON"
    assert res_carbon["price_usd"] == 78.50

    res_ets = pyth_oracle_client.get_realtime_price("EU_ETS")
    assert res_ets["symbol"] == "EU_ETS"
    assert res_ets["price_usd"] == 78.50


def test_multi_oracle_consensus_medianizer():
    """Validates hybrid aggregation and corridor protection."""
    res_cu = pyth_oracle_client.get_hybrid_aggregated_price("Cu")
    assert res_cu["symbol"] == "Cu"
    assert res_cu["consensus_price_usd"] > 0.0
    assert res_cu["is_tamper_resistant"] is True
    assert "consensus_status" in res_cu

    res_li = pyth_oracle_client.get_hybrid_aggregated_price("LITHIUM_CARBONATE")
    assert res_li["symbol"] == "LITHIUM_CARBONATE"
    assert res_li["statutory_benchmark_usd"] == 13500.0


def test_global_trade_engine_cbam_liability():
    """Validates dynamic CBAM calculation using live carbon pricing."""
    cbam_res = global_trade_engine.calculate_cbam_liability(
        mineral_type=MineralType.LITHIUM_HYDROXIDE,
        cargo_weight_metric_tons=100.0,
        importer_jurisdiction="EU",
    )
    assert cbam_res["importer_jurisdiction"] == "EU"
    assert cbam_res["cbam_status"] == "LIABILITY_CALCULATED"
    assert cbam_res["embedded_carbon_intensity"] == 15.2
    assert cbam_res["total_embedded_co2_metric_tons"] == 1520.0
    assert cbam_res["live_eu_ets_carbon_price_usd"] == 78.50
    # 1520 tons * $78.50 = $119,320.00
    assert cbam_res["total_cbam_liability_usd"] == 119320.00
    assert cbam_res["cbam_surcharge_per_metric_ton_usd"] == round(15.2 * 78.50, 2)


def test_security_gate_circuit_breaker_transitions():
    """Validates Circuit Breaker states: CLOSED -> OPEN -> HALF_OPEN."""
    gate = SecurityGateClient()
    assert gate._circuit_state == "CLOSED"
    assert gate.can_attempt_remote() is True

    # Simulate 3 consecutive failures
    gate.record_failure(Exception("Connection refused"))
    gate.record_failure(Exception("Timeout 504"))
    assert gate._circuit_state == "CLOSED"

    gate.record_failure(Exception("Gateway 502"))
    assert gate._circuit_state == "OPEN"
    assert gate.can_attempt_remote() is False

    status = gate.get_circuit_status()
    assert status["state"] == "OPEN"
    assert status["failure_count"] == 3
    assert status["open_remaining_sec"] > 0

    # Local fallback continues to protect without raising exceptions
    verify_res = gate.verify_input_safety("Clean benign query about lithium")
    assert verify_res["is_safe"] is True
    assert "Circuit Breaker" in verify_res["reason"]

    # Transition to HALF_OPEN after timeout simulation
    gate._circuit_open_until = 0.0
    assert gate.can_attempt_remote() is True
    assert gate._circuit_state == "HALF_OPEN"

    # Reset on success
    gate.record_success()
    assert gate._circuit_state == "CLOSED"
    assert gate._failure_count == 0


def test_prometheus_metrics_endpoint():
    """Validates /metrics endpoint outputs standard Prometheus exposition format."""
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    text = resp.text
    assert "oracle_uptime_seconds" in text
    assert "oracle_active_agent_sessions" in text
    assert "oracle_cached_prices" in text
    assert 'oracle_system_version{version="1.2.1"} 1' in text


def test_consensus_price_api_endpoint():
    """Validates /api/v1/oracle/consensus-price HTTP endpoint."""
    resp = client.get("/api/v1/oracle/consensus-price?symbol=Cu")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "Cu"
    assert "consensus_price_usd" in data
    assert data["is_tamper_resistant"] is True


def test_cbam_liability_api_endpoint():
    """Validates /api/v1/trade/cbam-liability HTTP endpoint."""
    resp = client.get(
        "/api/v1/trade/cbam-liability?mineral_type=INDONESIAN_NICKEL_MHP&cargo_weight_metric_tons=50.0&importer_jurisdiction=EU"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["cbam_status"] == "LIABILITY_CALCULATED"
    assert data["total_cbam_liability_usd"] > 0


def test_mineral_trade_escrow_contract_file():
    """Validates MineralTradeEscrow.sol contract presence and signature consistency."""
    contract_path = os.path.join("contracts", "MineralTradeEscrow.sol")
    assert os.path.exists(contract_path)
    with open(contract_path, "r", encoding="utf-8") as f:
        code = f.read()
    assert "contract MineralTradeEscrow" in code
    assert "releaseStage1BL" in code
    assert "releaseStage2Transit" in code
    assert "completeEscrow" in code
    assert "refundExpiredDeal" in code
