"""AttestationTracker monitoring helper functions.

Simple helper functions to query AttestationTracker contract statistics.
Functions return (0, False) if tracker not configured or on error.
"""

import logging
from typing import Tuple
from config import settings
from utils.web3_provider import get_w3
from utils.abi_loader import load_abi
from web3 import Web3

logger = logging.getLogger(__name__)


def get_multisig_info(multisig_address: str) -> Tuple[int, bool]:
    """Get attestation count and active status for a multisig.

    Args:
        multisig_address: The multisig address to query

    Returns:
        Tuple of (attestation_count, is_active)
        Active status defaults to True since deployed contract doesn't track active status
        Returns (0, False) if tracker not configured or on error
    """
    try:
        # Return defaults if tracker not configured
        if not settings.attestation_tracker_address:
            return (0, False)

        # Get Web3 instance
        w3 = get_w3("base")

        # Load contract ABI
        contract_abi = load_abi("attestation_tracker")

        # Create contract instance
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(settings.attestation_tracker_address),
            abi=contract_abi,
        )

        # Query multisig attestation count using available function
        count = contract.functions.getNumAttestations(multisig_address).call()

        # Default active status to True since separate active status tracking is not available
        is_active = True

        return (count, is_active)

    except Exception as e:
        logger.warning(f"Error querying AttestationTracker for {multisig_address}: {e}")
        return (0, False)


def get_attestation_count(multisig_address: str) -> int:
    """Get number of attestations for a multisig.

    Args:
        multisig_address: The multisig address to query

    Returns:
        Number of attestations, 0 if tracker not configured or on error
    """
    count, _ = get_multisig_info(multisig_address)
    return count
