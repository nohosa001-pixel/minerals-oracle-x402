"""
Tests for Multi-Chain Smart Contract Registry, Dynamic Signing, and Verification Artifacts.
"""

from pathlib import Path
from eth_account import Account
from fastapi.testclient import TestClient

from app.main import app
from app.multi_chain import CHAIN_REGISTRY, get_chain_config, SupportedChain
from app.onchain_signer import OnChainOracleSigner
from scripts.verify_contracts import get_constructor_args, NETWORKS

client = TestClient(app)
ROOT_DIR = Path(__file__).parent.parent


def test_multichain_contracts_registry():
    """Validates contract addresses for all supported networks."""
    for chain_name in ["polygon", "base", "arbitrum"]:
        cfg = get_chain_config(chain_name)
        assert cfg.payment_vault_address.startswith("0x")
        assert len(cfg.payment_vault_address) == 42
        assert cfg.oracle_consumer_address.startswith("0x")
        assert len(cfg.oracle_consumer_address) == 42
        assert cfg.usdc_address.startswith("0x")
        assert len(cfg.usdc_address) == 42


def test_onchain_signer_for_chain_factory():
    """Validates dynamic OnChainOracleSigner generation per chain."""
    for chain_key, expected_id in [("polygon", 137), ("base", 8453), ("arbitrum", 42161)]:
        signer = OnChainOracleSigner.for_chain(chain_key)
        assert signer.chain_id == expected_id
        domain = signer.get_domain_data()
        assert domain["chainId"] == expected_id
        assert domain["verifyingContract"] == get_chain_config(chain_key).oracle_consumer_address

        # Test signing on each chain
        signed = signer.sign_price_feed(symbol="Cu", price_usd=9650.0, round_id=2001)
        assert "signature" in signed
        assert signed["signature"]["v"] in (27, 28)
        assert signed["signature"]["r"].startswith("0x")
        assert signed["signature"]["s"].startswith("0x")
        assert len(signed["signature"]["fullSignature"]) == 130


def test_verification_artifacts_and_constructor_encoding():
    """Validates that flattened source files and constructor arguments are properly generated."""
    v_dir = ROOT_DIR / "contracts" / "verification"
    assert (v_dir / "AgentPaymentVault.flattened.sol").exists()
    assert (v_dir / "MineralsOracleConsumer.flattened.sol").exists()
    assert (v_dir / "VERIFICATION_GUIDE.md").exists()

    for chain in ["polygon", "base", "arbitrum"]:
        vault_args = get_constructor_args("AgentPaymentVault", chain)
        assert len(vault_args) == 128  # 2 addresses padded to 32 bytes each = 64 hex chars * 2 = 128
        consumer_args = get_constructor_args("MineralsOracleConsumer", chain)
        assert len(consumer_args) == 64  # 1 address padded to 32 bytes = 64 hex chars


def test_multichain_networks_api_response():
    """Validates that GET /api/v1/oracle/networks provides contract addresses."""
    resp = client.get("/api/v1/oracle/networks")
    assert resp.status_code == 200
    data = resp.json()
    for chain in data["supported_chains"]:
        assert "payment_vault_address" in chain
        assert "oracle_consumer_address" in chain
        assert chain["payment_vault_address"].startswith("0x")
        assert chain["oracle_consumer_address"].startswith("0x")
