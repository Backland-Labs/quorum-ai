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
    logger.info(f"Querying AttestationTracker for multisig info - address={multisig_address}")
    
    try:
        # Return defaults if tracker not configured
        if not settings.attestation_tracker_address:
            logger.warning(f"AttestationTracker not configured, returning default values for {multisig_address}")
            return (0, False)

        logger.debug(f"Using AttestationTracker at address: {settings.attestation_tracker_address}")

        # Get Web3 instance
        logger.debug("Getting Web3 connection for base chain")
        w3 = get_w3("base")
        current_block = w3.eth.get_block('latest')
        logger.debug(f"Connected to base chain - block_number={current_block['number']}")

        # Load contract ABI
        logger.debug("Loading AttestationTracker ABI")
        contract_abi = load_abi("attestation_tracker")
        logger.debug(f"Loaded AttestationTracker ABI with {len(contract_abi)} functions/events")

        # Create contract instance
        contract_address = Web3.to_checksum_address(settings.attestation_tracker_address)
        contract = w3.eth.contract(
            address=contract_address,
            abi=contract_abi,
        )
        logger.info(f"Created AttestationTracker contract instance at: {contract_address}")

        # Query multisig attestation count using available function
        logger.debug(f"Calling getNumAttestations for multisig: {multisig_address}")
        multisig_checksum_address = Web3.to_checksum_address(multisig_address)
        count = contract.functions.getNumAttestations(multisig_checksum_address).call()
        logger.info(f"AttestationTracker query successful - multisig={multisig_address}, count={count}")

        # Default active status to True since separate active status tracking is not available
        is_active = True
        logger.debug(f"Setting active status to default value: {is_active}")

        return (count, is_active)

    except Exception as e:
        logger.exception(f"Error querying AttestationTracker for multisig {multisig_address}: {str(e)}")
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
