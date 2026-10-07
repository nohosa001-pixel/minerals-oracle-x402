"""
Automated Contract Verification & Public Explorer Disclosure Script.
Supports Polygonscan (137), BaseScan (8453), and Arbiscan (42161) + Sourcify.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv
from eth_abi import encode
import requests

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CONTRACTS_DIR = ROOT_DIR / "contracts"
VERIFICATION_DIR = CONTRACTS_DIR / "verification"

# Multi-chain configurations
NETWORKS = {
    "polygon": {
        "chainId": 137,
        "name": "Polygon Mainnet",
        "explorer": "https://polygonscan.com",
        "api_url": "https://api.polygonscan.com/api",
        "api_key_env": "POLYGONSCAN_API_KEY",
        "usdc": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        "pyth": "0xff1a0f4744e8582DF1aE09D5611b887B6a12925C",
        "contracts": {
            "AgentPaymentVault": "0xb44Bc2Acdd156cE08b549A00a3102e4B01276654",
            "MineralsOracleConsumer": "0x835d01534a5D2e63D52636Fafb1019f889d1E66B",
            "DynamicTradeEscrow": "0x3A863A2b1018B47FE79041FCDF56efEa3f8b978F"
        }
    },
    "base": {
        "chainId": 8453,
        "name": "Base Mainnet",
        "explorer": "https://basescan.org",
        "api_url": "https://api.basescan.org/api",
        "api_key_env": "BASESCAN_API_KEY",
        "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "pyth": "0x8250f4aF4B972684F7b336503E2D6dFeDeB72416",
        "contracts": {
            "AgentPaymentVault": "0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d",
            "MineralsOracleConsumer": "0xe43a9C368808B2dfF139D27789C40A3C8F2282cF",
            "DynamicTradeEscrow": "0x54786360Db4582AEC2435E216479FD4ff093CB80"
        }
    },
    "arbitrum": {
        "chainId": 42161,
        "name": "Arbitrum One",
        "explorer": "https://arbiscan.io",
        "api_url": "https://api.arbiscan.io/api",
        "api_key_env": "ARBISCAN_API_KEY",
        "usdc": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "pyth": "0xff1a0f4744e8582DF1aE09D5611b887B6a12925C",
        "contracts": {
            "AgentPaymentVault": "0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d",
            "MineralsOracleConsumer": "0xe43a9C368808B2dfF139D27789C40A3C8F2282cF",
            "DynamicTradeEscrow": "0x54786360Db4582AEC2435E216479FD4ff093CB80"
        }
    }
}

TREASURY = os.getenv("ORACLE_TREASURY_WALLET", "0xA185B43fDD19619f99952AAed6eabf1029bF36a1")


def get_constructor_args(contract_name: str, chain: str) -> str:
    """Encodes constructor arguments into hex string."""
    net = NETWORKS[chain]
    if contract_name == "AgentPaymentVault":
        usdc = net["usdc"]
        encoded = encode(["address", "address"], [usdc, TREASURY])
        return encoded.hex()
    elif contract_name == "MineralsOracleConsumer":
        encoded = encode(["address"], [TREASURY])
        return encoded.hex()
    elif contract_name == "DynamicTradeEscrow":
        usdc = net["usdc"]
        pyth = net["pyth"]
        encoded = encode(["address", "address", "address"], [usdc, TREASURY, pyth])
        return encoded.hex()
    else:
        raise ValueError(f"Unknown contract {contract_name}")


def check_sourcify_status(chain_id: int, address: str):
    """Checks verification status on Sourcify V2 API."""
    try:
        url = f"https://sourcify.dev/server/v2/contract/{chain_id}/{address}"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            match = data.get("match")
            vat = data.get("verifiedAt")
            return f"✅ Verified ({match}) [VerifiedAt: {vat}]"
        return "Not verified on Sourcify"
    except Exception as e:
        return f"Sourcify query error: {e}"


def display_verification_details(chain: str):
    """Outputs structured verification parameters and direct URLs."""
    net = NETWORKS[chain]
    print(f"\n========================================================")
    print(f"  VERIFICATION PARAMETERS: {net['name']} (Chain ID {net['chainId']})")
    print(f"========================================================")
    print(f"Compiler Version:  v0.8.20+commit.a1b79de6")
    print(f"Optimization:      Enabled (200 runs)")
    print(f"License:           MIT License")
    print(f"Treasury / Signer: {TREASURY}")
    print(f"Native USDC:       {net['usdc']}")
    print(f"Pyth Feed Oracle:  {net.get('pyth')}")

    for cname, address in net["contracts"].items():
        c_args = get_constructor_args(cname, chain)
        source_file = VERIFICATION_DIR / f"{cname}.flattened.sol"
        verify_url = f"{net['explorer']}/verifyContract?a={address}"
        sourcify_url = f"https://sourcify.dev/#/lookup/{net['chainId']}/{address}"
        status = check_sourcify_status(net['chainId'], address)
        
        print(f"\n--- [{cname}] ---")
        print(f"Contract Address:  {address}")
        print(f"Sourcify Status:   {status}")
        print(f"Sourcify Badge:    {sourcify_url}")
        print(f"Direct Verify URL: {verify_url}")
        print(f"Flattened Source:  {source_file}")
        print(f"Constructor Hex:   {c_args}")


def main():
    parser = argparse.ArgumentParser(description="Contract Verification Helper for Minerals Oracle")
    parser.add_argument("--chain", choices=["polygon", "base", "arbitrum", "all"], default="all")
    args = parser.parse_args()

    chains = ["base", "arbitrum", "polygon"] if args.chain == "all" else [args.chain]
    for c in chains:
        display_verification_details(c)


if __name__ == "__main__":
    main()
