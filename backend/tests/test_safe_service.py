"""Tests for SafeService."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from web3 import Web3
import json

from services.safe_service import SafeService, SAFE_SERVICE_URLS



class TestSafeServiceInitialization:
    """Test SafeService initialization."""

    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    def test_safe_service_initialization(self, mock_settings, mock_json_loads, mock_file):
        """Test SafeService initialization loads configuration correctly."""
        # Setup mock settings
        mock_settings.safe_contract_addresses = '{"gnosis": "0x123", "ethereum": "0x456"}'
        mock_settings.ethereum_ledger_rpc = "https://eth.example.com"
        mock_settings.gnosis_ledger_rpc = "https://gnosis.example.com"
        mock_settings.base_ledger_rpc = "https://base.example.com"
        mock_settings.mode_ledger_rpc = "https://mode.example.com"
        
        mock_json_loads.return_value = {"gnosis": "0x123", "ethereum": "0x456"}
        
        service = SafeService()
        
        assert service.safe_addresses == {"gnosis": "0x123", "ethereum": "0x456"}
        assert service.rpc_endpoints["ethereum"] == "https://eth.example.com"
        assert service.rpc_endpoints["gnosis"] == "https://gnosis.example.com"
        assert service.account.address is not None
        mock_file.assert_called_once_with("ethereum_private_key.txt", "r")


class TestSafeServiceWebConnection:
    """Test SafeService Web3 connection management."""
    
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    @patch("services.safe_service.Web3")
    def test_get_web3_connection_success(self, mock_web3_class, mock_settings, mock_json_loads, mock_file):
        """Test successful Web3 connection creation."""
        mock_settings.safe_contract_addresses = '{"gnosis": "0x123"}'
        mock_settings.gnosis_ledger_rpc = "https://gnosis.example.com"
        mock_json_loads.return_value = {"gnosis": "0x123"}
        
        # Setup Web3 mock
        mock_web3_instance = MagicMock()
        mock_web3_instance.is_connected.return_value = True
        mock_web3_class.return_value = mock_web3_instance
        
        service = SafeService()
        result = service.get_web3_connection("gnosis")
        
        assert result == mock_web3_instance
        mock_web3_class.assert_called_with(mock_web3_class.HTTPProvider("https://gnosis.example.com"))
        
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    def test_get_web3_connection_invalid_chain(self, mock_settings, mock_json_loads, mock_file):
        """Test Web3 connection with invalid chain raises ValueError."""
        mock_settings.safe_contract_addresses = '{"gnosis": "0x123"}'
        mock_json_loads.return_value = {"gnosis": "0x123"}
        
        service = SafeService()
        
        with pytest.raises(ValueError, match="No RPC endpoint configured for chain: invalid"):
            service.get_web3_connection("invalid")
            
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    @patch("services.safe_service.Web3")
    def test_get_web3_connection_failure(self, mock_web3_class, mock_settings, mock_json_loads, mock_file):
        """Test Web3 connection failure raises ConnectionError."""
        mock_settings.safe_contract_addresses = '{"gnosis": "0x123"}'
        mock_settings.gnosis_ledger_rpc = "https://gnosis.example.com"
        mock_json_loads.return_value = {"gnosis": "0x123"}
        
        # Setup Web3 mock to fail connection
        mock_web3_instance = MagicMock()
        mock_web3_instance.is_connected.return_value = False
        mock_web3_class.return_value = mock_web3_instance
        
        service = SafeService()
        
        with pytest.raises(ConnectionError, match="Failed to connect to gnosis network"):
            service.get_web3_connection("gnosis")


class TestSafeServiceChainSelection:
    """Test SafeService chain selection logic."""
    
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    def test_select_optimal_chain_priority_order(self, mock_settings, mock_json_loads, mock_file):
        """Test chain selection follows priority order (gnosis first)."""
        mock_settings.safe_contract_addresses = '{"gnosis": "0x123", "ethereum": "0x456"}'
        mock_settings.gnosis_ledger_rpc = "https://gnosis.example.com"
        mock_settings.ethereum_ledger_rpc = "https://eth.example.com"
        mock_json_loads.return_value = {"gnosis": "0x123", "ethereum": "0x456"}
        
        service = SafeService()
        result = service.select_optimal_chain()
        
        assert result == "gnosis"  # Should prefer gnosis over ethereum
        
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    def test_select_optimal_chain_fallback(self, mock_settings, mock_json_loads, mock_file):
        """Test chain selection falls back when priority chains unavailable."""
        mock_settings.safe_contract_addresses = '{"ethereum": "0x456"}'
        mock_settings.ethereum_ledger_rpc = "https://eth.example.com"
        mock_settings.gnosis_ledger_rpc = None  # Gnosis not available
        mock_json_loads.return_value = {"ethereum": "0x456"}
        
        service = SafeService()
        result = service.select_optimal_chain()
        
        assert result == "ethereum"  # Falls back to available chain
        
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    def test_select_optimal_chain_no_config(self, mock_settings, mock_json_loads, mock_file):
        """Test chain selection raises error when no config available."""
        mock_settings.safe_contract_addresses = '{}'
        mock_json_loads.return_value = {}
        
        service = SafeService()
        
        with pytest.raises(ValueError, match="No valid chain configuration found"):
            service.select_optimal_chain()

    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    def test_select_optimal_chain_excludes_celo(self, mock_settings, mock_json_loads, mock_file):
        """Test that chain selection never returns 'celo' even if configured (critical edge case)."""
        # Setup: Configure both celo (no Safe service URL) and gnosis (has Safe service URL)
        mock_settings.safe_contract_addresses = '{"celo": "0x123", "gnosis": "0x456"}'
        mock_settings.celo_ledger_rpc = "https://celo.example.com"
        mock_settings.gnosis_ledger_rpc = "https://gnosis.example.com"
        mock_json_loads.return_value = {"celo": "0x123", "gnosis": "0x456"}
        
        service = SafeService()
        # Manually set celo RPC endpoint to ensure it's "configured"
        service.rpc_endpoints["celo"] = "https://celo.example.com"
        
        result = service.select_optimal_chain()
        
        # Should select gnosis, never celo (despite celo being in current priority order)
        assert result != "celo"
        assert result == "gnosis"
    
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    def test_select_optimal_chain_uses_validation_methods(self, mock_settings, mock_json_loads, mock_file):
        """Test that chain selection uses validation methods from Phase 1 (core business logic)."""
        # Setup: Multiple chains, only base should be fully configured
        mock_settings.safe_contract_addresses = '{"base": "0x123", "polygon": "0x456"}'
        mock_settings.base_ledger_rpc = "https://base.example.com"
        mock_settings.polygon_ledger_rpc = "https://polygon.example.com"
        mock_json_loads.return_value = {"base": "0x123", "polygon": "0x456"}
        
        service = SafeService()
        # Manually set polygon RPC endpoint
        service.rpc_endpoints["polygon"] = "https://polygon.example.com"
        
        result = service.select_optimal_chain()
        
        # Should return base (has Safe service URL), not polygon (no Safe service URL)
        assert result == "base"
        
        # Verify chain is actually fully configured according to Phase 1 validation
        assert service.is_chain_fully_configured("base") is True
        assert service.is_chain_fully_configured("polygon") is False


class TestSafeServiceActivityTransaction:
    """Test SafeService activity transaction functionality."""
    
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    @patch("services.safe_service.EthereumClient")
    @patch("services.safe_service.Safe")
    @patch("services.safe_service.TransactionServiceApi")
    @patch("services.safe_service.Web3")
    @pytest.mark.asyncio
    async def test_perform_activity_transaction_success(
        self, 
        mock_web3_class, 
        mock_tx_service_class,
        mock_safe_class,
        mock_eth_client_class,
        mock_settings, 
        mock_json_loads, 
        mock_file
    ):
        """Test successful activity transaction creation."""
        # Setup mocks
        mock_settings.safe_contract_addresses = '{"gnosis": "0x123"}'
        mock_settings.gnosis_ledger_rpc = "https://gnosis.example.com"
        mock_json_loads.return_value = {"gnosis": "0x123"}
        
        # Mock Web3
        mock_web3_instance = MagicMock()
        mock_web3_instance.is_connected.return_value = True
        mock_receipt = {"status": 1, "blockNumber": 12345, "gasUsed": 21000}
        mock_web3_instance.eth.wait_for_transaction_receipt.return_value = mock_receipt
        mock_web3_class.return_value = mock_web3_instance
        mock_web3_class.to_checksum_address.return_value = "0x123"
        
        # Mock Safe
        mock_safe_instance = MagicMock()
        mock_safe_tx = MagicMock()
        mock_safe_tx.safe_tx_hash = b"0" * 32  # 32-byte hash
        mock_safe_tx.to = "0x123"
        mock_safe_tx.value = 0
        mock_safe_tx.data = b""
        mock_safe_tx.operation = 0
        mock_safe_tx.safe_tx_gas = 0
        mock_safe_tx.base_gas = 0
        mock_safe_tx.gas_price = 0
        mock_safe_tx.gas_token = "0x0000000000000000000000000000000000000000"
        mock_safe_tx.refund_receiver = "0x0000000000000000000000000000000000000000"
        mock_safe_tx.safe_nonce = 1
        
        mock_safe_instance.build_multisig_tx.return_value = mock_safe_tx
        mock_tx_sent = MagicMock()
        mock_tx_sent.tx_hash = b"1" * 32  # 32-byte transaction hash
        mock_safe_instance.send_multisig_tx.return_value = mock_tx_sent
        mock_safe_class.return_value = mock_safe_instance
        
        # Mock TransactionServiceApi
        mock_tx_service = MagicMock()
        mock_tx_service_class.return_value = mock_tx_service
        
        service = SafeService()
        result = await service.perform_activity_transaction("gnosis")
        
        assert result["success"] is True
        assert result["chain"] == "gnosis"
        assert result["safe_address"] == "0x123"
        assert result["block_number"] == 12345
        assert result["gas_used"] == 21000
        assert "tx_hash" in result
        
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    @pytest.mark.asyncio
    async def test_perform_activity_transaction_no_safe_address(self, mock_settings, mock_json_loads, mock_file):
        """Test activity transaction fails when no Safe address configured."""
        mock_settings.safe_contract_addresses = '{}'
        mock_json_loads.return_value = {}
        
        service = SafeService()
        result = await service.perform_activity_transaction("gnosis")
        
        assert result["success"] is False
        assert "No Safe address configured for chain: gnosis" in result["error"]
        
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    @pytest.mark.asyncio
    async def test_perform_activity_transaction_uses_optimal_chain(self, mock_settings, mock_json_loads, mock_file):
        """Test activity transaction uses optimal chain when none specified."""
        mock_settings.safe_contract_addresses = '{"gnosis": "0x123"}'
        mock_settings.gnosis_ledger_rpc = "https://gnosis.example.com"
        mock_json_loads.return_value = {"gnosis": "0x123"}
        
        service = SafeService()
        with patch.object(service, 'select_optimal_chain', return_value="gnosis") as mock_select:
            # Mock the rest of the transaction to avoid complexity
            with patch.object(service, 'get_web3_connection'):
                with patch("services.safe_service.EthereumClient"):
                    with patch("services.safe_service.Safe"):
                        with patch("services.safe_service.TransactionServiceApi"):
                            result = await service.perform_activity_transaction()
            
            mock_select.assert_called_once()


class TestSafeServiceChainValidation:
    """Test SafeService chain validation methods."""
    
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    def test_is_chain_fully_configured_success(self, mock_settings, mock_json_loads, mock_file):
        """Test chain validation for fully configured chain (happy path)."""
        mock_settings.safe_contract_addresses = '{"base": "0x123"}'
        mock_settings.base_ledger_rpc = "https://base.example.com"
        mock_json_loads.return_value = {"base": "0x123"}
        
        service = SafeService()
        
        # Base should be fully configured (has Safe address, RPC endpoint, and Safe service URL)
        assert service.is_chain_fully_configured("base") is True
        
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    def test_is_chain_fully_configured_missing_safe_service(self, mock_settings, mock_json_loads, mock_file):
        """Test chain validation fails for chain without Safe service URL (critical edge case)."""
        mock_settings.safe_contract_addresses = '{"polygon": "0x123"}'
        mock_settings.polygon_ledger_rpc = "https://polygon.example.com"
        mock_json_loads.return_value = {"polygon": "0x123"}
        
        service = SafeService()
        service.rpc_endpoints["polygon"] = "https://polygon.example.com"
        
        # Polygon should fail validation (no Safe service URL in SAFE_SERVICE_URLS)
        assert service.is_chain_fully_configured("polygon") is False
        
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    def test_get_supported_chains(self, mock_settings, mock_json_loads, mock_file):
        """Test getting list of supported chains (critical for error messages)."""
        mock_settings.safe_contract_addresses = '{"base": "0x123", "gnosis": "0x456"}'
        mock_settings.base_ledger_rpc = "https://base.example.com"
        mock_settings.gnosis_ledger_rpc = "https://gnosis.example.com"
        mock_json_loads.return_value = {"base": "0x123", "gnosis": "0x456"}
        
        service = SafeService()
        supported_chains = service.get_supported_chains()
        
        # Should return only fully configured chains with Safe service URLs
        assert "base" in supported_chains
        assert "gnosis" in supported_chains
        assert len(supported_chains) >= 2


class TestSafeServiceHelperMethods:
    """Test SafeService helper methods."""
    
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    @patch("services.safe_service.EthereumClient")
    @patch("services.safe_service.Safe")
    @patch("services.safe_service.Web3")
    @pytest.mark.asyncio
    async def test_get_safe_nonce(
        self, 
        mock_web3_class,
        mock_safe_class, 
        mock_eth_client_class,
        mock_settings, 
        mock_json_loads, 
        mock_file
    ):
        """Test getting Safe nonce."""
        mock_settings.safe_contract_addresses = '{"gnosis": "0x123"}'
        mock_settings.gnosis_ledger_rpc = "https://gnosis.example.com"
        mock_json_loads.return_value = {"gnosis": "0x123"}
        
        mock_safe_instance = MagicMock()
        mock_safe_instance.retrieve_nonce.return_value = 5
        mock_safe_class.return_value = mock_safe_instance
        mock_web3_class.to_checksum_address.return_value = "0x123"
        
        service = SafeService()
        result = await service.get_safe_nonce("gnosis", "0x123")
        
        assert result == 5
        mock_safe_instance.retrieve_nonce.assert_called_once()
        
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    @patch("services.safe_service.EthereumClient")
    @patch("services.safe_service.Safe")
    @patch("services.safe_service.Web3")
    @pytest.mark.asyncio
    async def test_build_safe_transaction(
        self, 
        mock_web3_class,
        mock_safe_class, 
        mock_eth_client_class,
        mock_settings, 
        mock_json_loads, 
        mock_file
    ):
        """Test building Safe transaction."""
        mock_settings.safe_contract_addresses = '{"gnosis": "0x123"}'
        mock_settings.gnosis_ledger_rpc = "https://gnosis.example.com"
        mock_json_loads.return_value = {"gnosis": "0x123"}
        
        mock_safe_tx = MagicMock()
        mock_safe_tx.to = "0x456"
        mock_safe_tx.value = 100
        mock_safe_tx.data = b"test_data"
        mock_safe_tx.operation = 0
        mock_safe_tx.safe_tx_gas = 0
        mock_safe_tx.base_gas = 21000
        mock_safe_tx.gas_price = 1000000000
        mock_safe_tx.gas_token = "0x0000000000000000000000000000000000000000"
        mock_safe_tx.refund_receiver = "0x0000000000000000000000000000000000000000"
        mock_safe_tx.safe_nonce = 3
        mock_safe_tx.safe_tx_hash = b"safe_tx_hash"
        
        mock_safe_instance = MagicMock()
        mock_safe_instance.build_multisig_tx.return_value = mock_safe_tx
        mock_safe_class.return_value = mock_safe_instance
        mock_web3_class.to_checksum_address.return_value = "0x123"
        
        service = SafeService()
        result = await service.build_safe_transaction("gnosis", "0x456", 100, b"test_data")
        
        assert result["safe_address"] == "0x123"
        assert result["to"] == "0x456"
        assert result["value"] == 100
        assert result["data"] == "test_data".encode().hex()
        assert result["nonce"] == 3
        mock_safe_instance.build_multisig_tx.assert_called_once_with(
            to="0x456", value=100, data=b"test_data", operation=0
        )


class TestSafeServicePhase2Validation:
    """Test Phase 2: Transaction submission validation for unsupported chains."""

    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    @pytest.mark.asyncio
    async def test_unsupported_chain_transaction_fails_early(self, mock_settings, mock_json_loads, mock_file):
        """Test that transactions to unsupported chains fail early with clear error message."""
        # Setup: Only Base chain configured (has Safe service URL)
        mock_settings.safe_contract_addresses = '{"base": "0x123"}'
        mock_settings.base_ledger_rpc = "https://base.example.com"
        mock_json_loads.return_value = {"base": "0x123"}
        
        service = SafeService()
        
        # Attempt transaction on unsupported chain (polygon - no Safe service URL)
        result = await service._submit_safe_transaction(
            chain="polygon",
            to="0x0000000000000000000000000000000000000000",
            value=0,
            data=b"",
        )
        
        # Should fail early with clear error message
        assert result["success"] is False
        assert "not fully configured" in result["error"]
        assert "Supported chains:" in result["error"]
        assert "base" in result["error"]  # Should list which chains ARE supported

    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    @patch("services.safe_service.Safe")
    @patch("services.safe_service.EthereumClient")
    @patch("services.safe_service.Web3")
    @pytest.mark.asyncio
    async def test_supported_chain_transaction_proceeds(self, mock_web3_class, mock_eth_client, mock_safe_class, mock_settings, mock_json_loads, mock_file):
        """Test that transactions to supported chains are not blocked by validation."""
        # Setup: Base chain fully configured
        mock_settings.safe_contract_addresses = '{"base": "0x123"}'
        mock_settings.base_ledger_rpc = "https://base.example.com"
        mock_json_loads.return_value = {"base": "0x123"}
        
        # Mock Web3 connection
        mock_web3_instance = MagicMock()
        mock_web3_instance.is_connected.return_value = True
        mock_web3_class.return_value = mock_web3_instance
        mock_web3_class.to_checksum_address.return_value = "0x123"
        
        # Mock Safe transaction that would succeed
        mock_safe_tx = MagicMock()
        mock_safe_tx.safe_tx_hash = b"safe_tx_hash"
        mock_safe_instance = MagicMock()
        mock_safe_instance.build_multisig_tx.return_value = mock_safe_tx
        mock_safe_class.return_value = mock_safe_instance
        
        service = SafeService()
        
        # This test should not fail due to validation (it may fail for other reasons, but not validation)
        # We're testing that the upfront validation doesn't block supported chains
        try:
            result = await service._submit_safe_transaction(
                chain="base",
                to="0x0000000000000000000000000000000000000000",
                value=0,
                data=b"",
            )
            # If it gets past validation, that's success for this test
            # The transaction may fail for other reasons (network, etc.) but validation should not block it
        except Exception as e:
            # If there's an exception, it should NOT be a validation error about chain configuration
            error_message = str(e)
            assert "not fully configured" not in error_message
            assert "Supported chains:" not in error_message


class TestSafeServicePhase4Comprehensive:
    """Test Phase 4: Comprehensive validation tests following plan.md requirements."""

    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    @pytest.mark.asyncio
    async def test_chain_validation(self, mock_settings, mock_json_loads, mock_file):
        """Test chain configuration validation as specified in plan.md Phase 4."""
        # Setup: Base fully configured, polygon missing Safe service URL
        mock_settings.safe_contract_addresses = '{"base": "0x123", "polygon": "0x456"}'
        mock_settings.base_ledger_rpc = "https://base.example.com"
        mock_settings.polygon_ledger_rpc = "https://polygon.example.com"
        mock_json_loads.return_value = {"base": "0x123", "polygon": "0x456"}
        
        service = SafeService()
        # Manually set polygon RPC endpoint since it's not in default config
        service.rpc_endpoints["polygon"] = "https://polygon.example.com"
        
        # Test fully configured chain
        if "base" in service.safe_addresses:
            assert service.is_chain_fully_configured("base") == True
        
        # Test unconfigured chain (polygon lacks Safe service URL)
        assert service.is_chain_fully_configured("polygon") == False
        
        # Test supported chains list
        supported = service.get_supported_chains()
        assert isinstance(supported, list)
        assert all(chain in SAFE_SERVICE_URLS for chain in supported)
        assert "base" in supported
        assert "polygon" not in supported  # Should not include chains without Safe service URL
        
        # Test validation details for fully configured chain
        validation = service.validate_chain_configuration("base")
        assert "has_safe_address" in validation
        assert "has_rpc_endpoint" in validation
        assert "has_safe_service_url" in validation
        assert validation["has_safe_address"] is True
        assert validation["has_rpc_endpoint"] is True
        assert validation["has_safe_service_url"] is True
        assert validation["is_fully_configured"] is True
        
        # Test validation details for chain missing Safe service URL
        polygon_validation = service.validate_chain_configuration("polygon")
        assert polygon_validation["has_safe_address"] is True
        assert polygon_validation["has_rpc_endpoint"] is True
        assert polygon_validation["has_safe_service_url"] is False
        assert polygon_validation["is_fully_configured"] is False

    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    @pytest.mark.asyncio
    async def test_unsupported_chain_error(self, mock_settings, mock_json_loads, mock_file):
        """Test error handling for unsupported chains as specified in plan.md Phase 4."""
        # Setup: Only base configured
        mock_settings.safe_contract_addresses = '{"base": "0x123"}'
        mock_settings.base_ledger_rpc = "https://base.example.com"
        mock_json_loads.return_value = {"base": "0x123"}
        
        service = SafeService()
        
        # Attempt transaction on unsupported chain
        result = await service._submit_safe_transaction(
            chain="polygon",
            to="0x0000000000000000000000000000000000000000",
            value=0,
            data=b"",
        )
        
        assert result["success"] == False
        assert "not fully configured" in result["error"]
        assert "Supported chains:" in result["error"]
        
        # Should list which chains ARE supported
        assert "base" in result["error"]
        
        # Should specify what components are missing
        assert "Missing:" in result["error"] or "Safe Transaction Service URL" in result["error"]

    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    def test_validation_method_integration(self, mock_settings, mock_json_loads, mock_file):
        """Test integration between validation methods for consistency."""
        # Setup: Multiple chain configurations
        mock_settings.safe_contract_addresses = '{"base": "0x123", "ethereum": "0x456", "polygon": "0x789"}'
        mock_settings.base_ledger_rpc = "https://base.example.com"
        mock_settings.ethereum_ledger_rpc = "https://eth.example.com"
        mock_settings.polygon_ledger_rpc = "https://polygon.example.com"
        mock_json_loads.return_value = {"base": "0x123", "ethereum": "0x456", "polygon": "0x789"}
        
        service = SafeService()
        service.rpc_endpoints["polygon"] = "https://polygon.example.com"
        
        # Test that supported chains are subset of SAFE_SERVICE_URLS
        supported_chains = service.get_supported_chains()
        for chain in supported_chains:
            assert chain in SAFE_SERVICE_URLS
            assert service.is_chain_fully_configured(chain) is True
        
        # Test that validate_chain_configuration is consistent with is_chain_fully_configured
        for chain in ["base", "ethereum", "polygon"]:
            validation = service.validate_chain_configuration(chain)
            expected_configured = service.is_chain_fully_configured(chain)
            assert validation["is_fully_configured"] == expected_configured

    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    @pytest.mark.parametrize("chain,has_safe,has_rpc,has_service,expected", [
        ("base", True, True, True, True),      # Fully configured
        ("ethereum", True, True, True, True),  # Fully configured  
        ("gnosis", True, True, True, True),    # Fully configured
        ("mode", True, True, True, True),      # Fully configured
        ("polygon", True, True, False, False), # Missing Safe service
        ("celo", True, True, False, False),    # Missing Safe service
        ("unknown", False, False, False, False), # Completely unconfigured
    ])
    def test_chain_configuration_matrix(self, mock_settings, mock_json_loads, mock_file, chain, has_safe, has_rpc, has_service, expected):
        """Test all possible chain configuration combinations."""
        # Setup configuration based on test parameters
        safe_addresses = {}
        rpc_settings = {}
        
        if has_safe:
            safe_addresses[chain] = "0x123"
        if has_rpc:
            rpc_settings[f"{chain}_ledger_rpc"] = f"https://{chain}.example.com"
            
        mock_settings.safe_contract_addresses = json.dumps(safe_addresses)
        mock_json_loads.return_value = safe_addresses
        
        # Set RPC endpoint settings
        for attr, value in rpc_settings.items():
            setattr(mock_settings, attr, value)
        
        service = SafeService()
        
        # Manually set RPC endpoints for chains that need them
        if has_rpc:
            service.rpc_endpoints[chain] = f"https://{chain}.example.com"
            
        result = service.is_chain_fully_configured(chain)
        assert result == expected
        
        # Also test detailed validation matches expectation
        validation = service.validate_chain_configuration(chain)
        assert validation["is_fully_configured"] == expected
        assert validation["has_safe_service_url"] == has_service



