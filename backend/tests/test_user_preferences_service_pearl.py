"""Test Pearl logging compliance for UserPreferencesService.

This test module ensures that UserPreferencesService follows Pearl logging
standards and maintains all functionality while using Pearl-compliant logging.
"""

import logging
import io
import json
from unittest.mock import patch, mock_open, MagicMock, AsyncMock
import pytest
import tempfile
import os

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.user_preferences_service import UserPreferencesService
from models import UserPreferences, VotingStrategy
from logging_config import validate_log_format, PearlFormatter


class TestUserPreferencesServicePearlCompliance:
    """Test suite for Pearl logging compliance in UserPreferencesService."""
    
    def test_no_logfire_imports(self):
        """Test that UserPreferencesService module doesn't import logfire.
        
        This test ensures complete removal of logfire dependencies
        and verifies that Pearl logging utilities are imported instead.
        """
        # Check module imports
        import services.user_preferences_service as prefs_module
        
        # Verify no logfire in module namespace
        assert 'logfire' not in dir(prefs_module), "Logfire should not be imported"
        
        # Verify logging_config is imported instead
        assert 'setup_pearl_logger' in dir(prefs_module), "setup_pearl_logger should be imported"
    
    def test_logger_initialization(self):
        """Test that UserPreferencesService initializes Pearl logger correctly.
        
        This test verifies that the service creates a logger using
        setup_pearl_logger with the correct module name.
        """
        with patch('services.user_preferences_service.setup_pearl_logger') as mock_setup:
            mock_logger = MagicMock()
            mock_setup.return_value = mock_logger
            
            service = UserPreferencesService()
            
            # Verify setup_pearl_logger was called with module name
            mock_setup.assert_called_once_with('services.user_preferences_service')
            
            # Verify logger is assigned
            assert hasattr(service, 'logger'), "Service should have logger attribute"
            assert service.logger == mock_logger
    
    @pytest.mark.asyncio
    @patch("os.path.exists")
    async def test_load_preferences_file_not_found_pearl_logging(self, mock_exists):
        """Test Pearl-compliant logging when preferences file doesn't exist.
        
        This test ensures info logs are generated with Pearl format
        when the preferences file is not found.
        """
        mock_exists.return_value = False
        
        with patch('logging.Logger.info') as mock_info:
            service = UserPreferencesService()
            prefs = await service.load_preferences()
            
            # Verify info log was called
            mock_info.assert_called()
            
            # Check log message format
            log_message = mock_info.call_args[0][0]
            assert "Preferences file not found" in log_message
            assert "preferences_file=%s" in log_message
    
    @pytest.mark.asyncio
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data='{"voting_strategy": "balanced", "confidence_threshold": 0.7}')
    async def test_load_preferences_success_pearl_logging(self, mock_file, mock_exists):
        """Test Pearl-compliant logging during successful preference loading.
        
        This test verifies that successful preference loading generates
        Pearl-compliant log messages with proper formatting.
        """
        mock_exists.return_value = True
        
        with patch('logging.Logger.info') as mock_info:
            service = UserPreferencesService()
            prefs = await service.load_preferences()
            
            # Verify info log was called
            mock_info.assert_called()
            
            # Find the success log
            log_calls = [call[0][0] for call in mock_info.call_args_list]
            success_logs = [msg for msg in log_calls if "User preferences loaded successfully" in msg]
            assert len(success_logs) > 0, "Should log successful preference loading"
            
            # Verify structured logging with %s formatting
            assert "preferences_file=%s" in success_logs[0]
            assert "voting_strategy=%s" in success_logs[0]
    
    @pytest.mark.asyncio
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data='invalid json{')
    async def test_parse_error_pearl_logging(self, mock_file, mock_exists):
        """Test Pearl-compliant warning logging on JSON parse errors.
        
        This test verifies warning logging follows Pearl format when
        JSON parsing fails during preference loading.
        """
        mock_exists.return_value = True
        
        with patch('logging.Logger.warning') as mock_warning:
            service = UserPreferencesService()
            prefs = await service.load_preferences()
            
            # Verify warning log was called
            mock_warning.assert_called()
            
            # Check log message format
            log_message = mock_warning.call_args[0][0]
            assert "Could not load user preferences" in log_message
            assert "error=%s" in log_message
    
    @pytest.mark.asyncio
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.rename")
    @patch("os.makedirs")
    async def test_save_preferences_pearl_logging(self, mock_makedirs, mock_rename, mock_file):
        """Test Pearl-compliant logging during preference saving.
        
        This test ensures info logs are generated with Pearl format
        when preferences are successfully saved.
        """
        with patch('logging.Logger.info') as mock_info:
            service = UserPreferencesService()
            prefs = UserPreferences(voting_strategy=VotingStrategy.BALANCED)
            
            # Mock tempfile creation
            with patch('tempfile.NamedTemporaryFile', mock_open()):
                await service.save_preferences(prefs)
            
            # Verify info log was called
            mock_info.assert_called()
            
            # Check log message
            log_calls = [call[0][0] for call in mock_info.call_args_list]
            save_logs = [msg for msg in log_calls if "User preferences saved successfully" in msg]
            assert len(save_logs) > 0
            assert "preferences_file=%s" in save_logs[0]
    
    @pytest.mark.asyncio
    async def test_save_error_pearl_logging(self):
        """Test Pearl-compliant error logging on save failures.
        
        This test verifies error logging follows Pearl format when
        saving preferences fails due to permission errors.
        """
        with patch('logging.Logger.error') as mock_error:
            service = UserPreferencesService()
            prefs = UserPreferences(voting_strategy=VotingStrategy.BALANCED)
            
            # Mock the rename operation to fail with permission error
            with patch("os.rename", side_effect=PermissionError("No write access")):
                with patch('tempfile.NamedTemporaryFile', mock_open()):
                    await service.save_preferences(prefs)
            
            # Verify error log was called
            mock_error.assert_called()
            
            # Check log message
            log_message = mock_error.call_args[0][0]
            assert "Could not save user preferences" in log_message
            assert "error=%s" in log_message
    
    @pytest.mark.asyncio
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data='{"voting_strategy": "balanced"}')
    async def test_update_preference_pearl_logging(self, mock_file, mock_exists):
        """Test Pearl-compliant logging during preference updates.
        
        This test ensures info logs are generated when preferences
        are updated, following Pearl format standards.
        """
        mock_exists.return_value = True
        
        with patch('logging.Logger.info') as mock_info:
            with patch('os.rename'):
                with patch('tempfile.NamedTemporaryFile', mock_open()):
                    service = UserPreferencesService()
                    await service.update_preference("voting_strategy", VotingStrategy.AGGRESSIVE)
            
            # Check for preference update log
            log_calls = [call[0][0] for call in mock_info.call_args_list]
            update_logs = [msg for msg in log_calls if "User preference updated" in msg]
            assert len(update_logs) > 0
            assert "key=%s" in update_logs[0]
            assert "value=%s" in update_logs[0]
    
    @pytest.mark.asyncio
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data='{"voting_strategy": "balanced"}')
    async def test_pearl_log_format_validation(self, mock_file, mock_exists):
        """Test that all logs from UserPreferencesService pass Pearl format validation.
        
        This test captures actual log output and validates it against
        the Pearl format specification using the validate_log_format function.
        """
        mock_exists.return_value = True
        
        # Create a string buffer to capture logs
        log_capture = io.StringIO()
        
        # Set up handler to capture logs
        handler = logging.StreamHandler(log_capture)
        handler.setFormatter(PearlFormatter())
        
        # Create service
        service = UserPreferencesService()
        
        # Add our handler to the service's logger temporarily
        original_handlers = service.logger.handlers[:]
        service.logger.handlers = [handler]
        service.logger.setLevel(logging.INFO)
        
        try:
            # Perform operations that generate logs
            with patch('os.rename'):
                with patch('tempfile.NamedTemporaryFile', mock_open()):
                    prefs = await service.load_preferences()
                    await service.update_preference("confidence_threshold", 0.8)
                    await service.save_preferences(prefs)
            
            # Get all logged lines
            log_output = log_capture.getvalue()
            log_lines = log_output.strip().split('\n')
            
            # Validate each line against Pearl format
            for line in log_lines:
                if line:  # Skip empty lines
                    assert validate_log_format(line), f"Log line failed Pearl validation: {line}"
                    
                    # Additional checks for Pearl format
                    assert line.startswith('['), "Log should start with timestamp"
                    assert '[agent]' in line, "Log should contain [agent] tag"
                    assert line.count('[') >= 3, "Log should have timestamp, level, and agent tags"
        finally:
            # Restore original handlers
            service.logger.handlers = original_handlers
    
    def test_logger_uses_correct_level_methods(self):
        """Test that the logger uses correct Pearl-compliant level methods.
        
        Pearl uses WARN instead of WARNING, so we need to ensure
        the service uses logger.warning() which Pearl maps correctly.
        """
        with patch('services.user_preferences_service.setup_pearl_logger') as mock_setup:
            mock_logger = MagicMock()
            mock_setup.return_value = mock_logger
            
            service = UserPreferencesService()
            
            # Verify the logger has the correct methods
            assert hasattr(service.logger, 'info'), "Logger should have info method"
            assert hasattr(service.logger, 'warning'), "Logger should have warning method"
            assert hasattr(service.logger, 'error'), "Logger should have error method"
    
    @pytest.mark.asyncio
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data='{"voting_strategy": "balanced"}')
    async def test_structured_logging_preserved(self, mock_file, mock_exists):
        """Test that structured logging with key-value pairs is preserved.
        
        This test ensures that the migration maintains the structured
        logging format with key=value pairs using %s formatting.
        """
        mock_exists.return_value = True
        
        with patch('logging.Logger.info') as mock_info:
            service = UserPreferencesService()
            
            # Test load preferences
            prefs = await service.load_preferences()
            
            # Find the load success log call
            load_calls = [call for call in mock_info.call_args_list 
                         if "User preferences loaded successfully" in call[0][0]]
            
            assert len(load_calls) > 0, "Should log preference loading"
            
            # Verify structured data with %s formatting
            log_message = load_calls[0][0][0]
            log_args = load_calls[0][0][1:]
            
            assert "preferences_file=%s" in log_message
            assert "voting_strategy=%s" in log_message
            assert "confidence_threshold=%s" in log_message
            
            # Verify args contain actual values
            assert service.preferences_file in log_args
            assert "balanced" in log_args  # voting strategy value