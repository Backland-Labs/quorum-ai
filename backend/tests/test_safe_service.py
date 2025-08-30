"""Tests for SafeService."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from web3 import Web3
import json

from services.safe_service import SafeService



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



