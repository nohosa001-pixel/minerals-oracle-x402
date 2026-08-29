"""
On-Chain EIP-712 Cryptographic Signer and Web3 Calldata Relay Engine.
Handles EIP-712 typed-data hashing and ECDSA signing for MineralsOracleConsumer.sol on Polygon (Chain ID 137).
"""

import os
import time
import secrets
from typing import Dict, Any, Optional, Tuple

from eth_account import Account
from eth_account.messages import encode_typed_data
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

# Network & Contract configuration
POLYGON_CHAIN_ID = int(os.getenv("POLYGON_CHAIN_ID", os.getenv("CHAIN_ID", "137")))
CONTRACT_ADDRESS = os.getenv(
    "MINERALS_ORACLE_CONTRACT_ADDRESS",
    "0x71C836642F4F97E09635b7194685387b9b183652"
)
ORACLE_SIGNER_PRIVATE_KEY = os.getenv(
    "ORACLE_SIGNER_PRIVATE_KEY",
    # Safe default for local/sandbox development: Hardhat Account #0
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
)

# In-memory incremental round sequence tracker per symbol
_ROUND_TRACKER: Dict[str, int] = {
    "Ag": 1001,
    "Pt": 1001,
    "Cu": 1001,
    "Li": 1001,
    "NdDy": 1001,
}


class OnChainOracleSigner:
    """
    Cryptographic signer for Minerals Oracle on-chain consumption.
    Produces EIP-712 typed data signatures (v, r, s) and ABI-encoded calldata.
    """

    def __init__(
        self,
        private_key: str = ORACLE_SIGNER_PRIVATE_KEY,
        chain_id: int = POLYGON_CHAIN_ID,
        contract_address: str = CONTRACT_ADDRESS,
    ):
        self.chain_id = chain_id
        self.contract_address = Web3.to_checksum_address(contract_address)
        self.account = Account.from_key(private_key)
        self.signer_address = self.account.address

    def get_domain_data(self) -> Dict[str, Any]:
        """Returns the EIP-712 domain separator matching MineralsOracleConsumer.sol."""
        return {
            "name": "MineralsOracle",
            "version": "1.0.0",
            "chainId": self.chain_id,
            "verifyingContract": self.contract_address,
        }

    def sign_price_feed(
        self,
        symbol: str,
        price_usd: float,
        round_id: Optional[int] = None,
        timestamp: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Signs a mineral spot price feed using EIP-712 typed data.
        Returns the struct payload, 8-decimal fixed-point price, and ECDSA (v, r, s).
        """
        if timestamp is None:
            timestamp = int(time.time())

        if round_id is None:
            _ROUND_TRACKER[symbol] = _ROUND_TRACKER.get(symbol, 1000) + 1
            round_id = _ROUND_TRACKER[symbol]

        # Convert price to 8 decimals standard (Chainlink standard, e.g. $9,650.00 -> 965000000000)
        spot_price_8dec = int(round(price_usd * 10**8))

        types = {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "MineralPriceFeed": [
                {"name": "symbol", "type": "string"},
                {"name": "spotPriceUsd8Dec", "type": "uint256"},
                {"name": "timestamp", "type": "uint256"},
                {"name": "roundId", "type": "uint256"},
            ],
        }

        message = {
            "symbol": symbol,
            "spotPriceUsd8Dec": spot_price_8dec,
            "timestamp": timestamp,
            "roundId": round_id,
        }

        typed_data = {
            "types": types,
            "primaryType": "MineralPriceFeed",
            "domain": self.get_domain_data(),
            "message": message,
        }

        signable_message = encode_typed_data(full_message=typed_data)
        signed = self.account.sign_message(signable_message)

        v = signed.v
        r = "0x" + signed.r.to_bytes(32, byteorder="big").hex()
        s = "0x" + signed.s.to_bytes(32, byteorder="big").hex()

        # Build raw function calldata for updateMineralPrice((string,uint256,uint256,uint256),uint8,bytes32,bytes32)
        # Function selector for updateMineralPrice((string,uint256,uint256,uint256),uint8,bytes32,bytes32)
        # keccak256("updateMineralPrice((string,uint256,uint256,uint256),uint8,bytes32,bytes32)") -> 4 bytes
        abi_types = ["(string,uint256,uint256,uint256)", "uint8", "bytes32", "bytes32"]
        fn_selector = Web3.keccak(text="updateMineralPrice((string,uint256,uint256,uint256),uint8,bytes32,bytes32)")[:4]
        encoded_args = Web3().codec.encode(
            abi_types,
            [
                (symbol, spot_price_8dec, timestamp, round_id),
                v,
                bytes.fromhex(r[2:]),
                bytes.fromhex(s[2:]),
            ]
        )
        calldata = "0x" + (fn_selector + encoded_args).hex()

        return {
            "feed": {
                "symbol": symbol,
                "spotPriceUsd": price_usd,
                "spotPriceUsd8Dec": spot_price_8dec,
                "timestamp": timestamp,
                "roundId": round_id,
            },
            "signature": {
                "v": v,
                "r": r,
                "s": s,
                "fullSignature": signed.signature.hex(),
                "signerAddress": self.signer_address,
            },
            "contract": {
                "address": self.contract_address,
                "chainId": self.chain_id,
                "standard": "AggregatorV3Interface + EIP-712",
            },
            "calldata": calldata,
        }

    def sign_scrap_settlement(
        self,
        scrap_category: str,
        net_value_usd: float,
        quantity_kg: float,
        batch_id: Optional[str] = None,
        timestamp: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Signs a physical urban mining scrap settlement for on-chain execution.
        """
        if timestamp is None:
            timestamp = int(time.time())

        if batch_id is None:
            batch_id = "0x" + secrets.token_hex(32)
        elif not batch_id.startswith("0x"):
            batch_id = "0x" + batch_id

        net_value_8dec = int(round(net_value_usd * 10**8))
        quantity_kg_int = int(round(quantity_kg))

        types = {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "ScrapSettlement": [
                {"name": "scrapCategory", "type": "string"},
                {"name": "netValueUsd8Dec", "type": "uint256"},
                {"name": "quantityKg", "type": "uint256"},
                {"name": "timestamp", "type": "uint256"},
                {"name": "batchId", "type": "bytes32"},
            ],
        }

        message = {
            "scrapCategory": scrap_category,
            "netValueUsd8Dec": net_value_8dec,
            "quantityKg": quantity_kg_int,
            "timestamp": timestamp,
            "batchId": bytes.fromhex(batch_id[2:]),
        }

        typed_data = {
            "types": types,
            "primaryType": "ScrapSettlement",
            "domain": self.get_domain_data(),
            "message": message,
        }

        signable_message = encode_typed_data(full_message=typed_data)
        signed = self.account.sign_message(signable_message)

        v = signed.v
        r = "0x" + signed.r.to_bytes(32, byteorder="big").hex()
        s = "0x" + signed.s.to_bytes(32, byteorder="big").hex()

        fn_selector = Web3.keccak(text="settleScrapBatch((string,uint256,uint256,uint256,bytes32),uint8,bytes32,bytes32)")[:4]
        abi_types = ["(string,uint256,uint256,uint256,bytes32)", "uint8", "bytes32", "bytes32"]
        encoded_args = Web3().codec.encode(
            abi_types,
            [
                (scrap_category, net_value_8dec, quantity_kg_int, timestamp, bytes.fromhex(batch_id[2:])),
                v,
                bytes.fromhex(r[2:]),
                bytes.fromhex(s[2:]),
            ]
        )
        calldata = "0x" + (fn_selector + encoded_args).hex()

        return {
            "settlement": {
                "batchId": batch_id,
                "scrapCategory": scrap_category,
                "netValueUsd": net_value_usd,
                "netValueUsd8Dec": net_value_8dec,
                "quantityKg": quantity_kg_int,
                "timestamp": timestamp,
            },
            "signature": {
                "v": v,
                "r": r,
                "s": s,
                "fullSignature": signed.signature.hex(),
                "signerAddress": self.signer_address,
            },
            "calldata": calldata,
        }


# Singleton oracle signer instance
onchain_signer = OnChainOracleSigner()
