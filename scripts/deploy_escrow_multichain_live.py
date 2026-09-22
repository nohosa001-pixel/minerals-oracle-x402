"""
Live Multi-Chain Deployment Script for MineralTradeEscrow.sol.
Deploys on Base Mainnet (8453) and Arbitrum One (42161) from canonical creator wallet 0x255F9991233f86B29dB847c8d5b8CB9915e80dCf.
"""

import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

DEPLOYER_PK = os.getenv("POLYGON_DEPLOYER_PRIVATE_KEY") or os.getenv("DEPLOYER_PRIVATE_KEY")
TREASURY_WALLET = os.getenv("ORACLE_TREASURY_WALLET", "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf")

CHAINS_TO_DEPLOY = [
    {
        "key": "base",
        "name": "Base (Coinbase L2)",
        "chain_id": 8453,
        "rpc": os.getenv("BASE_RPC_URL", "https://mainnet.base.org"),
        "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "explorer": "https://basescan.org",
    },
    {
        "key": "arbitrum",
        "name": "Arbitrum One",
        "chain_id": 42161,
        "rpc": os.getenv("ARBITRUM_RPC_URL", "https://arb1.arbitrum.io/rpc"),
        "usdc": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "explorer": "https://arbiscan.io",
    },
]

if not DEPLOYER_PK:
    print("[-] Error: Deployer private key missing.")
    sys.exit(1)

# Load compiled artifact
artifact_path = ROOT_DIR / "contracts" / "artifacts" / "MineralTradeEscrow.json"
if not artifact_path.exists():
    print("[-] Error: Compiled artifact MineralTradeEscrow.json not found.")
    sys.exit(1)

with open(artifact_path, "r", encoding="utf-8") as f:
    artifact = json.load(f)

abi = artifact["abi"]
bytecode = artifact["bytecode"]

results = {}

for chain_info in CHAINS_TO_DEPLOY:
    key = chain_info["key"]
    name = chain_info["name"]
    chain_id = chain_info["chain_id"]
    rpc = chain_info["rpc"]
    usdc = chain_info["usdc"]
    explorer = chain_info["explorer"]

    print("\n" + "=" * 65)
    print(f"  DEPLOYING TO: {name} (Chain ID: {chain_id})")
    print("=" * 65)

    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 30}))
    if not w3.is_connected():
        print(f"[-] Failed to connect to RPC: {rpc}")
        continue

    account = w3.eth.account.from_key(DEPLOYER_PK)
    deployer_address = account.address
    balance_wei = w3.eth.get_balance(deployer_address)
    balance_eth = w3.from_wei(balance_wei, "ether")

    print(f"Contract Creator: {deployer_address}")
    print(f"Wallet Balance:   {balance_eth:.6f} ETH")
    print(f"USDC Token:       {usdc}")
    print(f"Oracle Signer:    {TREASURY_WALLET}")

    contract_factory = w3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = w3.eth.get_transaction_count(deployer_address, "pending")
    gas_price = int(w3.eth.gas_price * 1.35)

    deploy_txn = contract_factory.constructor(
        Web3.to_checksum_address(usdc),
        Web3.to_checksum_address(TREASURY_WALLET)
    ).build_transaction({
        "chainId": chain_id,
        "from": deployer_address,
        "nonce": nonce,
        "gasPrice": gas_price,
    })

    try:
        estimated_gas = w3.eth.estimate_gas(deploy_txn)
        deploy_txn["gas"] = int(estimated_gas * 1.25)
    except Exception as e:
        print(f"[!] Warning estimating gas: {e}, falling back to 2,500,000")
        deploy_txn["gas"] = 2500000

    print(f"[*] Nonce: {nonce} | Gas Limit: {deploy_txn['gas']} | Gas Price: {w3.from_wei(gas_price, 'gwei'):.4f} Gwei")
    signed_txn = w3.eth.account.sign_transaction(deploy_txn, private_key=DEPLOYER_PK)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)

    print(f"[+] Broadcast TX Hash: {tx_hash.hex()}")
    print(f"[*] Waiting for {name} block confirmation...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180, poll_latency=2)

    if receipt["status"] != 1:
        print(f"[-] Deployment failed on {name}!")
        continue

    escrow_address = Web3.to_checksum_address(receipt["contractAddress"])
    block_num = receipt["blockNumber"]
    gas_used = receipt["gasUsed"]

    print(f"[+] DEPLOYED SUCCESSFULLY ON {name}!")
    print(f"    Contract Address: {escrow_address}")
    print(f"    Contract Creator: {deployer_address}")
    print(f"    TX Hash:          {tx_hash.hex()}")
    print(f"    Block:            {block_num} | Gas Used: {gas_used}")
    print(f"    Explorer:         {explorer}/address/{escrow_address}")

    results[key] = {
        "address": escrow_address,
        "creator": deployer_address,
        "creation_tx": tx_hash.hex(),
        "blockNumber": block_num,
        "explorer_link": f"{explorer}/address/{escrow_address}",
        "tx_link": f"{explorer}/tx/{tx_hash.hex()}",
        "standard": "ERC-MilestoneTradeEscrow",
        "settlementToken": usdc,
    }
    time.sleep(2)

# Update deployed_multichain.json
multichain_file = ROOT_DIR / "contracts" / "deployed_multichain.json"
if multichain_file.exists():
    try:
        with open(multichain_file, "r", encoding="utf-8") as f:
            multi_data = json.load(f)
        for k, v in results.items():
            net_contracts = multi_data.setdefault("networks", {}).setdefault(k, {}).setdefault("contracts", {})
            net_contracts["MineralTradeEscrow"] = v
        with open(multichain_file, "w", encoding="utf-8") as f:
            json.dump(multi_data, f, indent=2)
        print(f"\n[+] Successfully updated {multichain_file}")
    except Exception as e:
        print(f"[!] Warning updating {multichain_file}: {e}")

print("\n" + "=" * 65)
print("  MULTI-CHAIN LIVE DEPLOYMENT COMPLETE!")
print("=" * 65)
for k, v in results.items():
    print(f"{k.upper()}:")
    print(f"  Address: {v['address']}")
    print(f"  Creator: {v['creator']}")
    print(f"  TX:      {v['creation_tx']}")
    print(f"  Link:    {v['explorer_link']}")
