"""
Polygon Mainnet (Chain ID 137) Deployment Script for Minerals Oracle.
Deploys AgentPaymentVault.sol and MineralsOracleConsumer.sol to Polygon Mainnet.
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

# Load environment
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

POLYGON_RPC_URL = os.getenv("POLYGON_RPC_URL", "https://polygon-bor-rpc.publicnode.com")
CHAIN_ID = int(os.getenv("POLYGON_CHAIN_ID", os.getenv("CHAIN_ID", "137")))
DEPLOYER_PRIVATE_KEY = os.getenv("POLYGON_DEPLOYER_PRIVATE_KEY")
TREASURY_WALLET = os.getenv("ORACLE_TREASURY_WALLET", "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf")
POLYGON_NATIVE_USDC = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"

if not DEPLOYER_PRIVATE_KEY:
    print("ERROR: POLYGON_DEPLOYER_PRIVATE_KEY not set in .env")
    sys.exit(1)

deployer_account = Account.from_key(DEPLOYER_PRIVATE_KEY)
deployer_address = deployer_account.address

print(f"==================================================")
print(f"  POLYGON MAINNET DEPLOYMENT (CHAIN ID: {CHAIN_ID})")
print(f"==================================================")
print(f"Deployer Address:    {deployer_address}")
print(f"Treasury Wallet:     {TREASURY_WALLET}")
print(f"Polygon Native USDC: {POLYGON_NATIVE_USDC}")
print(f"RPC Endpoint:        {POLYGON_RPC_URL}")

from web3.middleware import ExtraDataToPOAMiddleware

w3 = Web3(Web3.HTTPProvider(POLYGON_RPC_URL, request_kwargs={"timeout": 30}))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

if not w3.is_connected():
    print("ERROR: Failed to connect to Polygon RPC endpoint.")
    sys.exit(1)

balance_wei = w3.eth.get_balance(deployer_address)
balance_pol = w3.from_wei(balance_wei, "ether")
print(f"Deployer Balance:    {balance_pol:.4f} POL")

if balance_pol < 0.1:
    print("ERROR: Insufficient POL balance for deployment gas.")
    sys.exit(1)

# Step 1: Ensure solc 0.8.20 is installed
print("\n[1/4] Ensuring Solidity 0.8.20 compiler is ready...")
installed_versions = solcx.get_installed_solc_versions()
solc_v0820 = any(str(v).startswith("0.8.20") for v in installed_versions)
if not solc_v0820:
    print("Installing solc 0.8.20...")
    solcx.install_solc("0.8.20")
solcx.set_solc_version("0.8.20")

# Step 2: Compile Contracts
print("\n[2/4] Compiling AgentPaymentVault.sol & MineralsOracleConsumer.sol...")
contracts_dir = ROOT_DIR / "contracts"

vault_source = (contracts_dir / "AgentPaymentVault.sol").read_text(encoding="utf-8")
consumer_source = (contracts_dir / "MineralsOracleConsumer.sol").read_text(encoding="utf-8")

compiled = solcx.compile_standard({
    "language": "Solidity",
    "sources": {
        "AgentPaymentVault.sol": {"content": vault_source},
        "MineralsOracleConsumer.sol": {"content": consumer_source}
    },
    "settings": {
        "optimizer": {"enabled": True, "runs": 200},
        "outputSelection": {
            "*": {
                "*": ["abi", "metadata", "evm.bytecode"]
            }
        }
    }
})

vault_contract_interface = compiled["contracts"]["AgentPaymentVault.sol"]["AgentPaymentVault"]
vault_abi = vault_contract_interface["abi"]
vault_bytecode = vault_contract_interface["evm"]["bytecode"]["object"]

consumer_contract_interface = compiled["contracts"]["MineralsOracleConsumer.sol"]["MineralsOracleConsumer"]
consumer_abi = consumer_contract_interface["abi"]
consumer_bytecode = consumer_contract_interface["evm"]["bytecode"]["object"]

print("Contracts compiled successfully!")

# Helper to send deployment transaction
def deploy_contract(contract_name: str, abi: list, bytecode: str, constructor_args: tuple) -> str:
    print(f"\nDeploying {contract_name} with args {constructor_args}...")
    contract_factory = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    nonce = w3.eth.get_transaction_count(deployer_address, "pending")
    
    latest_block = w3.eth.get_block("latest")
    base_fee = latest_block.get("baseFeePerGas", w3.to_wei(30, "gwei"))
    priority_fee = w3.to_wei(35, "gwei")
    max_fee = int(base_fee * 2) + priority_fee
    
    deploy_txn = contract_factory.constructor(*constructor_args).build_transaction({
        "chainId": CHAIN_ID,
        "from": deployer_address,
        "nonce": nonce,
        "maxFeePerGas": max_fee,
        "maxPriorityFeePerGas": priority_fee,
    })
    
    # Estimate gas
    try:
        estimated_gas = w3.eth.estimate_gas(deploy_txn)
        deploy_txn["gas"] = int(estimated_gas * 1.25)
    except Exception as e:
        print(f"Gas estimation warning: {e}, using default 2,500,000")
        deploy_txn["gas"] = 2500000

    signed_txn = w3.eth.account.sign_transaction(deploy_txn, private_key=DEPLOYER_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"Transaction broadcasted! TX Hash: {tx_hash.hex()}")
    print("Waiting for Polygon block confirmation...")
    
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180, poll_latency=2)
    if receipt["status"] != 1:
        raise RuntimeError(f"Deployment transaction for {contract_name} failed on-chain!")
    
    contract_address = receipt["contractAddress"]
    print(f"--> SUCCESS: {contract_name} deployed at: {contract_address}")
    print(f"    Block: {receipt['blockNumber']} | Gas Used: {receipt['gasUsed']}")
    return contract_address

# Step 3: Execute Deployments
print("\n[3/4] Transacting on Polygon Mainnet...")

# 3-A: Deploy AgentPaymentVault
vault_address = deploy_contract(
    "AgentPaymentVault",
    vault_abi,
    vault_bytecode,
    (POLYGON_NATIVE_USDC, TREASURY_WALLET)
)

time.sleep(3)

# 3-B: Deploy MineralsOracleConsumer
consumer_address = deploy_contract(
    "MineralsOracleConsumer",
    consumer_abi,
    consumer_bytecode,
    (TREASURY_WALLET,)
)

# Step 4: Record & Save Deployment Metadata
print("\n[4/4] Recording Deployed Contract Addresses...")
deployed_info = {
    "network": "Polygon Mainnet",
    "chainId": CHAIN_ID,
    "deployer": deployer_address,
    "treasury": TREASURY_WALLET,
    "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "contracts": {
        "AgentPaymentVault": {
            "address": vault_address,
            "usdcToken": POLYGON_NATIVE_USDC,
            "operator": TREASURY_WALLET
        },
        "MineralsOracleConsumer": {
            "address": consumer_address,
            "trustedSigner": TREASURY_WALLET,
            "primarySymbol": "Cu"
        }
    }
}

deploy_file = contracts_dir / "deployed_polygon_mainnet.json"
deploy_file.write_text(json.dumps(deployed_info, indent=2), encoding="utf-8")
print(f"Deployment record written to: {deploy_file}")

# Update .env
env_file = ROOT_DIR / ".env"
env_text = env_file.read_text(encoding="utf-8")
for key, val in [
    ("MINERALS_ORACLE_CONTRACT_ADDRESS", consumer_address),
    ("AGENT_PAYMENT_VAULT_CONTRACT_ADDRESS", vault_address)
]:
    if key in env_text:
        import re
        env_text = re.sub(rf"^{key}=.*$", f"{key}={val}", env_text, flags=re.MULTILINE)
    else:
        env_text += f"\n{key}={val}"

env_file.write_text(env_text, encoding="utf-8")
print("Updated .env with live contract addresses!")

print("\n==================================================")
print("  POLYGON MAINNET DEPLOYMENT COMPLETED 100%!")
print("==================================================")
print(f"MineralsOracleConsumer: {consumer_address}")
print(f"Polygonscan: https://polygonscan.com/address/{consumer_address}")
print(f"AgentPaymentVault:      {vault_address}")
print(f"Polygonscan: https://polygonscan.com/address/{vault_address}")
