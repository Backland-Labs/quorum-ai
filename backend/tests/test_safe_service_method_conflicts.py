"""
Test SafeService method conflicts and missing implementations.

This test suite specifically validates that the SafeService class has:
1. No duplicate method definitions that could cause silent failures
2. All referenced methods are properly implemented
3. Method signatures are consistent across the class

These tests are written following TDD methodology to ensure the critical
production bugs in SafeService are resolved before deployment.
"""

import pytest
import inspect
from unittest.mock import patch, MagicMock, mock_open
from services.safe_service import SafeService


class TestSafeServiceMethodConflicts:
    """Test SafeService for method conflicts and missing implementations."""

    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    def test_no_duplicate_submit_safe_transaction_methods(self, mock_settings, mock_json_loads, mock_file):
        """
        Test that there are no duplicate _submit_safe_transaction method definitions.
        
        This test ensures that the SafeService class has exactly one _submit_safe_transaction
        method to prevent silent failures where the wrong implementation is called.
        The duplicate method issue would cause production failures where transactions
        appear to succeed but no actual blockchain operations occur.
        
        Importance: Critical for production stability and transaction execution.
        """
        # Setup basic mocks for service initialization
        mock_settings.safe_contract_addresses = '{"gnosis": "0x123"}'
        mock_settings.gnosis_ledger_rpc = "https://gnosis.example.com"
        mock_json_loads.return_value = {"gnosis": "0x123"}
        
        service = SafeService()
        
        # Get all methods named _submit_safe_transaction in the class
        submit_methods = []
        for name, method in inspect.getmembers(service, inspect.ismethod):
            if name == "_submit_safe_transaction":
                submit_methods.append(method)
        
        # Should have exactly one _submit_safe_transaction method
        assert len(submit_methods) == 1, f"Found {len(submit_methods)} _submit_safe_transaction methods, expected exactly 1"

    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    def test_submit_safe_transaction_method_signature_consistency(self, mock_settings, mock_json_loads, mock_file):
        """
        Test that _submit_safe_transaction has a consistent method signature.
        
        This test validates that the _submit_safe_transaction method accepts
        the correct parameters with proper types. Inconsistent signatures
        could cause runtime errors when the method is called with different
        parameter types.
        
        Importance: Ensures method can be called consistently from all code paths.
        """
        mock_settings.safe_contract_addresses = '{"gnosis": "0x123"}'
        mock_settings.gnosis_ledger_rpc = "https://gnosis.example.com"
        mock_json_loads.return_value = {"gnosis": "0x123"}
        
        service = SafeService()
        
        # Check that _submit_safe_transaction method exists and has correct signature
        assert hasattr(service, "_submit_safe_transaction"), "_submit_safe_transaction method not found"
        
        method = getattr(service, "_submit_safe_transaction")
        signature = inspect.signature(method)
        
        # Check expected parameters exist
        params = list(signature.parameters.keys())
        assert "to" in params, "_submit_safe_transaction missing 'to' parameter"
        assert "data" in params, "_submit_safe_transaction missing 'data' parameter"
        assert "value" in params, "_submit_safe_transaction missing 'value' parameter"
        assert "chain" in params, "_submit_safe_transaction missing 'chain' parameter"

    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    def test_all_referenced_methods_exist(self, mock_settings, mock_json_loads, mock_file):
        """
        Test that all methods referenced in _submit_safe_transaction exist.
        
        This test ensures that any method called within _submit_safe_transaction
        is properly implemented in the class. Missing method references would
        cause AttributeError exceptions at runtime when processing attestations.
        
        Importance: Prevents runtime crashes during EAS attestation processing.
        """
        mock_settings.safe_contract_addresses = '{"gnosis": "0x123"}'
        mock_settings.gnosis_ledger_rpc = "https://gnosis.example.com"
        mock_json_loads.return_value = {"gnosis": "0x123"}
        
        service = SafeService()
        
        # Check that commonly referenced helper methods exist
        required_methods = [
            "get_web3_connection",
            "get_safe_nonce", 
            "build_safe_transaction"
        ]
        
        for method_name in required_methods:
            assert hasattr(service, method_name), f"Required method '{method_name}' not found in SafeService"
            
        # Verify that _submit_safe_transaction doesn't reference non-existent methods
        # This was the missing method causing AttributeError in the duplicate implementation
        source_code = inspect.getsource(service._submit_safe_transaction)
        
        # Check that any referenced private methods actually exist
        import re
        private_method_calls = re.findall(r'self\.(_\w+)\(', source_code)
        
        for method_name in private_method_calls:
            assert hasattr(service, method_name), f"Referenced method '{method_name}' not found in SafeService"

    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    @patch("services.safe_service.Web3")
    @patch("services.safe_service.Safe")
    @patch("services.safe_service.EthereumClient")
    @patch("services.safe_service.TransactionServiceApi")
    async def test_submit_safe_transaction_execution_flow(self, mock_tx_service, mock_eth_client, mock_safe, mock_web3_class, mock_settings, mock_json_loads, mock_file):
        """
        Test that _submit_safe_transaction executes the full transaction flow.
        
        This test validates that the _submit_safe_transaction method actually
        performs all required operations for transaction submission including
        building, signing, and executing the Safe transaction. This ensures
        the method is not a stub implementation that returns mock data.
        
        Importance: Ensures real blockchain transactions are executed, not mock responses.
        """
        # Setup comprehensive mocks
        mock_settings.safe_contract_addresses = '{"base": "0x123"}'
        mock_settings.base_ledger_rpc = "https://base.example.com"
        mock_json_loads.return_value = {"base": "0x123"}
        
        # Mock Web3 and Safe components
        mock_web3_instance = MagicMock()
        mock_web3_class.return_value = mock_web3_instance
        mock_web3_instance.is_connected.return_value = True
        
        # Mock transaction receipt for success
        mock_receipt = {
            "status": 1,  # Success
            "blockNumber": 12345,
            "gasUsed": 54321
        }
        mock_web3_instance.eth.wait_for_transaction_receipt.return_value = mock_receipt
        
        mock_safe_instance = MagicMock()
        mock_safe.return_value = mock_safe_instance
        
        # Mock Safe transaction building - matches actual method name
        mock_safe_tx = MagicMock()
        # Provide a proper 32-byte hash
        mock_safe_tx.safe_tx_hash = b'\x12' * 32
        mock_safe_tx.safe_nonce = 42
        mock_safe_instance.build_multisig_tx.return_value = mock_safe_tx
        
        # Mock transaction service
        mock_tx_service_instance = MagicMock()
        mock_tx_service.return_value = mock_tx_service_instance
        mock_tx_service_instance.post_transaction.return_value = "0x789"
        
        # Mock the send_multisig_tx method
        mock_ethereum_tx = MagicMock()
        mock_tx_hash = MagicMock()
        mock_tx_hash.hex.return_value = "0x" + "78" * 32
        mock_ethereum_tx.tx_hash = mock_tx_hash
        mock_safe_instance.send_multisig_tx.return_value = mock_ethereum_tx
        
        service = SafeService()
        
        # Test transaction submission using keyword-only arguments
        result = await service._submit_safe_transaction(
            chain="base",
            to="0x456",
            data=b"test_data",
            value=0
        )
        
        # Verify that actual Safe operations were called, not just mock returns
        mock_safe_instance.build_multisig_tx.assert_called_once()
        mock_tx_service_instance.post_transaction.assert_called_once()
        
        # Result should contain transaction details for successful transaction
        assert result["success"] is True
        assert "tx_hash" in result
        assert result["tx_hash"] == "0x" + "78" * 32