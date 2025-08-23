"""Tests for ActivityService."""

import pytest
from unittest.mock import patch, MagicMock, mock_open, call
from datetime import date, timedelta
import json
import os
import logging
import re

from services.activity_service import ActivityService
from logging_config import validate_log_format

# Create a mock logger for tests that don't specifically test logging
def get_mock_logger():
    """Create a mock logger that doesn't write to files."""
    mock_logger = MagicMock(spec=logging.Logger)
    mock_logger.info = MagicMock()
    mock_logger.warning = MagicMock()
    mock_logger.error = MagicMock()
    mock_logger.debug = MagicMock()
    return mock_logger


class TestActivityServiceInitialization:
    """Test ActivityService initialization."""

    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_activity_service_initialization_no_store_path(self, mock_exists, mock_settings):
        """Test ActivityService initialization without store path."""
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        
        assert service.last_activity_date is None
        assert service.last_tx_hash is None
        assert service.persistent_file == "activity_tracker.json"
        
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_activity_service_initialization_with_store_path(self, mock_exists, mock_settings):
        """Test ActivityService initialization with store path."""
        mock_settings.store_path = "/tmp/olas"
        mock_exists.return_value = False
        
        service = ActivityService()
        
        assert service.persistent_file == "/tmp/olas/activity_tracker.json"


class TestActivityServiceStateManagement:
    """Test ActivityService state loading and saving."""
    
    @patch("services.activity_service.settings")
    @patch("services.activity_service.setup_pearl_logger")
    @patch("builtins.open", new_callable=mock_open, read_data='{"last_activity_date": "2024-01-15", "last_tx_hash": "0x123"}')
    @patch("os.path.exists")
    def test_load_state_success(self, mock_exists, mock_file, mock_setup_logger, mock_settings):
        """Test successful state loading from file."""
        mock_settings.store_path = None
        mock_exists.return_value = True
        mock_setup_logger.return_value = get_mock_logger()
        
        service = ActivityService()
        
        assert service.last_activity_date == date(2024, 1, 15)
        assert service.last_tx_hash == "0x123"
        # Check that the activity tracker file was opened (not the log file)
        activity_file_calls = [call for call in mock_file.call_args_list 
                               if 'activity_tracker.json' in str(call)]
        assert len(activity_file_calls) > 0
        
    @patch("services.activity_service.settings")
    @patch("builtins.open", new_callable=mock_open, read_data='{}')
    @patch("os.path.exists")
    def test_load_state_empty_file(self, mock_exists, mock_file, mock_settings):
        """Test loading state from empty file."""
        mock_settings.store_path = None
        mock_exists.return_value = True
        
        service = ActivityService()
        
        assert service.last_activity_date is None
        assert service.last_tx_hash is None
        
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_load_state_file_not_exists(self, mock_exists, mock_settings):
        """Test loading state when file doesn't exist."""
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        
        assert service.last_activity_date is None
        assert service.last_tx_hash is None
        
    @patch("services.activity_service.settings")
    @patch("services.activity_service.setup_pearl_logger")
    @patch("builtins.open", side_effect=Exception("File error"))
    @patch("os.path.exists")
    def test_load_state_exception_handling(self, mock_exists, mock_file, mock_setup_logger, mock_settings):
        """Test exception handling during state loading."""
        mock_settings.store_path = None
        mock_exists.return_value = True
        mock_setup_logger.return_value = get_mock_logger()
        
        # Should not raise exception
        service = ActivityService()
        
        assert service.last_activity_date is None
        assert service.last_tx_hash is None
        
    @patch("services.activity_service.settings")
    @patch("services.activity_service.setup_pearl_logger")
    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    def test_save_state_success(self, mock_exists, mock_file, mock_makedirs, mock_setup_logger, mock_settings):
        """Test successful state saving."""
        mock_settings.store_path = "/tmp/olas"
        mock_exists.return_value = False
        mock_setup_logger.return_value = get_mock_logger()
        
        service = ActivityService()
        service.last_activity_date = date(2024, 1, 15)
        service.last_tx_hash = "0x123"
        
        # Reset the mock to clear initialization calls
        mock_file.reset_mock()
        
        service.save_state()
        
        # Check that file was opened for writing
        mock_file.assert_called_with("/tmp/olas/activity_tracker.json", 'w')
        
        # Get the actual JSON data written - json.dump writes in chunks
        handle = mock_file()
        all_written = ''.join(call[0][0] for call in handle.write.call_args_list)
        # Find the JSON content (between first { and last })
        json_start = all_written.find('{')
        json_end = all_written.rfind('}') + 1
        assert json_start >= 0 and json_end > json_start
        written_content = all_written[json_start:json_end]
        parsed_data = json.loads(written_content)
        
        assert parsed_data["last_activity_date"] == "2024-01-15"
        assert parsed_data["last_tx_hash"] == "0x123"
        
    @patch("services.activity_service.settings")
    @patch("services.activity_service.setup_pearl_logger")
    @patch("os.makedirs")
    @patch("os.path.exists")
    def test_save_state_exception_handling(self, mock_exists, mock_makedirs, mock_setup_logger, mock_settings):
        """Test exception handling during state saving."""
        mock_settings.store_path = "/tmp/olas"
        mock_exists.return_value = False
        mock_logger = get_mock_logger()
        mock_setup_logger.return_value = mock_logger
        
        service = ActivityService()
        service.last_activity_date = date(2024, 1, 15)
        
        # Mock makedirs to fail when save_state is called
        mock_makedirs.side_effect = Exception("Directory error")
        
        # Should not raise exception
        service.save_state()
        
        # Verify warning was logged
        mock_logger.warning.assert_called()


class TestActivityServiceActivityChecking:
    """Test ActivityService activity checking logic."""
    
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_is_daily_activity_needed_no_previous_activity(self, mock_exists, mock_settings):
        """Test activity needed when no previous activity recorded."""
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        
        assert service.is_daily_activity_needed() is True
        
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_is_daily_activity_needed_today_already_done(self, mock_exists, mock_settings):
        """Test no activity needed when already done today."""
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        service.last_activity_date = date.today()
        
        assert service.is_daily_activity_needed() is False
        
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_is_daily_activity_needed_yesterday(self, mock_exists, mock_settings):
        """Test activity needed when last activity was yesterday."""
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        service.last_activity_date = date.today() - timedelta(days=1)
        
        assert service.is_daily_activity_needed() is True


class TestActivityServiceActivityMarking:
    """Test ActivityService activity marking functionality."""
    
    @patch("services.activity_service.settings")
    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    def test_mark_activity_completed(self, mock_exists, mock_file, mock_makedirs, mock_settings):
        """Test marking activity as completed."""
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        test_tx_hash = "0xabcdef123456"
        
        service.mark_activity_completed(test_tx_hash)
        
        assert service.last_activity_date == date.today()
        assert service.last_tx_hash == test_tx_hash
        
        # Verify save_state was called (file operations)
        mock_file.assert_called_with("activity_tracker.json", 'w')


class TestActivityServiceNonceTracking:
    """Test ActivityService nonce tracking functionality (Phase 1)."""
    
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_nonce_tracking_initialization(self, mock_exists, mock_settings):
        """Test nonces are initialized as empty dict for multi-chain tracking."""
        # This test ensures the core nonce tracking data structure is properly initialized
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        
        # Critical assertion: nonces must be initialized as Dict[str, Dict[int, int]]
        assert hasattr(service, 'nonces')
        assert isinstance(service.nonces, dict)
        assert service.nonces == {}
        
        # Verify nonce type constants are defined
        assert hasattr(service, 'NONCE_MULTISIG_ACTIVITY')
        assert hasattr(service, 'NONCE_VOTE_ATTESTATIONS')  
        assert hasattr(service, 'NONCE_VOTING_CONSIDERED')
        assert hasattr(service, 'NONCE_NO_VOTING')
        
        # Verify constant values match expected interface
        assert service.NONCE_MULTISIG_ACTIVITY == 0
        assert service.NONCE_VOTE_ATTESTATIONS == 1
        assert service.NONCE_VOTING_CONSIDERED == 2
        assert service.NONCE_NO_VOTING == 3
        
    @patch("services.activity_service.settings")
    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    def test_unified_state_data_includes_nonces(self, mock_exists, mock_file, mock_makedirs, mock_settings):
        """Test _prepare_state_data includes nonces in unified format."""
        # This test verifies the critical state persistence includes nonce data
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        service.last_activity_date = date(2024, 1, 15)
        service.last_tx_hash = "0x123"
        
        # Set up nonce data for ethereum chain
        service.nonces = {
            "ethereum": {0: 5, 1: 3, 2: 10, 3: 2}
        }
        
        # Reset mock to clear initialization calls
        mock_file.reset_mock()
        
        service.save_state()
        
        # Verify file was written with unified state data
        handle = mock_file()
        all_written = ''.join(call[0][0] for call in handle.write.call_args_list)
        json_start = all_written.find('{')
        json_end = all_written.rfind('}') + 1
        written_content = all_written[json_start:json_end]
        parsed_data = json.loads(written_content)
        
        # Critical assertion: unified state includes both OLAS compliance and nonces
        assert "last_activity_date" in parsed_data
        assert "last_tx_hash" in parsed_data
        assert "nonces" in parsed_data
        assert "last_updated" in parsed_data
        
        # Verify nonce structure
        assert parsed_data["nonces"]["ethereum"]["0"] == 5  # JSON keys are strings
        assert parsed_data["nonces"]["ethereum"]["1"] == 3
        
    @patch("services.activity_service.settings")
    @patch("services.activity_service.setup_pearl_logger")
    @patch("builtins.open", new_callable=mock_open, read_data='{"last_activity_date": "2024-01-15", "last_tx_hash": "0x123", "nonces": {"ethereum": {"0": 5, "1": 3}}, "last_updated": "2024-01-15T10:30:00Z"}')
    @patch("os.path.exists")
    def test_load_state_handles_unified_schema(self, mock_exists, mock_file, mock_setup_logger, mock_settings):
        """Test loading state with unified schema including nonces."""
        # This test ensures backward compatibility and nonce loading works correctly
        mock_settings.store_path = None
        mock_exists.return_value = True
        mock_setup_logger.return_value = get_mock_logger()
        
        service = ActivityService()
        
        # Critical assertions: both OLAS compliance and nonce data are loaded
        assert service.last_activity_date == date(2024, 1, 15)
        assert service.last_tx_hash == "0x123"
        assert "ethereum" in service.nonces
        assert service.nonces["ethereum"][0] == 5  # Converted from string keys
        assert service.nonces["ethereum"][1] == 3


class TestActivityServiceOLASCompliance:
    """Test ActivityService OLAS compliance checking."""
    
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_get_activity_status_no_activity(self, mock_exists, mock_settings):
        """Test getting activity status when no activity recorded."""
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        status = service.get_activity_status()
        
        assert status["daily_activity_needed"] is True
        assert status["last_activity_date"] is None
        assert status["last_tx_hash"] is None
        
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_get_activity_status_with_activity(self, mock_exists, mock_settings):
        """Test getting activity status with previous activity."""
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        service.last_activity_date = date.today()
        service.last_tx_hash = "0x123"
        
        status = service.get_activity_status()
        
        assert status["daily_activity_needed"] is False
        assert status["last_activity_date"] == date.today().isoformat()
        assert status["last_tx_hash"] == "0x123"
        
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_check_olas_compliance_needed(self, mock_exists, mock_settings):
        """Test OLAS compliance check when activity is needed."""
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        # No previous activity
        
        compliance = service.check_olas_compliance()
        
        assert compliance["compliant"] is False
        assert compliance["reason"] == "Daily activity required for OLAS staking"
        assert compliance["action_required"] == "safe_transaction"
        
    @patch("services.activity_service.settings")  
    @patch("os.path.exists")
    def test_check_olas_compliance_satisfied(self, mock_exists, mock_settings):
        """Test OLAS compliance check when already satisfied."""
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        service.last_activity_date = date.today()
        
        compliance = service.check_olas_compliance()
        
        assert compliance["compliant"] is True
        assert compliance["reason"] == "Daily activity completed"
        assert compliance["action_required"] is None


class TestActivityServiceIntegration:
    """Test ActivityService integration methods."""
    
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_get_compliance_summary(self, mock_exists, mock_settings):
        """Test getting compliance summary."""
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        service.last_activity_date = date(2024, 1, 15)
        service.last_tx_hash = "0x123"
        
        summary = service.get_compliance_summary()
        
        assert "activity_status" in summary
        assert "olas_compliance" in summary
        assert summary["activity_status"]["last_activity_date"] == "2024-01-15"
        assert summary["olas_compliance"]["compliant"] is False  # Old date


class TestActivityServicePhase2NonceIncrement:
    """Test ActivityService Phase 2 nonce increment functionality."""
    
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_increment_multisig_activity(self, mock_exists, mock_settings):
        """Test incrementing multisig activity nonce for a chain."""
        # This test verifies that multisig activity nonces can be incremented correctly
        mock_settings.store_path = None
        mock_settings.safe_addresses = {"ethereum": "0x123", "gnosis": "0x456"}
        mock_exists.return_value = False
        
        service = ActivityService()
        
        # Critical assertion: increment method should exist and work
        assert hasattr(service, 'increment_multisig_activity')
        
        # Initialize with some nonce data
        service.nonces = {"ethereum": {0: 5, 1: 3, 2: 10, 3: 2}}
        
        service.increment_multisig_activity("ethereum")
        
        # Verify nonce was incremented
        assert service.nonces["ethereum"][service.NONCE_MULTISIG_ACTIVITY] == 6
        
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_increment_vote_attestation(self, mock_exists, mock_settings):
        """Test incrementing vote attestation nonce for a chain."""
        mock_settings.store_path = None
        mock_settings.safe_addresses = {"ethereum": "0x123"}
        mock_exists.return_value = False
        
        service = ActivityService()
        service.nonces = {"ethereum": {0: 5, 1: 3, 2: 10, 3: 2}}
        
        service.increment_vote_attestation("ethereum")
        
        assert service.nonces["ethereum"][service.NONCE_VOTE_ATTESTATIONS] == 4
        
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_increment_voting_considered(self, mock_exists, mock_settings):
        """Test incrementing voting considered nonce when proposal considered but not voted."""
        mock_settings.store_path = None
        mock_settings.safe_addresses = {"ethereum": "0x123"}
        mock_exists.return_value = False
        
        service = ActivityService()
        service.nonces = {"ethereum": {0: 5, 1: 3, 2: 10, 3: 2}}
        
        service.increment_voting_considered("ethereum")
        
        assert service.nonces["ethereum"][service.NONCE_VOTING_CONSIDERED] == 11
        
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_increment_no_voting(self, mock_exists, mock_settings):
        """Test incrementing no voting nonce when no voting opportunities available."""
        mock_settings.store_path = None
        mock_settings.safe_addresses = {"ethereum": "0x123"}
        mock_exists.return_value = False
        
        service = ActivityService()
        service.nonces = {"ethereum": {0: 5, 1: 3, 2: 10, 3: 2}}
        
        service.increment_no_voting("ethereum")
        
        assert service.nonces["ethereum"][service.NONCE_NO_VOTING] == 3
        
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_increment_nonce_new_chain(self, mock_exists, mock_settings):
        """Test incrementing nonce for a chain with no existing nonce data."""
        # This test ensures new chains are properly initialized
        mock_settings.store_path = None
        mock_settings.safe_addresses = {"gnosis": "0x789"}
        mock_exists.return_value = False
        
        service = ActivityService()
        
        service.increment_multisig_activity("gnosis")
        
        # Should initialize chain nonces and increment
        assert "gnosis" in service.nonces
        assert service.nonces["gnosis"][service.NONCE_MULTISIG_ACTIVITY] == 1
        assert service.nonces["gnosis"][service.NONCE_VOTE_ATTESTATIONS] == 0
        assert service.nonces["gnosis"][service.NONCE_VOTING_CONSIDERED] == 0
        assert service.nonces["gnosis"][service.NONCE_NO_VOTING] == 0
        
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_nonce_validation_error_exception(self, mock_exists, mock_settings):
        """Test NonceValidationError exception class exists with correct attributes."""
        mock_settings.store_path = None
        mock_settings.safe_addresses = {"ethereum": "0x123"}
        mock_exists.return_value = False
        
        service = ActivityService()
        
        # Critical assertion: NonceValidationError should be importable from service module
        from services.activity_service import NonceValidationError
        
        # Test exception attributes
        error = NonceValidationError("ethereum", 0, "Test error")
        assert error.chain == "ethereum"
        assert error.nonce_type == 0
        assert "ethereum" in str(error)
        assert "Test error" in str(error)
        
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_chain_validation_unsupported_chain(self, mock_exists, mock_settings):
        """Test that unsupported chains raise NonceValidationError."""
        mock_settings.store_path = None
        mock_settings.safe_addresses = {"ethereum": "0x123"}  # Only ethereum supported
        mock_exists.return_value = False
        
        service = ActivityService()
        
        from services.activity_service import NonceValidationError
        
        # Should raise error for unsupported chain
        with pytest.raises(NonceValidationError) as exc_info:
            service.increment_multisig_activity("polygon")
        
        assert exc_info.value.chain == "polygon"
        assert "Chain not configured" in str(exc_info.value)
        
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_supported_chains_property(self, mock_exists, mock_settings):
        """Test supported_chains property returns chains from Safe addresses."""
        mock_settings.store_path = None
        mock_settings.safe_addresses = {"ethereum": "0x123", "gnosis": "0x456", "polygon": "0x789"}
        mock_exists.return_value = False
        
        service = ActivityService()
        
        # Critical assertion: supported_chains should return list of configured chains
        assert hasattr(service, 'supported_chains')
        supported = service.supported_chains
        
        assert isinstance(supported, list)
        assert set(supported) == {"ethereum", "gnosis", "polygon"}
        
    @patch("services.activity_service.settings")
    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    def test_increment_saves_state(self, mock_exists, mock_file, mock_makedirs, mock_settings):
        """Test that nonce increments trigger state persistence."""
        # This test verifies that nonce changes are properly persisted
        mock_settings.store_path = None
        mock_settings.safe_addresses = {"ethereum": "0x123"}
        mock_exists.return_value = False
        
        service = ActivityService()
        
        # Reset mock to clear initialization calls
        mock_file.reset_mock()
        
        service.increment_multisig_activity("ethereum")
        
        # Verify save_state was called (file operations)
        mock_file.assert_called_with("activity_tracker.json", 'w')


class TestActivityServicePearlLogging:
    """Test ActivityService Pearl-compliant logging implementation.
    
    These tests ensure that ActivityService properly migrates from Logfire to Pearl logging,
    following the exact Pearl format requirements and maintaining structured logging capabilities.
    """
    
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_pearl_logger_initialization(self, mock_exists, mock_settings):
        """Test that ActivityService initializes with Pearl logger instead of Logfire.
        
        This test verifies that the service:
        1. Uses setup_pearl_logger for initialization
        2. Doesn't import or use logfire
        3. Has a properly configured logger instance
        """
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        # Create service and verify it has Pearl logger
        service = ActivityService()
        
        # Assert logger exists and is a Python logging.Logger instance
        assert hasattr(service, 'logger')
        assert isinstance(service.logger, logging.Logger)
        
        # Verify no logfire references in the service
        assert not hasattr(service, 'logfire')
    
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_initialization_logging_format(self, mock_file, mock_exists, mock_settings):
        """Test that initialization logs follow Pearl format.
        
        This test ensures that when ActivityService initializes, it logs
        properly formatted Pearl-compliant messages with structured data.
        """
        mock_settings.store_path = "/test/path"
        mock_exists.return_value = False
        
        with patch('logging.Logger.info') as mock_log:
            service = ActivityService()
            
            # Verify initialization log was called
            mock_log.assert_called()
            
            # Get the log message
            log_call = mock_log.call_args
            log_message = log_call[0][0]
            
            # Verify structured logging format
            assert "ActivityService initialized" in log_message
            assert "persistent_file=" in log_message
            assert "daily_activity_needed=" in log_message
    
    @patch("services.activity_service.settings")
    @patch("os.path.exists") 
    @patch("builtins.open", new_callable=mock_open, read_data='{"last_activity_date": "2024-01-15", "last_tx_hash": "0x123"}')
    def test_load_state_pearl_logging(self, mock_file, mock_exists, mock_settings):
        """Test that load_state uses Pearl logging for success and errors.
        
        This test verifies proper Pearl logging during state loading,
        including structured data logging for loaded values.
        """
        mock_settings.store_path = None
        mock_exists.return_value = True
        
        with patch('logging.Logger.info') as mock_info:
            service = ActivityService()
            
            # Find the "state loaded" log call
            state_loaded_calls = [call for call in mock_info.call_args_list 
                                  if "Activity state loaded" in str(call)]
            assert len(state_loaded_calls) > 0
            
            # Verify structured logging
            log_message = state_loaded_calls[0][0][0]
            assert "last_activity_date=" in log_message
            assert "last_tx_hash=" in log_message
    
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_load_state_error_pearl_logging(self, mock_exists, mock_settings):
        """Test that load_state error handling uses Pearl WARN level.
        
        This test ensures errors during state loading are logged at WARN level
        with appropriate error details.
        """
        mock_settings.store_path = None
        mock_exists.return_value = True
        
        # Create service first with working logger
        service = ActivityService()
        
        # Now patch the open to fail for load_state and test warning
        with patch("builtins.open", side_effect=Exception("File error")):
            with patch.object(service.logger, 'warning') as mock_warn:
                service.load_state()
                
                # Verify warning was logged for the error
                mock_warn.assert_called()
                log_message = mock_warn.call_args[0][0]
                assert "Could not load activity state" in log_message
    
    @patch("services.activity_service.settings")
    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    def test_save_state_pearl_logging(self, mock_exists, mock_file, mock_makedirs, mock_settings):
        """Test that save_state uses Pearl logging.
        
        This test verifies proper Pearl logging when saving state,
        including structured data for saved values.
        """
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        service.last_activity_date = date(2024, 1, 15)
        service.last_tx_hash = "0x123"
        
        with patch('logging.Logger.info') as mock_info:
            service.save_state()
            
            # Find save state log
            save_calls = [call for call in mock_info.call_args_list
                          if "Activity state saved" in str(call)]
            assert len(save_calls) > 0
            
            log_message = save_calls[0][0][0]
            assert "last_activity_date=" in log_message
            assert "last_tx_hash=" in log_message
    
    @patch("services.activity_service.settings")
    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    def test_mark_activity_completed_pearl_logging(self, mock_exists, mock_file, mock_makedirs, mock_settings):
        """Test that marking activity completed uses Pearl logging.
        
        This test ensures activity completion is logged with Pearl format
        including transaction hash and date.
        """
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        
        with patch('logging.Logger.info') as mock_info:
            service.mark_activity_completed("0xabc123")
            
            # Find activity completed log
            completed_calls = [call for call in mock_info.call_args_list
                               if "Activity marked as completed" in str(call)]
            assert len(completed_calls) > 0
            
            log_message = completed_calls[0][0][0]
            assert "tx_hash=" in log_message
            assert "date=" in log_message
    
    @pytest.mark.asyncio
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    async def test_ensure_daily_compliance_log_span(self, mock_exists, mock_settings):
        """Test that ensure_daily_compliance uses Pearl log_span instead of logfire.span.
        
        This test verifies the migration from logfire.span to Pearl's log_span
        context manager for tracking operation spans.
        """
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        service.last_activity_date = date.today() - timedelta(days=1)  # Need activity
        
        # Mock safe_service
        mock_safe_service = MagicMock()
        
        # Create async mock for async method
        async def mock_perform_activity():
            return {"success": True, "tx_hash": "0x999"}
        
        mock_safe_service.perform_activity_transaction = mock_perform_activity
        
        with patch('logging.Logger.info') as mock_info:
            result = await service.ensure_daily_compliance(mock_safe_service)
            
            # Verify span start/end logs
            log_messages = [call[0][0] for call in mock_info.call_args_list]
            
            # Should have span start log
            span_start_logs = [msg for msg in log_messages if "Starting activity_service.ensure_daily_compliance" in msg]
            assert len(span_start_logs) > 0
            
            # Should have activity needed log
            activity_logs = [msg for msg in log_messages if "Daily OLAS activity needed" in msg]
            assert len(activity_logs) > 0
    
    @pytest.mark.asyncio
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    async def test_ensure_daily_compliance_no_activity_needed_logging(self, mock_exists, mock_settings):
        """Test Pearl logging when no daily activity is needed.
        
        This test ensures proper logging when compliance is already satisfied.
        """
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        service.last_activity_date = date.today()  # Already done today
        
        # Create a mock safe_service even though it won't be used
        mock_safe_service = MagicMock()
        
        with patch('logging.Logger.info') as mock_info:
            result = await service.ensure_daily_compliance(mock_safe_service)
            
            # Should log that activity is already completed
            completed_logs = [call[0][0] for call in mock_info.call_args_list
                              if "Daily OLAS activity already completed" in call[0][0]]
            assert len(completed_logs) > 0
    
    def test_no_logfire_imports(self):
        """Test that ActivityService module doesn't import logfire.
        
        This test ensures complete removal of logfire dependencies.
        """
        # Check module imports
        import services.activity_service as activity_module
        
        # Verify no logfire in module namespace
        assert 'logfire' not in dir(activity_module)
        
        # Verify logging_config is imported instead
        assert 'setup_pearl_logger' in dir(activity_module)
        assert 'log_span' in dir(activity_module)
    
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_pearl_log_format_validation(self, mock_file, mock_exists, mock_settings):
        """Test that all logs from ActivityService pass Pearl format validation.
        
        This test captures actual log output and validates it against
        the Pearl format specification using the validate_log_format function.
        """
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        # Create a string buffer to capture logs
        import io
        log_capture = io.StringIO()
        
        # Set up handler to capture logs
        handler = logging.StreamHandler(log_capture)
        # Use the actual Pearl formatter
        from logging_config import PearlFormatter
        handler.setFormatter(PearlFormatter())
        
        # Create service
        service = ActivityService()
        
        # Add our handler to the service's logger temporarily
        original_handlers = service.logger.handlers[:]
        service.logger.handlers = [handler]
        
        try:
            # Perform operations that generate logs
            service.mark_activity_completed("0xtest123")
            
            # Get all logged lines
            log_output = log_capture.getvalue()
            log_lines = log_output.strip().split('\n')
            
            # Validate each line against Pearl format
            for line in log_lines:
                if line:  # Skip empty lines
                    assert validate_log_format(line), f"Log line failed Pearl validation: {line}"
        finally:
            # Restore original handlers
            service.logger.handlers = original_handlers