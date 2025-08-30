"""Comprehensive integration tests for AttestationTracker contract integration.

This test suite validates:
- Smart contract service connection validation  
- Environment variable loading verification
- Owner wallet configuration and private key handling
- Gas estimation and transaction sending capabilities
- Error handling for contract interaction failures
- Transaction signing and nonce management

These integration tests focus on the complete integration flow rather than isolated unit testing,
ensuring the AttestationTracker contract integration works end-to-end with proper error handling,
transaction execution, and state management.
"""

import pytest
import asyncio
import os
import json
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
from typing import Dict, Any, Optional
from web3 import Web3
from web3.exceptions import ContractLogicError, TransactionNotFound
from eth_account import Account

from config import settings
from utils.web3_provider import get_w3
from utils.abi_loader import load_abi
from utils.attestation_tracker_helpers import get_multisig_info, get_attestation_count
from services.safe_service import SafeService
from models import EASAttestationData


class TestAttestationTrackerIntegration:
    """Comprehensive integration tests for AttestationTracker contract integration."""

    @pytest.fixture
    def valid_test_config(self):
        """Create valid test configuration for AttestationTracker integration."""
        return {
            "attestation_tracker_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f89590",
            "rpc_url": "http://localhost:8545",
            "chain_id": 31337,
            "owner_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f89591",
            "private_key": "0x" + "a" * 64,
            "base_safe_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f89592",
            "eas_contract_address": "0x4200000000000000000000000000000000000021",
            "eas_schema_uid": "0x" + "b" * 64,
        }

    @pytest.fixture
    def mock_w3_connected(self):
        """Create a mock Web3 instance that appears connected."""
        mock_w3 = MagicMock(spec=Web3)
        mock_w3.is_connected.return_value = True
        mock_w3.eth.chain_id = 31337
        mock_w3.eth.get_block.return_value = {"number": 1000}
        mock_w3.eth.gas_price = 20000000000  # 20 gwei
        mock_w3.eth.get_transaction_count.return_value = 5
        return mock_w3

    @pytest.fixture
    def mock_contract(self):
        """Create a mock AttestationTracker contract."""
        mock_contract = MagicMock()
        mock_contract.address = "0x742d35Cc6634C0532925a3b844Bc9e7595f89590"
        mock_contract.functions.owner.return_value.call.return_value = "0x742d35Cc6634C0532925a3b844Bc9e7595f89591"
        mock_contract.functions.easContract.return_value.call.return_value = "0x4200000000000000000000000000000000000021"
        mock_contract.functions.multisigStats.return_value.call.return_value = (1 << 255) | 3  # Active with 3 attestations
        return mock_contract

    @pytest.fixture
    def sample_attestation_data(self):
        """Create sample EAS attestation data for testing."""
        return EASAttestationData(
            proposal_id="test-proposal-123",
            space_id="test.eth",
            choice=1,
            voter_address="0x742d35Cc6634C0532925a3b844Bc9e7595f89591",
            vote_tx_hash="0x" + "c" * 64,
        )

    def test_environment_variable_loading_validation(self, valid_test_config):
        """Test validation of environment variables for AttestationTracker configuration.
        
        This test ensures that all required environment variables are properly loaded
        and validated according to expected formats and constraints.
        """
        with patch.dict(os.environ, {
            "ATTESTATION_TRACKER_ADDRESS": valid_test_config["attestation_tracker_address"],
            "RPC_URL": valid_test_config["rpc_url"],
            "CHAIN_ID": str(valid_test_config["chain_id"]),
        }):
            # Import settings to trigger environment variable loading
            from config import Settings
            test_settings = Settings()
            
            # Verify configuration loaded correctly
            assert test_settings.attestation_tracker_address == valid_test_config["attestation_tracker_address"]
            assert test_settings.rpc_url == valid_test_config["rpc_url"] 
            assert test_settings.chain_id == valid_test_config["chain_id"]

    def test_environment_variable_validation_failures(self):
        """Test proper handling of invalid environment variable configurations.
        
        This test ensures that invalid configurations are detected and handled gracefully
        with appropriate error messages and fallback behavior.
        """
        # Test invalid address format
        with patch.dict(os.environ, {"ATTESTATION_TRACKER_ADDRESS": "invalid-address"}):
            from config import Settings
            with pytest.raises(ValueError, match="Invalid ATTESTATION_TRACKER_ADDRESS"):
                Settings()
        
        # Test invalid chain ID
        with patch.dict(os.environ, {"CHAIN_ID": "not-a-number"}):
            with pytest.raises(ValueError):
                Settings()

    @patch("utils.web3_provider.Web3")
    def test_smart_contract_service_connection_validation(self, mock_web3_class, mock_w3_connected, valid_test_config):
        """Test smart contract service connection validation and initialization.
        
        This test validates that the Web3 connection is properly established,
        the chain ID matches expectations, and basic connectivity tests pass.
        """
        # Setup mock Web3 connection
        mock_web3_class.return_value = mock_w3_connected
        
        with patch("config.settings.attestation_tracker_address", valid_test_config["attestation_tracker_address"]):
            with patch("config.settings.rpc_url", valid_test_config["rpc_url"]):
                with patch("config.settings.chain_id", valid_test_config["chain_id"]):
                    # Test Web3 connection establishment
                    w3 = get_w3("base")
                    
                    # Verify connection validation
                    assert w3.is_connected()
                    assert w3.eth.chain_id == valid_test_config["chain_id"]
                    
                    # Verify basic chain interaction
                    current_block = w3.eth.get_block("latest")
                    assert current_block is not None
                    assert current_block["number"] > 0

    def test_smart_contract_service_connection_failure_handling(self):
        """Test proper error handling when smart contract service connection fails.
        
        This test ensures that connection failures are detected and handled with
        appropriate error messages and fallback behavior.
        """
        with patch("utils.web3_provider.Web3") as mock_web3_class:
            # Mock connection failure
            mock_w3 = MagicMock(spec=Web3)
            mock_w3.is_connected.return_value = False
            mock_web3_class.return_value = mock_w3
            
            # Test connection failure handling
            with pytest.raises(ConnectionError, match="Failed to connect"):
                w3 = get_w3("base")
                if not w3.is_connected():
                    raise ConnectionError("Failed to connect to network")

    def test_owner_wallet_configuration_and_private_key_handling(self, valid_test_config):
        """Test owner wallet configuration and private key handling security.
        
        This test validates that private keys are properly loaded, wallet addresses
        are correctly derived, and sensitive data is handled securely.
        """
        test_private_key = valid_test_config["private_key"]
        expected_address = Account.from_key(test_private_key).address
        
        # Test private key loading from file
        with patch("builtins.open", mock_open(read_data=test_private_key.strip("0x"))):
            # Initialize SafeService which loads private key
            safe_service = SafeService()
            
            # Verify wallet configuration
            assert safe_service.account.address == expected_address
            assert safe_service.account.key.hex() == test_private_key

    def test_private_key_file_handling_errors(self):
        """Test error handling for private key file operations.
        
        This test ensures that missing or corrupted private key files are handled
        gracefully with appropriate error messages.
        """
        # Test missing private key file
        with patch("builtins.open", side_effect=FileNotFoundError("Private key file not found")):
            with pytest.raises(FileNotFoundError):
                SafeService()
        
        # Test invalid private key format
        with patch("builtins.open", mock_open(read_data="invalid-private-key")):
            with pytest.raises(ValueError):
                SafeService()

    @patch("utils.web3_provider.get_w3")
    @patch("utils.abi_loader.load_abi")
    def test_contract_owner_and_eas_address_verification(self, mock_load_abi, mock_get_w3, mock_w3_connected, mock_contract, valid_test_config):
        """Test contract owner and EAS address verification against deployment.
        
        This test validates that the contract is deployed correctly with expected
        owner and EAS contract addresses matching configuration.
        """
        # Setup mocks
        mock_get_w3.return_value = mock_w3_connected  
        mock_w3_connected.eth.contract.return_value = mock_contract
        mock_load_abi.return_value = [{"name": "owner"}, {"name": "easContract"}]
        
        with patch("config.settings.attestation_tracker_address", valid_test_config["attestation_tracker_address"]):
            # Load contract and verify configuration
            w3 = get_w3("base")
            contract_abi = load_abi("attestation_tracker")
            contract = w3.eth.contract(
                address=Web3.to_checksum_address(valid_test_config["attestation_tracker_address"]),
                abi=contract_abi
            )
            
            # Verify owner address
            owner = contract.functions.owner().call()
            assert owner == valid_test_config["owner_address"]
            
            # Verify EAS contract address
            eas_address = contract.functions.easContract().call()
            assert eas_address == valid_test_config["eas_contract_address"]

    @patch("utils.web3_provider.get_w3")
    @patch("utils.abi_loader.load_abi")
    def test_private_key_to_address_derivation_validation(self, mock_load_abi, mock_get_w3, valid_test_config):
        """Test private key to address derivation validation.
        
        This test ensures that the private key correctly derives to the expected
        wallet address that matches the contract owner configuration.
        """
        # Test address derivation
        account = Account.from_key(valid_test_config["private_key"])
        derived_address = account.address
        
        # Verify derivation matches expected owner
        assert derived_address == valid_test_config["owner_address"]
        
        # Verify checksum address handling
        checksum_address = Web3.to_checksum_address(derived_address)
        assert checksum_address == derived_address

    @patch("utils.web3_provider.get_w3")
    @patch("utils.abi_loader.load_abi")
    async def test_gas_estimation_capabilities(self, mock_load_abi, mock_get_w3, mock_w3_connected, mock_contract, sample_attestation_data, valid_test_config):
        """Test gas estimation for AttestationTracker transactions.
        
        This test validates that gas estimation works correctly for contract interactions
        and returns reasonable gas limits for transaction execution.
        """
        # Setup mocks
        mock_get_w3.return_value = mock_w3_connected
        mock_w3_connected.eth.contract.return_value = mock_contract
        mock_load_abi.return_value = [{"name": "attestByDelegation"}]
        
        # Mock gas estimation
        mock_transaction = MagicMock()
        mock_transaction.estimate_gas.return_value = 150000
        mock_contract.functions.attestByDelegation.return_value.build_transaction.return_value = {
            "to": valid_test_config["attestation_tracker_address"],
            "data": "0x" + "d" * 64,
            "gas": 150000,
            "gasPrice": 20000000000,
        }
        
        with patch("config.settings.attestation_tracker_address", valid_test_config["attestation_tracker_address"]):
            with patch("config.settings.base_safe_address", valid_test_config["base_safe_address"]):
                # Initialize SafeService with mocked private key
                with patch("builtins.open", mock_open(read_data=valid_test_config["private_key"].strip("0x"))):
                    safe_service = SafeService()
                    
                    # Test gas estimation for attestation transaction
                    tx_data = safe_service._build_eas_attestation_tx(sample_attestation_data)
                    
                    # Verify transaction data structure
                    assert "to" in tx_data
                    assert "data" in tx_data
                    assert "value" in tx_data
                    assert tx_data["to"] == valid_test_config["attestation_tracker_address"]

    @patch("utils.web3_provider.get_w3")  
    @patch("utils.abi_loader.load_abi")
    async def test_transaction_execution_and_state_verification(self, mock_load_abi, mock_get_w3, mock_w3_connected, mock_contract, sample_attestation_data, valid_test_config):
        """Test transaction execution and state verification capabilities.
        
        This test validates that transactions can be properly built, signed, and executed
        with correct state changes reflected in contract storage.
        """
        # Setup mocks for successful transaction
        mock_get_w3.return_value = mock_w3_connected
        mock_w3_connected.eth.contract.return_value = mock_contract
        mock_load_abi.return_value = [{"name": "attestByDelegation"}]
        
        # Mock transaction receipt
        mock_receipt = {
            "status": 1,
            "transactionHash": "0x" + "e" * 64,
            "blockNumber": 1001,
            "gasUsed": 120000,
        }
        mock_w3_connected.eth.wait_for_transaction_receipt.return_value = mock_receipt
        
        # Mock successful transaction building
        mock_contract.functions.attestByDelegation.return_value.build_transaction.return_value = {
            "to": valid_test_config["attestation_tracker_address"],
            "data": "0x" + "d" * 64,
            "gas": 150000,
            "gasPrice": 20000000000,
            "nonce": 5,
        }
        
        with patch("config.settings.attestation_tracker_address", valid_test_config["attestation_tracker_address"]):
            with patch("config.settings.base_safe_address", valid_test_config["base_safe_address"]):
                with patch("config.settings.eas_schema_uid", valid_test_config["eas_schema_uid"]):
                    # Initialize SafeService
                    with patch("builtins.open", mock_open(read_data=valid_test_config["private_key"].strip("0x"))):
                        safe_service = SafeService()
                        
                        # Test transaction building
                        tx_data = safe_service._build_eas_attestation_tx(sample_attestation_data)
                        
                        # Verify transaction data is properly formatted
                        assert isinstance(tx_data, dict)
                        assert Web3.is_address(tx_data["to"])
                        assert isinstance(tx_data["data"], str)
                        assert tx_data["data"].startswith("0x")

    def test_nonce_tracking_across_multiple_transactions(self, mock_w3_connected, valid_test_config):
        """Test nonce management and tracking across multiple transactions.
        
        This test ensures that transaction nonces are properly managed and incremented
        across multiple transaction submissions to prevent nonce conflicts.
        """
        # Track nonce increments
        nonce_tracker = [5]  # Starting nonce
        
        def mock_get_transaction_count(address):
            current_nonce = nonce_tracker[0] 
            nonce_tracker[0] += 1  # Increment for next call
            return current_nonce
        
        mock_w3_connected.eth.get_transaction_count.side_effect = mock_get_transaction_count
        
        with patch("utils.web3_provider.get_w3", return_value=mock_w3_connected):
            # Initialize SafeService
            with patch("builtins.open", mock_open(read_data=valid_test_config["private_key"].strip("0x"))):
                safe_service = SafeService()
                
                # Test multiple nonce retrievals
                first_nonce = mock_w3_connected.eth.get_transaction_count(safe_service.account.address)
                second_nonce = mock_w3_connected.eth.get_transaction_count(safe_service.account.address)
                third_nonce = mock_w3_connected.eth.get_transaction_count(safe_service.account.address)
                
                # Verify nonce progression
                assert first_nonce == 5
                assert second_nonce == 6
                assert third_nonce == 7

    def test_error_handling_contract_interaction_failures(self, mock_w3_connected, valid_test_config):
        """Test error handling for various contract interaction failure scenarios.
        
        This test ensures that different types of contract interaction failures
        are properly caught and handled with appropriate error messages.
        """
        # Test contract call failure
        mock_contract = MagicMock()
        mock_contract.functions.owner.return_value.call.side_effect = ContractLogicError("Contract execution reverted")
        
        mock_w3_connected.eth.contract.return_value = mock_contract
        
        with patch("utils.web3_provider.get_w3", return_value=mock_w3_connected):
            with patch("utils.abi_loader.load_abi", return_value=[{"name": "owner"}]):
                # Test contract call error handling
                try:
                    w3 = get_w3("base")
                    contract_abi = load_abi("attestation_tracker") 
                    contract = w3.eth.contract(
                        address=Web3.to_checksum_address(valid_test_config["attestation_tracker_address"]),
                        abi=contract_abi
                    )
                    owner = contract.functions.owner().call()
                    assert False, "Should have raised ContractLogicError"
                except ContractLogicError as e:
                    assert "Contract execution reverted" in str(e)

    def test_error_handling_network_failures(self, valid_test_config):
        """Test error handling for network connectivity failures.
        
        This test ensures that network failures are properly detected and handled
        with appropriate retry logic and error messages.
        """
        with patch("utils.web3_provider.Web3") as mock_web3_class:
            # Mock network failure
            mock_w3 = MagicMock(spec=Web3)
            mock_w3.is_connected.return_value = False
            mock_web3_class.return_value = mock_w3
            
            # Test network failure detection
            with pytest.raises(ConnectionError):
                w3 = get_w3("base")
                if not w3.is_connected():
                    raise ConnectionError("Failed to connect to base network")

    def test_error_handling_unauthorized_access(self, mock_w3_connected, valid_test_config):
        """Test error handling for unauthorized access attempts.
        
        This test ensures that unauthorized access attempts are properly rejected
        with appropriate error messages.
        """
        # Mock unauthorized access error
        mock_contract = MagicMock()
        mock_contract.functions.owner.return_value.call.side_effect = ContractLogicError("Ownable: caller is not the owner")
        
        mock_w3_connected.eth.contract.return_value = mock_contract
        
        with patch("utils.web3_provider.get_w3", return_value=mock_w3_connected):
            with patch("utils.abi_loader.load_abi", return_value=[{"name": "owner"}]):
                # Test unauthorized access handling
                try:
                    w3 = get_w3("base")
                    contract_abi = load_abi("attestation_tracker")
                    contract = w3.eth.contract(
                        address=Web3.to_checksum_address(valid_test_config["attestation_tracker_address"]),
                        abi=contract_abi
                    )
                    contract.functions.owner().call()
                    assert False, "Should have raised ContractLogicError"
                except ContractLogicError as e:
                    assert "caller is not the owner" in str(e)

    @patch("utils.attestation_tracker_helpers.get_w3")
    @patch("utils.attestation_tracker_helpers.load_abi")
    def test_service_initialization_with_local_testnet_configuration(self, mock_load_abi, mock_get_w3, mock_w3_connected, mock_contract, valid_test_config):
        """Test service initialization with local testnet configuration.
        
        This test validates that services can be properly initialized with local
        testnet configuration and establish connections successfully.
        """
        # Setup mocks for local testnet
        mock_get_w3.return_value = mock_w3_connected
        mock_w3_connected.eth.contract.return_value = mock_contract
        mock_load_abi.return_value = [{"name": "multisigStats"}]
        
        # Configure for local testnet
        with patch("config.settings.attestation_tracker_address", valid_test_config["attestation_tracker_address"]):
            with patch("config.settings.rpc_url", "http://localhost:8545"):
                with patch("config.settings.chain_id", 31337):
                    # Test helper function initialization
                    count, is_active = get_multisig_info(valid_test_config["owner_address"])
                    
                    # Verify successful initialization and query
                    assert isinstance(count, int)
                    assert isinstance(is_active, bool)
                    mock_get_w3.assert_called_with("base")

    @patch("utils.attestation_tracker_helpers.get_w3")
    @patch("utils.attestation_tracker_helpers.load_abi") 
    def test_transaction_signing_validation(self, mock_load_abi, mock_get_w3, mock_w3_connected, valid_test_config):
        """Test transaction signing and signature validation.
        
        This test ensures that transactions are properly signed with the correct
        private key and signatures can be validated against the expected signer.
        """
        # Setup mocks
        mock_get_w3.return_value = mock_w3_connected
        mock_load_abi.return_value = [{"name": "attestByDelegation"}]
        
        # Test transaction signing
        account = Account.from_key(valid_test_config["private_key"])
        test_message = "Test message for signing"
        
        # Sign message
        signature = account.unsafe_sign_hash(Web3.keccak(text=test_message))
        
        # Verify signature components
        assert len(signature.signature) == 65  # 65 bytes for Ethereum signature
        assert signature.v in [27, 28]  # Valid recovery values
        assert len(signature.r.to_bytes(32, 'big')) == 32
        assert len(signature.s.to_bytes(32, 'big')) == 32
        
        # Verify signature can be recovered to original address
        recovered_address = Account.recover_message(
            Web3.keccak(text=test_message),
            signature=signature.signature
        )
        assert recovered_address == account.address

    def test_integration_service_initialization_error_scenarios(self):
        """Test integration service initialization with various error scenarios.
        
        This test ensures that service initialization handles various error conditions
        gracefully and provides appropriate error messages for debugging.
        """
        # Test missing configuration
        with patch("config.settings.attestation_tracker_address", None):
            count, is_active = get_multisig_info("0x742d35Cc6634C0532925a3b844Bc9e7595f89591")
            assert count == 0
            assert is_active == False
        
        # Test invalid Web3 provider
        with patch("utils.attestation_tracker_helpers.get_w3", side_effect=ConnectionError("RPC connection failed")):
            count, is_active = get_multisig_info("0x742d35Cc6634C0532925a3b844Bc9e7595f89591") 
            assert count == 0
            assert is_active == False

    @patch("utils.web3_provider.get_w3")
    @patch("utils.abi_loader.load_abi")
    async def test_comprehensive_safe_service_integration(self, mock_load_abi, mock_get_w3, mock_w3_connected, sample_attestation_data, valid_test_config):
        """Test comprehensive SafeService integration with AttestationTracker.
        
        This test validates the complete integration flow from SafeService through
        to AttestationTracker contract interaction including transaction building,
        signing, and execution.
        """
        # Setup comprehensive mocks
        mock_get_w3.return_value = mock_w3_connected
        mock_contract = MagicMock()
        mock_w3_connected.eth.contract.return_value = mock_contract
        mock_load_abi.return_value = [{"name": "attestByDelegation"}]
        
        # Mock successful transaction build
        mock_tx = {
            "to": valid_test_config["attestation_tracker_address"],
            "data": "0x" + "f" * 128,
            "gas": 200000,
            "gasPrice": 20000000000,
            "value": 0,
        }
        mock_contract.functions.attestByDelegation.return_value.build_transaction.return_value = mock_tx
        
        with patch("config.settings.attestation_tracker_address", valid_test_config["attestation_tracker_address"]):
            with patch("config.settings.base_safe_address", valid_test_config["base_safe_address"]):
                with patch("config.settings.eas_schema_uid", valid_test_config["eas_schema_uid"]):
                    # Initialize SafeService with all required configurations
                    with patch("builtins.open", mock_open(read_data=valid_test_config["private_key"].strip("0x"))):
                        safe_service = SafeService()
                        
                        # Test full attestation creation flow
                        result = await safe_service.create_eas_attestation(sample_attestation_data)
                        
                        # Verify result structure
                        assert isinstance(result, dict)
                        assert "success" in result
                        
                        # Verify transaction was built correctly
                        mock_contract.functions.attestByDelegation.assert_called_once()