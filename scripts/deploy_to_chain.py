"""
Universal Live Deployment Script for Base (8453) and Arbitrum One (42161).
Compiles Solidity 0.8.20 contracts with optimizer 200 runs and broadcasts transactions.
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
import solcx

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

CONTRACTS_DIR = ROOT_DIR / "contracts"
DEPLOYED_FILE = CONTRACTS_DIR / "deployed_multichain.json"

TREASURY_WALLET = os.getenv("ORACLE_TREASURY_WALLET", "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf")
DEPLOYER_PK = os.getenv("POLYGON_DEPLOYER_PRIVATE_KEY") or os.getenv("ORACLE_SIGNER_PRIVATE_KEY")

if not DEPLOYER_PK:
    print("[ERROR] Deployer private key missing from .env")
    sys.exit(1)

deployer_account = Account.from_key(DEPLOYER_PK)
deployer_address = deployer_account.address

CHAINS = {
    "base": {
        "chainId": 8453,
        "name": "Base (Coinbase L2)",
        "rpc": os.getenv("BASE_RPC_URL", "https://mainnet.base.org"),
        "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "explorer": "https://basescan.org",
    },
    "arbitrum": {
        "chainId": 42161,
        "name": "Arbitrum One",
        "rpc": os.getenv("ARBITRUM_RPC_URL", "https://arb1.arbitrum.io/rpc"),
        "usdc": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "explorer": "https://arbiscan.io",
    },
}


def compile_contracts():
    print("[1/3] Compiling AgentPaymentVault.sol & MineralsOracleConsumer.sol with solc 0.8.20...")
    solcx.set_solc_version("0.8.20")
    vault_source = (CONTRACTS_DIR / "AgentPaymentVault.sol").read_text(encoding="utf-8")
    consumer_source = (CONTRACTS_DIR / "MineralsOracleConsumer.sol").read_text(encoding="utf-8")

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
                    "*": ["abi", "evm.bytecode"]
                }
            }
        }
    })

    vault_iface = compiled["contracts"]["AgentPaymentVault.sol"]["AgentPaymentVault"]
    consumer_iface = compiled["contracts"]["MineralsOracleConsumer.sol"]["MineralsOracleConsumer"]

    return {
        "vault": {"abi": vault_iface["abi"], "bytecode": vault_iface["evm"]["bytecode"]["object"]},
        "consumer": {"abi": consumer_iface["abi"], "bytecode": consumer_iface["evm"]["bytecode"]["object"]}
    }


def deploy_to_chain(chain_key: str):
    config = CHAINS[chain_key]
    print(f"\n========================================================")
    print(f"  DEPLOYING TO: {config['name']} (Chain ID: {config['chainId']})")
    print(f"  Deployer: {deployer_address}")
    print(f"  Treasury: {TREASURY_WALLET}")
    print(f"  Native USDC: {config['usdc']}")
    print(f"========================================================")

    w3 = Web3(Web3.HTTPProvider(config["rpc"], request_kwargs={"timeout": 30}))
    if not w3.is_connected():
        print(f"[ERROR] Cannot connect to RPC: {config['rpc']}")
        return False

    balance_wei = w3.eth.get_balance(deployer_address)
    balance_eth = w3.from_wei(balance_wei, "ether")
    print(f"Current Balance: {balance_eth:.6f} ETH")

    if balance_wei < w3.to_wei(0.00005, "ether"):
        print(f"[ERROR] Insufficient balance for deployment: {balance_eth} ETH")
        return False

    compiled = compile_contracts()

    # Helper function for deployment
    def broadcast_contract(name: str, abi: list, bytecode: str, args: tuple) -> str:
        print(f"\nBroadcasting {name}...")
        factory = w3.eth.contract(abi=abi, bytecode=bytecode)
        nonce = w3.eth.get_transaction_count(deployer_address, "pending")

        latest_block = w3.eth.get_block("latest")
        base_fee = latest_block.get("baseFeePerGas", w3.to_wei(0.05, "gwei"))
        
        if chain_key == "base":
            priority_fee = w3.to_wei(0.005, "gwei")
            max_fee = int(base_fee * 1.5) + priority_fee
        else: # arbitrum
            gas_price = w3.eth.gas_price
            priority_fee = w3.to_wei(0.01, "gwei")
            max_fee = int(gas_price * 1.3)

        txn = factory.constructor(*args).build_transaction({
            "chainId": config["chainId"],
            "from": deployer_address,
            "nonce": nonce,
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": priority_fee,
        })

        try:
            est_gas = w3.eth.estimate_gas(txn)
            txn["gas"] = int(est_gas * 1.25)
        except Exception as e:
            print(f"Gas estimation fallback ({e}) -> using 1,200,000")
            txn["gas"] = 1200000

        signed = w3.eth.account.sign_transaction(txn, private_key=DEPLOYER_PK)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        print(f"--> Broadcasted! TX Hash: {tx_hash.hex()}")
        print(f"Waiting for confirmation on {config['name']}...")

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120, poll_latency=2)
        if receipt["status"] != 1:
            raise RuntimeError(f"Deployment failed for {name} on {config['name']}")

        addr = receipt["contractAddress"]
        print(f"--> [SUCCESS] {name} deployed at: {addr}")
        print(f"    Explorer: {config['explorer']}/address/{addr}")
        print(f"    Gas used: {receipt['gasUsed']}")
        return addr

    # 1. Deploy AgentPaymentVault
    vault_addr = broadcast_contract(
        "AgentPaymentVault",
        compiled["vault"]["abi"],
        compiled["vault"]["bytecode"],
        (config["usdc"], TREASURY_WALLET)
    )

    time.sleep(2)

    # 2. Deploy MineralsOracleConsumer
    consumer_addr = broadcast_contract(
        "MineralsOracleConsumer",
        compiled["consumer"]["abi"],
        compiled["consumer"]["bytecode"],
        (TREASURY_WALLET,)
    )

    # 3. Update Registry
    registry = {}
    if DEPLOYED_FILE.exists():
        try:
            registry = json.loads(DEPLOYED_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    if "networks" not in registry:
        registry["networks"] = {}

    registry["networks"][chain_key] = {
        "chain_name": chain_key,
        "chainId": config["chainId"],
        "display_name": config["name"],
        "rpc_url": config["rpc"],
        "explorer_url": config["explorer"],
        "status": "active",
        "usdc_token": config["usdc"],
        "permit2": "0x000000000022D473030F116dDEE9F6B43aC78BA3",
        "contracts": {
            "AgentPaymentVault": {
                "address": vault_addr,
                "explorer_link": f"{config['explorer']}/address/{vault_addr}"
            },
            "MineralsOracleConsumer": {
                "address": consumer_addr,
                "explorer_link": f"{config['explorer']}/address/{consumer_addr}",
                "primarySymbol": "Cu"
            }
        }
    }
    registry["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    DEPLOYED_FILE.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    print(f"\n[+] Updated deployed_multichain.json with live {config['name']} addresses!")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chain", choices=["base", "arbitrum", "all"], required=True)
    args = parser.parse_args()

    targets = ["base", "arbitrum"] if args.chain == "all" else [args.chain]
    for c in targets:
        success = deploy_to_chain(c)
        if not success:
            print(f"[!] Deployment aborted for {c}")
            break
