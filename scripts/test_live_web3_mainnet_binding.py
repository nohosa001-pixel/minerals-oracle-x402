#!/usr/bin/env python3
"""
Polygon Mainnet Web3 Wallet & Smart Contract Live Binding Diagnostic Script.
Verifies:
1. Real-time RPC connectivity to Polygon Mainnet (Chain ID 137).
2. Live Deployer & Treasury wallet balance (POL) and transaction nonce.
3. On-chain contract deployment & bytecode verification (MineralsOracleConsumer & AgentPaymentVault).
4. Read verification of contract state (owner, trustedOracleSigner, usdcToken, benchmark symbols).
5. Cryptographic EIP-712 typed-data signing & EVM state simulation (eth.call) against live Mainnet.
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from eth_account import Account
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / ".env")

from app.onchain_signer import OnChainOracleSigner

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_banner(title: str):
    print(f"\n{BOLD}{CYAN}{'=' * 80}{RESET}")
    print(f"{BOLD}{CYAN}  🌐 {title}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 80}{RESET}\n")


def run_live_binding_test(broadcast: bool = False) -> dict:
    print_banner("POLYGON MAINNET (CHAIN ID 137) LIVE WEB3 BINDING TEST")

    # [1] Configuration & Key Management
    pk = os.getenv("POLYGON_DEPLOYER_PRIVATE_KEY")
    if not pk:
        print(f"{RED}[-] Error: POLYGON_DEPLOYER_PRIVATE_KEY not set in .env{RESET}")
        raise ValueError("POLYGON_DEPLOYER_PRIVATE_KEY not set in environment or .env")
    if not pk.startswith("0x"):
        pk = "0x" + pk

    account = Account.from_key(pk)
    wallet_address = account.address
    treasury_address = os.getenv("ORACLE_TREASURY_WALLET", "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf")
    consumer_address = os.getenv("MINERALS_ORACLE_CONTRACT_ADDRESS", "0x835d01534a5D2e63D52636Fafb1019f889d1E66B")
    vault_address = os.getenv("AGENT_PAYMENT_VAULT_CONTRACT_ADDRESS", "0xb44Bc2Acdd156cE08b549A00a3102e4B01276654")
    rpc_url = os.getenv("POLYGON_RPC_URL", "https://polygon-bor-rpc.publicnode.com")

    print(f"{BOLD}[1/5] Wallet & Environment Config:{RESET}")
    print(f"  • Deployer / Signer Address : {GREEN}{wallet_address}{RESET}")
    print(f"  • Treasury Wallet Address   : {GREEN}{treasury_address}{RESET}")
    print(f"  • Oracle Consumer Contract  : {GREEN}{consumer_address}{RESET}")
    print(f"  • Agent Payment Vault       : {GREEN}{vault_address}{RESET}")
    print(f"  • Polygon RPC Endpoint      : {rpc_url}")

    # [2] Web3 RPC Connectivity & PoA Middleware Injection
    print(f"\n{BOLD}[2/5] Connecting to Polygon Mainnet Node...{RESET}")
    start_time = time.perf_counter()
    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    if not w3.is_connected():
        print(f"{RED}[-] Failed to connect to Polygon RPC endpoint: {rpc_url}{RESET}")
        raise ConnectionError(f"Failed to connect to Polygon RPC endpoint: {rpc_url}")

    latest_block = w3.eth.get_block("latest")
    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    chain_id = w3.eth.chain_id

    print(f"  ✓ Connected: {GREEN}SUCCESS{RESET} (Latency: {latency_ms}ms)")
    print(f"  ✓ Chain ID : {GREEN}{chain_id}{RESET} (Polygon Mainnet)")
    print(f"  ✓ Block Height: #{latest_block['number']:,} | Timestamp: {latest_block['timestamp']}")

    # [3] On-Chain Balance & Nonce Check
    print(f"\n{BOLD}[3/5] Inspecting On-Chain Account State...{RESET}")
    balance_wei = w3.eth.get_balance(wallet_address)
    balance_pol = w3.from_wei(balance_wei, "ether")
    nonce = w3.eth.get_transaction_count(wallet_address)

    print(f"  ✓ Wallet Balance : {GREEN}{balance_pol:.5f} POL{RESET} ({balance_wei:,} wei)")
    print(f"  ✓ On-Chain Nonce : {nonce} transactions confirmed")
    assert balance_pol > 0, "Wallet must hold POL for transaction fees."

    # [4] Smart Contract Deployment & State Verification
    print(f"\n{BOLD}[4/5] Verifying On-Chain Smart Contracts...{RESET}")

    # MineralsOracleConsumer
    consumer_cs = Web3.to_checksum_address(consumer_address)
    consumer_code = w3.eth.get_code(consumer_cs)
    print(f"  • MineralsOracleConsumer Bytecode Size: {GREEN}{len(consumer_code):,} bytes{RESET}")
    assert len(consumer_code) > 0, "MineralsOracleConsumer contract has no bytecode on Polygon!"

    consumer_abi = [
        {"inputs": [], "name": "owner", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "trustedOracleSigner", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "primaryBenchmarkSymbol", "outputs": [{"type": "string"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "description", "outputs": [{"type": "string"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "decimals", "outputs": [{"type": "uint8"}], "stateMutability": "view", "type": "function"},
        {
            "inputs": [
                {
                    "components": [
                        {"name": "symbol", "type": "string"},
                        {"name": "spotPriceUsd8Dec", "type": "uint256"},
                        {"name": "timestamp", "type": "uint256"},
                        {"name": "roundId", "type": "uint256"}
                    ],
                    "name": "feed",
                    "type": "tuple"
                },
                {"name": "v", "type": "uint8"},
                {"name": "r", "type": "bytes32"},
                {"name": "s", "type": "bytes32"}
            ],
            "name": "updateMineralPrice",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function"
        }
    ]
    consumer_contract = w3.eth.contract(address=consumer_cs, abi=consumer_abi)
    c_owner = consumer_contract.functions.owner().call()
    c_signer = consumer_contract.functions.trustedOracleSigner().call()
    c_symbol = consumer_contract.functions.primaryBenchmarkSymbol().call()
    c_decimals = consumer_contract.functions.decimals().call()
    c_desc = consumer_contract.functions.description().call()

    print(f"    - Owner                 : {c_owner}")
    print(f"    - Trusted Oracle Signer : {GREEN}{c_signer}{RESET}")
    print(f"    - Benchmark Symbol      : {c_symbol} ({c_decimals} decimals)")
    print(f"    - Description           : {c_desc}")
    assert c_signer.lower() == wallet_address.lower(), "Trusted signer mismatch on contract!"

    # AgentPaymentVault
    vault_cs = Web3.to_checksum_address(vault_address)
    vault_code = w3.eth.get_code(vault_cs)
    print(f"  • AgentPaymentVault Bytecode Size: {GREEN}{len(vault_code):,} bytes{RESET}")
    assert len(vault_code) > 0, "AgentPaymentVault contract has no bytecode on Polygon!"

    vault_abi = [
        {"inputs": [], "name": "owner", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "oracleOperator", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "usdcToken", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"name": "agent", "type": "address"}], "name": "getBalance", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"}
    ]
    vault_contract = w3.eth.contract(address=vault_cs, abi=vault_abi)
    v_owner = vault_contract.functions.owner().call()
    v_operator = vault_contract.functions.oracleOperator().call()
    v_usdc = vault_contract.functions.usdcToken().call()

    print(f"    - Owner           : {v_owner}")
    print(f"    - Oracle Operator : {GREEN}{v_operator}{RESET}")
    print(f"    - USDC Contract   : {GREEN}{v_usdc}{RESET}")
    assert v_operator.lower() == wallet_address.lower(), "Oracle operator mismatch on vault!"

    # [5] EIP-712 Live Cryptographic Signing & EVM Simulation (eth.call)
    print(f"\n{BOLD}[5/5] Testing EIP-712 Signature Verification against Polygon EVM...{RESET}")
    signer_engine = OnChainOracleSigner(private_key=pk, chain_id=137, contract_address=consumer_cs)

    # Use block timestamp - 30 seconds to satisfy require(feed.timestamp <= block.timestamp)
    feed_timestamp = latest_block["timestamp"] - 30
    round_id = int(time.time()) % 1_000_000

    signed_feed = signer_engine.sign_price_feed(
        symbol="Cu",
        price_usd=14200.00,
        round_id=round_id,
        timestamp=feed_timestamp
    )
    feed_data = signed_feed["feed"]
    sig_data = signed_feed["signature"]

    tuple_feed = (
        feed_data["symbol"],
        feed_data["spotPriceUsd8Dec"],
        feed_data["timestamp"],
        feed_data["roundId"]
    )
    v = sig_data["v"]
    r = bytes.fromhex(sig_data["r"][2:])
    s = bytes.fromhex(sig_data["s"][2:])

    print(f"  • Generated EIP-712 Payload : {feed_data['symbol']} @ ${feed_data['spotPriceUsd']:,.2f} USD")
    print(f"  • Signature (v, r, s)       : v={v}, r={sig_data['r'][:12]}..., s={sig_data['s'][:12]}...")

    # Dry-Run Simulation via eth.call on Live Polygon Mainnet State
    sim_start = time.perf_counter()
    consumer_contract.functions.updateMineralPrice(tuple_feed, v, r, s).call({"from": wallet_address})
    sim_latency = round((time.perf_counter() - sim_start) * 1000, 2)

    print(f"  ✓ Live EVM eth.call Simulation : {GREEN}SUCCESS (No Revert!){RESET} (Latency: {sim_latency}ms)")
    print(f"  ✓ Cryptographic Attestation   : Contract successfully accepted ECDSA EIP-712 proof.")

    tx_hash = None
    if broadcast:
        print(f"\n{YELLOW}[!] Broadcasting real on-chain transaction to Polygon Mainnet...{RESET}")
        tx = consumer_contract.functions.updateMineralPrice(tuple_feed, v, r, s).build_transaction({
            "from": wallet_address,
            "nonce": nonce,
            "gas": 150000,
            "maxFeePerGas": w3.eth.gas_price * 2,
            "maxPriorityFeePerGas": w3.to_wei(30, "gwei"),
            "chainId": 137
        })
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=pk)
        tx_hash_bytes = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash = tx_hash_bytes.hex()
        print(f"  ✓ Transaction Broadcasted! TX Hash: {GREEN}{tx_hash}{RESET}")
        print(f"  • Polygonscan Link: https://polygonscan.com/tx/{tx_hash}")

    print(f"\n{BOLD}{GREEN}{'=' * 80}{RESET}")
    print(f"{BOLD}{GREEN}🎯 ALL WEB3 MAINNET BINDING CHECKS PASSED FLAWLESSLY ON POLYGON MAINNET!{RESET}")
    print(f"{BOLD}{GREEN}{'=' * 80}{RESET}\n")

    return {
        "status": "SUCCESS",
        "chain_id": 137,
        "wallet": wallet_address,
        "balance_pol": float(balance_pol),
        "nonce": nonce,
        "consumer_address": consumer_address,
        "vault_address": vault_address,
        "sim_latency_ms": sim_latency,
        "tx_hash": tx_hash
    }


if __name__ == "__main__":
    is_broadcast = "--broadcast" in sys.argv
    try:
        run_live_binding_test(broadcast=is_broadcast)
    except Exception as e:
        print(f"\n{RED}[-] Execution failed: {e}{RESET}")
        sys.exit(1)
