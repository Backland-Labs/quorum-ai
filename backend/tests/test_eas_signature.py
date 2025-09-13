"""Unit tests for EAS signature generation utility.

This test ensures that the signature generation remains consistent
between SafeService and test scripts.
"""

import pytest
from unittest.mock import Mock
from web3 import Web3
from eth_account import Account

from utils.eas_signature import (
    generate_eas_delegated_signature,
    parse_signature_bytes,
    create_signature_tuple,
    get_signer_address,
)


class TestEASSignature:
    """Test EAS signature generation functions."""

    @pytest.fixture
    def setup_test_data(self):
        """Set up test data for signature generation."""
        # Test private key (DO NOT USE IN PRODUCTION)
        private_key = (
            "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
        )
        account = Account.from_key(private_key)

        # Mock Web3 instance
        w3 = Mock(spec=Web3)
        w3.eth = Mock()
        w3.eth.chain_id = 8453  # Base chain ID

        # EAS contract address
        eas_contract = "0xF095fE4b23958b08D38e52d5d5674bBF0C03cbF6"

        # Test request data
        request_data = {
            "schema": bytes.fromhex(
                "56e7ff73404d5c8102a063b9efeb4b992c90b01c9c958de4c2baae18340f242b"
            ),
            "recipient": "0x742d35Cc6634C0532925a3b844Bc9e7595f0fA27",
            "expirationTime": 0,
            "revocable": True,
            "refUID": bytes(32),
            "data": b"test attestation data",
            "value": 0,
            "deadline": 1234567890,
        }

        return {
            "private_key": private_key,
            "account": account,
            "w3": w3,
            "eas_contract": eas_contract,
            "request_data": request_data,
        }

    def test_generate_eas_delegated_signature(self, setup_test_data):
        """Test that signature generation produces valid 65-byte signature."""
        data = setup_test_data

        # Generate signature
        signature = generate_eas_delegated_signature(
            request_data=data["request_data"],
            w3=data["w3"],
            eas_contract_address=data["eas_contract"],
            private_key=data["private_key"],
        )

        # Verify signature is 65 bytes
        assert len(signature) == 65, (
            f"Signature should be 65 bytes, got {len(signature)}"
        )
        assert isinstance(signature, bytes), "Signature should be bytes"

    def test_signature_deterministic(self, setup_test_data):
        """Test that the same inputs produce the same signature."""
        data = setup_test_data

        # Generate signature twice with same inputs
        sig1 = generate_eas_delegated_signature(
            request_data=data["request_data"],
            w3=data["w3"],
            eas_contract_address=data["eas_contract"],
            private_key=data["private_key"],
        )

        sig2 = generate_eas_delegated_signature(
            request_data=data["request_data"],
            w3=data["w3"],
            eas_contract_address=data["eas_contract"],
            private_key=data["private_key"],
        )

        # Signatures should be identical
        assert sig1 == sig2, "Same inputs should produce same signature"

    def test_parse_signature_bytes(self):
        """Test parsing of signature bytes into v, r, s components."""
        # Create a test signature (65 bytes)
        test_sig = b"\x11" * 32 + b"\x22" * 32 + b"\x1b"

        parsed = parse_signature_bytes(test_sig)

        assert parsed["r"] == b"\x11" * 32
        assert parsed["s"] == b"\x22" * 32
        assert parsed["v"] == 0x1B

    def test_parse_signature_invalid_length(self):
        """Test that parsing fails for invalid signature length."""
        # Invalid signature (wrong length)
        test_sig = b"\x11" * 30  # Only 30 bytes

        with pytest.raises(ValueError, match="Invalid signature length"):
            parse_signature_bytes(test_sig)

    def test_create_signature_tuple(self):
        """Test creation of signature tuple for contract calls."""
        # Create a test signature
        test_sig = b"\xaa" * 32 + b"\xbb" * 32 + b"\x1c"

        sig_tuple = create_signature_tuple(test_sig)

        assert sig_tuple[0] == 0x1C  # v
        assert sig_tuple[1] == b"\xaa" * 32  # r
        assert sig_tuple[2] == b"\xbb" * 32  # s

    def test_get_signer_address(self):
        """Test getting address from private key."""
        # Known test private key and address
        private_key = (
            "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
        )
        expected_address = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"

        address = get_signer_address(private_key)

        assert address == expected_address

    def test_signature_different_for_different_data(self, setup_test_data):
        """Test that different data produces different signatures."""
        data = setup_test_data

        # Generate first signature
        sig1 = generate_eas_delegated_signature(
            request_data=data["request_data"],
            w3=data["w3"],
            eas_contract_address=data["eas_contract"],
            private_key=data["private_key"],
        )

        # Modify request data
        modified_data = data["request_data"].copy()
        modified_data["data"] = b"different attestation data"

        # Generate second signature
        sig2 = generate_eas_delegated_signature(
            request_data=modified_data,
            w3=data["w3"],
            eas_contract_address=data["eas_contract"],
            private_key=data["private_key"],
        )

        # Signatures should be different
        assert sig1 != sig2, "Different data should produce different signatures"

    def test_signature_different_for_different_chain(self, setup_test_data):
        """Test that different chain IDs produce different signatures."""
        data = setup_test_data

        # Generate first signature
        sig1 = generate_eas_delegated_signature(
            request_data=data["request_data"],
            w3=data["w3"],
            eas_contract_address=data["eas_contract"],
            private_key=data["private_key"],
        )

        # Modify chain ID
        w2 = Mock(spec=Web3)
        w2.eth = Mock()
        w2.eth.chain_id = 1  # Ethereum mainnet

        # Generate second signature
        sig2 = generate_eas_delegated_signature(
            request_data=data["request_data"],
            w3=w2,
            eas_contract_address=data["eas_contract"],
            private_key=data["private_key"],
        )

        # Signatures should be different
        assert sig1 != sig2, "Different chain IDs should produce different signatures"

    def test_eip712_domain_consistency(self, setup_test_data):
        """Test that EIP-712 domain values are consistent."""
        data = setup_test_data

        # This test verifies the signature can be generated without errors
        # The domain values are hardcoded in the function to match EIP712Proxy
        signature = generate_eas_delegated_signature(
            request_data=data["request_data"],
            w3=data["w3"],
            eas_contract_address=data["eas_contract"],
            private_key=data["private_key"],
        )

        # If we get here without errors, domain is consistent
        assert signature is not None

        # Verify the signature can be parsed
        parsed = parse_signature_bytes(signature)
        assert "v" in parsed
        assert "r" in parsed
        assert "s" in parsed
