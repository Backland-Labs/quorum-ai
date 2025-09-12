"""Full coverage test for SafeService without import conflicts."""

import sys
import pytest
import asyncio
import json
from unittest.mock import Mock, patch, mock_open, AsyncMock, MagicMock


class MockEASAttestationData:
    """Mock EAS attestation data for testing."""
    def __init__(self):
        self.agent = "0x4567890123456789012345678901234567890123"
        self.space_id = "test.eth"
        self.proposal_id = "prop123"
        self.vote_choice = 1
        self.snapshot_sig = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        self.timestamp = 1234567890
        self.run_id = "run123"
        self.confidence = 95


def get_mocked_safe_service():
    """Get SafeService with all dependencies mocked."""
    # Mock all the modules and dependencies
    with patch.dict('sys.modules', {
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
    }), \
    patch('services.safe_service.setup_pearl_logger'), \
    patch('builtins.open', mock_open(read_data='ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80')):
        
        # Mock settings
        mock_settings = Mock()
        mock_settings.safe_contract_addresses = '{"base": "0x1234567890123456789012345678901234567890", "ethereum": "0x9876543210987654321098765432109876543210"}'
        mock_settings.get_base_rpc_endpoint.return_value = "https://base-rpc.com"
        mock_settings.ethereum_ledger_rpc = "https://eth-rpc.com"
        mock_settings.gnosis_ledger_rpc = "https://gnosis-rpc.com"  
        mock_settings.mode_ledger_rpc = "https://mode-rpc.com"
        mock_settings.eas_contract_address = "0xeas123"
        mock_settings.eas_schema_uid = "0x" + "a" * 64
        mock_settings.base_safe_address = "0x1234567890123456789012345678901234567890"
        mock_settings.attestation_tracker_address = None
        mock_settings.attestation_chain = "base"
        
        with patch('services.safe_service.settings', mock_settings):
            from services.safe_service import SafeService
            return SafeService()


def test_initialization_error():
    """Test SafeService initialization error when base RPC is not set."""
    with patch.dict('sys.modules', {
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
    }):
        mock_settings = Mock()
        mock_settings.get_base_rpc_endpoint.return_value = None
        
        with patch('services.safe_service.settings', mock_settings):
            with pytest.raises(RuntimeError, match="Safe service is disabled in configuration"):
                from services.safe_service import SafeService


def test_chain_configuration_methods():
    """Test chain configuration validation methods."""
    service = get_mocked_safe_service()
    
    # Test is_chain_fully_configured
    assert service.is_chain_fully_configured("base") is True
    assert service.is_chain_fully_configured("ethereum") is True
    assert service.is_chain_fully_configured("unknown") is False
    
    # Test get_supported_chains
    supported = service.get_supported_chains()
    assert "base" in supported
    assert "ethereum" in supported
    
    # Test validate_chain_configuration
    validation = service.validate_chain_configuration("base")
    assert validation["chain"] == "base"
    assert validation["has_safe_address"] is True
    assert validation["has_rpc_endpoint"] is True
    assert validation["has_safe_service_url"] is True
    assert validation["is_fully_configured"] is True
    
    # Test unsupported chain
    validation = service.validate_chain_configuration("unsupported")
    assert validation["has_safe_service_url"] is False
    assert validation["is_fully_configured"] is False


def test_web3_connection():
    """Test Web3 connection methods."""
    service = get_mocked_safe_service()
    
    # Test missing RPC endpoint
    with pytest.raises(ValueError, match="No RPC endpoint configured for chain: unknown"):
        service.get_web3_connection("unknown")
    
    # Test connection failure
    with patch('services.safe_service.Web3') as mock_web3_class:
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = False
        mock_web3_class.return_value = mock_web3
        
        with patch.object(service, '_rate_limit_base_rpc'):
            with pytest.raises(ConnectionError, match="Failed to connect to base network"):
                service.get_web3_connection("base")
    
    # Test successful connection
    with patch('services.safe_service.Web3') as mock_web3_class:
        mock_web3 = Mock()
        mock_web3.is_connected.return_value = True
        mock_web3_class.return_value = mock_web3
        
        with patch.object(service, '_rate_limit_base_rpc'):
            w3 = service.get_web3_connection("base")
            assert w3 == mock_web3
            assert service._web3_connections["base"] == mock_web3
    
    # Test cached connection
    cached_w3 = service.get_web3_connection("base")
    assert cached_w3 == mock_web3


def test_rate_limiting():
    """Test Base RPC rate limiting."""
    service = get_mocked_safe_service()
    
    with patch('services.safe_service.time.sleep') as mock_sleep:
        # Test Base mainnet URL - should trigger rate limiting
        service._rate_limit_base_rpc("https://mainnet.base.org/rpc")
        mock_sleep.assert_called_once_with(1.0)
        
        # Test non-Base URL - should not trigger rate limiting
        mock_sleep.reset_mock()
        service._rate_limit_base_rpc("https://ethereum-rpc.com")
        mock_sleep.assert_not_called()


def test_chain_selection():
    """Test optimal chain selection."""
    service = get_mocked_safe_service()
    
    # Test normal selection (gnosis first)
    with patch.object(service, 'is_chain_fully_configured', return_value=True):
        chain = service.select_optimal_chain()
        assert chain == "gnosis"
    
    # Test fallback when gnosis not available
    def mock_config(chain):
        return chain in ["base", "ethereum"]
    
    with patch.object(service, 'is_chain_fully_configured', side_effect=mock_config):
        chain = service.select_optimal_chain()
        assert chain == "base"
    
    # Test complete failure
    with patch.object(service, 'is_chain_fully_configured', return_value=False), \
         patch.object(service, 'get_supported_chains', return_value=[]):
        with pytest.raises(ValueError, match="No valid chain configuration found"):
            service.select_optimal_chain()


@pytest.mark.asyncio
async def test_submit_safe_transaction():
    """Test Safe transaction submission."""
    service = get_mocked_safe_service()
    
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
    with patch('services.safe_service.EthereumClient'), \
         patch('services.safe_service.Safe') as mock_safe_class, \
         patch('services.safe_service.TransactionServiceApi'), \
         patch('services.safe_service.Web3') as mock_web3_class:
        
        # Mock receipt
        mock_receipt = {"blockNumber": 12345, "gasUsed": 100000, "status": 1}
        
        # Mock Web3
        mock_w3 = Mock()
        mock_w3.eth.wait_for_transaction_receipt.return_value = mock_receipt
        
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
        
        with patch.object(service, 'get_web3_connection', return_value=mock_w3), \
             patch.object(service, '_rate_limit_base_rpc'), \
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
        mock_safe_tx.safe_tx_hash.hex.return_value = "0xsafetx"
        mock_safe_tx.signatures = b"signature"
        mock_safe_tx.call.side_effect = Exception("Execution reverted")
        
        mock_safe = Mock()
        mock_safe.build_multisig_tx.return_value = mock_safe_tx
        mock_safe_class.return_value = mock_safe
        
        with patch.object(service, 'get_web3_connection'), \
             patch.object(service, '_rate_limit_base_rpc'), \
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
        
        mock_receipt = {"blockNumber": 12345, "gasUsed": 100000, "status": 0}  # Failed
        
        mock_w3 = Mock()
        mock_w3.eth.wait_for_transaction_receipt.return_value = mock_receipt
        
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
        mock_safe_tx.safe_tx_hash.hex.return_value = "0xsafetx"
        mock_safe_tx.signatures = b"signature"
        mock_safe_tx.call = Mock()
        
        mock_safe = Mock()
        mock_safe.build_multisig_tx.return_value = mock_safe_tx
        mock_tx_hash = Mock()
        mock_tx_hash.hex.return_value = "0xtxhash"
        mock_safe.send_multisig_tx.return_value.tx_hash = mock_tx_hash
        mock_safe_class.return_value = mock_safe
        
        with patch.object(service, 'get_web3_connection', return_value=mock_w3), \
             patch.object(service, '_rate_limit_base_rpc'), \
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
        
        with patch.object(service, 'get_web3_connection'), \
             patch.object(service, '_rate_limit_base_rpc'), \
             patch.object(service, 'is_chain_fully_configured', return_value=True):
            
            result = await service._submit_safe_transaction(
                chain="base", to="0x456", value=0, data=b"test"
            )
        
        assert result["success"] is False
        assert "Connection failed" in result["error"]


@pytest.mark.asyncio
async def test_perform_activity_transaction():
    """Test activity transaction."""
    service = get_mocked_safe_service()
    
    # Test with automatic chain selection
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
    
    # Test with specific chain
    with patch.object(service, '_submit_safe_transaction', new_callable=AsyncMock) as mock_submit:
        mock_submit.return_value = {"success": True, "tx_hash": "0xtest"}
        
        result = await service.perform_activity_transaction(chain="base")
        
        assert result["success"] is True
    
    # Test with missing Safe address
    result = await service.perform_activity_transaction(chain="unknown")
    
    assert result["success"] is False
    assert "No Safe address configured" in result["error"]


@pytest.mark.asyncio
async def test_get_safe_nonce():
    """Test Safe nonce retrieval."""
    service = get_mocked_safe_service()
    
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
async def test_build_safe_transaction():
    """Test Safe transaction building."""
    service = get_mocked_safe_service()
    
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
async def test_create_eas_attestation():
    """Test EAS attestation creation."""
    service = get_mocked_safe_service()
    attestation_data = MockEASAttestationData()
    
    # Test missing EAS configuration
    with patch('services.safe_service.settings') as mock_settings:
        mock_settings.eas_contract_address = None
        mock_settings.eas_schema_uid = None
        
        result = await service.create_eas_attestation(attestation_data)
        
        assert result["success"] is False
        assert "EAS configuration missing" in result["error"]
    
    # Test missing Safe address
    with patch('services.safe_service.settings') as mock_settings:
        mock_settings.eas_contract_address = "0xeas123"
        mock_settings.eas_schema_uid = "0x" + "a" * 64
        mock_settings.base_safe_address = None
        
        result = await service.create_eas_attestation(attestation_data)
        
        assert result["success"] is False
        assert "Base Safe address not configured" in result["error"]
    
    # Test successful creation
    with patch.object(service, '_build_eas_attestation_tx') as mock_build_tx, \
         patch.object(service, '_submit_safe_transaction', new_callable=AsyncMock) as mock_submit:
        
        mock_build_tx.return_value = {"to": "0xeas123", "data": "0x1234abcd", "value": 0}
        mock_submit.return_value = {"success": True, "tx_hash": "0xtxhash"}
        
        result = await service.create_eas_attestation(attestation_data)
        
        assert result["success"] is True
        assert result["safe_tx_hash"] == "0xtxhash"
    
    # Test exception handling
    with patch.object(service, '_build_eas_attestation_tx') as mock_build_tx:
        mock_build_tx.side_effect = Exception("Contract error")
        
        result = await service.create_eas_attestation(attestation_data)
        
        assert result["success"] is False
        assert "Contract error" in result["error"]


def test_build_eas_attestation_tx():
    """Test EAS attestation transaction building."""
    service = get_mocked_safe_service()
    attestation_data = MockEASAttestationData()
    
    # Test with AttestationTracker
    with patch('services.safe_service.settings') as mock_settings:
        mock_settings.attestation_tracker_address = "0xtracker123"
        mock_settings.eas_contract_address = "0xeas123"
        
        with patch.object(service, '_build_delegated_attestation_tx') as mock_build:
            mock_build.return_value = {"to": "0xtracker123", "data": "0x1234", "value": 0}
            
            result = service._build_eas_attestation_tx(attestation_data)
            
            assert result["to"] == "0xtracker123"
            mock_build.assert_called_once_with(
                attestation_data,
                target_address="0xtracker123",
                abi_name="attestation_tracker"
            )
    
    # Test with direct EAS
    with patch('services.safe_service.settings') as mock_settings:
        mock_settings.attestation_tracker_address = None
        mock_settings.eas_contract_address = "0xeas123"
        
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
    with patch('services.safe_service.settings') as mock_settings:
        mock_settings.attestation_tracker_address = None
        mock_settings.eas_contract_address = None
        
        with pytest.raises(ValueError, match="EAS contract address not configured"):
            service._build_eas_attestation_tx(attestation_data)


def test_build_delegated_attestation_tx():
    """Test delegated attestation transaction building."""
    service = get_mocked_safe_service()
    attestation_data = MockEASAttestationData()
    
    # Mock Web3 and contract
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
         patch('services.safe_service.settings') as mock_settings, \
         patch.object(service, '_generate_eas_delegated_signature') as mock_generate_sig, \
         patch('builtins.open', mock_open(read_data='ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80')):
        
        mock_settings.attestation_chain = "base"
        mock_settings.eas_schema_uid = "0x" + "a" * 64
        mock_settings.base_safe_address = "0x1234567890123456789012345678901234567890"
        mock_settings.eas_contract_address = "0xeas123"
        
        mock_generate_sig.return_value = b"\x01" * 65
        
        # Test AttestationTracker
        result = service._build_delegated_attestation_tx(
            attestation_data, "0xtracker123", "attestation_tracker"
        )
        
        assert result["to"] == "0xtest123"
        assert result["data"] == "0xabcd1234"
        assert result["value"] == 0
        
        # Test EIP712Proxy
        result = service._build_delegated_attestation_tx(
            attestation_data, "0xeas123", "eip712proxy"
        )
        
        assert result["to"] == "0xtest123"
        assert result["data"] == "0xabcd1234"
        assert result["value"] == 0


def test_encode_attestation_data():
    """Test attestation data encoding."""
    service = get_mocked_safe_service()
    attestation_data = MockEASAttestationData()
    
    with patch('services.safe_service.Web3') as mock_web3_class:
        mock_w3 = Mock()
        mock_codec = Mock()
        mock_codec.encode.return_value = b"encoded_attestation_data"
        mock_w3.codec = mock_codec
        mock_web3_class.return_value = mock_w3
        
        result = service._encode_attestation_data(attestation_data)
        
        assert result == b"encoded_attestation_data"
        mock_codec.encode.assert_called_once()


def test_get_web3_instance():
    """Test _get_web3_instance method."""
    service = get_mocked_safe_service()
    
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


def test_generate_eas_delegated_signature():
    """Test EAS delegated signature generation."""
    service = get_mocked_safe_service()
    
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
    pytest.main([__file__, "-v", "--cov=services.safe_service", "--cov-report=term-missing"])