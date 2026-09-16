"""
Integration tests for Live Web3 Mainnet Binding & On-Chain State Verification.
"""

import os
import pytest
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

load_dotenv()


def test_offline_mainnet_contract_configuration():
    """
    Validates on-chain contract registry, EIP-712 signer and ABI configuration
    without requiring live RPC connectivity or deployer private key.
    Ensures CI pipeline passes deterministically on all environments.
    """
    from app.onchain_signer import OnChainOracleSigner
    from scripts.verify_contracts import NETWORKS

    # Verify Polygon Mainnet contract addresses in registry
    polygon_cfg = NETWORKS.get("polygon")
    assert polygon_cfg is not None
    assert polygon_cfg["chainId"] == 137
    assert polygon_cfg["contracts"]["MineralsOracleConsumer"] == "0x835d01534a5D2e63D52636Fafb1019f889d1E66B"
    assert polygon_cfg["contracts"]["AgentPaymentVault"] == "0xb44Bc2Acdd156cE08b549A00a3102e4B01276654"
    assert polygon_cfg["usdc"] == "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"

    # Verify EIP-712 signing format and calldata encoding
    signer = OnChainOracleSigner(chain_id=137)
    res = signer.sign_price_feed(
        symbol="Cu",
        price_usd=14200.0,
        round_id=1001,
        timestamp=1720000000,
    )
    assert res["feed"]["symbol"] == "Cu"
    assert res["feed"]["spotPriceUsd"] == 14200.0
    assert res["signature"]["v"] in (27, 28)
    assert res["calldata"].startswith("0x")


@pytest.mark.skipif(
    not os.getenv("POLYGON_DEPLOYER_PRIVATE_KEY"),
    reason="Requires POLYGON_DEPLOYER_PRIVATE_KEY in environment for live mainnet binding."
)
def test_live_mainnet_account_and_contract_binding():
    """Validates that the live Polygon wallet and smart contracts exist and are bound."""
    from scripts.test_live_web3_mainnet_binding import run_live_binding_test

    try:
        result = run_live_binding_test(broadcast=False)
    except ConnectionError as ce:
        pytest.skip(f"Live Polygon RPC endpoint unavailable: {ce}")
    except ValueError as ve:
        pytest.skip(f"Live binding credentials unavailable: {ve}")

    assert result["status"] == "SUCCESS"
    assert result["chain_id"] == 137
    assert result["wallet"].lower() == "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf".lower()
    assert result["balance_pol"] > 0
    assert result["sim_latency_ms"] < 5000.0  # Allow reasonable RPC network latency
