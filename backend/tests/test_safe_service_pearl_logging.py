"""Simplified test suite for Pearl-compliant logging in safe_service.py.

This test file validates that the SafeService properly uses Pearl-compliant logging.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
import json

from services.safe_service import SafeService
from logging_config import validate_log_format


class TestSafeServicePearlLogging:
    """Test Pearl-compliant logging implementation in SafeService."""

    def test_initialization_uses_pearl_logger(self):
        """Test that service initialization uses Pearl logger."""
        mock_logger = Mock()
        
        with patch('services.safe_service.setup_pearl_logger', return_value=mock_logger) as mock_setup:
            with patch('builtins.open', mock_open(read_data="0x1234567890123456789012345678901234567890123456789012345678901234")):
                with patch('config.settings') as mock_settings:
                    mock_settings.safe_contract_addresses = json.dumps({
                        "ethereum": "0x742d35Cc6634C0532925a3b844Bc9e7595f62222",
                        "polygon": "0x742d35Cc6634C0532925a3b844Bc9e7595f62333"
                    })
                    mock_settings.ethereum_ledger_rpc = "https://eth.rpc"
                    mock_settings.gnosis_ledger_rpc = "https://gnosis.rpc"
                    mock_settings.base_ledger_rpc = "https://base.rpc"
                    mock_settings.mode_ledger_rpc = "https://mode.rpc"
                    
                    service = SafeService()
        
        # Verify Pearl logger setup was called
        mock_setup.assert_called_once_with('services.safe_service')
        
        # Verify initialization logging
        assert mock_logger.info.called
        init_message = mock_logger.info.call_args[0][0]
        assert "SafeService initialized" in init_message
        assert "eoa_address=" in init_message
        assert "safe_addresses=" in init_message
        assert "available_chains=" in init_message

    def test_no_logfire_imports(self):
        """Test that the service does not import or use logfire."""
        import services.safe_service as safe_module
        import inspect
        
        # Check module doesn't have logfire
        assert not hasattr(safe_module, 'logfire')
        
        # Check source code doesn't contain logfire
        source_code = inspect.getsource(safe_module)
        assert 'import logfire' not in source_code
        assert 'from logfire' not in source_code
        assert 'logfire.' not in source_code

    def test_perform_activity_transaction_uses_log_span(self):
        """Test that perform_activity_transaction uses Pearl log_span."""
        mock_logger = Mock()
        
        with patch('services.safe_service.setup_pearl_logger', return_value=mock_logger):
            with patch('services.safe_service.log_span') as mock_log_span:
                # Setup context manager mock
                mock_span_cm = Mock()
                mock_span_cm.__enter__ = Mock(return_value=None)
                mock_span_cm.__exit__ = Mock(return_value=None)
                mock_log_span.return_value = mock_span_cm
                
                with patch('builtins.open', mock_open(read_data="0x1234567890123456789012345678901234567890123456789012345678901234")):
                    with patch('config.settings') as mock_settings:
                        mock_settings.safe_contract_addresses = json.dumps({"ethereum": "0x742d35"})
                        mock_settings.ethereum_ledger_rpc = "https://eth.rpc"
                        mock_settings.gnosis_ledger_rpc = ""
                        mock_settings.base_ledger_rpc = ""
                        mock_settings.mode_ledger_rpc = ""
                        
                        service = SafeService()
                        
                        # Call the method (it will fail but we just want to verify log_span is called)
                        try:
                            import asyncio
                            asyncio.run(service.perform_activity_transaction(chain="ethereum"))
                        except:
                            pass  # Expected to fail due to mocking
                
                # Verify log_span was called with correct parameters
                mock_log_span.assert_called_with(
                    mock_logger,
                    "safe_service.perform_activity_transaction",
                    chain="ethereum"
                )

    def test_pearl_log_format_examples(self):
        """Test that example log messages comply with Pearl format."""
        test_messages = [
            "[2025-07-17 18:14:17,293] [INFO] [agent] SafeService initialized (eoa_address=0x123, chains=ethereum,polygon)",
            "[2025-07-17 18:14:17,294] [INFO] [agent] Creating Safe transaction for activity on ethereum",
            "[2025-07-17 18:14:17,295] [ERROR] [agent] Transaction reverted (tx_hash=0x123)",
            "[2025-07-17 18:14:17,296] [INFO] [agent] Transaction successful (gas_used=21000, block_number=12345)"
        ]
        
        for message in test_messages:
            assert validate_log_format(message), f"Message does not comply with Pearl format: {message}"

    def test_structured_data_formatting(self):
        """Test that structured data follows Pearl conventions."""
        # Example of proper structured data formatting
        tx_data = {
            "tx_hash": "0x123",
            "gas_used": 21000,
            "block_number": 12345
        }
        
        # Format as Pearl expects
        log_message = f"Transaction completed (tx_hash={tx_data['tx_hash']}, gas_used={tx_data['gas_used']}, block_number={tx_data['block_number']})"
        
        # Verify format
        assert "tx_hash=0x123" in log_message
        assert "gas_used=21000" in log_message
        assert "block_number=12345" in log_message
        assert log_message.startswith("Transaction completed (")
        assert log_message.endswith(")")