"""
Live Polygon Mainnet Deployment Script for MineralTradeEscrow.sol.
Deploys from canonical deployer wallet 0x255F9991233f86B29dB847c8d5b8CB9915e80dCf.
"""

import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
import solcx

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

POLYGON_RPC_URL = os.getenv("POLYGON_RPC_URL", "https://polygon-bor-rpc.publicnode.com")
CHAIN_ID = int(os.getenv("POLYGON_CHAIN_ID", os.getenv("CHAIN_ID", "137")))
DEPLOYER_PK = os.getenv("POLYGON_DEPLOYER_PRIVATE_KEY") or os.getenv("DEPLOYER_PRIVATE_KEY")
TREASURY_WALLET = os.getenv("ORACLE_TREASURY_WALLET", "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf")
POLYGON_NATIVE_USDC = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"

if not DEPLOYER_PK:
    print("[-] Error: POLYGON_DEPLOYER_PRIVATE_KEY is missing in .env")
    sys.exit(1)

w3 = Web3(Web3.HTTPProvider(POLYGON_RPC_URL, request_kwargs={"timeout": 30}))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

if not w3.is_connected():
    print(f"[-] Error: Cannot connect to Polygon RPC: {POLYGON_RPC_URL}")
    sys.exit(1)

deployer_account = w3.eth.account.from_key(DEPLOYER_PK)
deployer_address = deployer_account.address

balance_wei = w3.eth.get_balance(deployer_address)
balance_pol = w3.from_wei(balance_wei, "ether")

print("=" * 60)
print("  POLYGON MAINNET LIVE DEPLOYMENT: MineralTradeEscrow")
print("=" * 60)
print(f"Contract Creator / Deployer: {deployer_address}")
print(f"Balance:                    {balance_pol:.4f} POL")
print(f"Native USDC Address:        {POLYGON_NATIVE_USDC}")
print(f"Trusted Oracle Signer:      {TREASURY_WALLET}")
print(f"Chain ID:                   {CHAIN_ID}")
print(f"RPC Endpoint:               {POLYGON_RPC_URL}")

if balance_pol < 0.1:
    print("[-] Error: Insufficient POL for gas fee.")
    sys.exit(1)

# Step 1: Ensure Solidity 0.8.20 compiler
print("\n[1/3] Preparing Solidity 0.8.20...")
installed_versions = solcx.get_installed_solc_versions()
if not any(str(v).startswith("0.8.20") for v in installed_versions):
    solcx.install_solc("0.8.20")
solcx.set_solc_version("0.8.20")

# Step 2: Compile MineralTradeEscrow.sol
print("[2/3] Compiling MineralTradeEscrow.sol with optimizer (runs=200)...")
source_path = ROOT_DIR / "contracts" / "MineralTradeEscrow.sol"
source_code = source_path.read_text(encoding="utf-8")

compiled = solcx.compile_standard({
    "language": "Solidity",
    "sources": {"MineralTradeEscrow.sol": {"content": source_code}},
    "settings": {
        "optimizer": {"enabled": True, "runs": 200},
        "outputSelection": {
            "*": {"*": ["abi", "evm.bytecode", "metadata"]}
        }
    }
})

cdata = compiled["contracts"]["MineralTradeEscrow.sol"]["MineralTradeEscrow"]
abi = cdata["abi"]
bytecode = cdata["evm"]["bytecode"]["object"]

# Save compiled artifact
artifact_path = ROOT_DIR / "contracts" / "artifacts" / "MineralTradeEscrow.json"
artifact_path.parent.mkdir(parents=True, exist_ok=True)
with open(artifact_path, "w", encoding="utf-8") as f:
    json.dump({"contractName": "MineralTradeEscrow", "abi": abi, "bytecode": bytecode}, f, indent=2)
print(f"[+] Artifact saved to {artifact_path}")

# Step 3: Broadcast transaction from deployer
print("\n[3/3] Broadcasting deployment transaction to Polygon Mainnet...")
contract_factory = w3.eth.contract(abi=abi, bytecode=bytecode)
nonce = w3.eth.get_transaction_count(deployer_address, "pending")

latest_block = w3.eth.get_block("latest")
base_fee = latest_block.get("baseFeePerGas", w3.to_wei(30, "gwei"))
priority_fee = w3.to_wei(35, "gwei")
max_fee = int(base_fee * 2) + priority_fee

deploy_txn = contract_factory.constructor(
    Web3.to_checksum_address(POLYGON_NATIVE_USDC),
    Web3.to_checksum_address(TREASURY_WALLET)
).build_transaction({
    "chainId": CHAIN_ID,
    "from": deployer_address,
    "nonce": nonce,
    "maxFeePerGas": max_fee,
    "maxPriorityFeePerGas": priority_fee,
})

try:
    estimated_gas = w3.eth.estimate_gas(deploy_txn)
    deploy_txn["gas"] = int(estimated_gas * 1.3)
except Exception as e:
    print(f"[!] Gas estimation warning: {e}, falling back to 2,500,000")
    deploy_txn["gas"] = 2500000

print(f"[*] Nonce: {nonce} | Gas Limit: {deploy_txn['gas']} | Max Fee: {w3.from_wei(max_fee, 'gwei'):.2f} Gwei")
signed_txn = w3.eth.account.sign_transaction(deploy_txn, private_key=DEPLOYER_PK)
tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)

print(f"[+] Broadcast TX Hash: {tx_hash.hex()}")
print("[*] Waiting for Polygon block confirmation receipt...")

receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180, poll_latency=2)

if receipt["status"] != 1:
    print(f"[-] Deployment failed! Receipt: {receipt}")
    sys.exit(1)

escrow_address = Web3.to_checksum_address(receipt["contractAddress"])
block_num = receipt["blockNumber"]
gas_used = receipt["gasUsed"]

print("\n" + "=" * 60)
print("  DEPLOYMENT SUCCESSFUL!")
print("=" * 60)
print(f"Contract Name:       MineralTradeEscrow")
print(f"Contract Address:    {escrow_address}")
print(f"Contract Creator:    {deployer_address}")
print(f"Creation TX Hash:    {tx_hash.hex()}")
print(f"Block Number:        {block_num}")
print(f"Gas Used:            {gas_used}")
print(f"Explorer Link:       https://polygonscan.com/address/{escrow_address}")
print(f"TX Explorer Link:    https://polygonscan.com/tx/{tx_hash.hex()}")

# Update deployed_polygon_mainnet.json
mainnet_file = ROOT_DIR / "contracts" / "deployed_polygon_mainnet.json"
if mainnet_file.exists():
    try:
        with open(mainnet_file, "r", encoding="utf-8") as f:
            m_data = json.load(f)
        m_data.setdefault("contracts", {})["MineralTradeEscrow"] = {
            "address": escrow_address,
            "creator": deployer_address,
            "creation_tx": tx_hash.hex(),
            "blockNumber": block_num,
            "usdcToken": POLYGON_NATIVE_USDC,
            "trustedOracleSigner": TREASURY_WALLET,
            "explorer_link": f"https://polygonscan.com/address/{escrow_address}",
        }
        with open(mainnet_file, "w", encoding="utf-8") as f:
            json.dump(m_data, f, indent=2)
        print(f"[+] Updated {mainnet_file}")
    except Exception as e:
        print(f"[!] Warning updating {mainnet_file}: {e}")

# Update deployed_multichain.json
multichain_file = ROOT_DIR / "contracts" / "deployed_multichain.json"
if multichain_file.exists():
    try:
        with open(multichain_file, "r", encoding="utf-8") as f:
            multi_data = json.load(f)
        poly_contracts = multi_data.setdefault("networks", {}).setdefault("polygon", {}).setdefault("contracts", {})
        poly_contracts["MineralTradeEscrow"] = {
            "address": escrow_address,
            "creator": deployer_address,
            "creation_tx": tx_hash.hex(),
            "blockNumber": block_num,
            "explorer_link": f"https://polygonscan.com/address/{escrow_address}",
            "standard": "ERC-MilestoneTradeEscrow",
            "settlementToken": POLYGON_NATIVE_USDC,
        }
        with open(multichain_file, "w", encoding="utf-8") as f:
            json.dump(multi_data, f, indent=2)
        print(f"[+] Updated {multichain_file}")
    except Exception as e:
        print(f"[!] Warning updating {multichain_file}: {e}")
