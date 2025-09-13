"""Test configuration updates for Pearl-compliant logging.

This test module validates the Phase 1.2 implementation of Pearl-compliant
logging configuration changes, ensuring proper removal of Logfire settings
and addition of Pearl logging configuration.

Why this test is important:
- Ensures config.py properly removes all Logfire-related settings
- Validates that Pearl logging environment variables are properly configured
- Tests that log file paths are correctly parsed
- Verifies backward compatibility and proper default values
- Critical for Pearl platform compliance and logging infrastructure migration
"""

import os
import pytest
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
        assert not hasattr(settings, "logfire_token"), "logfire_token should be removed"
        assert not hasattr(settings, "logfire_project"), (
            "logfire_project should be removed"
        )
        assert not hasattr(settings, "logfire_ignore_no_config"), (
            "logfire_ignore_no_config should be removed"
        )


    def test_pearl_log_file_path_configuration(self):
        """Test that LOG_FILE_PATH environment variable is properly configured.

        This test validates that the Pearl logging system can properly
        configure custom log file paths. Critical for Pearl platform
        compliance which requires specific log file locations.
        """
        custom_path = "/custom/path/to/log.txt"
        with patch.dict(os.environ, {"LOG_FILE_PATH": custom_path}):
            settings = Settings()
            assert settings.log_file_path == custom_path

    def test_pearl_log_file_path_defaults(self):
        """Test that log file path defaults to Pearl-compliant location.

        This test ensures that when no custom path is specified,
        the system defaults to the Pearl platform standard location
        loaded from parent .env file configuration.
        """
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert settings.log_file_path == "/app/store/logs/pearl/log.txt"

    def test_pearl_log_file_path_validation(self):
        """Test that log file paths are properly validated.

        This test prevents invalid file paths that could cause
        logging failures in the Pearl platform container environment.
        """
        # Test empty string defaults to Pearl default path
        with patch.dict(os.environ, {"LOG_FILE_PATH": ""}):
            settings = Settings()
            assert settings.log_file_path == "/app/store/logs/pearl/log.txt"

        # Test None value string raises error
        with patch.dict(os.environ, {"LOG_FILE_PATH": "None"}):
            with pytest.raises(ValueError, match="Log file path cannot be empty"):
                Settings()

    def test_pearl_logging_environment_integration(self):
        """Test complete Pearl logging environment configuration.

        This integration test validates that Pearl logging
        settings are properly loaded from environment variables.
        """
        test_config = {"LOG_FILE_PATH": "/pearl/logs/agent.log"}

        with patch.dict(os.environ, test_config):
            settings = Settings()
            assert settings.log_file_path == "/pearl/logs/agent.log"

    def test_no_logfire_environment_variables_parsed(self):
        """Test that Logfire environment variables are no longer parsed.

        This test ensures complete removal of Logfire integration
        by verifying that even if Logfire environment variables exist,
        they are not loaded or used by the application.
        """
        logfire_env = {
            "LOGFIRE_TOKEN": "fake-token",
            "LOGFIRE_PROJECT": "fake-project",
            "LOGFIRE_IGNORE_NO_CONFIG": "true",
        }

        with patch.dict(os.environ, logfire_env):
            settings = Settings()

            # Verify Logfire settings are not loaded
            assert not hasattr(settings, "logfire_token")
            assert not hasattr(settings, "logfire_project")
            assert not hasattr(settings, "logfire_ignore_no_config")

    def test_backward_compatibility_without_pearl_config(self):
        """Test that application still works without Pearl logging config.

        This test ensures that during migration, the application
        can still function if Pearl logging environment variables
        are not yet configured (graceful degradation).
        """
        # Clear all logging-related environment variables
        env_clear = {
            "LOG_FILE_PATH": "",
            "LOGFIRE_TOKEN": "",
            "LOGFIRE_PROJECT": "",
        }

        with patch.dict(os.environ, env_clear, clear=False):
            settings = Settings()

            # Should use Pearl defaults
            assert settings.log_file_path == "/app/store/logs/pearl/log.txt"

    def test_pearl_logging_config_method(self):
        """Test new method to get Pearl logging configuration.

        This test validates the new get_pearl_logging_config() method
        that provides a clean interface for accessing Pearl logging
        settings throughout the application.
        """
        with patch.dict(os.environ, {"LOG_FILE_PATH": "debug.log"}):
            settings = Settings()
            config = settings.get_pearl_logging_config()

            expected_config = {"log_level": settings.log_level, "log_file_path": "debug.log"}

            assert config == expected_config
            assert isinstance(config, dict)
