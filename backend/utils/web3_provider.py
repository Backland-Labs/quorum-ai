"""Shared Web3 provider utility for blockchain interactions."""

from web3 import Web3
from config import settings
import logging

logger = logging.getLogger(__name__)


def get_w3(chain: str = "base") -> Web3:
    """Get Web3 instance for a specific chain.

    Args:
        chain: The chain name (e.g., 'base', 'ethereum')

    Returns:
        Web3 instance connected to the chain

    Raises:
        ValueError: If no RPC endpoint configured for chain
    """
    # Map chain to RPC endpoint
    rpc_endpoints = {
        "base": settings.get_base_rpc_endpoint(),
        "ethereum": settings.ethereum_ledger_rpc,
    }

    rpc_url = rpc_endpoints.get(chain)
    if not rpc_url:
        raise ValueError(f"No RPC endpoint configured for chain: {chain}")

    w3 = Web3(Web3.HTTPProvider(rpc_url))

    if not w3.is_connected():
        logger.warning(f"Web3 provider for {chain} not connected, retrying...")
        # Provider will retry on next call

    return w3
