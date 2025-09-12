"""Comprehensive test suite for SafeService to achieve 90%+ coverage."""

import json
import sys
import pytest
import time
import os
from unittest.mock import Mock, patch, mock_open, AsyncMock, MagicMock
from web3 import Web3
from eth_account import Account


class MockEASAttestationData:
    """Mock EAS attestation data for testing."""
    def __init__(self, agent="0x4567890123456789012345678901234567890123",
                 space_id="test.eth", proposal_id="prop123", vote_choice=1,
                 snapshot_sig="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                 timestamp=1234567890, run_id="run123", confidence=95):
        self.agent = agent
        self.space_id = space_id
        self.proposal_id = proposal_id
        self.vote_choice = vote_choice
        self.snapshot_sig = snapshot_sig
        self.timestamp = timestamp
        self.run_id = run_id
        self.confidence = confidence


def setup_safe_service_mocks():
    """Setup all required mocks for SafeService."""
    # Mock all modules that could cause import issues
    modules_to_mock = {
        'config': Mock(),
        'models': Mock(),
        'utils.eas_signature': Mock(),
        'logging_config': Mock(),
        'utils.web3_provider': Mock(),
        'utils.abi_loader': Mock(),
        'services.agent_run_service': Mock(),
        'safe_eth.eth': Mock(),
        'safe_eth.safe': Mock(),
        'safe_eth.safe.api': Mock(),
    }
    
    return patch.dict('sys.modules', modules_to_mock)


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock()
    settings.safe_contract_addresses = '{"base": "0x1234567890123456789012345678901234567890", "ethereum": "0x9876543210987654321098765432109876543210"}'
    settings.get_base_rpc_endpoint.return_value = "https://base-rpc.com"
    settings.ethereum_ledger_rpc = "https://eth-rpc.com"
    settings.gnosis_ledger_rpc = "https://gnosis-rpc.com"
    settings.mode_ledger_rpc = "https://mode-rpc.com"
    settings.eas_contract_address = "0xeas123"
    settings.eas_schema_uid = "0x" + "a" * 64
    settings.base_safe_address = "0x1234567890123456789012345678901234567890"
    settings.attestation_tracker_address = None
    settings.attestation_chain = "base"
    return settings


class TestSafeServiceComprehensive:
    """Comprehensive test suite for SafeService."""
    
    def get_safe_service(self, mock_settings):
        """Get SafeService instance with mocked dependencies."""
        with setup_safe_service_mocks(), \
             patch('services.safe_service.settings', mock_settings), \
             patch('services.safe_service.setup_pearl_logger'), \
             patch('builtins.open', mock_open(read_data='ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80')):
            
            from services.safe_service import SafeService
            return SafeService()

    def test_initialization_error(self):
        """Test SafeService initialization error when base RPC is not set."""
        with setup_safe_service_mocks():
            mock_settings = Mock()
            mock_settings.get_base_rpc_endpoint.return_value = None
            
            with patch('services.safe_service.settings', mock_settings):
                with pytest.raises(RuntimeError, match="Safe service is disabled in configuration"):
                    from services.safe_service import SafeService

    def test_web3_connection_no_rpc_endpoint(self, mock_settings):
        """Test Web3 connection with no RPC endpoint configured."""
        service = self.get_safe_service(mock_settings)
        
        with pytest.raises(ValueError, match="No RPC endpoint configured for chain: unknown"):
            service.get_web3_connection("unknown")

    def test_web3_connection_failed(self, mock_settings):
        """Test Web3 connection failure."""
        service = self.get_safe_service(mock_settings)
        
        with patch('services.safe_service.Web3') as mock_web3_class:
            mock_web3 = Mock()
            mock_web3.is_connected.return_value = False
            mock_web3_class.return_value = mock_web3
            
            with patch.object(service, '_rate_limit_base_rpc'):
                with pytest.raises(ConnectionError, match="Failed to connect to base network"):
                    service.get_web3_connection("base")

    def test_select_optimal_chain_comprehensive(self, mock_settings):
        """Test comprehensive chain selection scenarios."""
        service = self.get_safe_service(mock_settings)
        
        # Test normal case - should return gnosis as first priority
        with patch.object(service, 'is_chain_fully_configured', return_value=True):
            chain = service.select_optimal_chain()
            assert chain == "gnosis"  # First in priority order
        
        # Test fallback when gnosis not available
        def mock_config(chain):
            return chain in ["base", "ethereum"]
        
        with patch.object(service, 'is_chain_fully_configured', side_effect=mock_config):
            chain = service.select_optimal_chain()
            assert chain == "base"  # Next in priority after gnosis
        
        # Test when only ethereum is available
        with patch.object(service, 'is_chain_fully_configured', side_effect=lambda c: c == "ethereum"):
            chain = service.select_optimal_chain()
            assert chain == "ethereum"
        
        # Test no available chains - should check get_supported_chains fallback
        with patch.object(service, 'is_chain_fully_configured', return_value=False), \
             patch.object(service, 'get_supported_chains', return_value=["base"]):
            chain = service.select_optimal_chain()
            assert chain == "base"
        
        # Test complete failure
        with patch.object(service, 'is_chain_fully_configured', return_value=False), \
             patch.object(service, 'get_supported_chains', return_value=[]):
            with pytest.raises(ValueError, match="No valid chain configuration found"):
                service.select_optimal_chain()

    @pytest.mark.asyncio
    async def test_submit_safe_transaction_comprehensive(self, mock_settings):
        """Test comprehensive Safe transaction submission."""
        service = self.get_safe_service(mock_settings)
        
        # Test invalid chain configuration
        with patch.object(service, 'is_chain_fully_configured', return_value=False), \
             patch.object(service, 'validate_chain_configuration') as mock_validate, \
             patch.object(service, 'get_supported_chains', return_value=["base"]):
            
            mock_validate.return_value = {
                'has_safe_address': False,
                'has_rpc_endpoint': True,
                'has_safe_service_url': True
            }
            
            result = await service._submit_safe_transaction(
                chain="unknown", to="0x456", value=0, data=b""
            )
            
            assert result["success"] is False
            assert "not fully configured" in result["error"]

        # Test successful transaction
        with patch('services.safe_service.EthereumClient') as mock_eth_client, \
             patch('services.safe_service.Safe') as mock_safe_class, \
             patch('services.safe_service.TransactionServiceApi') as mock_tx_service, \
             patch('services.safe_service.Web3') as mock_web3_class:
            
            # Mock transaction receipt
            mock_receipt = {
                "blockNumber": 12345,
                "gasUsed": 100000,
                "status": 1,
                "transactionHash": "0xtxhash"
            }
            
            # Mock Web3
            mock_w3 = Mock()
            mock_w3.eth.wait_for_transaction_receipt.return_value = mock_receipt
            mock_web3_class.return_value = mock_w3
            
            # Mock Safe transaction
            mock_safe_tx = Mock()
            mock_safe_tx.to = "0x456"
            mock_safe_tx.value = 0
            mock_safe_tx.data = b"test"
            mock_safe_tx.operation = 0
            mock_safe_tx.safe_tx_gas = 100000
            mock_safe_tx.base_gas = 50000
            mock_safe_tx.gas_price = 1000000000
            mock_safe_tx.gas_token = "0x0000000000000000000000000000000000000000"
            mock_safe_tx.refund_receiver = "0x0000000000000000000000000000000000000000"
            mock_safe_tx.safe_nonce = 5
            mock_safe_tx.safe_tx_hash = Mock()
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
            
            # Mock transaction service
            mock_service = Mock()
            mock_tx_service.return_value = mock_service
            
            with patch.object(service, '_rate_limit_base_rpc'), \
                 patch.object(service, 'is_chain_fully_configured', return_value=True):
                
                result = await service._submit_safe_transaction(
                    chain="base", to="0x456", value=0, data=b"test"
                )
            
            assert result["success"] is True
            assert result["tx_hash"] == "0xtxhash"
            assert result["chain"] == "base"
            assert result["block_number"] == 12345
            assert result["gas_used"] == 100000

        # Test simulation failure
        with patch('services.safe_service.EthereumClient'), \
             patch('services.safe_service.Safe') as mock_safe_class, \
             patch('services.safe_service.TransactionServiceApi'), \
             patch('services.safe_service.Web3'):
            
            mock_safe_tx = Mock()
            mock_safe_tx.to = "0x456"
            mock_safe_tx.value = 0
            mock_safe_tx.data = b"test"
            mock_safe_tx.operation = 0
            mock_safe_tx.safe_tx_gas = 100000
            mock_safe_tx.base_gas = 50000
            mock_safe_tx.gas_price = 1000000000
            mock_safe_tx.gas_token = "0x0000000000000000000000000000000000000000"
            mock_safe_tx.refund_receiver = "0x0000000000000000000000000000000000000000"
            mock_safe_tx.safe_nonce = 5
            mock_safe_tx.safe_tx_hash = Mock()
            mock_safe_tx.safe_tx_hash.hex.return_value = "0xsafetx"
            mock_safe_tx.signatures = b"signature"
            mock_safe_tx.call.side_effect = Exception("Execution reverted")
            
            mock_safe = Mock()
            mock_safe.build_multisig_tx.return_value = mock_safe_tx
            mock_safe_class.return_value = mock_safe
            
            with patch.object(service, '_rate_limit_base_rpc'), \
                 patch.object(service, 'is_chain_fully_configured', return_value=True):
                
                result = await service._submit_safe_transaction(
                    chain="base", to="0x456", value=0, data=b"test"
                )
            
            assert result["success"] is False
            assert "Transaction would revert" in result["error"]
            assert result["simulation_failed"] is True

        # Test transaction revert
        with patch('services.safe_service.EthereumClient'), \
             patch('services.safe_service.Safe') as mock_safe_class, \
             patch('services.safe_service.TransactionServiceApi'), \
             patch('services.safe_service.Web3') as mock_web3_class:
            
            # Mock failed transaction receipt
            mock_receipt = {
                "blockNumber": 12345,
                "gasUsed": 100000,
                "status": 0,  # Failed status
                "transactionHash": "0xtxhash"
            }
            
            mock_w3 = Mock()
            mock_w3.eth.wait_for_transaction_receipt.return_value = mock_receipt
            mock_web3_class.return_value = mock_w3
            
            mock_safe_tx = Mock()
            mock_safe_tx.to = "0x456"
            mock_safe_tx.value = 0
            mock_safe_tx.data = b"test"
            mock_safe_tx.operation = 0
            mock_safe_tx.safe_tx_gas = 100000
            mock_safe_tx.base_gas = 50000
            mock_safe_tx.gas_price = 1000000000
            mock_safe_tx.gas_token = "0x0000000000000000000000000000000000000000"
            mock_safe_tx.refund_receiver = "0x0000000000000000000000000000000000000000"
            mock_safe_tx.safe_nonce = 5
            mock_safe_tx.safe_tx_hash = Mock()
            mock_safe_tx.safe_tx_hash.hex.return_value = "0xsafetx"
            mock_safe_tx.signatures = b"signature"
            mock_safe_tx.call = Mock()  # Simulation succeeds
            
            mock_safe = Mock()
            mock_safe.build_multisig_tx.return_value = mock_safe_tx
            mock_tx_hash = Mock()
            mock_tx_hash.hex.return_value = "0xtxhash"
            mock_safe.send_multisig_tx.return_value.tx_hash = mock_tx_hash
            mock_safe_class.return_value = mock_safe
            
            with patch.object(service, '_rate_limit_base_rpc'), \
                 patch.object(service, 'is_chain_fully_configured', return_value=True):
                
                result = await service._submit_safe_transaction(
                    chain="base", to="0x456", value=0, data=b"test"
                )
            
            assert result["success"] is False
            assert result["error"] == "Transaction reverted"
            assert result["tx_hash"] == "0xtxhash"

        # Test exception handling
        with patch('services.safe_service.EthereumClient'), \
             patch('services.safe_service.Safe') as mock_safe_class:
            
            mock_safe_class.side_effect = Exception("Connection failed")
            
            with patch.object(service, '_rate_limit_base_rpc'), \
                 patch.object(service, 'is_chain_fully_configured', return_value=True):
                
                result = await service._submit_safe_transaction(
                    chain="base", to="0x456", value=0, data=b"test"
                )
            
            assert result["success"] is False
            assert "Connection failed" in result["error"]

    @pytest.mark.asyncio
    async def test_perform_activity_transaction(self, mock_settings):
        """Test perform_activity_transaction method."""
        service = self.get_safe_service(mock_settings)
        
        # Test automatic chain selection
        with patch.object(service, 'select_optimal_chain', return_value="base"), \
             patch.object(service, '_submit_safe_transaction', new_callable=AsyncMock) as mock_submit:
            
            mock_submit.return_value = {"success": True, "tx_hash": "0xtest"}
            
            result = await service.perform_activity_transaction()
            
            mock_submit.assert_called_once_with(
                chain="base",
                to="0x1234567890123456789012345678901234567890",
                value=0,
                data=b"",
                operation=0
            )
            assert result["success"] is True

        # Test specific chain
        with patch.object(service, '_submit_safe_transaction', new_callable=AsyncMock) as mock_submit:
            mock_submit.return_value = {"success": True, "tx_hash": "0xtest"}
            
            result = await service.perform_activity_transaction(chain="base")
            
            mock_submit.assert_called_once_with(
                chain="base",
                to="0x1234567890123456789012345678901234567890",
                value=0,
                data=b"",
                operation=0
            )

        # Test missing Safe address
        result = await service.perform_activity_transaction(chain="unknown")
        
        assert result["success"] is False
        assert "No Safe address configured" in result["error"]

    @pytest.mark.asyncio
    async def test_get_safe_nonce(self, mock_settings):
        """Test get_safe_nonce method."""
        service = self.get_safe_service(mock_settings)
        
        with patch('services.safe_service.EthereumClient'), \
             patch('services.safe_service.Safe') as mock_safe_class:
            
            mock_safe = Mock()
            mock_safe.retrieve_nonce.return_value = 42
            mock_safe_class.return_value = mock_safe
            
            with patch.object(service, '_rate_limit_base_rpc'):
                nonce = await service.get_safe_nonce("base", "0x1234567890123456789012345678901234567890")
                
            assert nonce == 42
            mock_safe.retrieve_nonce.assert_called_once()

    @pytest.mark.asyncio
    async def test_build_safe_transaction(self, mock_settings):
        """Test build_safe_transaction method."""
        service = self.get_safe_service(mock_settings)
        
        # Test missing Safe address
        with pytest.raises(ValueError, match="No Safe address configured for chain: unknown"):
            await service.build_safe_transaction(chain="unknown", to="0x456")

        # Test successful build
        with patch('services.safe_service.EthereumClient'), \
             patch('services.safe_service.Safe') as mock_safe_class:
            
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
            mock_safe_tx.safe_tx_hash = Mock()
            mock_safe_tx.safe_tx_hash.hex.return_value = "0xabcd"
            
            mock_safe = Mock()
            mock_safe.build_multisig_tx.return_value = mock_safe_tx
            mock_safe_class.return_value = mock_safe
            
            with patch.object(service, '_rate_limit_base_rpc'):
                result = await service.build_safe_transaction(
                    chain="base", to="0x456", value=100, data=b"test_data"
                )
            
            assert result["safe_address"] == "0x1234567890123456789012345678901234567890"
            assert result["to"] == "0x456"
            assert result["value"] == 100
            assert result["data"] == b"test_data".hex()
            assert result["nonce"] == 5

    @pytest.mark.asyncio
    async def test_create_eas_attestation_comprehensive(self, mock_settings):
        """Test comprehensive EAS attestation creation."""
        service = self.get_safe_service(mock_settings)
        attestation_data = MockEASAttestationData()
        
        # Test missing EAS configuration
        with patch('services.safe_service.settings') as mock_settings_patch:
            mock_settings_patch.eas_contract_address = None
            mock_settings_patch.eas_schema_uid = None
            
            result = await service.create_eas_attestation(attestation_data)
            
            assert result["success"] is False
            assert "EAS configuration missing" in result["error"]

        # Test missing Safe address
        with patch('services.safe_service.settings') as mock_settings_patch:
            mock_settings_patch.eas_contract_address = "0xeas123"
            mock_settings_patch.eas_schema_uid = "0x" + "a" * 64
            mock_settings_patch.base_safe_address = None
            
            result = await service.create_eas_attestation(attestation_data)
            
            assert result["success"] is False
            assert "Base Safe address not configured" in result["error"]

        # Test successful creation
        with patch.object(service, '_build_eas_attestation_tx') as mock_build_tx, \
             patch.object(service, '_submit_safe_transaction', new_callable=AsyncMock) as mock_submit:
            
            mock_build_tx.return_value = {
                "to": "0xeas123",
                "data": "0x1234abcd",
                "value": 0
            }
            mock_submit.return_value = {"success": True, "tx_hash": "0xtxhash"}
            
            result = await service.create_eas_attestation(attestation_data)
            
            assert result["success"] is True
            assert result["safe_tx_hash"] == "0xtxhash"
            mock_submit.assert_called_once()

        # Test exception handling
        with patch.object(service, '_build_eas_attestation_tx') as mock_build_tx:
            mock_build_tx.side_effect = Exception("Contract error")
            
            result = await service.create_eas_attestation(attestation_data)
            
            assert result["success"] is False
            assert "Contract error" in result["error"]

    def test_build_eas_attestation_tx(self, mock_settings):
        """Test _build_eas_attestation_tx method."""
        service = self.get_safe_service(mock_settings)
        attestation_data = MockEASAttestationData()
        
        # Test with AttestationTracker
        with patch('services.safe_service.settings') as mock_settings_patch:
            mock_settings_patch.attestation_tracker_address = "0xtracker123"
            mock_settings_patch.eas_contract_address = "0xeas123"
            
            with patch.object(service, '_build_delegated_attestation_tx') as mock_build:
                mock_build.return_value = {"to": "0xtracker123", "data": "0x1234", "value": 0}
                
                result = service._build_eas_attestation_tx(attestation_data)
                
                assert result["to"] == "0xtracker123"
                mock_build.assert_called_once_with(
                    attestation_data,
                    target_address="0xtracker123",
                    abi_name="attestation_tracker"
                )

        # Test with direct EAS (no tracker)
        with patch('services.safe_service.settings') as mock_settings_patch:
            mock_settings_patch.attestation_tracker_address = None
            mock_settings_patch.eas_contract_address = "0xeas123"
            
            with patch.object(service, '_build_delegated_attestation_tx') as mock_build:
                mock_build.return_value = {"to": "0xeas123", "data": "0x5678", "value": 0}
                
                result = service._build_eas_attestation_tx(attestation_data)
                
                assert result["to"] == "0xeas123"
                mock_build.assert_called_once_with(
                    attestation_data,
                    target_address="0xeas123",
                    abi_name="eip712proxy"
                )

        # Test missing EAS contract address
        with patch('services.safe_service.settings') as mock_settings_patch:
            mock_settings_patch.attestation_tracker_address = None
            mock_settings_patch.eas_contract_address = None
            
            with pytest.raises(ValueError, match="EAS contract address not configured"):
                service._build_eas_attestation_tx(attestation_data)

    def test_build_delegated_attestation_tx(self, mock_settings):
        """Test _build_delegated_attestation_tx method."""
        service = self.get_safe_service(mock_settings)
        attestation_data = MockEASAttestationData()
        
        # Mock dependencies
        mock_w3 = Mock()
        mock_w3.eth.get_block.return_value = {"timestamp": 1234567900, "number": 12345}
        mock_w3.eth.chain_id = 8453
        
        mock_contract = Mock()
        mock_contract.functions.attestByDelegation.return_value.build_transaction.return_value = {
            "to": "0xtest123",
            "data": "0xabcd1234",
            "value": 0,
            "gas": 1000000
        }
        mock_w3.eth.contract.return_value = mock_contract
        
        mock_abi = [{"name": "attestByDelegation"}]
        
        with patch('utils.web3_provider.get_w3', return_value=mock_w3), \
             patch('utils.abi_loader.load_abi', return_value=mock_abi), \
             patch('services.safe_service.settings') as mock_settings_patch, \
             patch.object(service, '_generate_eas_delegated_signature') as mock_generate_sig:
            
            mock_settings_patch.attestation_chain = "base"
            mock_settings_patch.eas_schema_uid = "0x" + "a" * 64
            mock_settings_patch.base_safe_address = "0x1234567890123456789012345678901234567890"
            mock_settings_patch.eas_contract_address = "0xeas123"
            
            mock_generate_sig.return_value = b"\x01" * 65  # 65-byte signature
            
            # Test AttestationTracker
            with patch('builtins.open', mock_open(read_data='ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80')), \
                 patch.dict(os.environ, {'ETHEREUM_PRIVATE_KEY': 'ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80'}):
                
                result = service._build_delegated_attestation_tx(
                    attestation_data, "0xtracker123", "attestation_tracker"
                )
                
                assert result["to"] == "0xtest123"
                assert result["data"] == "0xabcd1234"
                assert result["value"] == 0
                
                # Verify contract function was called
                mock_contract.functions.attestByDelegation.assert_called_once()
            
            # Test EIP712Proxy
            mock_contract.functions.attestByDelegation.reset_mock()
            
            result = service._build_delegated_attestation_tx(
                attestation_data, "0xeas123", "eip712proxy"
            )
            
            assert result["to"] == "0xtest123"
            assert result["data"] == "0xabcd1234"
            assert result["value"] == 0

    def test_encode_attestation_data(self, mock_settings):
        """Test _encode_attestation_data method."""
        service = self.get_safe_service(mock_settings)
        attestation_data = MockEASAttestationData()
        
        with patch('services.safe_service.Web3') as mock_web3_class:
            mock_w3 = Mock()
            mock_codec = Mock()
            mock_codec.encode.return_value = b"encoded_attestation_data"
            mock_w3.codec = mock_codec
            mock_web3_class.return_value = mock_w3
            
            result = service._encode_attestation_data(attestation_data)
            
            assert result == b"encoded_attestation_data"
            
            # Verify encoding was called with correct parameters
            mock_codec.encode.assert_called_once()
            call_args = mock_codec.encode.call_args
            assert call_args[0][0] == ["address", "string", "string", "uint8", "string", "uint256", "string", "uint8"]
            assert call_args[0][1][0] == "0x4567890123456789012345678901234567890123"  # checksummed address
            assert call_args[0][1][1] == "test.eth"  # space_id
            assert call_args[0][1][2] == "prop123"  # proposal_id
            assert call_args[0][1][3] == 1  # vote_choice
            assert call_args[0][1][4] == "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"  # snapshot_sig
            assert call_args[0][1][5] == 1234567890  # timestamp
            assert call_args[0][1][6] == "run123"  # run_id
            assert call_args[0][1][7] == 95  # confidence

    def test_get_web3_instance_comprehensive(self, mock_settings):
        """Test _get_web3_instance method."""
        service = self.get_safe_service(mock_settings)
        
        # Test missing RPC endpoint
        with pytest.raises(ValueError, match="No RPC endpoint configured for chain: unknown"):
            service._get_web3_instance("unknown")
        
        # Test successful creation
        with patch('services.safe_service.Web3') as mock_web3_class:
            mock_web3 = Mock()
            mock_web3_class.return_value = mock_web3
            
            with patch.object(service, '_rate_limit_base_rpc') as mock_rate_limit:
                result = service._get_web3_instance("base")
                
                assert result == mock_web3
                mock_rate_limit.assert_called_once_with("https://base-rpc.com")

    def test_generate_eas_delegated_signature(self, mock_settings):
        """Test _generate_eas_delegated_signature method."""
        service = self.get_safe_service(mock_settings)
        
        request_data = {
            "schema": b"\x01" * 32,
            "recipient": "0x4567890123456789012345678901234567890123",
            "deadline": 1234567890,
            "data": b"test_request_data"
        }
        
        mock_w3 = Mock()
        mock_w3.eth.chain_id = 8453
        
        with patch('services.safe_service.generate_eas_delegated_signature') as mock_generate_sig, \
             patch('builtins.open', mock_open(read_data='ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80')):
            
            mock_signature = b"\x01" * 65
            mock_generate_sig.return_value = mock_signature
            
            result = service._generate_eas_delegated_signature(
                request_data, mock_w3, "0xeas123"
            )
            
            assert result == mock_signature
            mock_generate_sig.assert_called_once_with(
                request_data=request_data,
                w3=mock_w3,
                eas_contract_address="0xeas123",
                private_key="ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])