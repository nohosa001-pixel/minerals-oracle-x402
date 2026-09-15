"""
Integration tests for Live Web3 Mainnet Binding & On-Chain State Verification.
"""

import os
import pytest
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

load_dotenv()


def test_live_mainnet_account_and_contract_binding():
    """Validates that the live Polygon wallet and smart contracts exist and are bound."""
    from scripts.test_live_web3_mainnet_binding import run_live_binding_test

    result = run_live_binding_test(broadcast=False)
    assert result["status"] == "SUCCESS"
    assert result["chain_id"] == 137
    assert result["wallet"].lower() == "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf".lower()
    assert result["balance_pol"] > 0
    assert result["sim_latency_ms"] < 2000.0  # EVM eth.call within 2 seconds
