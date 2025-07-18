"""Test configuration updates for Pearl-compliant logging.

This test module validates the Phase 1.2 implementation of Pearl-compliant
logging configuration changes, ensuring proper removal of Logfire settings
and addition of Pearl logging configuration.

Why this test is important:
- Ensures config.py properly removes all Logfire-related settings
- Validates that Pearl logging environment variables are properly configured
- Tests that log levels and file paths are correctly parsed
- Verifies backward compatibility and proper default values
- Critical for Pearl platform compliance and logging infrastructure migration
"""

import os
import pytest
from typing import Dict, Any
from unittest.mock import patch

from config import Settings


class TestPearlLoggingConfiguration:
    """Test Pearl-compliant logging configuration changes."""

    def test_logfire_settings_removed(self):
        """Test that all Logfire-related settings are removed from config.
        
        This test is critical because Logfire settings must be completely
        removed for Pearl compliance. The test verifies that no Logfire
        configuration options remain in the Settings class.
        """
        settings = Settings()
        
        # Verify that Logfire settings no longer exist
        assert not hasattr(settings, 'logfire_token'), "logfire_token should be removed"
        assert not hasattr(settings, 'logfire_project'), "logfire_project should be removed" 
        assert not hasattr(settings, 'logfire_ignore_no_config'), "logfire_ignore_no_config should be removed"

    def test_pearl_log_level_configuration(self):
        """Test that LOG_LEVEL environment variable is properly configured.
        
        This test validates that the Pearl logging system can properly
        read and validate log levels from environment variables.
        Critical for ensuring proper log filtering in Pearl platform.
        """
        with patch.dict(os.environ, {'LOG_LEVEL': 'DEBUG'}):
            settings = Settings()
            assert settings.log_level == 'DEBUG'

        with patch.dict(os.environ, {'LOG_LEVEL': 'INFO'}):
            settings = Settings()
            assert settings.log_level == 'INFO'

        with patch.dict(os.environ, {'LOG_LEVEL': 'WARNING'}):
            settings = Settings()
            assert settings.log_level == 'WARNING'

        with patch.dict(os.environ, {'LOG_LEVEL': 'ERROR'}):
            settings = Settings()
            assert settings.log_level == 'ERROR'

    def test_pearl_log_level_defaults(self):
        """Test that log level defaults to INFO when not specified.
        
        This test ensures proper fallback behavior when LOG_LEVEL
        environment variable is not set. INFO level is the Pearl
        platform standard for production deployments.
        """
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert settings.log_level == 'INFO'

    def test_pearl_log_level_validation(self):
        """Test that invalid log levels are properly rejected.
        
        This test is critical for preventing misconfigurations that
        could cause logging failures in the Pearl platform environment.
        """
        invalid_levels = ['TRACE', 'VERBOSE', 'INVALID', 'CRITICAL', 'FATAL']
        
        for invalid_level in invalid_levels:
            with patch.dict(os.environ, {'LOG_LEVEL': invalid_level}, clear=False):
                with pytest.raises(ValueError, match="Invalid log level"):
                    Settings()

    def test_pearl_log_file_path_configuration(self):
        """Test that LOG_FILE_PATH environment variable is properly configured.
        
        This test validates that the Pearl logging system can properly
        configure custom log file paths. Critical for Pearl platform
        compliance which requires specific log file locations.
        """
        custom_path = "/custom/path/to/log.txt"
        with patch.dict(os.environ, {'LOG_FILE_PATH': custom_path}):
            settings = Settings()
            assert settings.log_file_path == custom_path

    def test_pearl_log_file_path_defaults(self):
        """Test that log file path defaults to Pearl-compliant location.
        
        This test ensures that when no custom path is specified,
        the system defaults to the Pearl platform standard log.txt location.
        """
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert settings.log_file_path == "log.txt"

    def test_pearl_log_file_path_validation(self):
        """Test that log file paths are properly validated.
        
        This test prevents invalid file paths that could cause
        logging failures in the Pearl platform container environment.
        """
        # Test empty string defaults to log.txt
        with patch.dict(os.environ, {'LOG_FILE_PATH': ''}):
            settings = Settings()
            assert settings.log_file_path == 'log.txt'

        # Test None value string raises error
        with patch.dict(os.environ, {'LOG_FILE_PATH': 'None'}):
            with pytest.raises(ValueError, match="Log file path cannot be empty"):
                Settings()

    def test_pearl_logging_environment_integration(self):
        """Test complete Pearl logging environment configuration.
        
        This integration test validates that all Pearl logging
        settings work together correctly and are properly loaded
        from environment variables.
        """
        test_config = {
            'LOG_LEVEL': 'WARNING',
            'LOG_FILE_PATH': '/pearl/logs/agent.log'
        }
        
        with patch.dict(os.environ, test_config):
            settings = Settings()
            assert settings.log_level == 'WARNING'
            assert settings.log_file_path == '/pearl/logs/agent.log'

    def test_no_logfire_environment_variables_parsed(self):
        """Test that Logfire environment variables are no longer parsed.
        
        This test ensures complete removal of Logfire integration
        by verifying that even if Logfire environment variables exist,
        they are not loaded or used by the application.
        """
        logfire_env = {
            'LOGFIRE_TOKEN': 'fake-token',
            'LOGFIRE_PROJECT': 'fake-project',
            'LOGFIRE_IGNORE_NO_CONFIG': 'true'
        }
        
        with patch.dict(os.environ, logfire_env):
            settings = Settings()
            
            # Verify Logfire settings are not loaded
            assert not hasattr(settings, 'logfire_token')
            assert not hasattr(settings, 'logfire_project')
            assert not hasattr(settings, 'logfire_ignore_no_config')

    def test_backward_compatibility_without_pearl_config(self):
        """Test that application still works without Pearl logging config.
        
        This test ensures that during migration, the application
        can still function if Pearl logging environment variables
        are not yet configured (graceful degradation).
        """
        # Clear all logging-related environment variables
        env_clear = {
            'LOG_LEVEL': '',
            'LOG_FILE_PATH': '',
            'LOGFIRE_TOKEN': '',
            'LOGFIRE_PROJECT': ''
        }
        
        with patch.dict(os.environ, env_clear, clear=False):
            settings = Settings()
            
            # Should use Pearl defaults
            assert settings.log_level == 'INFO'
            assert settings.log_file_path == 'log.txt'

    def test_pearl_logging_config_method(self):
        """Test new method to get Pearl logging configuration.
        
        This test validates the new get_pearl_logging_config() method
        that provides a clean interface for accessing Pearl logging
        settings throughout the application.
        """
        with patch.dict(os.environ, {'LOG_LEVEL': 'DEBUG', 'LOG_FILE_PATH': 'debug.log'}):
            settings = Settings()
            config = settings.get_pearl_logging_config()
            
            expected_config = {
                'log_level': 'DEBUG',
                'log_file_path': 'debug.log'
            }
            
            assert config == expected_config
            assert isinstance(config, dict)