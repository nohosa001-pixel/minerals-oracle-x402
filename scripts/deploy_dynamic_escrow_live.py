"""
Live Deployment script for DynamicTradeEscrow.sol on Polygon Mainnet.
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
from web3.middleware import ExtraDataToPOAMiddleware

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

RESULT_FILE = ROOT_DIR / "deploy_result.json"

CHAIN_ID = int(os.getenv("POLYGON_CHAIN_ID", os.getenv("CHAIN_ID", "137")))
DEPLOYER_PRIVATE_KEY = os.getenv("POLYGON_DEPLOYER_PRIVATE_KEY")
TREASURY_WALLET = os.getenv("ORACLE_TREASURY_WALLET", "0xA185B43fDD19619f99952AAed6eabf1029bF36a1")
POLYGON_NATIVE_USDC = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"
PYTH_ORACLE_POLYGON = "0xff1a0f4744e8582DF1aE09D5611b887B6a12925C"

result = {
    "status": "pending",
    "deployer_address": None,
    "balance_pol": 0.0,
    "error": None
}

try:
    if not DEPLOYER_PRIVATE_KEY:
        raise ValueError("POLYGON_DEPLOYER_PRIVATE_KEY is missing in .env")

    pk_clean = DEPLOYER_PRIVATE_KEY.strip()
    if not pk_clean.startswith("0x"):
        pk_clean = "0x" + pk_clean

    account = Account.from_key(pk_clean)
    deployer_address = account.address
    result["deployer_address"] = deployer_address

    rpcs = [
        "https://polygon-bor-rpc.publicnode.com",
        "https://polygon.llamarpc.com",
        "https://1rpc.io/matic",
        "https://polygon.drpc.org",
        "https://rpc.ankr.com/polygon"
    ]

    w3 = None
    for rpc in rpcs:
        try:
            cand = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 15}))
            cand.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            if cand.is_connected():
                w3 = cand
                break
        except Exception:
            continue

    if not w3 or not w3.is_connected():
        raise ConnectionError("Failed to connect to any Polygon Mainnet RPC endpoint")

    balance_wei = w3.eth.get_balance(deployer_address)
    balance_pol = float(w3.from_wei(balance_wei, "ether"))
    result["balance_pol"] = balance_pol

    if balance_pol < 0.05:
        result["status"] = "insufficient_balance"
        result["error"] = f"Deployer address {deployer_address} has {balance_pol:.6f} POL. Minimum ~0.1 POL required."
        RESULT_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")
        sys.exit(0)

    import solcx
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

    contract_factory = w3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = w3.eth.get_transaction_count(deployer_address, "pending")

    latest_block = w3.eth.get_block("latest")
    base_fee = latest_block.get("baseFeePerGas", w3.to_wei(30, "gwei"))
    priority_fee = w3.to_wei(35, "gwei")
    max_fee = int(base_fee * 2) + priority_fee

    deploy_txn = contract_factory.constructor(
        Web3.to_checksum_address(POLYGON_NATIVE_USDC),
        Web3.to_checksum_address(TREASURY_WALLET),
        Web3.to_checksum_address(PYTH_ORACLE_POLYGON)
    ).build_transaction({
        "chainId": CHAIN_ID,
        "from": deployer_address,
        "nonce": nonce,
        "maxFeePerGas": max_fee,
        "maxPriorityFeePerGas": priority_fee,
    })

    try:
        estimated_gas = w3.eth.estimate_gas(deploy_txn)
        deploy_txn["gas"] = int(estimated_gas * 1.25)
    except Exception:
        deploy_txn["gas"] = 2800000

    signed_txn = account.sign_transaction(deploy_txn)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180, poll_latency=2)
    if receipt["status"] != 1:
        raise RuntimeError(f"Transaction reverted on-chain: {tx_hash.hex()}")

    new_contract_address = receipt["contractAddress"]
    result["status"] = "success"
    result["contract_address"] = new_contract_address
    result["tx_hash"] = tx_hash.hex()
    result["block_number"] = receipt["blockNumber"]
    result["gas_used"] = receipt["gasUsed"]
    result["explorer_url"] = f"https://polygonscan.com/address/{new_contract_address}"

    # Update deployed_multichain.json
    reg_path = ROOT_DIR / "contracts" / "deployed_multichain.json"
    if reg_path.exists():
        with open(reg_path, "r", encoding="utf-8") as f:
            reg_data = json.load(f)
        reg_data["networks"]["polygon"]["contracts"]["DynamicTradeEscrow"] = {
            "address": new_contract_address,
            "creator": deployer_address,
            "creation_tx": tx_hash.hex(),
            "blockNumber": receipt["blockNumber"],
            "trustedOracle": TREASURY_WALLET,
            "pythOracle": PYTH_ORACLE_POLYGON,
            "standard": "DynamicTradeEscrow-PythMarkToMarket",
            "settlementToken": POLYGON_NATIVE_USDC,
            "explorer_link": f"https://polygonscan.com/address/{new_contract_address}"
        }
        with open(reg_path, "w", encoding="utf-8") as f:
            json.dump(reg_data, f, indent=2)

    # Update deployed_polygon_mainnet.json
    poly_path = ROOT_DIR / "contracts" / "deployed_polygon_mainnet.json"
    if poly_path.exists():
        with open(poly_path, "r", encoding="utf-8") as f:
            poly_data = json.load(f)
        poly_data["contracts"]["DynamicTradeEscrow"] = {
            "address": new_contract_address,
            "creator": deployer_address,
            "creation_tx": tx_hash.hex(),
            "blockNumber": receipt["blockNumber"],
            "usdcToken": POLYGON_NATIVE_USDC,
            "trustedOracleSigner": TREASURY_WALLET,
            "pythOracle": PYTH_ORACLE_POLYGON,
            "explorer_link": f"https://polygonscan.com/address/{new_contract_address}"
        }
        with open(poly_path, "w", encoding="utf-8") as f:
            json.dump(poly_data, f, indent=2)

except Exception as e:
    result["status"] = "error"
    result["error"] = str(e)
    result["traceback"] = traceback.format_exc()

RESULT_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")
