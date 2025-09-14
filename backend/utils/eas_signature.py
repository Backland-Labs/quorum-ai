"""Standalone EAS signature generation utility.

This module provides EIP-712 signature generation for EAS (Ethereum Attestation Service)
delegated attestations. It's designed to be used by both SafeService and test scripts
to ensure consistency.
"""

from typing import Dict, Any
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_typed_data


def generate_eas_delegated_signature(
    request_data: Dict[str, Any], w3: Web3, eas_contract_address: str, private_key: str
) -> bytes:
    """Generate EIP-712 signature for EAS delegated attestation.

    This is the single source of truth for EAS signature generation,
    used by both SafeService and test scripts.

    Args:
        request_data: The attestation request data containing:
            - schema: bytes32 schema UID
            - recipient: address to receive attestation
            - expirationTime: uint64 expiration timestamp (0 for no expiration)
            - revocable: bool whether attestation can be revoked
            - refUID: bytes32 reference UID (zero bytes for new attestation)
            - data: bytes encoded attestation data
            - value: uint256 ETH value to send
            - deadline: uint64 signature deadline
        w3: Web3 instance for chain interaction
        eas_contract_address: Address of the EAS contract (EIP712Proxy)
        private_key: Private key for signing

    Returns:
        65-byte signature (r: 32 bytes, s: 32 bytes, v: 1 byte)
    """
    account = Account.from_key(private_key)

    # EAS EIP-712 domain and types structure
    # These MUST match the EIP712Proxy contract's domain
    types = {
        "EIP712Domain": [
            {"name": "name", "type": "string"},
            {"name": "version", "type": "string"},
            {"name": "chainId", "type": "uint256"},
            {"name": "verifyingContract", "type": "address"},
        ],
        "Attest": [
            {"name": "schema", "type": "bytes32"},
            {"name": "recipient", "type": "address"},
            {"name": "expirationTime", "type": "uint64"},
            {"name": "revocable", "type": "bool"},
            {"name": "refUID", "type": "bytes32"},
            {"name": "data", "type": "bytes"},
            {"name": "value", "type": "uint256"},
            {"name": "deadline", "type": "uint64"},
        ],
    }

    # Domain MUST match EIP712Proxy's domain exactly
    domain = {
        "name": "EIP712Proxy",
        "version": "1.2.0",
        "chainId": w3.eth.chain_id,
        "verifyingContract": Web3.to_checksum_address(eas_contract_address),
    }

    # Message data - ensure all fields are present and correctly typed
    message = {
        "schema": request_data["schema"],
        "recipient": request_data["recipient"],
        "expirationTime": request_data["expirationTime"],
        "revocable": request_data["revocable"],
        "refUID": request_data["refUID"],
        "data": request_data["data"],
        "value": request_data["value"],
        "deadline": request_data["deadline"],
    }

    # Create EIP-712 encoded data
    typed_data = {
        "domain": domain,
        "primaryType": "Attest",
        "types": types,
        "message": message,
    }

    # Encode and sign
    encoded = encode_typed_data(full_message=typed_data)
    signature = account.sign_message(encoded)

    # Return raw signature bytes
    return signature.signature


def parse_signature_bytes(signature_bytes: bytes) -> Dict[str, Any]:
    """Parse 65-byte signature into v, r, s components.

    Args:
        signature_bytes: 65-byte signature (r: 32, s: 32, v: 1)

    Returns:
        Dict with 'v' (int), 'r' (bytes), 's' (bytes)
    """
    if len(signature_bytes) != 65:
        raise ValueError(
            f"Invalid signature length: {len(signature_bytes)}, expected 65"
        )

    r = signature_bytes[:32]
    s = signature_bytes[32:64]
    v = signature_bytes[64]

    return {"v": v, "r": r, "s": s}


def create_signature_tuple(signature_bytes: bytes) -> tuple:
    """Create signature tuple for contract calls.

    Args:
        signature_bytes: 65-byte signature

    Returns:
        Tuple of (v, r, s) for contract calls
    """
    parsed = parse_signature_bytes(signature_bytes)
    return (parsed["v"], parsed["r"], parsed["s"])


def get_signer_address(private_key: str) -> str:
    """Get the address associated with a private key.

    Args:
        private_key: Hex private key string

    Returns:
        Checksummed Ethereum address
    """
    account = Account.from_key(private_key)
    return account.address
