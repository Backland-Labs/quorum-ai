"""Unit tests for SafeService.

This test suite covers the SafeService class which handles multi-signature wallet
transactions across different blockchain networks.
"""

import json
import pytest
import time
from unittest.mock import Mock, MagicMock, patch, mock_open, AsyncMock
from web3 import Web3
from eth_account import Account

from services.safe_service import SafeService, SAFE_SERVICE_URLS, EAS_ATTESTATION_GAS_LIMIT
from models import EASAttestationData


class TestSafeServiceInitialization:
    """Test SafeService initialization and configuration."""

    @patch("services.safe_service.setup_pearl_logger")
    @patch("builtins.open", new_callable=mock_open, read_data="ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")
    @patch("services.safe_service.settings")
    def test_init_with_valid_config(self, mock_settings, mock_file, mock_logger):
        """Test SafeService initialization with valid configuration."""
        mock_settings.safe_contract_addresses = '{"base": "0x123", "ethereum": "0x456"}'
        mock_settings.ethereum_ledger_rpc = "https://eth-rpc.com"
        mock_settings.gnosis_ledger_rpc = "https://gnosis-rpc.com"
        mock_settings.get_base_rpc_endpoint.return_value = "https://base-rpc.com"
        mock_settings.mode_ledger_rpc = "https://mode-rpc.com"
        
        service = SafeService()
        
        assert service.safe_addresses == {"base": "0x123", "ethereum": "0x456"}
        assert service.private_key == "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
        assert service.account.address is not None
        assert service._web3_connections == {}

    @patch("services.safe_service.setup_pearl_logger")
    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_init_missing_private_key_file(self, mock_file, mock_logger):
        """Test that SafeService raises error when private key file is missing."""
        with pytest.raises(FileNotFoundError):
            SafeService()

    @patch("services.safe_service.setup_pearl_logger")
    @patch("builtins.open", new_callable=mock_open, read_data="invalid_key")
    @patch("services.safe_service.settings")
    def test_init_with_invalid_private_key(self, mock_settings, mock_file, mock_logger):
        """Test SafeService initialization with invalid private key."""
        mock_settings.safe_contract_addresses = '{"base": "0x123"}'
        mock_settings.get_base_rpc_endpoint.return_value = "https://base-rpc.com"
        
        # Account.from_key should raise an error for invalid key format
        with pytest.raises(ValueError):
            SafeService()


class TestChainConfiguration:
    """Test chain configuration validation methods."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("services.safe_service.setup_pearl_logger"), \
             patch("builtins.open", new_callable=mock_open, read_data="0x" + "a" * 64), \
             patch("services.safe_service.settings") as mock_settings:
            mock_settings.safe_contract_addresses = '{"base": "0x123", "ethereum": "0x456"}'
            mock_settings.ethereum_ledger_rpc = "https://eth-rpc.com"
            mock_settings.gnosis_ledger_rpc = ""  # Missing RPC
            mock_settings.get_base_rpc_endpoint.return_value = "https://base-rpc.com"
            mock_settings.mode_ledger_rpc = "https://mode-rpc.com"
            self.service = SafeService()

    def test_is_chain_fully_configured_valid_chain(self):
        """Test that fully configured chains are detected correctly."""
        assert self.service.is_chain_fully_configured("base") is True
        assert self.service.is_chain_fully_configured("ethereum") is True

    def test_is_chain_fully_configured_missing_rpc(self):
        """Test that chains with missing RPC are not fully configured."""
        assert self.service.is_chain_fully_configured("gnosis") is False

    def test_is_chain_fully_configured_missing_safe_address(self):
        """Test that chains with missing Safe address are not fully configured."""
        assert self.service.is_chain_fully_configured("mode") is False

    def test_is_chain_fully_configured_unsupported_chain(self):
        """Test that unsupported chains are not fully configured."""
        assert self.service.is_chain_fully_configured("unknown_chain") is False

    def test_get_supported_chains(self):
        """Test getting list of supported chains."""
        supported = self.service.get_supported_chains()
        assert "base" in supported
        assert "ethereum" in supported
        assert "gnosis" not in supported  # Missing RPC
        assert "mode" not in supported  # Missing Safe address

    def test_validate_chain_configuration(self):
        """Test detailed chain configuration validation."""
        # Test fully configured chain
        validation = self.service.validate_chain_configuration("base")
        assert validation["chain"] == "base"
        assert validation["has_safe_address"] is True
        assert validation["has_rpc_endpoint"] is True
        assert validation["has_safe_service_url"] is True
        assert validation["is_fully_configured"] is True
        assert validation["safe_address"] == "0x123"

        # Test partially configured chain
        validation = self.service.validate_chain_configuration("gnosis")
        assert validation["chain"] == "gnosis"
        assert validation["has_safe_address"] is False
        assert validation["has_rpc_endpoint"] is False
        assert validation["has_safe_service_url"] is True
        assert validation["is_fully_configured"] is False


class TestWeb3Connection:
    """Test Web3 connection management."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("services.safe_service.setup_pearl_logger"), \
             patch("builtins.open", new_callable=mock_open, read_data="0x" + "a" * 64), \
             patch("services.safe_service.settings") as mock_settings:
            mock_settings.safe_contract_addresses = '{"base": "0x123"}'
            mock_settings.get_base_rpc_endpoint.return_value = "https://base-rpc.com"
            mock_settings.ethereum_ledger_rpc = "https://eth-rpc.com"
            mock_settings.gnosis_ledger_rpc = "https://gnosis-rpc.com"
            mock_settings.mode_ledger_rpc = "https://mode-rpc.com"
            self.service = SafeService()

    @patch("services.safe_service.Web3")
    def test_get_web3_connection_success(self, mock_web3_class):
        """Test successful Web3 connection."""
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3_class.return_value = mock_web3
        
        with patch.object(self.service, "_rate_limit_base_rpc"):
            w3 = self.service.get_web3_connection("base")
            
            assert w3 == mock_web3
            assert self.service._web3_connections["base"] == mock_web3

    @patch("services.safe_service.Web3")
    def test_get_web3_connection_cached(self, mock_web3_class):
        """Test that Web3 connections are cached."""
        mock_web3 = Mock()
        self.service._web3_connections["base"] = mock_web3
        
        w3 = self.service.get_web3_connection("base")
        
        assert w3 == mock_web3
        mock_web3_class.assert_not_called()

    def test_get_web3_connection_no_rpc(self):
        """Test Web3 connection with missing RPC endpoint."""
        with pytest.raises(ValueError, match="No RPC endpoint configured for chain: unknown"):
            self.service.get_web3_connection("unknown")

    @patch("services.safe_service.Web3")
    def test_get_web3_connection_failed(self, mock_web3_class):
        """Test Web3 connection failure."""
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = False
        mock_web3_class.return_value = mock_web3
        
        with patch.object(self.service, "_rate_limit_base_rpc"):
            with pytest.raises(ConnectionError, match="Failed to connect to base network"):
                self.service.get_web3_connection("base")

    @patch("services.safe_service.time.sleep")
    def test_rate_limit_base_rpc(self, mock_sleep):
        """Test rate limiting for Base mainnet RPC calls."""
        # Test with Base mainnet URL
        self.service._rate_limit_base_rpc("https://mainnet.base.org/rpc")
        mock_sleep.assert_called_once_with(1.0)
        
        # Test with non-Base URL
        mock_sleep.reset_mock()
        self.service._rate_limit_base_rpc("https://ethereum-rpc.com")
        mock_sleep.assert_not_called()


class TestChainSelection:
    """Test optimal chain selection logic."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("services.safe_service.setup_pearl_logger"), \
             patch("builtins.open", new_callable=mock_open, read_data="0x" + "a" * 64), \
             patch("services.safe_service.settings") as mock_settings:
            mock_settings.safe_contract_addresses = '{"base": "0x123", "ethereum": "0x456", "gnosis": "0x789"}'
            mock_settings.ethereum_ledger_rpc = "https://eth-rpc.com"
            mock_settings.gnosis_ledger_rpc = "https://gnosis-rpc.com"
            mock_settings.get_base_rpc_endpoint.return_value = "https://base-rpc.com"
            mock_settings.mode_ledger_rpc = "https://mode-rpc.com"
            self.service = SafeService()

    def test_select_optimal_chain_gnosis_preferred(self):
        """Test that Gnosis is selected as cheapest option when available."""
        chain = self.service.select_optimal_chain()
        assert chain == "gnosis"

    def test_select_optimal_chain_fallback_order(self):
        """Test chain selection fallback order."""
        # Mock gnosis as not fully configured
        with patch.object(self.service, "is_chain_fully_configured") as mock_config:
            mock_config.side_effect = lambda c: c in ["base", "ethereum"]
            
            chain = self.service.select_optimal_chain()
            assert chain == "base"  # Next in priority after gnosis

    def test_select_optimal_chain_no_valid_chains(self):
        """Test error when no valid chains are configured."""
        with patch.object(self.service, "get_supported_chains", return_value=[]):
            with pytest.raises(ValueError, match="No valid chain configuration found"):
                self.service.select_optimal_chain()


class TestSafeTransactionBuilding:
    """Test Safe transaction building functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("services.safe_service.setup_pearl_logger"), \
             patch("builtins.open", new_callable=mock_open, read_data="0x" + "a" * 64), \
             patch("services.safe_service.settings") as mock_settings:
            mock_settings.safe_contract_addresses = '{"base": "0x123"}'
            mock_settings.get_base_rpc_endpoint.return_value = "https://base-rpc.com"
            mock_settings.ethereum_ledger_rpc = "https://eth-rpc.com"
            mock_settings.gnosis_ledger_rpc = "https://gnosis-rpc.com"
            mock_settings.mode_ledger_rpc = "https://mode-rpc.com"
            self.service = SafeService()

    @patch("services.safe_service.EthereumClient")
    @patch("services.safe_service.Safe")
    async def test_build_safe_transaction(self, mock_safe_class, mock_eth_client):
        """Test building a Safe transaction."""
        # Mock Safe instance and transaction
        mock_safe_tx = Mock()
        mock_safe_tx.to = "0x456"
        mock_safe_tx.value = 100
        mock_safe_tx.data = b"test_data"
        mock_safe_tx.operation = 0
        mock_safe_tx.safe_tx_gas = 100000
        mock_safe_tx.base_gas = 50000
        mock_safe_tx.gas_price = 1000000000
        mock_safe_tx.gas_token = "0x0000000000000000000000000000000000000000"
        mock_safe_tx.refund_receiver = "0x0000000000000000000000000000000000000000"
        mock_safe_tx.safe_nonce = 5
        mock_safe_tx.safe_tx_hash.hex.return_value = "0xabcd"
        
        mock_safe = Mock()
        mock_safe.build_multisig_tx.return_value = mock_safe_tx
        mock_safe_class.return_value = mock_safe

        with patch.object(self.service, "_rate_limit_base_rpc"):
            result = await self.service.build_safe_transaction(
                chain="base",
                to="0x456",
                value=100,
                data=b"test_data"
            )

        assert result["safe_address"] == "0x123"
        assert result["to"] == "0x456"
        assert result["value"] == 100
        assert result["data"] == "test_data".encode().hex()
        assert result["nonce"] == 5

    async def test_build_safe_transaction_no_safe_address(self):
        """Test building transaction with missing Safe address."""
        with pytest.raises(ValueError, match="No Safe address configured for chain: unknown"):
            await self.service.build_safe_transaction(
                chain="unknown",
                to="0x456"
            )

    @patch("services.safe_service.EthereumClient")
    @patch("services.safe_service.Safe")
    async def test_get_safe_nonce(self, mock_safe_class, mock_eth_client):
        """Test getting Safe nonce."""
        mock_safe = Mock()
        mock_safe.retrieve_nonce.return_value = 10
        mock_safe_class.return_value = mock_safe

        with patch.object(self.service, "_rate_limit_base_rpc"):
            nonce = await self.service.get_safe_nonce("base", "0x123")
            
        assert nonce == 10
        mock_safe.retrieve_nonce.assert_called_once()


class TestSafeTransactionSubmission:
    """Test Safe transaction submission functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("services.safe_service.setup_pearl_logger"), \
             patch("builtins.open", new_callable=mock_open, read_data="0x" + "a" * 64), \
             patch("services.safe_service.settings") as mock_settings:
            mock_settings.safe_contract_addresses = '{"base": "0x123"}'
            mock_settings.get_base_rpc_endpoint.return_value = "https://base-rpc.com"
            mock_settings.ethereum_ledger_rpc = "https://eth-rpc.com"
            mock_settings.gnosis_ledger_rpc = "https://gnosis-rpc.com"
            mock_settings.mode_ledger_rpc = "https://mode-rpc.com"
            self.service = SafeService()

    async def test_submit_safe_transaction_invalid_inputs(self):
        """Test transaction submission with invalid inputs."""
        # Test invalid chain
        result = await self.service._submit_safe_transaction(
            chain="",
            to="0x456",
            value=0,
            data=b""
        )
        assert result["success"] is False
        assert "Chain must be a non-empty string" in result["error"]

        # Test invalid to address
        result = await self.service._submit_safe_transaction(
            chain="base",
            to="",
            value=0,
            data=b""
        )
        assert result["success"] is False
        assert "To address must be a non-empty string" in result["error"]

        # Test invalid value
        result = await self.service._submit_safe_transaction(
            chain="base",
            to="0x456",
            value=-1,
            data=b""
        )
        assert result["success"] is False
        assert "Value must be a non-negative integer" in result["error"]

        # Test invalid data type
        result = await self.service._submit_safe_transaction(
            chain="base",
            to="0x456",
            value=0,
            data="not_bytes"
        )
        assert result["success"] is False
        assert "Data must be bytes" in result["error"]

    async def test_submit_safe_transaction_unconfigured_chain(self):
        """Test transaction submission with unconfigured chain."""
        result = await self.service._submit_safe_transaction(
            chain="unknown",
            to="0x456",
            value=0,
            data=b""
        )
        assert result["success"] is False
        assert "not fully configured" in result["error"]

    @patch("services.safe_service.EthereumClient")
    @patch("services.safe_service.Safe")
    @patch("services.safe_service.TransactionServiceApi")
    async def test_submit_safe_transaction_success(self, mock_tx_service, mock_safe_class, mock_eth_client):
        """Test successful Safe transaction submission."""
        # Mock transaction receipt
        mock_receipt = {
            "blockNumber": 12345,
            "gasUsed": 100000,
            "status": 1
        }
        
        # Mock Web3 connection
        mock_w3 = Mock()
        mock_w3.eth.wait_for_transaction_receipt.return_value = mock_receipt
        
        # Mock Safe transaction
        mock_safe_tx = Mock()
        mock_safe_tx.to = "0x456"
        mock_safe_tx.value = 0
        mock_safe_tx.data = b""
        mock_safe_tx.operation = 0
        mock_safe_tx.safe_tx_gas = 100000
        mock_safe_tx.base_gas = 50000
        mock_safe_tx.gas_price = 1000000000
        mock_safe_tx.gas_token = "0x0000000000000000000000000000000000000000"
        mock_safe_tx.refund_receiver = "0x0000000000000000000000000000000000000000"
        mock_safe_tx.safe_nonce = 5
        mock_safe_tx.safe_tx_hash.hex.return_value = "0xsafetx"
        mock_safe_tx.signatures = b"signature"
        mock_safe_tx.call = Mock()  # Simulation succeeds
        
        # Mock Safe instance
        mock_safe = Mock()
        mock_safe.build_multisig_tx.return_value = mock_safe_tx
        mock_tx_hash = Mock()
        mock_tx_hash.hex.return_value = "0xtxhash"
        mock_safe.send_multisig_tx.return_value.tx_hash = mock_tx_hash
        mock_safe_class.return_value = mock_safe
        
        with patch.object(self.service, "get_web3_connection", return_value=mock_w3), \
             patch.object(self.service, "_rate_limit_base_rpc"):
            
            result = await self.service._submit_safe_transaction(
                chain="base",
                to="0x456",
                value=0,
                data=b""
            )

        assert result["success"] is True
        assert result["tx_hash"] == "0xtxhash"
        assert result["chain"] == "base"
        assert result["block_number"] == 12345
        assert result["gas_used"] == 100000

    @patch("services.safe_service.EthereumClient")
    @patch("services.safe_service.Safe")
    @patch("services.safe_service.TransactionServiceApi")
    async def test_submit_safe_transaction_simulation_failure(self, mock_tx_service, mock_safe_class, mock_eth_client):
        """Test transaction submission with simulation failure."""
        # Mock Web3 connection
        mock_w3 = Mock()
        
        # Mock Safe transaction that fails simulation
        mock_safe_tx = Mock()
        mock_safe_tx.to = "0x456"
        mock_safe_tx.value = 0
        mock_safe_tx.data = b""
        mock_safe_tx.operation = 0
        mock_safe_tx.safe_tx_gas = 100000
        mock_safe_tx.base_gas = 50000
        mock_safe_tx.gas_price = 1000000000
        mock_safe_tx.gas_token = "0x0000000000000000000000000000000000000000"
        mock_safe_tx.refund_receiver = "0x0000000000000000000000000000000000000000"
        mock_safe_tx.safe_nonce = 5
        mock_safe_tx.safe_tx_hash.hex.return_value = "0xsafetx"
        mock_safe_tx.signatures = b"signature"
        mock_safe_tx.call.side_effect = Exception("Execution reverted")
        
        # Mock Safe instance
        mock_safe = Mock()
        mock_safe.build_multisig_tx.return_value = mock_safe_tx
        mock_safe_class.return_value = mock_safe
        
        with patch.object(self.service, "get_web3_connection", return_value=mock_w3), \
             patch.object(self.service, "_rate_limit_base_rpc"):
            
            result = await self.service._submit_safe_transaction(
                chain="base",
                to="0x456",
                value=0,
                data=b""
            )

        assert result["success"] is False
        assert "Transaction would revert" in result["error"]
        assert result["simulation_failed"] is True


class TestActivityTransaction:
    """Test activity transaction functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("services.safe_service.setup_pearl_logger"), \
             patch("builtins.open", new_callable=mock_open, read_data="0x" + "a" * 64), \
             patch("services.safe_service.settings") as mock_settings:
            mock_settings.safe_contract_addresses = '{"base": "0x123"}'
            mock_settings.get_base_rpc_endpoint.return_value = "https://base-rpc.com"
            mock_settings.ethereum_ledger_rpc = "https://eth-rpc.com"
            mock_settings.gnosis_ledger_rpc = "https://gnosis-rpc.com"
            mock_settings.mode_ledger_rpc = "https://mode-rpc.com"
            self.service = SafeService()

    async def test_perform_activity_transaction_auto_chain(self):
        """Test activity transaction with automatic chain selection."""
        with patch.object(self.service, "select_optimal_chain", return_value="base"), \
             patch.object(self.service, "_submit_safe_transaction", new_callable=AsyncMock) as mock_submit:
            
            mock_submit.return_value = {"success": True, "tx_hash": "0xtest"}
            
            result = await self.service.perform_activity_transaction()
            
            mock_submit.assert_called_once_with(
                chain="base",
                to="0x123",  # Safe address
                value=0,
                data=b"",
                operation=0
            )
            assert result["success"] is True

    async def test_perform_activity_transaction_specific_chain(self):
        """Test activity transaction with specific chain."""
        with patch.object(self.service, "_submit_safe_transaction", new_callable=AsyncMock) as mock_submit:
            mock_submit.return_value = {"success": True, "tx_hash": "0xtest"}
            
            result = await self.service.perform_activity_transaction(chain="base")
            
            mock_submit.assert_called_once_with(
                chain="base",
                to="0x123",
                value=0,
                data=b"",
                operation=0
            )

    async def test_perform_activity_transaction_no_safe_address(self):
        """Test activity transaction with missing Safe address."""
        result = await self.service.perform_activity_transaction(chain="unknown")
        
        assert result["success"] is False
        assert "No Safe address configured" in result["error"]


class TestEASAttestation:
    """Test EAS attestation functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("services.safe_service.setup_pearl_logger"), \
             patch("builtins.open", new_callable=mock_open, read_data="0x" + "a" * 64), \
             patch("services.safe_service.settings") as mock_settings:
            mock_settings.safe_contract_addresses = '{"base": "0x123"}'
            mock_settings.get_base_rpc_endpoint.return_value = "https://base-rpc.com"
            mock_settings.ethereum_ledger_rpc = "https://eth-rpc.com"
            mock_settings.gnosis_ledger_rpc = "https://gnosis-rpc.com"
            mock_settings.mode_ledger_rpc = "https://mode-rpc.com"
            mock_settings.eas_contract_address = "0xeas123"
            mock_settings.eas_schema_uid = "0x" + "a" * 64
            mock_settings.base_safe_address = "0x123"
            mock_settings.attestation_tracker_address = None
            mock_settings.attestation_chain = "base"
            self.service = SafeService()

    async def test_create_eas_attestation_missing_config(self):
        """Test EAS attestation creation with missing configuration."""
        attestation_data = EASAttestationData(
            agent="0x4567890123456789012345678901234567890123",
            space_id="test.eth", 
            proposal_id="prop123",
            vote_choice=1,
            snapshot_sig="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            timestamp=1234567890,
            run_id="run123",
            confidence=95
        )

        with patch("services.safe_service.settings") as mock_settings:
            mock_settings.eas_contract_address = None
            
            result = await self.service.create_eas_attestation(attestation_data)
            
        assert result["success"] is False
        assert "EAS configuration missing" in result["error"]

    async def test_create_eas_attestation_missing_safe_address(self):
        """Test EAS attestation creation with missing Safe address."""
        attestation_data = EASAttestationData(
            agent="0x4567890123456789012345678901234567890123",
            space_id="test.eth", 
            proposal_id="prop123",
            vote_choice=1,
            snapshot_sig="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            timestamp=1234567890,
            run_id="run123",
            confidence=95
        )

        with patch("services.safe_service.settings") as mock_settings:
            mock_settings.base_safe_address = None
            
            result = await self.service.create_eas_attestation(attestation_data)
            
        assert result["success"] is False
        assert "Base Safe address not configured" in result["error"]

    @patch("services.safe_service.get_w3")
    @patch("services.safe_service.load_abi")
    async def test_create_eas_attestation_success(self, mock_load_abi, mock_get_w3):
        """Test successful EAS attestation creation."""
        attestation_data = EASAttestationData(
            agent="0x4567890123456789012345678901234567890123",
            space_id="test.eth", 
            proposal_id="prop123",
            vote_choice=1,
            snapshot_sig="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            timestamp=1234567890,
            run_id="run123",
            confidence=95
        )

        # Mock Web3 and contract
        mock_w3 = Mock()
        mock_w3.eth.get_block.return_value = {"timestamp": 1234567900, "number": 12345}
        mock_w3.eth.chain_id = 8453
        mock_get_w3.return_value = mock_w3

        mock_contract = Mock()
        mock_contract.functions.attestByDelegation.return_value.build_transaction.return_value = {
            "to": "0xeas123",
            "data": "0xabcd",
            "value": 0,
            "gas": EAS_ATTESTATION_GAS_LIMIT
        }
        mock_w3.eth.contract.return_value = mock_contract

        mock_load_abi.return_value = []

        with patch.object(self.service, "_build_eas_attestation_tx") as mock_build_tx, \
             patch.object(self.service, "_submit_safe_transaction", new_callable=AsyncMock) as mock_submit:
            
            mock_build_tx.return_value = {
                "to": "0xeas123",
                "data": "0xabcd",
                "value": 0
            }
            mock_submit.return_value = {"success": True, "tx_hash": "0xtxhash"}
            
            result = await self.service.create_eas_attestation(attestation_data)
            
        assert result["success"] is True
        assert result["safe_tx_hash"] == "0xtxhash"
        mock_submit.assert_called_once()

    def test_encode_attestation_data(self):
        """Test attestation data encoding."""
        attestation_data = EASAttestationData(
            agent="0x4567890123456789012345678901234567890123",
            space_id="test.eth", 
            proposal_id="prop123",
            vote_choice=1,
            snapshot_sig="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            timestamp=1234567890,
            run_id="run123",
            confidence=95
        )

        encoded = self.service._encode_attestation_data(attestation_data)
        
        assert isinstance(encoded, bytes)
        assert len(encoded) > 0

    @patch("services.safe_service.generate_eas_delegated_signature")
    @patch("services.safe_service.get_w3")
    @patch("services.safe_service.load_abi")
    @patch("builtins.open", new_callable=mock_open, read_data="0x" + "a" * 64)
    def test_build_delegated_attestation_tx_eip712proxy(self, mock_file, mock_load_abi, mock_get_w3, mock_generate_sig):
        """Test building delegated attestation transaction for EIP712Proxy."""
        attestation_data = EASAttestationData(
            agent="0x4567890123456789012345678901234567890123",
            space_id="test.eth", 
            proposal_id="prop123",
            vote_choice=1,
            snapshot_sig="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            timestamp=1234567890,
            run_id="run123",
            confidence=95
        )

        # Mock Web3 and contract
        mock_w3 = Mock()
        mock_w3.eth.get_block.return_value = {"timestamp": 1234567900, "number": 12345}
        mock_get_w3.return_value = mock_w3

        mock_contract = Mock()
        mock_contract.functions.attestByDelegation.return_value.build_transaction.return_value = {
            "to": "0xeas123",
            "data": "0xabcd",
            "value": 0
        }
        mock_w3.eth.contract.return_value = mock_contract

        mock_load_abi.return_value = []
        mock_generate_sig.return_value = b"\x01" * 65  # 65-byte signature

        result = self.service._build_delegated_attestation_tx(
            attestation_data,
            target_address="0xeas123",
            abi_name="eip712proxy"
        )

        assert result["to"] == "0xeas123"
        assert result["data"] == "0xabcd"
        assert result["value"] == 0

    @patch("services.safe_service.generate_eas_delegated_signature")
    @patch("services.safe_service.get_w3")
    @patch("services.safe_service.load_abi")
    @patch("builtins.open", new_callable=mock_open, read_data="0x" + "a" * 64)
    def test_build_delegated_attestation_tx_attestation_tracker(self, mock_file, mock_load_abi, mock_get_w3, mock_generate_sig):
        """Test building delegated attestation transaction for AttestationTracker."""
        attestation_data = EASAttestationData(
            agent="0x4567890123456789012345678901234567890123",
            space_id="test.eth", 
            proposal_id="prop123",
            vote_choice=1,
            snapshot_sig="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            timestamp=1234567890,
            run_id="run123",
            confidence=95
        )

        # Mock Web3 and contract
        mock_w3 = Mock()
        mock_w3.eth.get_block.return_value = {"timestamp": 1234567900, "number": 12345}
        mock_get_w3.return_value = mock_w3

        mock_contract = Mock()
        mock_contract.functions.attestByDelegation.return_value.build_transaction.return_value = {
            "to": "0xtracker123",
            "data": "0xefgh",
            "value": 0
        }
        mock_w3.eth.contract.return_value = mock_contract

        mock_load_abi.return_value = []
        mock_generate_sig.return_value = b"\x01" * 65  # 65-byte signature

        result = self.service._build_delegated_attestation_tx(
            attestation_data,
            target_address="0xtracker123",
            abi_name="attestation_tracker"
        )

        assert result["to"] == "0xtracker123"
        assert result["data"] == "0xefgh"
        assert result["value"] == 0


class TestUtilityMethods:
    """Test utility methods in SafeService."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("services.safe_service.setup_pearl_logger"), \
             patch("builtins.open", new_callable=mock_open, read_data="0x" + "a" * 64), \
             patch("services.safe_service.settings") as mock_settings:
            mock_settings.safe_contract_addresses = '{"base": "0x123"}'
            mock_settings.get_base_rpc_endpoint.return_value = "https://base-rpc.com"
            mock_settings.ethereum_ledger_rpc = "https://eth-rpc.com"
            mock_settings.gnosis_ledger_rpc = "https://gnosis-rpc.com"
            mock_settings.mode_ledger_rpc = "https://mode-rpc.com"
            self.service = SafeService()

    @patch("services.safe_service.Web3")
    def test_get_web3_instance(self, mock_web3_class):
        """Test getting Web3 instance for specific chain."""
        mock_web3 = Mock()
        mock_web3_class.return_value = mock_web3
        
        with patch.object(self.service, "_rate_limit_base_rpc"):
            result = self.service._get_web3_instance("base")
            
        assert result == mock_web3
        mock_web3_class.assert_called_once()

    def test_get_web3_instance_no_rpc(self):
        """Test getting Web3 instance with missing RPC."""
        with pytest.raises(ValueError, match="No RPC endpoint configured for chain: unknown"):
            self.service._get_web3_instance("unknown")

    @patch("services.safe_service.generate_eas_delegated_signature")
    @patch("builtins.open", new_callable=mock_open, read_data="0xtest_key")
    def test_generate_eas_delegated_signature(self, mock_file, mock_generate_sig):
        """Test EAS delegated signature generation."""
        mock_w3 = Mock()
        mock_w3.eth.chain_id = 8453
        
        request_data = {
            "schema": b"\x01" * 32,
            "recipient": "0x456",
            "deadline": 1234567890
        }
        
        mock_generate_sig.return_value = b"\x01" * 65
        
        result = self.service._generate_eas_delegated_signature(
            request_data, mock_w3, "0xeas123"
        )
        
        assert result == b"\x01" * 65
        mock_generate_sig.assert_called_once_with(
            request_data=request_data,
            w3=mock_w3,
            eas_contract_address="0xeas123",
            private_key="0xtest_key"
        )


class TestConstantsAndConfiguration:
    """Test module constants and configuration."""

    def test_safe_service_urls(self):
        """Test that Safe service URLs are properly configured."""
        expected_chains = {"ethereum", "gnosis", "base", "mode"}
        assert set(SAFE_SERVICE_URLS.keys()) == expected_chains
        
        for chain, url in SAFE_SERVICE_URLS.items():
            assert url.startswith("https://")
            assert "safe-transaction" in url

    def test_eas_attestation_gas_limit(self):
        """Test that EAS attestation gas limit is reasonable."""
        assert EAS_ATTESTATION_GAS_LIMIT == 1000000
        assert EAS_ATTESTATION_GAS_LIMIT > 0