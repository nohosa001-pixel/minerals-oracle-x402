"""
Live Deployment script for DynamicTradeEscrow.sol on Base Mainnet and Arbitrum One.
Signs with POLYGON_DEPLOYER_PRIVATE_KEY from .env and pays gas fees on-chain.
"""

import os
import sys
import json
import traceback
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
import solcx

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

RESULT_FILE = ROOT_DIR / "deploy_base_arb_result.json"

DEPLOYER_PRIVATE_KEY = os.getenv("POLYGON_DEPLOYER_PRIVATE_KEY")
TREASURY_WALLET = os.getenv("ORACLE_TREASURY_WALLET", "0xA185B43fDD19619f99952AAed6eabf1029bF36a1")

if not DEPLOYER_PRIVATE_KEY:
    print("ERROR: POLYGON_DEPLOYER_PRIVATE_KEY missing in .env")
    sys.exit(1)

pk_clean = DEPLOYER_PRIVATE_KEY.strip()
if not pk_clean.startswith("0x"):
    pk_clean = "0x" + pk_clean

account = Account.from_key(pk_clean)
deployer_address = account.address

CONFIGS = [
    {
        "key": "base",
        "name": "Base (Coinbase L2)",
        "chain_id": 8453,
        "rpcs": ["https://mainnet.base.org", "https://base.llamarpc.com", "https://1rpc.io/base"],
        "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "pyth": "0x8250f4aF4B972684F7b336503E2D6dFeDeB72416",
        "explorer": "https://basescan.org"
    },
    {
        "key": "arbitrum",
        "name": "Arbitrum One",
        "chain_id": 42161,
        "rpcs": ["https://arb1.arbitrum.io/rpc", "https://arbitrum.llamarpc.com", "https://1rpc.io/arb"],
        "usdc": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "pyth": "0xff1a0f4744e8582DF1aE09D5611b887B6a12925C",
        "explorer": "https://arbiscan.io"
    }
]

print("=" * 60)
print(f"DEPLOYER ADDRESS: {deployer_address}")
print("=" * 60)

# Compile DynamicTradeEscrow.sol with viaIR
installed = solcx.get_installed_solc_versions()
if not any(str(v).startswith("0.8.20") for v in installed):
    solcx.install_solc("0.8.20")
solcx.set_solc_version("0.8.20")

escrow_source = (ROOT_DIR / "contracts" / "DynamicTradeEscrow.sol").read_text(encoding="utf-8")
compiled = solcx.compile_standard({
    "language": "Solidity",
    "sources": {
        "DynamicTradeEscrow.sol": {"content": escrow_source}
    },
    "settings": {
        "optimizer": {"enabled": True, "runs": 200},
        "viaIR": True,
        "outputSelection": {
            "*": {"*": ["abi", "metadata", "evm.bytecode"]}
        }
    }
})

contract_interface = compiled["contracts"]["DynamicTradeEscrow.sol"]["DynamicTradeEscrow"]
abi = contract_interface["abi"]
bytecode = contract_interface["evm"]["bytecode"]["object"]

deployment_results = {}

for cfg in CONFIGS:
    key = cfg["key"]
    name = cfg["name"]
    chain_id = cfg["chain_id"]
    print(f"\n>>> PROCESSING {name} (Chain ID {chain_id}) <<<")
    
    w3 = None
    for rpc in cfg["rpcs"]:
        try:
            cand = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 15}))
            if cand.is_connected():
                w3 = cand
                print(f"Connected to {rpc}")
                break
        except Exception:
            continue
            
    if not w3 or not w3.is_connected():
        deployment_results[key] = {"status": "error", "error": f"Failed to connect to RPC for {name}"}
        continue

    bal = w3.eth.get_balance(deployer_address)
    bal_eth = float(w3.from_wei(bal, "ether"))
    print(f"Deployer Balance: {bal_eth:.6f} ETH")

    if bal_eth < 0.0001:
        deployment_results[key] = {"status": "insufficient_balance", "balance_eth": bal_eth}
        continue

    contract_factory = w3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = w3.eth.get_transaction_count(deployer_address, "pending")

    gas_price = w3.eth.gas_price
    print(f"Current Gas Price: {w3.from_wei(gas_price, 'gwei'):.4f} Gwei")

    deploy_txn = contract_factory.constructor(
        Web3.to_checksum_address(cfg["usdc"]),
        Web3.to_checksum_address(TREASURY_WALLET),
        Web3.to_checksum_address(cfg["pyth"])
    ).build_transaction({
        "chainId": chain_id,
        "from": deployer_address,
        "nonce": nonce,
        "gasPrice": int(gas_price * 1.25),
    })

    try:
        est_gas = w3.eth.estimate_gas(deploy_txn)
        deploy_txn["gas"] = int(est_gas * 1.3)
    except Exception as e:
        print(f"Gas estimation fallback ({e}) -> using 2,500,000")
        deploy_txn["gas"] = 2500000

    est_cost = float(w3.from_wei(deploy_txn["gas"] * deploy_txn["gasPrice"], "ether"))
    print(f"Estimated Max Gas Cost: {est_cost:.6f} ETH (Balance: {bal_eth:.6f} ETH)")

    signed_txn = account.sign_transaction(deploy_txn)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    tx_hex = tx_hash.hex()
    print(f"Broadcasted TX: {tx_hex}")
    print("Waiting for block confirmation...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180, poll_latency=2)
    if receipt["status"] != 1:
        deployment_results[key] = {"status": "reverted", "tx_hash": tx_hex}
        continue

    new_addr = receipt["contractAddress"]
    print(f"[+] DEPLOYED SUCCESS on {name}: {new_addr}")
    print(f"[+] Block: {receipt['blockNumber']} | Gas Used: {receipt['gasUsed']}")

    deployment_results[key] = {
        "status": "success",
        "contract_address": new_addr,
        "tx_hash": tx_hex,
        "block_number": receipt["blockNumber"],
        "gas_used": receipt["gasUsed"],
        "explorer_link": f"{cfg['explorer']}/address/{new_addr}",
        "tx_link": f"{cfg['explorer']}/tx/{tx_hex}"
    }

RESULT_FILE.write_text(json.dumps(deployment_results, indent=2), encoding="utf-8")

# Update multichain registry
reg_path = ROOT_DIR / "contracts" / "deployed_multichain.json"
if reg_path.exists():
    with open(reg_path, "r", encoding="utf-8") as f:
        reg_data = json.load(f)
    for k, v in deployment_results.items():
        if v.get("status") == "success":
            cfg_item = next(c for c in CONFIGS if c["key"] == k)
            reg_data["networks"][k]["contracts"]["DynamicTradeEscrow"] = {
                "address": v["contract_address"],
                "creator": deployer_address,
                "creation_tx": v["tx_hash"],
                "blockNumber": v["block_number"],
                "trustedOracle": TREASURY_WALLET,
                "pythOracle": cfg_item["pyth"],
                "standard": "DynamicTradeEscrow-PythMarkToMarket",
                "settlementToken": cfg_item["usdc"],
                "explorer_link": v["explorer_link"]
            }
    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(reg_data, f, indent=2)
    print("\ndeployed_multichain.json successfully updated with live addresses!")
