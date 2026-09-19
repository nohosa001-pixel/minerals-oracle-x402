"""
Test suite for on-chain transaction receipt verification, anti-replay protection,
and EIP-712 signer mainnet alignment.
"""

import os
import time
import pytest
from app.x402_verifier import x402_verifier, _REDEEMED_TX_HASHES
from app.onchain_signer import onchain_signer
from app.vault_manager import VaultManager
from app.schemas import PricingTier


def test_invalid_tx_hash_format():
    """Invalid tx_hash format (e.g. wrong length, non-hex) must be immediately rejected."""
    is_valid, reason = x402_verifier.verify_onchain_tx(
        tx_hash="not_a_valid_hash",
        chain_name="polygon",
        required_amount_usdc=0.005,
    )
    assert not is_valid
    assert reason is not None
    assert "Invalid EVM transaction hash format" in reason


def test_onchain_tx_replay_protection():
    """A valid tx_hash can only be redeemed once. Replaying it must be rejected."""
    tx_hash = "0x" + "f" * 64
    _REDEEMED_TX_HASHES.pop(tx_hash.lower(), None)

    # First redemption succeeds in test environment
    is_valid_1, reason_1 = x402_verifier.verify_onchain_tx(
        tx_hash=tx_hash,
        chain_name="polygon",
        required_amount_usdc=0.005,
    )
    assert is_valid_1
    assert reason_1 is not None
    assert "tx:" in reason_1

    # Second redemption with identical tx_hash must be blocked as replay attack
    is_valid_2, reason_2 = x402_verifier.verify_onchain_tx(
        tx_hash=tx_hash,
        chain_name="polygon",
        required_amount_usdc=0.005,
    )
    assert not is_valid_2
    assert reason_2 is not None
    assert "Replay attack blocked" in reason_2


def test_onchain_tx_random_unconfirmed_hash_rejected(monkeypatch):
    """
    In production mode (non-mock), an unconfirmed or nonexistent random tx_hash
    must be queried against RPC and rejected if not found or unconfirmed.
    """
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("ALLOW_DEV_BYPASS", "false")

    # A random 66-character hex hash that does not exist on mainnet
    random_fake_hash = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    _REDEEMED_TX_HASHES.pop(random_fake_hash.lower(), None)

    is_valid, reason = x402_verifier.verify_onchain_tx(
        tx_hash=random_fake_hash,
        chain_name="polygon",
        required_amount_usdc=0.005,
    )
    assert not is_valid
    assert reason is not None
    assert ("not found" in reason.lower() or "not confirmed" in reason.lower())


@pytest.mark.skipif(
    not os.getenv("ORACLE_SIGNER_PRIVATE_KEY") and not os.getenv("POLYGON_DEPLOYER_PRIVATE_KEY"),
    reason="Requires live ORACLE_SIGNER_PRIVATE_KEY or POLYGON_DEPLOYER_PRIVATE_KEY in environment."
)
def test_signer_alignment_with_mainnet():
    """
    Verify that the oracle signer private key produces an Ethereum address
    that matches the trustedSigner of the deployed Polygon Mainnet contract.
    """
    assert onchain_signer.is_signer_aligned_with_mainnet()
    assert onchain_signer.signer_address.lower() == "0x255f9991233f86b29db847c8d5b8cb9915e80dcf"


def test_production_mode_disables_demo_account(monkeypatch):
    """
    In production mode, the hardcoded demo account (0x7099...) must NOT be seeded.
    """
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("DISABLE_DEMO_ACCOUNT", "true")

    fresh_vault = VaultManager()
    demo_addr = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    assert demo_addr not in fresh_vault._accounts
    assert fresh_vault.get_account_by_session_key("vault_key_demo_agent_sandbox_2026") is None
