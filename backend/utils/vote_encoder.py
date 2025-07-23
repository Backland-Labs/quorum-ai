"""Vote Encoder for On-Chain Governor Voting.

NOTE: This module is currently not in active use as the system has migrated to
Snapshot (off-chain) voting. However, this code is being retained for future
implementation of on-chain governance support.

This module provides utilities for encoding vote transactions for various on-chain
governor contracts. It handles the different voting interfaces and parameters
required by different governor implementations (Compound Bravo, OpenZeppelin, etc.).

Future work will use this encoder when submitting on-chain votes through Safe
multisig transactions.
"""

from enum import IntEnum
from typing import Optional
from web3 import Web3
from eth_abi import encode

from services.governor_registry import get_governor, GovernorRegistryError


class VoteEncoderError(Exception):
    pass


class Support(IntEnum):
    AGAINST = 0
    FOR = 1
    ABSTAIN = 2


def validate_proposal_id(proposal_id: int) -> int:
    if proposal_id < 0:
        raise VoteEncoderError("Proposal ID must be non-negative")
    return proposal_id


def validate_reason_length(reason: Optional[str]) -> Optional[str]:
    if reason is not None and len(reason) > 256:
        raise VoteEncoderError("Reason too long (max 256 characters)")
    return reason


def encode_cast_vote(
    governor_id: str, proposal_id: int, support: Support, reason: Optional[str] = None
) -> str:
    try:
        validate_proposal_id(proposal_id)
        validate_reason_length(reason)

        meta, abi = get_governor(governor_id)
    except GovernorRegistryError as e:
        raise VoteEncoderError(str(e))

    try:
        if reason is not None:
            function_selector = Web3.keccak(
                text="castVoteWithReason(uint256,uint8,string)"
            )[:4]
            encoded_params = encode(
                ["uint256", "uint8", "string"], [proposal_id, int(support), reason]
            )
        else:
            function_selector = Web3.keccak(text="castVote(uint256,uint8)")[:4]
            encoded_params = encode(["uint256", "uint8"], [proposal_id, int(support)])

        encoded_data = "0x" + (function_selector + encoded_params).hex()
        return encoded_data
    except Exception as e:
        raise VoteEncoderError(f"Failed to encode vote: {e}")
