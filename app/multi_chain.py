"""
Multi-Chain Network Registry and Gasless Permit2 Configuration.
Supports Polygon (137), Base (8453), and Arbitrum One (42161) for autonomous AI agent USDC settlements.
"""

import os
from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel


class SupportedChain(str, Enum):
    POLYGON = "polygon"      # Chain ID 137
    BASE = "base"            # Chain ID 8453 (Coinbase L2)
    ARBITRUM = "arbitrum"    # Chain ID 42161 (Arbitrum One)
    SOLANA = "solana"        # Chain ID 501 (Solana Mainnet-Beta)


class ChainConfig(BaseModel):
    chain_name: str
    chain_id: int
    display_name: str
    usdc_address: str
    rpc_url: str
    fallback_rpc_urls: List[str] = []
    explorer_url: str
    permit2_address: str = "0x000000000022D473030F116dDEE9F6B43aC78BA3"  # Universal Permit2 address
    payment_vault_address: str = "0xb44Bc2Acdd156cE08b549A00a3102e4B01276654"
    oracle_consumer_address: str = "0x835d01534a5D2e63D52636Fafb1019f889d1E66B"
    is_gasless_supported: bool = True
    speed_ms: int


# Canonical USDC, Permit2, and deployed contract addresses across supported networks
CHAIN_REGISTRY: Dict[str, ChainConfig] = {
    SupportedChain.POLYGON.value: ChainConfig(
        chain_name="polygon",
        chain_id=137,
        display_name="Polygon Mainnet",
        usdc_address="0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        rpc_url=os.getenv("POLYGON_RPC_URL", "https://polygon-bor-rpc.publicnode.com"),
        fallback_rpc_urls=[
            "https://polygon-rpc.com",
            "https://1rpc.io/matic",
            "https://polygon.llamarpc.com"
        ],
        explorer_url="https://polygonscan.com",
        permit2_address="0x000000000022D473030F116dDEE9F6B43aC78BA3",
        payment_vault_address="0xb44Bc2Acdd156cE08b549A00a3102e4B01276654",
        oracle_consumer_address="0x835d01534a5D2e63D52636Fafb1019f889d1E66B",
        is_gasless_supported=True,
        speed_ms=1800,
    ),
    SupportedChain.BASE.value: ChainConfig(
        chain_name="base",
        chain_id=8453,
        display_name="Base (Coinbase L2)",
        usdc_address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # Native USDC on Base
        rpc_url=os.getenv("BASE_RPC_URL", "https://mainnet.base.org"),
        fallback_rpc_urls=[
            "https://base.publicnode.com",
            "https://1rpc.io/base",
            "https://base-rpc.publicnode.com"
        ],
        explorer_url="https://basescan.org",
        permit2_address="0x000000000022D473030F116dDEE9F6B43aC78BA3",
        payment_vault_address="0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d",
        oracle_consumer_address="0xe43a9C368808B2dfF139D27789C40A3C8F2282cF",
        is_gasless_supported=True,
        speed_ms=1200,
    ),
    SupportedChain.ARBITRUM.value: ChainConfig(
        chain_name="arbitrum",
        chain_id=42161,
        display_name="Arbitrum One",
        usdc_address="0xaf88d065e77c8cC2239327C5EDb3A432268e5831",  # Native USDC on Arbitrum
        rpc_url=os.getenv("ARBITRUM_RPC_URL", "https://arb1.arbitrum.io/rpc"),
        fallback_rpc_urls=[
            "https://arbitrum-one.publicnode.com",
            "https://1rpc.io/arb"
        ],
        explorer_url="https://arbiscan.io",
        permit2_address="0x000000000022D473030F116dDEE9F6B43aC78BA3",
        payment_vault_address="0x8ACafCEce0B1BFE140e75614b90FD1307b6f389d",
        oracle_consumer_address="0xe43a9C368808B2dfF139D27789C40A3C8F2282cF",
        is_gasless_supported=True,
        speed_ms=950,
    ),
    SupportedChain.SOLANA.value: ChainConfig(
        chain_name="solana",
        chain_id=501,
        display_name="Solana Mainnet",
        usdc_address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # Native SPL USDC on Solana Mainnet
        rpc_url=os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com"),
        fallback_rpc_urls=[
            "https://solana-rpc.publicnode.com",
            "https://rpc.tenderly.co/solana/mainnet"
        ],
        explorer_url="https://solscan.io",
        permit2_address="None",
        payment_vault_address=os.getenv("SOLANA_AGENT_VAULT_PROGRAM_ID", "7oZ16YaazQzN6z5uA1nAZWD9oGUDXyvHwXGJLFYyWi3y"),
        oracle_consumer_address=os.getenv("SOLANA_ORACLE_CONSUMER_PROGRAM_ID", "21ZR1QCyAbNrRLs1iWEkdbNsfCFdJcy6ip9R2JxDbkTL"),
        is_gasless_supported=True,
        speed_ms=400,
    ),
}


def get_chain_config(chain_identifier: Any) -> ChainConfig:
    """Resolves chain configuration by name ('polygon', 'base', 'arbitrum', 'solana') or chain ID (137, 8453, 42161, 501)."""
    if isinstance(chain_identifier, int) or (isinstance(chain_identifier, str) and chain_identifier.isdigit()):
        c_id = int(chain_identifier)
        for cfg in CHAIN_REGISTRY.values():
            if cfg.chain_id == c_id:
                return cfg

    clean_name = str(chain_identifier).lower().strip()
    if clean_name in ["sol", "solana", "solana-mainnet", "501"]:
        return CHAIN_REGISTRY[SupportedChain.SOLANA.value]

    if clean_name in CHAIN_REGISTRY:
        return CHAIN_REGISTRY[clean_name]

    # Default fallback to Polygon
    return CHAIN_REGISTRY[SupportedChain.POLYGON.value]


def resolve_chain_name(chain_identifier: Any) -> str:
    """Returns the canonical chain name (e.g. 'solana', 'polygon', 'base', 'arbitrum')."""
    cfg = get_chain_config(chain_identifier)
    return cfg.chain_name


def is_chain_supported(chain_identifier: Any) -> bool:
    """Checks whether the given identifier maps to a registered chain."""
    if isinstance(chain_identifier, int) or (isinstance(chain_identifier, str) and chain_identifier.isdigit()):
        c_id = int(chain_identifier)
        return any(cfg.chain_id == c_id for cfg in CHAIN_REGISTRY.values())
    clean_name = str(chain_identifier).lower().strip()
    return clean_name in CHAIN_REGISTRY or clean_name in ["sol", "solana", "solana-mainnet", "501"]


def list_supported_chains() -> List[Dict[str, Any]]:
    """Returns a list of all supported payment networks."""
    return [cfg.model_dump() for cfg in CHAIN_REGISTRY.values()]


def get_all_rpc_urls(chain_identifier: Any) -> List[str]:
    """Returns primary and fallback RPC URLs in failover priority order."""
    cfg = get_chain_config(chain_identifier)
    urls = [cfg.rpc_url]
    for fb in cfg.fallback_rpc_urls:
        if fb and fb not in urls:
            urls.append(fb)
    return urls


