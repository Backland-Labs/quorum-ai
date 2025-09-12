"""Unit tests for SafeService.

This test suite covers the SafeService class which handles multi-signature wallet
transactions across different blockchain networks.
"""

import json
import pytest
import time
from unittest.mock import Mock, MagicMock, patch, mock_open, AsyncMock


class MockHash(bytes):
    """Mock class for hash objects that support both hex() and direct bytes usage."""
    def __new__(cls, hex_value, byte_value=None):
        if byte_value is None:
            # Remove '0x' prefix if present and convert to bytes
            clean_hex = hex_value[2:] if hex_value.startswith('0x') else hex_value
            # Pad to 32 bytes (64 hex chars) if needed
            if len(clean_hex) < 64:
                clean_hex = clean_hex.ljust(64, '0')
            byte_value = bytes.fromhex(clean_hex)
        
        instance = super().__new__(cls, byte_value)
        instance.hex_value = hex_value
        return instance
    
    def hex(self):
        return self.hex_value
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
        mock_settings.safe_contract_addresses = '{"base": "0x1234567890123456789012345678901234567890", "ethereum": "0x4567890123456789012345678901234567890123"}'
        mock_settings.ethereum_ledger_rpc = "https://eth-rpc.com"
        mock_settings.gnosis_ledger_rpc = "https://gnosis-rpc.com"
        mock_settings.get_base_rpc_endpoint.return_value = "https://base-rpc.com"
        mock_settings.mode_ledger_rpc = "https://mode-rpc.com"
        
        service = SafeService()
        
        assert service.safe_addresses == {"base": "0x1234567890123456789012345678901234567890", "ethereum": "0x4567890123456789012345678901234567890123"}
        assert service.private_key == "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
        assert service.account.address is not None
        assert service._web3_connections == {}

    @patch("services.safe_service.setup_pearl_logger")
    @patch("builtins.open", side_effect=FileNotFoundError)
    @patch("services.safe_service.settings")
    def test_init_missing_private_key_file(self, mock_settings, mock_file, mock_logger):
        """Test that SafeService raises error when private key file is missing."""
        mock_settings.safe_contract_addresses = '{"base": "0x1234567890123456789012345678901234567890"}'
        mock_settings.ethereum_ledger_rpc = "https://eth-rpc.com"
        mock_settings.gnosis_ledger_rpc = "https://gnosis-rpc.com"
        mock_settings.get_base_rpc_endpoint.return_value = "https://base-rpc.com"
        mock_settings.mode_ledger_rpc = "https://mode-rpc.com"
        
        with pytest.raises(FileNotFoundError):
            SafeService()

    @patch("services.safe_service.setup_pearl_logger")
    @patch("builtins.open", new_callable=mock_open, read_data="invalid_key")
    @patch("services.safe_service.settings")
    def test_init_with_invalid_private_key(self, mock_settings, mock_file, mock_logger):
        """Test SafeService initialization with invalid private key."""
        mock_settings.safe_contract_addresses = '{"base": "0x1234567890123456789012345678901234567890"}'
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
            mock_settings.safe_contract_addresses = '{"base": "0x1234567890123456789012345678901234567890", "ethereum": "0x4567890123456789012345678901234567890123"}'
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
        assert validation["safe_address"] == "0x1234567890123456789012345678901234567890"

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
            mock_settings.safe_contract_addresses = '{"base": "0x1234567890123456789012345678901234567890"}'
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
            mock_settings.safe_contract_addresses = '{"base": "0x1234567890123456789012345678901234567890", "ethereum": "0x4567890123456789012345678901234567890123", "gnosis": "0x7890123456789012345678901234567890123456"}'
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
        with patch.object(self.service, "get_supported_chains", return_value=[]), \
             patch.object(self.service, "is_chain_fully_configured", return_value=False):
            with pytest.raises(ValueError, match="No valid chain configuration found"):
                self.service.select_optimal_chain()


class TestSafeTransactionBuilding:
    """Test Safe transaction building functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("services.safe_service.setup_pearl_logger"), \
             patch("builtins.open", new_callable=mock_open, read_data="0x" + "a" * 64), \
             patch("services.safe_service.settings") as mock_settings:
            mock_settings.safe_contract_addresses = '{"base": "0x1234567890123456789012345678901234567890"}'
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
        # Fix: Create a proper mock for safe_tx_hash with hex() method and bytes support
        mock_safe_tx.safe_tx_hash = MockHash("0xabcd")
        
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

        assert result["safe_address"] == "0x1234567890123456789012345678901234567890"
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
            nonce = await self.service.get_safe_nonce("base", "0x1234567890123456789012345678901234567890")
            
        assert nonce == 10
        mock_safe.retrieve_nonce.assert_called_once()


class TestSafeTransactionSubmission:
    """Test Safe transaction submission functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("services.safe_service.setup_pearl_logger"), \
             patch("builtins.open", new_callable=mock_open, read_data="0x" + "a" * 64), \
             patch("services.safe_service.settings") as mock_settings:
            mock_settings.safe_contract_addresses = '{"base": "0x1234567890123456789012345678901234567890"}'
            mock_settings.get_base_rpc_endpoint.return_value = "https://base-rpc.com"
            mock_settings.ethereum_ledger_rpc = "https://eth-rpc.com"
            mock_settings.gnosis_ledger_rpc = "https://gnosis-rpc.com"
            mock_settings.mode_ledger_rpc = "https://mode-rpc.com"
            self.service = SafeService()

    async def test_submit_safe_transaction_invalid_inputs(self):
        """Test transaction submission with invalid inputs raises assertions."""
        # Test invalid chain
        with pytest.raises(AssertionError, match="Chain must be a non-empty string"):
            await self.service._submit_safe_transaction(
                chain="",
                to="0x4567890123456789012345678901234567890123",
                value=0,
                data=b""
            )

        # Test invalid to address
        with pytest.raises(AssertionError, match="To address must be a non-empty string"):
            await self.service._submit_safe_transaction(
                chain="base",
                to="",
                value=0,
                data=b""
            )

        # Test invalid value
        with pytest.raises(AssertionError, match="Value must be a non-negative integer"):
            await self.service._submit_safe_transaction(
                chain="base",
                to="0x4567890123456789012345678901234567890123",
                value=-1,
                data=b""
            )

        # Test invalid data type
        with pytest.raises(AssertionError, match="Data must be bytes"):
            await self.service._submit_safe_transaction(
                chain="base",
                to="0x4567890123456789012345678901234567890123",
                value=0,
                data="not_bytes"
            )

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
        # Fix: Create a proper mock for safe_tx_hash with hex() method and bytes support
        mock_safe_tx.safe_tx_hash = MockHash("0xabc123")
        mock_safe_tx.signatures = b"signature"
        mock_safe_tx.call = Mock()  # Simulation succeeds
        
        # Mock Safe instance
        mock_safe = Mock()
        mock_safe.build_multisig_tx.return_value = mock_safe_tx
        # Fix: Create proper mock for ethereum transaction with tx_hash
        mock_ethereum_tx = Mock()
        mock_ethereum_tx.tx_hash = MockHash("0x123456")
        mock_safe.send_multisig_tx.return_value = mock_ethereum_tx
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
        assert result["tx_hash"] == "0x123456"
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
        # Fix: Create a proper mock for safe_tx_hash with hex() method and bytes support
        mock_safe_tx.safe_tx_hash = MockHash("0xabc123")
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
            mock_settings.safe_contract_addresses = '{"base": "0x1234567890123456789012345678901234567890"}'
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
                to="0x1234567890123456789012345678901234567890",  # Safe address
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
                to="0x1234567890123456789012345678901234567890",
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
            mock_settings.safe_contract_addresses = '{"base": "0x1234567890123456789012345678901234567890"}'
            mock_settings.get_base_rpc_endpoint.return_value = "https://base-rpc.com"
            mock_settings.ethereum_ledger_rpc = "https://eth-rpc.com"
            mock_settings.gnosis_ledger_rpc = "https://gnosis-rpc.com"
            mock_settings.mode_ledger_rpc = "https://mode-rpc.com"
            mock_settings.eas_contract_address = "0x1234567890123456789012345678901234567890"
            mock_settings.eas_schema_uid = "0x" + "a" * 64
            mock_settings.base_safe_address = "0x1234567890123456789012345678901234567890"
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

    @patch("services.safe_service.settings")
    @patch("utils.web3_provider.get_w3")
    @patch("utils.abi_loader.load_abi")
    async def test_create_eas_attestation_success(self, mock_load_abi, mock_get_w3, mock_settings):
        """Test successful EAS attestation creation."""
        # Configure settings for EAS
        mock_settings.eas_contract_address = "0x1234567890123456789012345678901234567890"
        mock_settings.eas_schema_uid = "0x" + "a" * 64
        mock_settings.base_safe_address = "0x1234567890123456789012345678901234567890"
        mock_settings.attestation_tracker_address = None
        mock_settings.attestation_chain = "base"
        
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
            "to": "0x1234567890123456789012345678901234567890",
            "data": "0xabcd",
            "value": 0,
            "gas": EAS_ATTESTATION_GAS_LIMIT
        }
        mock_w3.eth.contract.return_value = mock_contract

        mock_load_abi.return_value = []

        with patch.object(self.service, "_build_eas_attestation_tx") as mock_build_tx, \
             patch.object(self.service, "_submit_safe_transaction", new_callable=AsyncMock) as mock_submit:
            
            mock_build_tx.return_value = {
                "to": "0x1234567890123456789012345678901234567890",
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
    @patch("utils.web3_provider.get_w3")
    @patch("utils.abi_loader.load_abi")
    @patch("services.safe_service.settings")
    @patch("builtins.open", new_callable=mock_open, read_data="0x" + "a" * 64)
    def test_build_delegated_attestation_tx_eip712proxy(self, mock_file, mock_settings, mock_load_abi, mock_get_w3, mock_generate_sig):
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

        # Configure settings
        mock_settings.eas_contract_address = "0x1234567890123456789012345678901234567890"
        mock_settings.eas_schema_uid = "0x" + "a" * 64
        mock_settings.attestation_chain = "base"
        mock_settings.base_safe_address = "0x1234567890123456789012345678901234567890"

        # Mock Web3 and contract
        mock_w3 = Mock()
        mock_w3.eth.get_block.return_value = {"timestamp": 1234567900, "number": 12345}
        mock_get_w3.return_value = mock_w3

        mock_contract = Mock()
        mock_contract.functions.attestByDelegation.return_value.build_transaction.return_value = {
            "to": "0x1234567890123456789012345678901234567890",
            "data": "0xabcd",
            "value": 0
        }
        mock_w3.eth.contract.return_value = mock_contract

        mock_load_abi.return_value = []
        mock_generate_sig.return_value = b"\x01" * 65  # 65-byte signature

        with patch.dict('os.environ', {'ETHEREUM_PRIVATE_KEY': '0x' + 'a' * 64}):
            result = self.service._build_delegated_attestation_tx(
                attestation_data,
                target_address="0x1234567890123456789012345678901234567890",
                abi_name="eip712proxy"
            )

        assert result["to"] == "0x1234567890123456789012345678901234567890"
        assert result["data"] == "0xabcd"
        assert result["value"] == 0

    @patch("services.safe_service.generate_eas_delegated_signature")
    @patch("utils.web3_provider.get_w3")
    @patch("utils.abi_loader.load_abi")
    @patch("services.safe_service.settings")
    @patch("builtins.open", new_callable=mock_open, read_data="0x" + "a" * 64)
    def test_build_delegated_attestation_tx_attestation_tracker(self, mock_file, mock_settings, mock_load_abi, mock_get_w3, mock_generate_sig):
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

        # Configure settings
        mock_settings.eas_contract_address = "0x1234567890123456789012345678901234567890"
        mock_settings.eas_schema_uid = "0x" + "a" * 64
        mock_settings.attestation_chain = "base"
        mock_settings.base_safe_address = "0x1234567890123456789012345678901234567890"

        # Mock Web3 and contract
        mock_w3 = Mock()
        mock_w3.eth.get_block.return_value = {"timestamp": 1234567900, "number": 12345}
        mock_get_w3.return_value = mock_w3

        mock_contract = Mock()
        mock_contract.functions.attestByDelegation.return_value.build_transaction.return_value = {
            "to": "0x1111111111111111111111111111111111111111",
            "data": "0xefgh",
            "value": 0
        }
        mock_w3.eth.contract.return_value = mock_contract

        mock_load_abi.return_value = []
        mock_generate_sig.return_value = b"\x01" * 65  # 65-byte signature

        with patch.dict('os.environ', {'ETHEREUM_PRIVATE_KEY': '0x' + 'a' * 64}):
            result = self.service._build_delegated_attestation_tx(
                attestation_data,
                target_address="0x1111111111111111111111111111111111111111",
                abi_name="attestation_tracker"
            )

        assert result["to"] == "0x1111111111111111111111111111111111111111"
        assert result["data"] == "0xefgh"
        assert result["value"] == 0


class TestUtilityMethods:
    """Test utility methods in SafeService."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("services.safe_service.setup_pearl_logger"), \
             patch("builtins.open", new_callable=mock_open, read_data="0x" + "a" * 64), \
             patch("services.safe_service.settings") as mock_settings:
            mock_settings.safe_contract_addresses = '{"base": "0x1234567890123456789012345678901234567890"}'
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
            "recipient": "0x4567890123456789012345678901234567890123",
            "deadline": 1234567890,
            "data": b"test_request_data"
        }
        
        mock_generate_sig.return_value = b"\x01" * 65
        
        result = self.service._generate_eas_delegated_signature(
            request_data, mock_w3, "0x1234567890123456789012345678901234567890"
        )
        
        assert result == b"\x01" * 65
        mock_generate_sig.assert_called_once_with(
            request_data=request_data,
            w3=mock_w3,
            eas_contract_address="0x1234567890123456789012345678901234567890",
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


class TestSafeTransactionSubmissionComprehensive:
    """Comprehensive tests for Safe transaction submission with high coverage."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("services.safe_service.setup_pearl_logger"), \
             patch("builtins.open", new_callable=mock_open, read_data="ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"), \
             patch("services.safe_service.settings") as mock_settings:
            mock_settings.safe_contract_addresses = '{"base": "0x1234567890123456789012345678901234567890"}'
            mock_settings.get_base_rpc_endpoint.return_value = "https://base-rpc.com"
            mock_settings.ethereum_ledger_rpc = "https://eth-rpc.com"
            mock_settings.gnosis_ledger_rpc = "https://gnosis-rpc.com"
            mock_settings.mode_ledger_rpc = "https://mode-rpc.com"
            self.service = SafeService()

    @patch("services.safe_service.EthereumClient")
    @patch("services.safe_service.Safe")
    @patch("services.safe_service.TransactionServiceApi")
    async def test_submit_safe_transaction_complete_flow(self, mock_tx_service, mock_safe_class, mock_eth_client):
        """Test complete Safe transaction submission flow with all steps."""
        # Mock transaction receipt
        mock_receipt = {
            "blockNumber": 12345,
            "gasUsed": 100000,
            "status": 1,
            "transactionHash": "0xtxhash"
        }
        
        # Mock Web3 connection
        mock_w3 = Mock()
        mock_w3.eth.wait_for_transaction_receipt.return_value = mock_receipt
        
        # Mock Safe transaction with all required attributes
        mock_safe_tx = Mock()
        mock_safe_tx.to = "0x4567890123456789012345678901234567890123"
        mock_safe_tx.value = 100
        mock_safe_tx.data = b"test_data"
        mock_safe_tx.operation = 0
        mock_safe_tx.safe_tx_gas = 100000
        mock_safe_tx.base_gas = 50000
        mock_safe_tx.gas_price = 1000000000
        mock_safe_tx.gas_token = "0x0000000000000000000000000000000000000000"
        mock_safe_tx.refund_receiver = "0x0000000000000000000000000000000000000000"
        mock_safe_tx.safe_nonce = 5
        # Fix: Create a proper mock for safe_tx_hash with hex() method and bytes support
        mock_safe_tx.safe_tx_hash = MockHash("0xabc123")
        mock_safe_tx.signatures = b"signature"
        mock_safe_tx.call = Mock()  # Simulation succeeds
        
        # Mock Safe instance
        mock_safe = Mock()
        mock_safe.build_multisig_tx.return_value = mock_safe_tx
        mock_ethereum_tx = Mock()
        mock_ethereum_tx.tx_hash = MockHash("0x123456")
        mock_safe.send_multisig_tx.return_value = mock_ethereum_tx
        mock_safe_class.return_value = mock_safe
        
        # Mock transaction service
        mock_service = Mock()
        mock_tx_service.return_value = mock_service
        
        with patch.object(self.service, "get_web3_connection", return_value=mock_w3), \
             patch.object(self.service, "_rate_limit_base_rpc"):
            
            result = await self.service._submit_safe_transaction(
                chain="base",
                to="0x4567890123456789012345678901234567890123",
                value=100,
                data=b"test_data"
            )

        # Verify the complete flow was executed
        assert result["success"] is True
        assert result["tx_hash"] == "0x123456"
        assert result["chain"] == "base"
        assert result["block_number"] == 12345
        assert result["gas_used"] == 100000
        assert result["safe_address"] == "0x1234567890123456789012345678901234567890"
        
        # Verify all components were called
        mock_safe.build_multisig_tx.assert_called_once()
        mock_service.post_transaction.assert_called_once()
        mock_safe_tx.call.assert_called_once()  # Simulation
        mock_safe.send_multisig_tx.assert_called_once()
        mock_w3.eth.wait_for_transaction_receipt.assert_called_once()

    @patch("services.safe_service.EthereumClient")
    @patch("services.safe_service.Safe")
    @patch("services.safe_service.TransactionServiceApi")
    async def test_submit_safe_transaction_reverted_receipt(self, mock_tx_service, mock_safe_class, mock_eth_client):
        """Test handling of reverted transaction receipt."""
        # Mock failed transaction receipt
        mock_receipt = {
            "blockNumber": 12345,
            "gasUsed": 100000,
            "status": 0,  # Failed status
            "transactionHash": "0xtxhash"
        }
        
        mock_w3 = Mock()
        mock_w3.eth.wait_for_transaction_receipt.return_value = mock_receipt
        
        # Mock successful Safe transaction but failed execution
        mock_safe_tx = Mock()
        mock_safe_tx.to = "0x4567890123456789012345678901234567890123"
        mock_safe_tx.value = 0
        mock_safe_tx.data = b""
        mock_safe_tx.operation = 0
        mock_safe_tx.safe_tx_gas = 100000
        mock_safe_tx.base_gas = 50000
        mock_safe_tx.gas_price = 1000000000
        mock_safe_tx.gas_token = "0x0000000000000000000000000000000000000000"
        mock_safe_tx.refund_receiver = "0x0000000000000000000000000000000000000000"
        mock_safe_tx.safe_nonce = 5
        # Fix: Create a proper mock for safe_tx_hash with hex() method and bytes support
        mock_safe_tx.safe_tx_hash = MockHash("0xabc123")
        mock_safe_tx.signatures = b"signature"
        mock_safe_tx.call = Mock()  # Simulation succeeds
        
        mock_safe = Mock()
        mock_safe.build_multisig_tx.return_value = mock_safe_tx
        mock_ethereum_tx = Mock()
        mock_ethereum_tx.tx_hash = MockHash("0x123456")
        mock_safe.send_multisig_tx.return_value = mock_ethereum_tx
        mock_safe_class.return_value = mock_safe
        
        mock_service = Mock()
        mock_tx_service.return_value = mock_service
        
        with patch.object(self.service, "get_web3_connection", return_value=mock_w3), \
             patch.object(self.service, "_rate_limit_base_rpc"):
            
            result = await self.service._submit_safe_transaction(
                chain="base",
                to="0x4567890123456789012345678901234567890123",
                value=0,
                data=b""
            )

        assert result["success"] is False
        assert result["error"] == "Transaction reverted"
        assert result["tx_hash"] == "0x123456"

    @patch("services.safe_service.EthereumClient")
    @patch("services.safe_service.Safe")
    async def test_submit_safe_transaction_exception_handling(self, mock_safe_class, mock_eth_client):
        """Test exception handling in transaction submission."""
        # Mock Safe that throws exception
        mock_safe_class.side_effect = Exception("Connection failed")
        
        with patch.object(self.service, "get_web3_connection"), \
             patch.object(self.service, "_rate_limit_base_rpc"):
            
            result = await self.service._submit_safe_transaction(
                chain="base",
                to="0x4567890123456789012345678901234567890123",
                value=0,
                data=b""
            )

        assert result["success"] is False
        assert "Connection failed" in result["error"]

    async def test_submit_safe_transaction_validation_comprehensive(self):
        """Test comprehensive input validation assertions."""
        # Test empty chain - should raise AssertionError
        with pytest.raises(AssertionError, match="Chain must be a non-empty string"):
            await self.service._submit_safe_transaction(
                chain="", to="0x4567890123456789012345678901234567890123", value=0, data=b""
            )
        
        # Test empty to address - should raise AssertionError
        with pytest.raises(AssertionError, match="To address must be a non-empty string"):
            await self.service._submit_safe_transaction(
                chain="base", to="", value=0, data=b""
            )
        
        # Test negative value - should raise AssertionError
        with pytest.raises(AssertionError, match="Value must be a non-negative integer"):
            await self.service._submit_safe_transaction(
                chain="base", to="0x4567890123456789012345678901234567890123", value=-5, data=b""
            )
        
        # Test invalid data type - should raise AssertionError
        with pytest.raises(AssertionError, match="Data must be bytes"):
            await self.service._submit_safe_transaction(
                chain="base", to="0x4567890123456789012345678901234567890123", value=0, data="not_bytes"
            )


class TestSafeTransactionBuildingComprehensive:
    """Comprehensive tests for Safe transaction building methods."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("services.safe_service.setup_pearl_logger"), \
             patch("builtins.open", new_callable=mock_open, read_data="ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"), \
             patch("services.safe_service.settings") as mock_settings:
            mock_settings.safe_contract_addresses = '{"base": "0x1234567890123456789012345678901234567890"}'
            mock_settings.get_base_rpc_endpoint.return_value = "https://base-rpc.com"
            mock_settings.ethereum_ledger_rpc = "https://eth-rpc.com"
            mock_settings.gnosis_ledger_rpc = "https://gnosis-rpc.com"
            mock_settings.mode_ledger_rpc = "https://mode-rpc.com"
            self.service = SafeService()

    @patch("services.safe_service.EthereumClient")
    @patch("services.safe_service.Safe")
    async def test_build_safe_transaction_with_all_params(self, mock_safe_class, mock_eth_client):
        """Test building Safe transaction with all parameters."""
        # Mock Safe transaction with full data
        mock_safe_tx = Mock()
        mock_safe_tx.to = "0x4567890123456789012345678901234567890123"
        mock_safe_tx.value = 500
        mock_safe_tx.data = b"complex_contract_call_data"
        mock_safe_tx.operation = 1  # DELEGATECALL
        mock_safe_tx.safe_tx_gas = 200000
        mock_safe_tx.base_gas = 75000
        mock_safe_tx.gas_price = 2000000000
        mock_safe_tx.gas_token = "0x1111111111111111111111111111111111111111"
        mock_safe_tx.refund_receiver = "0x2222222222222222222222222222222222222222"
        mock_safe_tx.safe_nonce = 15
        # Fix: Create a proper mock for safe_tx_hash with hex() method and bytes support
        mock_safe_tx.safe_tx_hash = MockHash("0xabcdef123456")
        
        mock_safe = Mock()
        mock_safe.build_multisig_tx.return_value = mock_safe_tx
        mock_safe_class.return_value = mock_safe

        with patch.object(self.service, "_rate_limit_base_rpc"):
            result = await self.service.build_safe_transaction(
                chain="base",
                to="0x4567890123456789012345678901234567890123",
                value=500,
                data=b"complex_contract_call_data",
                operation=1
            )

        # Verify all fields are properly returned
        assert result["safe_address"] == "0x1234567890123456789012345678901234567890"
        assert result["to"] == "0x4567890123456789012345678901234567890123"
        assert result["value"] == 500
        assert result["data"] == b"complex_contract_call_data".hex()
        assert result["operation"] == 1
        assert result["safe_tx_gas"] == 200000
        assert result["base_gas"] == 75000
        assert result["gas_price"] == 2000000000
        assert result["gas_token"] == "0x1111111111111111111111111111111111111111"
        assert result["refund_receiver"] == "0x2222222222222222222222222222222222222222"
        assert result["nonce"] == 15
        assert result["safe_tx_hash"] == "0xabcdef123456"

    @patch("services.safe_service.EthereumClient")
    @patch("services.safe_service.Safe")
    async def test_get_safe_nonce_comprehensive(self, mock_safe_class, mock_eth_client):
        """Test comprehensive nonce retrieval."""
        mock_safe = Mock()
        mock_safe.retrieve_nonce.return_value = 42
        mock_safe_class.return_value = mock_safe

        with patch.object(self.service, "_rate_limit_base_rpc") as mock_rate_limit:
            nonce = await self.service.get_safe_nonce(
                "base", "0x1234567890123456789012345678901234567890"
            )
            
        assert nonce == 42
        mock_safe.retrieve_nonce.assert_called_once()
        mock_rate_limit.assert_called_once_with("https://base-rpc.com")
        
        # Verify Safe was initialized with checksummed address
        mock_safe_class.assert_called_once()
        args = mock_safe_class.call_args[0]
        assert args[0] == "0x1234567890123456789012345678901234567890"  # Checksummed


class TestEASAttestationComprehensive:
    """Comprehensive tests for EAS attestation functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("services.safe_service.setup_pearl_logger"), \
             patch("builtins.open", new_callable=mock_open, read_data="ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"), \
             patch("services.safe_service.settings") as mock_settings:
            mock_settings.safe_contract_addresses = '{"base": "0x1234567890123456789012345678901234567890"}'
            mock_settings.get_base_rpc_endpoint.return_value = "https://base-rpc.com"
            mock_settings.ethereum_ledger_rpc = "https://eth-rpc.com"
            mock_settings.gnosis_ledger_rpc = "https://gnosis-rpc.com"
            mock_settings.mode_ledger_rpc = "https://mode-rpc.com"
            mock_settings.eas_contract_address = "0x12345678901234567890123456789012345678904567890123456789012345678901234567890"
            mock_settings.eas_schema_uid = "0x" + "a" * 64
            mock_settings.base_safe_address = "0x1234567890123456789012345678901234567890"
            mock_settings.attestation_tracker_address = None
            mock_settings.attestation_chain = "base"
            self.service = SafeService()

    @patch("services.safe_service.settings")
    async def test_create_eas_attestation_complete_flow_direct_eas(self, mock_settings):
        """Test complete EAS attestation creation flow using direct EAS."""
        # Configure settings for EAS
        mock_settings.eas_contract_address = "0x12345678901234567890123456789012345678904567890123456789012345678901234567890"
        mock_settings.eas_schema_uid = "0x" + "a" * 64
        mock_settings.base_safe_address = "0x1234567890123456789012345678901234567890"
        mock_settings.attestation_tracker_address = None
        mock_settings.attestation_chain = "base"
        
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

        with patch.object(self.service, "_build_eas_attestation_tx") as mock_build_tx, \
             patch.object(self.service, "_submit_safe_transaction", new_callable=AsyncMock) as mock_submit:
            
            mock_build_tx.return_value = {
                "to": "0x12345678901234567890123456789012345678904567890123456789012345678901234567890",
                "data": "0x" + "1234" * 100,  # Large hex data
                "value": 0
            }
            mock_submit.return_value = {"success": True, "tx_hash": "0xtxhash123"}
            
            result = await self.service.create_eas_attestation(attestation_data)
            
        assert result["success"] is True
        assert result["safe_tx_hash"] == "0xtxhash123"
        
        # Verify transaction was built and submitted
        mock_build_tx.assert_called_once_with(attestation_data)
        mock_submit.assert_called_once_with(
            chain="base",
            to="0x12345678901234567890123456789012345678904567890123456789012345678901234567890",
            data=bytes.fromhex("1234" * 100),
            value=0
        )

    async def test_create_eas_attestation_with_attestation_tracker(self):
        """Test EAS attestation creation using AttestationTracker."""
        attestation_data = EASAttestationData(
            agent="0x4567890123456789012345678901234567890123",
            space_id="test.eth", 
            proposal_id="prop123",
            vote_choice=2,
            snapshot_sig="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            timestamp=1234567890,
            run_id="run123",
            confidence=85
        )

        # Configure for AttestationTracker
        with patch("services.safe_service.settings") as mock_settings:
            mock_settings.attestation_tracker_address = "0xtracker567890123456789012345678901234567890"
            mock_settings.eas_contract_address = "0x12345678901234567890123456789012345678904567890123456789012345678901234567890"
            mock_settings.eas_schema_uid = "0x" + "b" * 64
            mock_settings.base_safe_address = "0x1234567890123456789012345678901234567890"
            
            with patch.object(self.service, "_build_eas_attestation_tx") as mock_build_tx, \
                 patch.object(self.service, "_submit_safe_transaction", new_callable=AsyncMock) as mock_submit:
                
                mock_build_tx.return_value = {
                    "to": "0xtracker567890123456789012345678901234567890",
                    "data": "0x" + "5678" * 50,
                    "value": 0
                }
                mock_submit.return_value = {"success": True, "tx_hash": "0xtrackerTx"}
                
                result = await self.service.create_eas_attestation(attestation_data)
                
            assert result["success"] is True
            assert result["safe_tx_hash"] == "0xtrackerTx"
            mock_build_tx.assert_called_once_with(attestation_data)

    @patch("services.safe_service.settings")
    async def test_create_eas_attestation_failure_scenarios(self, mock_settings):
        """Test various failure scenarios for EAS attestation creation."""
        # Configure settings for EAS
        mock_settings.eas_contract_address = "0x12345678901234567890123456789012345678904567890123456789012345678901234567890"
        mock_settings.eas_schema_uid = "0x" + "a" * 64
        mock_settings.base_safe_address = "0x1234567890123456789012345678901234567890"
        mock_settings.attestation_tracker_address = None
        mock_settings.attestation_chain = "base"
        
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

        # Test transaction building failure
        with patch.object(self.service, "_build_eas_attestation_tx") as mock_build_tx:
            mock_build_tx.side_effect = Exception("Contract ABI load failed")
            
            result = await self.service.create_eas_attestation(attestation_data)
            
        assert result["success"] is False
        assert "Contract ABI load failed" in result["error"]

        # Test Safe transaction submission failure
        with patch.object(self.service, "_build_eas_attestation_tx") as mock_build_tx, \
             patch.object(self.service, "_submit_safe_transaction", new_callable=AsyncMock) as mock_submit:
            
            mock_build_tx.return_value = {"to": "0xtest", "data": "0x1234", "value": 0}
            mock_submit.return_value = {"success": False, "error": "Insufficient gas"}
            
            result = await self.service.create_eas_attestation(attestation_data)
            
        assert result["success"] is False

    def test_encode_attestation_data_comprehensive(self):
        """Test comprehensive attestation data encoding."""
        attestation_data = EASAttestationData(
            agent="0x4567890123456789012345678901234567890123",
            space_id="complex.space.with.dots.eth", 
            proposal_id="very-long-proposal-id-with-special-chars-123",
            vote_choice=255,  # Max uint8
            snapshot_sig="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            timestamp=9999999999,  # Large timestamp
            run_id="run-with-special-chars_456",
            confidence=100
        )

        encoded = self.service._encode_attestation_data(attestation_data)
        
        assert isinstance(encoded, bytes)
        assert len(encoded) > 32  # Should have substantial data
        
        # Verify the encoding includes all fields
        # Note: This would be more precise with actual ABI decoding, but tests basic functionality


class TestUtilityMethodsComprehensive:
    """Comprehensive tests for utility methods."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("services.safe_service.setup_pearl_logger"), \
             patch("builtins.open", new_callable=mock_open, read_data="ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"), \
             patch("services.safe_service.settings") as mock_settings:
            mock_settings.safe_contract_addresses = '{"base": "0x1234567890123456789012345678901234567890"}'
            mock_settings.get_base_rpc_endpoint.return_value = "https://base-rpc.com"
            mock_settings.ethereum_ledger_rpc = "https://eth-rpc.com"
            mock_settings.gnosis_ledger_rpc = "https://gnosis-rpc.com"
            mock_settings.mode_ledger_rpc = "https://mode-rpc.com"
            self.service = SafeService()

    @patch("services.safe_service.Web3")
    def test_get_web3_instance_comprehensive(self, mock_web3_class):
        """Test comprehensive Web3 instance creation."""
        mock_web3 = Mock()
        mock_web3_class.return_value = mock_web3
        
        with patch.object(self.service, "_rate_limit_base_rpc") as mock_rate_limit:
            # Test different chains
            for chain in ["base", "ethereum", "gnosis"]:
                result = self.service._get_web3_instance(chain)
                assert result == mock_web3
                
        # Verify rate limiting was called for each chain
        assert mock_rate_limit.call_count >= 3

    @patch("services.safe_service.generate_eas_delegated_signature")
    @patch("builtins.open", new_callable=mock_open, read_data="ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")
    def test_generate_eas_delegated_signature_comprehensive(self, mock_file, mock_generate_sig):
        """Test comprehensive EAS delegated signature generation."""
        mock_w3 = Mock()
        mock_w3.eth.chain_id = 8453
        
        request_data = {
            "schema": b"\x01" * 32,
            "recipient": "0x4567890123456789012345678901234567890123",
            "deadline": 1234567890,
            "data": b"test_attestation_data_with_content",
            "value": 0,
            "expirationTime": 0,
            "revocable": True,
            "refUID": b"\x00" * 32
        }
        
        mock_signature = b"\x01" * 32 + b"\x02" * 32 + b"\x1b"  # 65-byte signature
        mock_generate_sig.return_value = mock_signature
        
        result = self.service._generate_eas_delegated_signature(
            request_data, mock_w3, "0x12345678901234567890123456789012345678904567890123456789012345678901234567890"
        )
        
        assert result == mock_signature
        assert len(result) == 65
        
        # Verify the shared function was called with correct parameters
        mock_generate_sig.assert_called_once_with(
            request_data=request_data,
            w3=mock_w3,
            eas_contract_address="0x12345678901234567890123456789012345678904567890123456789012345678901234567890",
            private_key="ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
        )

    @patch("services.safe_service.time.sleep")
    def test_rate_limit_base_rpc_comprehensive(self, mock_sleep):
        """Test comprehensive Base RPC rate limiting scenarios."""
        test_cases = [
            ("https://mainnet.base.org/rpc", True),
            ("https://mainnet.base.org/v1/rpc", True),
            ("https://base-mainnet.base.org/rpc", True),
            ("https://ethereum-rpc.com", False),
            ("https://polygon-rpc.com", False),
            ("https://gnosis-rpc.com", False),
        ]
        
        for rpc_url, should_rate_limit in test_cases:
            mock_sleep.reset_mock()
            self.service._rate_limit_base_rpc(rpc_url)
            
            if should_rate_limit:
                mock_sleep.assert_called_once_with(1.0)
            else:
                mock_sleep.assert_not_called()


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and comprehensive error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("services.safe_service.setup_pearl_logger"), \
             patch("builtins.open", new_callable=mock_open, read_data="ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"), \
             patch("services.safe_service.settings") as mock_settings:
            mock_settings.safe_contract_addresses = '{"base": "0x1234567890123456789012345678901234567890", "ethereum": "0x9999999999999999999999999999999999999999"}'
            mock_settings.get_base_rpc_endpoint.return_value = "https://base-rpc.com"
            mock_settings.ethereum_ledger_rpc = "https://eth-rpc.com"
            mock_settings.gnosis_ledger_rpc = "https://gnosis-rpc.com"
            mock_settings.mode_ledger_rpc = "https://mode-rpc.com"
            self.service = SafeService()

    def test_validate_chain_configuration_edge_cases(self):
        """Test chain configuration validation edge cases."""
        # Test chain with Safe address but no service URL
        validation = self.service.validate_chain_configuration("unsupported_chain")
        assert validation["chain"] == "unsupported_chain"
        assert validation["has_safe_service_url"] is False
        assert validation["is_fully_configured"] is False
        assert validation["safe_service_url"] is None

        # Test completely valid chain
        validation = self.service.validate_chain_configuration("base")
        assert validation["is_fully_configured"] is True
        assert validation["safe_address"] == "0x1234567890123456789012345678901234567890"
        assert validation["rpc_endpoint"] == "https://base-rpc.com"
        assert validation["safe_service_url"] == "https://safe-transaction-base.safe.global/"

    async def test_perform_activity_transaction_edge_cases(self):
        """Test activity transaction edge cases."""
        # Test with chain that has no Safe address after initial setup
        result = await self.service.perform_activity_transaction(chain="mode")
        assert result["success"] is False
        assert "No Safe address configured for chain: mode" in result["error"]

        # Test successful activity transaction
        with patch.object(self.service, "_submit_safe_transaction", new_callable=AsyncMock) as mock_submit:
            mock_submit.return_value = {"success": True, "tx_hash": "0xactivity"}
            
            result = await self.service.perform_activity_transaction(chain="base")
            
            assert result["success"] is True
            mock_submit.assert_called_once_with(
                chain="base",
                to="0x1234567890123456789012345678901234567890",
                value=0,
                data=b"",
                operation=0
            )

    def test_get_supported_chains_dynamic(self):
        """Test dynamic supported chains calculation."""
        # Initially should support base and ethereum
        supported = self.service.get_supported_chains()
        assert "base" in supported
        assert "ethereum" in supported
        
        # Should not support chains missing components
        assert "gnosis" not in supported  # No safe address in our test setup
        assert "mode" not in supported    # No safe address in our test setup

    @patch("services.safe_service.EthereumClient")
    @patch("services.safe_service.Safe")
    async def test_build_safe_transaction_empty_data_handling(self, mock_safe_class, mock_eth_client):
        """Test Safe transaction building with empty data."""
        mock_safe_tx = Mock()
        mock_safe_tx.to = "0x4567890123456789012345678901234567890123"
        mock_safe_tx.value = 0
        mock_safe_tx.data = None  # Empty data case
        mock_safe_tx.operation = 0
        mock_safe_tx.safe_tx_gas = 21000
        mock_safe_tx.base_gas = 0
        mock_safe_tx.gas_price = 0
        mock_safe_tx.gas_token = "0x0000000000000000000000000000000000000000"
        mock_safe_tx.refund_receiver = "0x0000000000000000000000000000000000000000"
        mock_safe_tx.safe_nonce = 0
        # Fix: Create a proper mock for safe_tx_hash with hex() method and bytes support
        mock_safe_tx.safe_tx_hash = MockHash("0xdef456")
        
        mock_safe = Mock()
        mock_safe.build_multisig_tx.return_value = mock_safe_tx
        mock_safe_class.return_value = mock_safe

        with patch.object(self.service, "_rate_limit_base_rpc"):
            result = await self.service.build_safe_transaction(
                chain="base",
                to="0x4567890123456789012345678901234567890123"
            )

        assert result["data"] == ""  # Should handle None data gracefully
        assert result["value"] == 0
        assert result["nonce"] == 0


class TestSafeServiceMissingCoverage:
    """Additional tests to reach 90% coverage for SafeService."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch("services.safe_service.setup_pearl_logger"), \
             patch("builtins.open", new_callable=mock_open, read_data="ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"), \
             patch("services.safe_service.settings") as mock_settings:
            mock_settings.safe_contract_addresses = '{"base": "0x1234567890123456789012345678901234567890", "ethereum": "0x9876543210987654321098765432109876543210"}'
            mock_settings.get_base_rpc_endpoint.return_value = "https://base-rpc.com"
            mock_settings.ethereum_ledger_rpc = "https://eth-rpc.com"
            mock_settings.gnosis_ledger_rpc = "https://gnosis-rpc.com"
            mock_settings.mode_ledger_rpc = "https://mode-rpc.com"
            mock_settings.eas_contract_address = "0x1234567890123456789012345678901234567890"
            mock_settings.eas_schema_uid = "0x" + "a" * 64
            mock_settings.base_safe_address = "0x1234567890123456789012345678901234567890"
            mock_settings.attestation_tracker_address = None
            mock_settings.attestation_chain = "base"
            self.service = SafeService()

    def test_is_chain_fully_configured_edge_cases(self):
        """Test edge cases for chain configuration validation."""
        # Test chain with empty Safe address - should return falsy value
        with patch.object(self.service, 'safe_addresses', {"empty": ""}):
            result = self.service.is_chain_fully_configured("empty")
            assert not result  # Should be falsy (empty string)
            
        # Test chain with empty RPC endpoint - should return falsy value
        with patch.object(self.service, 'rpc_endpoints', {"empty_rpc": ""}):
            result = self.service.is_chain_fully_configured("empty_rpc")
            assert not result  # Should be falsy

    def test_validate_chain_configuration_comprehensive(self):
        """Test comprehensive validate_chain_configuration scenarios."""
        # Test chain with all missing components
        validation = self.service.validate_chain_configuration("nonexistent")
        assert validation["chain"] == "nonexistent"
        assert validation["has_safe_address"] is False
        assert validation["has_rpc_endpoint"] is False
        assert validation["has_safe_service_url"] is False
        assert validation["is_fully_configured"] is False
        assert validation["safe_address"] is None
        assert validation["rpc_endpoint"] is None
        assert validation["safe_service_url"] is None

    def test_rate_limit_base_rpc_multiple_patterns(self):
        """Test various Base mainnet URL patterns for rate limiting."""
        with patch("services.safe_service.time.sleep") as mock_sleep:
            test_urls = [
                "https://mainnet.base.org/rpc",
                "https://base-mainnet.base.org/v1/rpc",  
                "https://mainnet.base.org/api/v1/rpc",
                "https://other-base-mainnet.base.org/rpc"
            ]
            
            for url in test_urls:
                mock_sleep.reset_mock()
                self.service._rate_limit_base_rpc(url)
                mock_sleep.assert_called_once_with(1.0)

    @patch("services.safe_service.EthereumClient")
    @patch("services.safe_service.Safe")
    @patch("services.safe_service.TransactionServiceApi")
    async def test_submit_safe_transaction_no_safe_address_configured(self, mock_tx_service, mock_safe_class, mock_eth_client):
        """Test _submit_safe_transaction when Safe address is not configured for a chain."""
        # Mock a scenario where safe address lookup returns None
        with patch.object(self.service, 'safe_addresses', {"base": None}), \
             patch.object(self.service, 'is_chain_fully_configured', return_value=True), \
             patch.object(self.service, 'get_web3_connection'), \
             patch.object(self.service, '_rate_limit_base_rpc'):
            
            # This should trigger the ValueError inside _submit_safe_transaction
            mock_safe_class.side_effect = ValueError("No Safe address configured for chain: base")
            
            result = await self.service._submit_safe_transaction(
                chain="base", to="0x456", value=0, data=b""
            )
            
            assert result["success"] is False
            assert "No Safe address configured for chain: base" in result["error"]

    @patch("services.safe_service.EthereumClient")
    @patch("services.safe_service.Safe")
    async def test_build_safe_transaction_with_none_data(self, mock_safe_class, mock_eth_client):
        """Test building Safe transaction when data is None."""
        mock_safe_tx = Mock()
        mock_safe_tx.to = "0x456"
        mock_safe_tx.value = 0
        mock_safe_tx.data = None  # None data case
        mock_safe_tx.operation = 0
        mock_safe_tx.safe_tx_gas = 100000
        mock_safe_tx.base_gas = 50000
        mock_safe_tx.gas_price = 1000000000
        mock_safe_tx.gas_token = "0x0000000000000000000000000000000000000000"
        mock_safe_tx.refund_receiver = "0x0000000000000000000000000000000000000000"
        mock_safe_tx.safe_nonce = 5
        # Fix: Create a proper mock for safe_tx_hash with hex() method and bytes support
        mock_safe_tx.safe_tx_hash = MockHash("0xabcd")
        
        mock_safe = Mock()
        mock_safe.build_multisig_tx.return_value = mock_safe_tx
        mock_safe_class.return_value = mock_safe
        
        with patch.object(self.service, "_rate_limit_base_rpc"):
            result = await self.service.build_safe_transaction(
                chain="base", to="0x456", value=0, data=b"test"
            )
            
        assert result["data"] == ""  # Should handle None gracefully

    @patch("services.safe_service.settings")
    async def test_create_eas_attestation_data_hex_conversion(self, mock_settings):
        """Test EAS attestation data hex conversion scenarios."""
        # Configure settings for EAS
        mock_settings.eas_contract_address = "0x1234567890123456789012345678901234567890"
        mock_settings.eas_schema_uid = "0x" + "a" * 64
        mock_settings.base_safe_address = "0x1234567890123456789012345678901234567890"
        mock_settings.attestation_tracker_address = None
        mock_settings.attestation_chain = "base"
        
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

        # Test with hex data starting with 0x
        with patch.object(self.service, '_build_eas_attestation_tx') as mock_build_tx, \
             patch.object(self.service, '_submit_safe_transaction', new_callable=AsyncMock) as mock_submit:
            
            mock_build_tx.return_value = {
                "to": "0x1234567890123456789012345678901234567890",
                "data": "0x1234abcd",  # Starts with 0x
                "value": 0
            }
            mock_submit.return_value = {"success": True, "tx_hash": "0xtxhash"}
            
            result = await self.service.create_eas_attestation(attestation_data)
            
            # Verify bytes conversion was called correctly
            mock_submit.assert_called_once()
            call_args = mock_submit.call_args
            assert isinstance(call_args[1]['data'], bytes)

        # Test with hex data not starting with 0x  
        with patch.object(self.service, '_build_eas_attestation_tx') as mock_build_tx, \
             patch.object(self.service, '_submit_safe_transaction', new_callable=AsyncMock) as mock_submit:
            
            mock_build_tx.return_value = {
                "to": "0x1234567890123456789012345678901234567890", 
                "data": "1234abcd",  # No 0x prefix
                "value": 0
            }
            mock_submit.return_value = {"success": True, "tx_hash": "0xtxhash"}
            
            result = await self.service.create_eas_attestation(attestation_data)
            
            # Verify bytes conversion handles no 0x prefix
            mock_submit.assert_called_once()
            call_args = mock_submit.call_args
            assert isinstance(call_args[1]['data'], bytes)

    def test_build_delegated_attestation_tx_with_env_private_key(self):
        """Test _build_delegated_attestation_tx using private key from environment."""
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
        
        mock_contract = Mock()
        mock_contract.functions.attestByDelegation.return_value.build_transaction.return_value = {
            "to": "0xtest123",
            "data": "0xabcd1234",
            "value": 0,
            "gas": 1000000
        }
        mock_w3.eth.contract.return_value = mock_contract
        
        with patch('utils.web3_provider.get_w3', return_value=mock_w3), \
             patch('utils.abi_loader.load_abi', return_value=[]), \
             patch('services.safe_service.settings') as mock_settings, \
             patch.object(self.service, '_generate_eas_delegated_signature') as mock_generate_sig, \
             patch('builtins.open', side_effect=FileNotFoundError), \
             patch.dict('os.environ', {'ETHEREUM_PRIVATE_KEY': '0x' + 'a' * 64}):
            
            mock_settings.attestation_chain = "base"
            mock_settings.eas_schema_uid = "0x" + "a" * 64
            mock_settings.base_safe_address = "0x1234567890123456789012345678901234567890"
            mock_settings.eas_contract_address = "0x1234567890123456789012345678901234567890"
            
            mock_generate_sig.return_value = b"\x01" * 65
            
            result = self.service._build_delegated_attestation_tx(
                attestation_data, "0x1111111111111111111111111111111111111111", "attestation_tracker"
            )
            
            assert result["to"] == "0xtest123"
            assert result["data"] == "0xabcd1234"
            assert result["value"] == 0

    def test_build_delegated_attestation_tx_no_private_key(self):
        """Test _build_delegated_attestation_tx when no private key is found."""
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

        mock_w3 = Mock()
        mock_w3.eth.get_block.return_value = {"timestamp": 1234567900, "number": 12345}
        
        with patch('utils.web3_provider.get_w3', return_value=mock_w3), \
             patch('utils.abi_loader.load_abi', return_value=[]), \
             patch('services.safe_service.settings') as mock_settings, \
             patch.object(self.service, '_generate_eas_delegated_signature', return_value=b"\x01" * 65), \
             patch('builtins.open', side_effect=FileNotFoundError), \
             patch('os.path.exists', return_value=False), \
             patch.dict('os.environ', {}, clear=True):
            
            mock_settings.attestation_chain = "base"
            mock_settings.eas_schema_uid = "0x" + "a" * 64
            mock_settings.base_safe_address = "0x1234567890123456789012345678901234567890"
            mock_settings.eas_contract_address = "0x1234567890123456789012345678901234567890"
            
            with pytest.raises(ValueError, match="Private key not found"):
                self.service._build_delegated_attestation_tx(
                    attestation_data, "0x1111111111111111111111111111111111111111", "attestation_tracker"
                )

    def test_encode_attestation_data_address_checksumming(self):
        """Test that attestation data encoding properly checksums addresses."""
        # Use a lowercase address to test checksumming
        attestation_data = EASAttestationData(
            agent="0x4567890123456789012345678901234567890123".lower(),
            space_id="test.eth", 
            proposal_id="prop123",
            vote_choice=1,
            snapshot_sig="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            timestamp=1234567890,
            run_id="run123",
            confidence=95
        )

        with patch('services.safe_service.Web3') as mock_web3_class:
            mock_w3 = Mock()
            mock_codec = Mock()
            mock_codec.encode.return_value = b"encoded_data"
            mock_w3.codec = mock_codec
            mock_web3_class.return_value = mock_w3
            
            # Mock the to_checksum_address static method
            mock_web3_class.to_checksum_address.return_value = "0x4567890123456789012345678901234567890123"
            
            result = self.service._encode_attestation_data(attestation_data)
            
            # Verify encode was called and first parameter was checksummed
            mock_codec.encode.assert_called_once()
            call_args = mock_codec.encode.call_args[0][1]
            agent_address = call_args[0]
            # Should be checksummed version
            assert agent_address == "0x4567890123456789012345678901234567890123"

    @patch("services.safe_service.generate_eas_delegated_signature")
    @patch("builtins.open", new_callable=mock_open, read_data="test_private_key")
    def test_generate_eas_delegated_signature_detailed_logging(self, mock_file, mock_generate_sig):
        """Test _generate_eas_delegated_signature with detailed logging."""
        mock_w3 = Mock()
        mock_w3.eth.chain_id = 8453
        
        request_data = {
            "schema": b"\x01" * 32,
            "recipient": "0x4567890123456789012345678901234567890123",
            "deadline": 1234567890,
            "data": b"test_request_data_longer_than_usual_for_testing"
        }
        
        mock_signature = b"\x01" * 32 + b"\x02" * 32 + b"\x1b"  # 65-byte signature
        mock_generate_sig.return_value = mock_signature
        
        result = self.service._generate_eas_delegated_signature(
            request_data, mock_w3, "0x12345678901234567890123456789012345678904567890123456789012345678901234567890"
        )
        
        assert result == mock_signature
        assert len(result) == 65
        
        # Verify the signature generation was called with correct parameters
        mock_generate_sig.assert_called_once_with(
            request_data=request_data,
            w3=mock_w3,
            eas_contract_address="0x12345678901234567890123456789012345678904567890123456789012345678901234567890",
            private_key="test_private_key"
        )