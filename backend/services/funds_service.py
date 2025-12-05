"""
Service for checking agent fund balances across chains.

This service monitors balances and reports deficits when balances
fall below configured thresholds.
"""

import logging
from typing import Dict, Optional, Tuple

from web3 import Web3
from web3.contract import Contract

from utils.web3_provider import get_w3

logger = logging.getLogger(__name__)

# Minimal ERC20 ABI for balance checks
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
]

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


class FundsService:
    """Manages balance checking and deficit calculation."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def fetch_balance(
        self, chain: str, address: str, asset_address: str
    ) -> Tuple[int, int]:
        """
        Fetch balance and decimals for an address/asset pair.

        Args:
            chain: Chain name (e.g., "base", "optimism")
            address: Account address to check
            asset_address: Token address (ZERO_ADDRESS for native token)

        Returns:
            Tuple of (balance, decimals)
            - balance: Raw balance in smallest unit
            - decimals: Number of decimals for the asset

        Raises:
            Exception: If RPC call fails or contract interaction errors
        """
        try:
            w3 = get_w3(chain)

            # Ensure addresses are checksummed
            address = Web3.to_checksum_address(address)
            asset_address = Web3.to_checksum_address(asset_address)

            # Native token (ETH, OP, etc.)
            if asset_address == ZERO_ADDRESS:
                balance = w3.eth.get_balance(address)
                return (balance, 18)

            # ERC20 token
            contract: Contract = w3.eth.contract(address=asset_address, abi=ERC20_ABI)
            balance = contract.functions.balanceOf(address).call()
            decimals = contract.functions.decimals().call()

            return (balance, decimals)

        except Exception as e:
            self.logger.error(f"Failed to fetch balance for {address} on {chain}: {e}")
            raise

    def calculate_deficit(self, balance: int, threshold: str, topup: str) -> int:
        """
        Calculate deficit based on Pearl v1 formula.

        Formula: deficit = max(topup - balance, 0) if balance < threshold else 0

        Args:
            balance: Current balance (raw units)
            threshold: Minimum required balance (string)
            topup: Target balance when refilling (string)

        Returns:
            Deficit amount (0 if balance >= threshold)
        """
        threshold_int = int(threshold)
        topup_int = int(topup)

        if balance < threshold_int:
            deficit = max(topup_int - balance, 0)
            return deficit

        return 0

    def compute_funds_status(
        self, requirements: Dict[str, Dict[str, Dict[str, Dict[str, str]]]]
    ) -> Dict[str, Dict[str, Dict[str, str]]]:
        """
        Compute funding status across all configured chains/addresses/assets.

        Args:
            requirements: Nested dict from config.fund_requirements
                Structure: {chain: {address: {asset: {threshold, topup}}}}

        Returns:
            Nested dict of deficits (empty {} if all balances healthy)
            Structure: {chain: {address: {asset: deficit_str}}}
        """
        result: Dict[str, Dict[str, Dict[str, str]]] = {}

        for chain, addresses in requirements.items():
            chain_deficits: Dict[str, Dict[str, str]] = {}

            for address, assets in addresses.items():
                address_deficits: Dict[str, str] = {}

                for asset_address, config in assets.items():
                    try:
                        # Fetch current balance
                        balance, decimals = self.fetch_balance(
                            chain, address, asset_address
                        )

                        # Calculate deficit
                        deficit = self.calculate_deficit(
                            balance, config["threshold"], config["topup"]
                        )

                        # Only include if deficit > 0
                        if deficit > 0:
                            address_deficits[asset_address] = str(deficit)
                            self.logger.warning(
                                f"Funding deficit detected: {chain}/{address}/{asset_address} "
                                f"balance={balance}, deficit={deficit}"
                            )

                    except Exception as e:
                        self.logger.error(
                            f"Failed to check balance for {chain}/{address}/{asset_address}: {e}"
                        )
                        # Continue checking other assets

                # Only include address if it has deficits
                if address_deficits:
                    chain_deficits[address] = address_deficits

            # Only include chain if it has deficits
            if chain_deficits:
                result[chain] = chain_deficits

        return result
