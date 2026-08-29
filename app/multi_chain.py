"""
Multi-Chain Network Registry and Gasless Permit2 Configuration.
Supports Polygon (137), Base (8453), and Arbitrum One (42161) for autonomous AI agent USDC settlements.
"""

from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel


class SupportedChain(str, Enum):
    POLYGON = "polygon"      # Chain ID 137
    BASE = "base"            # Chain ID 8453 (Coinbase L2)
    ARBITRUM = "arbitrum"    # Chain ID 42161 (Arbitrum One)


class ChainConfig(BaseModel):
    chain_name: str
    chain_id: int
    display_name: str
    usdc_address: str
    rpc_url: str
    explorer_url: str
    permit2_address: str = "0x000000000022D473030F116dDEE9F6B43aC78BA3"  # Universal Permit2 address
    is_gasless_supported: bool = True
    speed_ms: int


# Canonical USDC & Permit2 addresses across supported EVM networks
CHAIN_REGISTRY: Dict[str, ChainConfig] = {
    SupportedChain.POLYGON.value: ChainConfig(
        chain_name="polygon",
        chain_id=137,
        display_name="Polygon Mainnet",
        usdc_address="0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        rpc_url="https://polygon-rpc.com",
        explorer_url="https://polygonscan.com",
        permit2_address="0x000000000022D473030F116dDEE9F6B43aC78BA3",
        is_gasless_supported=True,
        speed_ms=1800,
    ),
    SupportedChain.BASE.value: ChainConfig(
        chain_name="base",
        chain_id=8453,
        display_name="Base (Coinbase L2)",
        usdc_address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # Native USDC on Base
        rpc_url="https://mainnet.base.org",
        explorer_url="https://basescan.org",
        permit2_address="0x000000000022D473030F116dDEE9F6B43aC78BA3",
        is_gasless_supported=True,
        speed_ms=1200,
    ),
    SupportedChain.ARBITRUM.value: ChainConfig(
        chain_name="arbitrum",
        chain_id=42161,
        display_name="Arbitrum One",
        usdc_address="0xaf88d065e77c8cC2239327C5EDb3A432268e5831",  # Native USDC on Arbitrum
        rpc_url="https://arb1.arbitrum.io/rpc",
        explorer_url="https://arbiscan.io",
        permit2_address="0x000000000022D473030F116dDEE9F6B43aC78BA3",
        is_gasless_supported=True,
        speed_ms=950,
    ),
}


def get_chain_config(chain_identifier: Any) -> ChainConfig:
    """Resolves chain configuration by name ('polygon', 'base', 'arbitrum') or chain ID (137, 8453, 42161)."""
    if isinstance(chain_identifier, int) or (isinstance(chain_identifier, str) and chain_identifier.isdigit()):
        c_id = int(chain_identifier)
        for cfg in CHAIN_REGISTRY.values():
            if cfg.chain_id == c_id:
                return cfg

    clean_name = str(chain_identifier).lower().strip()
    if clean_name in CHAIN_REGISTRY:
        return CHAIN_REGISTRY[clean_name]

    # Default fallback to Polygon
    return CHAIN_REGISTRY[SupportedChain.POLYGON.value]


def list_supported_chains() -> List[Dict[str, Any]]:
    """Returns a list of all supported payment networks."""
    return [cfg.model_dump() for cfg in CHAIN_REGISTRY.values()]
