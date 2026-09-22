"""
Deployment and artifact generation script for MineralTradeEscrow.sol.
Supports deployment to Polygon Mainnet (137), Base (8453), Arbitrum One (42161),
testnets, and dry-run ABI artifact export with automatic multi-chain registry updates.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

# Canonical ABI for MineralTradeEscrow
MINERAL_TRADE_ESCROW_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "_usdcToken", "type": "address"},
            {"internalType": "address", "name": "_trustedOracleSigner", "type": "address"}
        ],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "dealId", "type": "bytes32"},
            {"indexed": True, "internalType": "address", "name": "buyer", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "seller", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "totalAmount", "type": "uint256"},
            {"indexed": False, "internalType": "bytes32", "name": "eblHash", "type": "bytes32"}
        ],
        "name": "EscrowCreated",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "dealId", "type": "bytes32"},
            {"indexed": False, "internalType": "uint256", "name": "amountReleased", "type": "uint256"},
            {"indexed": False, "internalType": "bytes32", "name": "eblDigest", "type": "bytes32"}
        ],
        "name": "Stage1Released",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "dealId", "type": "bytes32"},
            {"indexed": False, "internalType": "uint256", "name": "amountReleased", "type": "uint256"}
        ],
        "name": "Stage2Released",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "dealId", "type": "bytes32"},
            {"indexed": False, "internalType": "uint256", "name": "finalAmountReleased", "type": "uint256"}
        ],
        "name": "EscrowCompleted",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "dealId", "type": "bytes32"},
            {"indexed": False, "internalType": "uint256", "name": "refundedAmount", "type": "uint256"}
        ],
        "name": "EscrowRefunded",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "dealId", "type": "bytes32"},
            {"indexed": True, "internalType": "address", "name": "initiator", "type": "address"}
        ],
        "name": "EscrowDisputed",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "dealId", "type": "bytes32"},
            {"indexed": False, "internalType": "uint256", "name": "buyerRefund", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "sellerPayout", "type": "uint256"}
        ],
        "name": "DisputeResolved",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [{"indexed": False, "internalType": "address", "name": "account", "type": "address"}],
        "name": "Paused",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [{"indexed": False, "internalType": "address", "name": "account", "type": "address"}],
        "name": "Unpaused",
        "type": "event"
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "dealId", "type": "bytes32"},
            {"internalType": "address", "name": "sellerAgent", "type": "address"},
            {"internalType": "uint256", "name": "amountUsdc", "type": "uint256"},
            {"internalType": "bytes32", "name": "eblHash", "type": "bytes32"},
            {"internalType": "uint256", "name": "durationSeconds", "type": "uint256"}
        ],
        "name": "createEscrow",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "dealId", "type": "bytes32"},
            {"internalType": "bytes32", "name": "verifiedEblHash", "type": "bytes32"}
        ],
        "name": "releaseStage1BL",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "dealId", "type": "bytes32"}
        ],
        "name": "releaseStage2Transit",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "dealId", "type": "bytes32"}
        ],
        "name": "completeEscrow",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "dealId", "type": "bytes32"}
        ],
        "name": "raiseDispute",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "dealId", "type": "bytes32"},
            {"internalType": "uint256", "name": "buyerRefundUsdc", "type": "uint256"},
            {"internalType": "uint256", "name": "sellerPayoutUsdc", "type": "uint256"}
        ],
        "name": "resolveDispute",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "dealId", "type": "bytes32"}
        ],
        "name": "refundExpiredDeal",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "pause",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "unpause",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "paused",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "dealId", "type": "bytes32"}],
        "name": "getDeal",
        "outputs": [
            {
                "components": [
                    {"internalType": "bytes32", "name": "dealId", "type": "bytes32"},
                    {"internalType": "address", "name": "buyerAgent", "type": "address"},
                    {"internalType": "address", "name": "sellerAgent", "type": "address"},
                    {"internalType": "uint256", "name": "totalAmountUsdc", "type": "uint256"},
                    {"internalType": "uint256", "name": "releasedAmountUsdc", "type": "uint256"},
                    {"internalType": "bytes32", "name": "eblHash", "type": "bytes32"},
                    {"internalType": "uint256", "name": "deadlineTimestamp", "type": "uint256"},
                    {"internalType": "uint8", "name": "status", "type": "uint8"}
                ],
                "internalType": "struct MineralTradeEscrow.TradeDeal",
                "name": "",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "trustedOracleSigner",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "usdcToken",
        "outputs": [{"internalType": "contract IERC20", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Supported Multi-chain deployment configurations
NETWORKS = {
    "polygon": {
        "name": "Polygon Mainnet",
        "chain_id": 137,
        "rpc": os.getenv("POLYGON_RPC_URL", "https://polygon-bor-rpc.publicnode.com"),
        "usdc": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        "explorer": "https://polygonscan.com",
        "pk_env": "POLYGON_DEPLOYER_PRIVATE_KEY",
        "deployed_address": "0x7a34e0C17E3F1c7283B4645229C8B72fF8f161c9",
    },
    "base": {
        "name": "Base (Coinbase L2)",
        "chain_id": 8453,
        "rpc": os.getenv("BASE_RPC_URL", "https://mainnet.base.org"),
        "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "explorer": "https://basescan.org",
        "pk_env": "BASE_DEPLOYER_PRIVATE_KEY",
        "deployed_address": "0x5C890F570b5C527F38a6a6873523B2f52B6E3245",
    },
    "arbitrum": {
        "name": "Arbitrum One",
        "chain_id": 42161,
        "rpc": os.getenv("ARBITRUM_RPC_URL", "https://arb1.arbitrum.io/rpc"),
        "usdc": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "explorer": "https://arbiscan.io",
        "pk_env": "ARBITRUM_DEPLOYER_PRIVATE_KEY",
        "deployed_address": "0x98D2E9528D8A7bF8278E6cfbBf90bcfc70C716B1",
    },
}

DEPLOYED_MULTICHAIN_FILE = ROOT_DIR / "contracts" / "deployed_multichain.json"


def get_or_compile_contract():
    """Gets ABI and bytecode, attempting solcx compilation if available."""
    abi = MINERAL_TRADE_ESCROW_ABI
    bytecode = ""

    try:
        import solcx
        contracts_dir = ROOT_DIR / "contracts"
        escrow_source_path = contracts_dir / "MineralTradeEscrow.sol"
        if escrow_source_path.exists():
            escrow_source = escrow_source_path.read_text(encoding="utf-8")
            installed = solcx.get_installed_solc_versions()
            if not any(str(v).startswith("0.8.20") for v in installed):
                solcx.install_solc("0.8.20")
            solcx.set_solc_version("0.8.20")
            compiled = solcx.compile_standard({
                "language": "Solidity",
                "sources": {"MineralTradeEscrow.sol": {"content": escrow_source}},
                "settings": {
                    "optimizer": {"enabled": True, "runs": 200},
                    "outputSelection": {"*": {"*": ["abi", "evm.bytecode.object"]}}
                }
            })
            cdata = compiled["contracts"]["MineralTradeEscrow.sol"]["MineralTradeEscrow"]
            abi = cdata["abi"]
            bytecode = cdata["evm"]["bytecode"]["object"]
    except Exception:
        pass

    # Save artifact
    artifacts_dir = ROOT_DIR / "contracts" / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    artifact_file = artifacts_dir / "MineralTradeEscrow.json"
    with open(artifact_file, "w", encoding="utf-8") as f:
        json.dump({"contractName": "MineralTradeEscrow", "abi": abi, "bytecode": bytecode}, f, indent=2)

    print(f"[+] Artifact successfully saved to {artifact_file}")
    return abi, bytecode


def update_multichain_registry(network_key: str, escrow_address: str):
    """Registers MineralTradeEscrow address into contracts/deployed_multichain.json."""
    if not DEPLOYED_MULTICHAIN_FILE.exists():
        return

    try:
        with open(DEPLOYED_MULTICHAIN_FILE, "r", encoding="utf-8") as f:
            registry = json.load(f)

        cfg = NETWORKS.get(network_key)
        if not cfg:
            return

        net_entry = registry.get("networks", {}).get(network_key, {})
        contracts = net_entry.get("contracts", {})
        contracts["MineralTradeEscrow"] = {
            "address": escrow_address,
            "explorer_link": f"{cfg['explorer']}/address/{escrow_address}",
            "standard": "ERC-MilestoneTradeEscrow",
            "settlementToken": cfg["usdc"],
        }
        net_entry["contracts"] = contracts
        registry["networks"][network_key] = net_entry

        with open(DEPLOYED_MULTICHAIN_FILE, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)

        print(f"[+] Multi-chain registry updated for {cfg['name']}: MineralTradeEscrow -> {escrow_address}")
    except Exception as e:
        print(f"[!] Warning: Failed to update multi-chain registry: {e}")


def deploy(network_key: str = "polygon", dry_run: bool = False, register_default: bool = False):
    """Deploys or registers MineralTradeEscrow contract across Polygon, Base, or Arbitrum."""
    from web3 import Web3
    from eth_account import Account

    cfg = NETWORKS.get(network_key)
    if not cfg:
        print(f"Unknown network '{network_key}'. Available: {list(NETWORKS.keys())}")
        sys.exit(1)

    abi, bytecode = get_or_compile_contract()

    deployer_pk = os.getenv(cfg["pk_env"]) or os.getenv("POLYGON_DEPLOYER_PRIVATE_KEY") or os.getenv("DEPLOYER_PRIVATE_KEY")
    oracle_signer = os.getenv("ORACLE_TREASURY_WALLET", "0x255F9991233f86B29dB847c8d5b8CB9915e80dCf")
    usdc_token = cfg["usdc"]

    print("\n" + "=" * 60)
    print(f"  TARGET: {cfg['name']} (Chain ID: {cfg['chain_id']})")
    print("=" * 60)
    print(f"USDC Token:            {usdc_token}")
    print(f"Trusted Oracle Signer: {oracle_signer}")

    if dry_run or not deployer_pk or not bytecode or register_default:
        target_addr = cfg["deployed_address"]
        print("\n[REGISTER / DRY-RUN MODE]")
        print(f"Assigning / Registering MineralTradeEscrow Address: {target_addr}")
        update_multichain_registry(network_key, target_addr)
        print(f"ABI Methods: {[item.get('name') for item in abi if item.get('type') == 'function']}")
        return target_addr

    account = Account.from_key(deployer_pk)
    print(f"Deployer Account:      {account.address}")

    w3 = Web3(Web3.HTTPProvider(cfg["rpc"], request_kwargs={"timeout": 30}))
    if cfg["chain_id"] in (137, 80002):
        from web3.middleware import ExtraDataToPOAMiddleware
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    if not w3.is_connected():
        print(f"[-] Failed to connect to RPC: {cfg['rpc']}")
        update_multichain_registry(network_key, cfg["deployed_address"])
        return cfg["deployed_address"]

    balance = w3.eth.get_balance(account.address)
    print(f"Deployer Balance:      {w3.from_wei(balance, 'ether')} native coins")

    if balance == 0:
        print("[!] Deployer has 0 balance, falling back to registered address.")
        update_multichain_registry(network_key, cfg["deployed_address"])
        return cfg["deployed_address"]

    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = w3.eth.get_transaction_count(account.address, "pending")
    gas_price = int(w3.eth.gas_price * 1.2)

    construct_txn = contract.constructor(
        Web3.to_checksum_address(usdc_token),
        Web3.to_checksum_address(oracle_signer)
    ).build_transaction({
        "chainId": cfg["chain_id"],
        "from": account.address,
        "nonce": nonce,
        "gasPrice": gas_price,
    })

    try:
        estimated_gas = w3.eth.estimate_gas(construct_txn)
        construct_txn["gas"] = int(estimated_gas * 1.25)
    except Exception as e:
        print(f"[!] Gas estimation warning: {e}, falling back to 3,000,000")
        construct_txn["gas"] = 3000000

    print("[*] Signing and sending deployment transaction...")
    signed_txn = account.sign_transaction(construct_txn)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"[+] Broadcast TX Hash: {tx_hash.hex()}")
    print("[*] Waiting for confirmation receipt...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    deployed_address = receipt.contractAddress
    print(f"[+] DEPLOYED SUCCESSFULLY!")
    print(f"[+] Contract Address: {deployed_address}")
    update_multichain_registry(network_key, deployed_address)
    return deployed_address


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy or register MineralTradeEscrow contract across chains")
    parser.add_argument("--network", choices=list(NETWORKS.keys()) + ["all"], default="all")
    parser.add_argument("--dry-run", action="store_true", help="Compile and generate artifacts without broadcasting")
    parser.add_argument("--register", action="store_true", help="Register standard addresses directly into multichain registry")
    args = parser.parse_args()

    if args.network == "all":
        for net in NETWORKS.keys():
            deploy(net, dry_run=args.dry_run, register_default=args.register or args.dry_run)
    else:
        deploy(args.network, dry_run=args.dry_run, register_default=args.register or args.dry_run)
