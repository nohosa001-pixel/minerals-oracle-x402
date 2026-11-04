# -*- coding: utf-8 -*-
"""
Multi-Chain Live Gas Payment & Solvency Verification Script
===========================================================
Validates real-time gas fee payment capability for Polygon (POL), Base (ETH),
and Arbitrum One (ETH) signed by creator wallet 0x356ECeA957b85120fef8cF5D89b85Cb3d4c13D5b.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

WALLET_ADDRESS = "0x356ECeA957b85120fef8cF5D89b85Cb3d4c13D5b"
DEPLOYER_KEY = os.getenv("POLYGON_DEPLOYER_PRIVATE_KEY") or os.getenv("DEPLOYER_PRIVATE_KEY")

NETWORKS = [
    {
        "name": "Polygon Mainnet",
        "key": "polygon",
        "chain_id": 137,
        "gas_token": "POL",
        "rpc_candidates": [
            os.getenv("POLYGON_RPC_URL", "https://polygon-bor-rpc.publicnode.com"),
            "https://polygon-rpc.com",
            "https://1rpc.io/matic",
        ],
        "explorer": "https://polygonscan.com",
        "settlement_engine": "0xC089E5f72a7F5550Bb383C31B04Bf430a4E31372",
    },
    {
        "name": "Base (Coinbase L2)",
        "key": "base",
        "chain_id": 8453,
        "gas_token": "ETH",
        "rpc_candidates": [
            os.getenv("BASE_RPC_URL", "https://mainnet.base.org"),
            "https://base-rpc.publicnode.com",
            "https://1rpc.io/base",
        ],
        "explorer": "https://basescan.org",
        "settlement_engine": "0xAAde57ABf49A52bC2981Ff64dc54dE27d8c8Ac28",
    },
    {
        "name": "Arbitrum One",
        "key": "arbitrum",
        "chain_id": 42161,
        "gas_token": "ETH",
        "rpc_candidates": [
            os.getenv("ARBITRUM_RPC_URL", "https://arb1.arbitrum.io/rpc"),
            "https://arbitrum-one-rpc.publicnode.com",
            "https://1rpc.io/arb",
        ],
        "explorer": "https://arbiscan.io",
        "settlement_engine": "0xAAde57ABf49A52bC2981Ff64dc54dE27d8c8Ac28",
    },
]


def main():
    print("=" * 72)
    print("   MULTI-CHAIN ON-CHAIN GAS PAYMENT & SOLVENCY AUDIT")
    print("=" * 72)
    print(f"Canonical Creator / Relayer: {WALLET_ADDRESS}")

    if DEPLOYER_KEY:
        derived = Account.from_key(DEPLOYER_KEY).address
        print(f"Deployer Key Signer Match  : {'MATCHED [OK]' if derived.lower() == WALLET_ADDRESS.lower() else 'MISMATCH'}")
    else:
        print("Deployer Key Signer Match  : KEY NOT CONFIGURED")

    all_funded = True

    for net in NETWORKS:
        print("\n" + "-" * 72)
        print(f"Network: {net['name']} (Chain ID: {net['chain_id']})")
        print("-" * 72)

        w3 = None
        used_rpc = None
        for rpc in net["rpc_candidates"]:
            try:
                candidate = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 6}))
                if candidate.is_connected():
                    if net["chain_id"] == 137:
                        try:
                            from web3.middleware import ExtraDataToPOAMiddleware
                            candidate.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
                        except Exception:
                            pass
                    w3 = candidate
                    used_rpc = rpc
                    break
            except Exception:
                continue

        if not w3:
            print(f"[-] RPC Error: All candidate RPC endpoints failed for {net['name']}")
            all_funded = False
            continue

        blk = w3.eth.block_number
        balance_wei = w3.eth.get_balance(WALLET_ADDRESS)
        balance_native = float(Web3.from_wei(balance_wei, "ether"))

        # Gas fee estimation
        latest_block = w3.eth.get_block("latest")
        base_fee_wei = latest_block.get("baseFeePerGas", w3.eth.gas_price)
        base_fee_gwei = float(Web3.from_wei(base_fee_wei, "gwei"))

        # Est. typical contract call gas: 120,000 gas
        est_tx_cost_wei = base_fee_wei * 120000
        est_tx_cost_native = float(Web3.from_wei(est_tx_cost_wei, "ether"))
        txs_payable = int(balance_native / est_tx_cost_native) if est_tx_cost_native > 0 else 0

        can_pay = balance_native > (est_tx_cost_native * 5)
        if not can_pay:
            all_funded = False

        token = net["gas_token"]
        print(f"  RPC Endpoint      : {used_rpc}")
        print(f"  Latest Block      : #{blk:,}")
        print(f"  Base Fee          : {base_fee_gwei:.4f} Gwei")
        print(f"  Current Gas Balance: {balance_native:.6f} {token}")
        print(f"  Est. Cost per Tx  : {est_tx_cost_native:.6f} {token} (120k gas)")
        print(f"  Payable Tx Count  : ~{txs_payable:,} transactions")
        print(f"  Gas Payment Status: {'READY & FUNDED [OK]' if can_pay else 'INSUFFICIENT FUNDS [WARN]'}")
        print(f"  Settlement Engine : {net['settlement_engine']}")
        print(f"  Explorer Link     : {net['explorer']}/address/{WALLET_ADDRESS}")

    print("\n" + "=" * 72)
    if all_funded:
        print("  ALL CHAINS (POLYGON, BASE, ARBITRUM) FULLY EQUIPPED TO PAY GAS!")
    else:
        print("  SOME NETWORKS REQUIRE GAS TOP-UP TO PAY TRANSACTION FEES")
    print("=" * 72)


if __name__ == "__main__":
    main()
