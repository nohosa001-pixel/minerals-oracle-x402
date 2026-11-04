# -*- coding: utf-8 -*-
"""
Live Multi-Chain Deployment Script for TradeFinanceSettlementEngine.sol
========================================================================
Deploys TradeFinanceSettlementEngine on Polygon (137), Base (8453), and Arbitrum One (42161)
paying native on-chain gas fees from canonical creator wallet:
0x356ECeA957b85120fef8cF5D89b85Cb3d4c13D5b.
"""

import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
import solcx

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

DEPLOYER_KEY = os.getenv("POLYGON_DEPLOYER_PRIVATE_KEY") or os.getenv("DEPLOYER_PRIVATE_KEY")
if not DEPLOYER_KEY:
    print("[-] Error: Deployer private key missing in .env")
    sys.exit(1)

clean_key = DEPLOYER_KEY.strip()
if not clean_key.startswith("0x"):
    clean_key = "0x" + clean_key

account = Account.from_key(clean_key)
DEPLOYER_ADDRESS = account.address
TREASURY_ADDRESS = os.getenv("ORACLE_TREASURY_WALLET", DEPLOYER_ADDRESS)
SETTLEMENT_ORACLE = DEPLOYER_ADDRESS

print("=" * 72)
print("  TRADE FINANCE SETTLEMENT ENGINE - LIVE MULTI-CHAIN DEPLOYMENT")
print("=" * 72)
print(f"Deployer / Creator Address: {DEPLOYER_ADDRESS}")
print(f"Treasury Address          : {TREASURY_ADDRESS}")
print(f"Settlement Oracle Address : {SETTLEMENT_ORACLE}")
print("=" * 72)

# Step 1: Compile TradeFinanceSettlementEngine.sol
print("\n[*] Step 1: Compiling TradeFinanceSettlementEngine.sol with solc 0.8.20...")
installed_versions = [str(v) for v in solcx.get_installed_solc_versions()]
if not any("0.8.20" in v for v in installed_versions):
    print("[*] Installing solc 0.8.20...")
    solcx.install_solc("0.8.20")
solcx.set_solc_version("0.8.20")

sol_file = ROOT_DIR / "contracts" / "TradeFinanceSettlementEngine.sol"
contract_source = sol_file.read_text(encoding="utf-8")

compiled = solcx.compile_standard({
    "language": "Solidity",
    "sources": {
        "TradeFinanceSettlementEngine.sol": {"content": contract_source}
    },
    "settings": {
        "optimizer": {"enabled": True, "runs": 200},
        "viaIR": True,
        "outputSelection": {
            "*": {"*": ["abi", "metadata", "evm.bytecode"]}
        }
    }
})

contract_data = compiled["contracts"]["TradeFinanceSettlementEngine.sol"]["TradeFinanceSettlementEngine"]
abi = contract_data["abi"]
bytecode = contract_data["evm"]["bytecode"]["object"]
print(f"[+] Compiled successfully! Bytecode size: {len(bytecode) // 2} bytes")

CHAINS = [
    {
        "key": "base",
        "name": "Base (Coinbase L2)",
        "chain_id": 8453,
        "gas_token": "ETH",
        "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "explorer": "https://basescan.org",
        "rpcs": [
            os.getenv("BASE_RPC_URL", "https://mainnet.base.org"),
            "https://base-rpc.publicnode.com",
            "https://1rpc.io/base"
        ]
    },
    {
        "key": "arbitrum",
        "name": "Arbitrum One",
        "chain_id": 42161,
        "gas_token": "ETH",
        "usdc": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "explorer": "https://arbiscan.io",
        "rpcs": [
            os.getenv("ARBITRUM_RPC_URL", "https://arb1.arbitrum.io/rpc"),
            "https://arbitrum-one-rpc.publicnode.com",
            "https://1rpc.io/arb"
        ]
    },
    {
        "key": "polygon",
        "name": "Polygon Mainnet",
        "chain_id": 137,
        "gas_token": "POL",
        "usdc": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        "explorer": "https://polygonscan.com",
        "rpcs": [
            os.getenv("POLYGON_RPC_URL", "https://polygon-bor-rpc.publicnode.com"),
            "https://polygon-rpc.com",
            "https://1rpc.io/matic"
        ]
    }
]

deployment_results = {}

for chain_info in CHAINS:
    key = chain_info["key"]
    name = chain_info["name"]
    chain_id = chain_info["chain_id"]
    token = chain_info["gas_token"]
    usdc = chain_info["usdc"]
    explorer = chain_info["explorer"]

    print("\n" + "#" * 72)
    print(f"  DEPLOYING TO: {name} (Chain ID: {chain_id})")
    print("#" * 72)

    w3 = None
    rpc_used = None
    for rpc in chain_info["rpcs"]:
        try:
            cand = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 15}))
            if cand.is_connected():
                if chain_id == 137:
                    try:
                        from web3.middleware import ExtraDataToPOAMiddleware
                        cand.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
                    except Exception:
                        pass
                w3 = cand
                rpc_used = rpc
                break
        except Exception:
            continue

    if not w3:
        print(f"[-] Could not connect to any RPC for {name}. Skipping.")
        continue

    bal_wei = w3.eth.get_balance(DEPLOYER_ADDRESS)
    bal_native = float(Web3.from_wei(bal_wei, "ether"))
    print(f"[*] Connected RPC   : {rpc_used}")
    print(f"[*] Wallet Balance  : {bal_native:.6f} {token}")
    print(f"[*] USDC Address    : {usdc}")

    contract_factory = w3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = w3.eth.get_transaction_count(DEPLOYER_ADDRESS, "pending")

    # Build constructor transaction
    constructor_args = (
        Web3.to_checksum_address(usdc),
        Web3.to_checksum_address(SETTLEMENT_ORACLE),
        Web3.to_checksum_address(TREASURY_ADDRESS),
    )

    latest_block = w3.eth.get_block("latest")
    base_fee = latest_block.get("baseFeePerGas", w3.eth.gas_price)
    
    # Priority fee and max fee calculation
    if chain_id == 137:
        priority_fee = w3.to_wei(35, "gwei")
        max_fee = int(base_fee * 1.5) + priority_fee
    elif chain_id == 8453:
        priority_fee = w3.to_wei(0.01, "gwei")
        max_fee = int(base_fee * 1.25) + priority_fee
    else:  # Arbitrum
        priority_fee = w3.to_wei(0.01, "gwei")
        max_fee = int(base_fee * 1.25) + priority_fee

    tx_params = {
        "chainId": chain_id,
        "from": DEPLOYER_ADDRESS,
        "nonce": nonce,
        "maxFeePerGas": max_fee,
        "maxPriorityFeePerGas": priority_fee,
    }

    raw_deploy_tx = contract_factory.constructor(*constructor_args).build_transaction(tx_params)

    # Estimate gas with safety margin
    try:
        est_gas = w3.eth.estimate_gas(raw_deploy_tx)
        raw_deploy_tx["gas"] = int(est_gas * 1.25)
    except Exception as e:
        print(f"[!] Gas estimation warning: {e}. Falling back to 2,800,000 gas limit.")
        raw_deploy_tx["gas"] = 2800000

    est_cost_native = float(Web3.from_wei(raw_deploy_tx["gas"] * max_fee, "ether"))
    print(f"[*] Gas Limit: {raw_deploy_tx['gas']:,} | Max Fee: {Web3.from_wei(max_fee, 'gwei'):.4f} Gwei")
    print(f"[*] Max Tx Cost: {est_cost_native:.6f} {token}")

    if bal_native < est_cost_native:
        print(f"[-] Insufficient {token} for deployment. Balance: {bal_native}, Need: {est_cost_native}")
        continue

    # Sign transaction
    signed_tx = w3.eth.account.sign_transaction(raw_deploy_tx, private_key=clean_key)
    raw_bytes = getattr(signed_tx, "rawTransaction", getattr(signed_tx, "raw_transaction", None))

    print(f"[*] Broadcasting deployment transaction paying on-chain gas...")
    tx_hash = w3.eth.send_raw_transaction(raw_bytes)
    tx_hash_hex = tx_hash.hex()
    print(f"[+] Broadcast TX Hash: {tx_hash_hex}")
    print(f"[*] Explorer Tx Link : {explorer}/tx/{tx_hash_hex}")
    print(f"[*] Waiting for {name} block confirmation...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=240, poll_latency=2)

    if receipt["status"] != 1:
        print(f"[-] Transaction reverted on {name}!")
        continue

    new_contract_address = Web3.to_checksum_address(receipt["contractAddress"])
    block_num = receipt["blockNumber"]
    gas_used = receipt["gasUsed"]
    effective_gas_price = receipt.get("effectiveGasPrice", max_fee)
    actual_gas_spent = float(Web3.from_wei(gas_used * effective_gas_price, "ether"))

    print(f"\n[+++] DEPLOYED SUCCESSFULLY ON {name}!")
    print(f"      New Contract Address : {new_contract_address}")
    print(f"      Contract Creator     : {DEPLOYER_ADDRESS}")
    print(f"      Block Number         : #{block_num:,}")
    print(f"      Gas Used             : {gas_used:,}")
    print(f"      Actual Gas Fee Paid  : {actual_gas_spent:.6f} {token}")
    print(f"      Explorer URL         : {explorer}/address/{new_contract_address}")

    deployment_results[key] = {
        "address": new_contract_address,
        "creator": DEPLOYER_ADDRESS,
        "creation_tx": tx_hash_hex,
        "blockNumber": block_num,
        "gas_used": gas_used,
        "gas_fee_paid": f"{actual_gas_spent:.6f} {token}",
        "trustedOracle": SETTLEMENT_ORACLE,
        "protocolTreasury": TREASURY_ADDRESS,
        "standard": "TradeFinanceSettlementEngine-EUDR-Umpire-v1",
        "protocolFeeBps": 15,
        "settlementToken": usdc,
        "explorer_link": f"{explorer}/address/{new_contract_address}",
        "tx_link": f"{explorer}/tx/{tx_hash_hex}",
    }
    time.sleep(2)

# Step 3: Update deployed_multichain.json and deployed_polygon_mainnet.json
print("\n" + "=" * 72)
print("  UPDATING MULTI-CHAIN REGISTRIES")
print("=" * 72)

multi_file = ROOT_DIR / "contracts" / "deployed_multichain.json"
if multi_file.exists() and deployment_results:
    with open(multi_file, "r", encoding="utf-8") as f:
        multi_data = json.load(f)
    for k, v in deployment_results.items():
        net = multi_data.setdefault("networks", {}).setdefault(k, {})
        net_contracts = net.setdefault("contracts", {})
        net_contracts["TradeFinanceSettlementEngine"] = v
    with open(multi_file, "w", encoding="utf-8") as f:
        json.dump(multi_data, f, indent=2)
    print(f"[+] Updated {multi_file}")

poly_file = ROOT_DIR / "contracts" / "deployed_polygon_mainnet.json"
if poly_file.exists() and "polygon" in deployment_results:
    with open(poly_file, "r", encoding="utf-8") as f:
        poly_data = json.load(f)
    poly_data.setdefault("contracts", {})["TradeFinanceSettlementEngine"] = deployment_results["polygon"]
    with open(poly_file, "w", encoding="utf-8") as f:
        json.dump(poly_data, f, indent=2)
    print(f"[+] Updated {poly_file}")

print("\n" + "=" * 72)
print("  MULTI-CHAIN ON-CHAIN DEPLOYMENT COMPLETE & RECORDED!")
print("=" * 72)
for k, v in deployment_results.items():
    print(f"{k.upper()}:")
    print(f"  Address : {v['address']}")
    print(f"  Creator : {v['creator']}")
    print(f"  Tx Hash : {v['creation_tx']}")
    print(f"  Gas Paid: {v['gas_fee_paid']}")
    print(f"  Link    : {v['explorer_link']}")

