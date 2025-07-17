"""Test suite for agent run configuration management.

This module tests the configuration management functionality specifically for
the agent run feature, including environment variable handling, validation,
and default values.
"""

import os
import pytest
from unittest.mock import patch
from pydantic import ValidationError

from config import Settings, settings


class TestAgentRunConfiguration:
    """Test agent run configuration management."""

    def test_agent_run_default_values(self):
        """Test that agent run configuration has proper default values."""
        # Test that the default values are set correctly
        assert settings.vote_confidence_threshold == 0.6
        assert settings.activity_check_interval == 3600  # 1 hour
        assert settings.proposal_check_interval == 300  # 5 minutes
        assert settings.min_time_before_deadline == 1800  # 30 minutes

    def test_agent_run_config_from_env(self):
        """Test agent run configuration loading from environment variables."""
        with patch.dict(os.environ, {
            "VOTE_CONFIDENCE_THRESHOLD": "0.8",
            "ACTIVITY_CHECK_INTERVAL": "7200",
            "PROPOSAL_CHECK_INTERVAL": "600",
            "MIN_TIME_BEFORE_DEADLINE": "3600"
        }):
            test_settings = Settings()
            assert test_settings.vote_confidence_threshold == 0.8
            assert test_settings.activity_check_interval == 7200
            assert test_settings.proposal_check_interval == 600
            assert test_settings.min_time_before_deadline == 3600

    def test_agent_run_config_validation(self):
        """Test validation of agent run configuration values."""
        # Test vote confidence threshold validation - Pydantic will catch this
        with patch.dict(os.environ, {"VOTE_CONFIDENCE_THRESHOLD": "1.5"}):
            with pytest.raises(ValidationError):
                Settings()

        with patch.dict(os.environ, {"VOTE_CONFIDENCE_THRESHOLD": "-0.1"}):
            with pytest.raises(ValidationError):
                Settings()

        # Test interval validation - Pydantic will catch these too
        with patch.dict(os.environ, {"ACTIVITY_CHECK_INTERVAL": "0"}):
            with pytest.raises(ValidationError):
                Settings()

        with patch.dict(os.environ, {"PROPOSAL_CHECK_INTERVAL": "-1"}):
            with pytest.raises(ValidationError):
                Settings()

        with patch.dict(os.environ, {"MIN_TIME_BEFORE_DEADLINE": "0"}):
            with pytest.raises(ValidationError):
                Settings()

    def test_agent_run_config_class_vars(self):
        """Test that class variables are correctly defined."""
        assert Settings.DEFAULT_ACTIVITY_CHECK_INTERVAL_SECONDS == 3600
        assert Settings.DEFAULT_PROPOSAL_CHECK_INTERVAL_SECONDS == 300
        assert Settings.DEFAULT_MIN_TIME_BEFORE_DEADLINE_SECONDS == 1800

    def test_agent_run_config_field_constraints(self):
        """Test field constraints for agent run configuration."""
        # Test that pydantic field constraints work correctly
        test_settings = Settings()
        
        # All intervals should be positive
        assert test_settings.activity_check_interval > 0
        assert test_settings.proposal_check_interval > 0
        assert test_settings.min_time_before_deadline > 0
        
        # Vote confidence threshold should be between 0 and 1
        assert 0.0 <= test_settings.vote_confidence_threshold <= 1.0


class TestAgentRunConfigurationExtensions:
    """Test new agent run configuration extensions."""

    def test_new_agent_run_config_defaults(self):
        """Test that new agent run configuration fields have proper defaults."""
        test_settings = Settings()
        
        # Test the new agent run configuration fields
        assert test_settings.max_proposals_per_run == 3
        assert test_settings.default_confidence_threshold == 0.7
        assert test_settings.proposal_fetch_timeout == 30
        assert test_settings.vote_execution_timeout == 60
        assert test_settings.max_retry_attempts == 3
        assert test_settings.retry_delay_seconds == 5
        
        # Test that existing fields still work correctly
        assert hasattr(test_settings, 'vote_confidence_threshold')
        assert hasattr(test_settings, 'activity_check_interval')
        assert hasattr(test_settings, 'proposal_check_interval')
        assert hasattr(test_settings, 'min_time_before_deadline')

    def test_agent_run_config_hot_reload_support(self):
        """Test that configuration supports hot reloading."""
        # Create a test settings instance
        test_settings = Settings()
        original_threshold = test_settings.default_confidence_threshold
        original_max_proposals = test_settings.max_proposals_per_run
        
        # Test that we can reload configuration without restarting the application
        with patch.dict(os.environ, {
            "DEFAULT_CONFIDENCE_THRESHOLD": "0.9",
            "MAX_PROPOSALS_PER_RUN": "5"
        }):
            # Reload configuration
            test_settings.reload_config()
            
            # Verify that values were updated
            assert test_settings.default_confidence_threshold == 0.9
            assert test_settings.max_proposals_per_run == 5
            
        # Test get_agent_run_config method
        agent_config = test_settings.get_agent_run_config()
        assert isinstance(agent_config, dict)
        assert "max_proposals_per_run" in agent_config
        assert "default_confidence_threshold" in agent_config
        assert "proposal_fetch_timeout" in agent_config
        assert "vote_execution_timeout" in agent_config
        assert "max_retry_attempts" in agent_config
        assert "retry_delay_seconds" in agent_config

    def test_agent_run_config_env_var_handling(self):
        """Test environment variable handling for agent run configuration."""
        # Test that environment variables are properly parsed and validated
        with patch.dict(os.environ, {
            "VOTE_CONFIDENCE_THRESHOLD": "0.75",
            "ACTIVITY_CHECK_INTERVAL": "5400",  # 1.5 hours
            "PROPOSAL_CHECK_INTERVAL": "450",   # 7.5 minutes
            "MIN_TIME_BEFORE_DEADLINE": "2700",  # 45 minutes
            "MAX_PROPOSALS_PER_RUN": "5",
            "DEFAULT_CONFIDENCE_THRESHOLD": "0.8",
            "PROPOSAL_FETCH_TIMEOUT": "45",
            "VOTE_EXECUTION_TIMEOUT": "90",
            "MAX_RETRY_ATTEMPTS": "5",
            "RETRY_DELAY_SECONDS": "10"
        }):
            test_settings = Settings()
            assert test_settings.vote_confidence_threshold == 0.75
            assert test_settings.activity_check_interval == 5400
            assert test_settings.proposal_check_interval == 450
            assert test_settings.min_time_before_deadline == 2700
            assert test_settings.max_proposals_per_run == 5
            assert test_settings.default_confidence_threshold == 0.8
            assert test_settings.proposal_fetch_timeout == 45
            assert test_settings.vote_execution_timeout == 90
            assert test_settings.max_retry_attempts == 5
            assert test_settings.retry_delay_seconds == 10

    def test_agent_run_config_integration_with_existing_config(self):
        """Test that agent run configuration integrates well with existing configuration."""
        test_settings = Settings()
        
        # Verify that existing configuration still works
        assert hasattr(test_settings, 'app_name')
        assert hasattr(test_settings, 'debug')
        assert hasattr(test_settings, 'host')
        assert hasattr(test_settings, 'port')
        
        # Verify that agent run configuration is properly integrated
        assert hasattr(test_settings, 'vote_confidence_threshold')
        assert hasattr(test_settings, 'activity_check_interval')
        assert hasattr(test_settings, 'proposal_check_interval')
        assert hasattr(test_settings, 'min_time_before_deadline')

    def test_agent_run_config_error_handling(self):
        """Test error handling for invalid agent run configuration."""
        # Test invalid string values
        with patch.dict(os.environ, {"VOTE_CONFIDENCE_THRESHOLD": "invalid"}):
            with pytest.raises(ValueError):
                Settings()

        with patch.dict(os.environ, {"ACTIVITY_CHECK_INTERVAL": "not_a_number"}):
            with pytest.raises(ValueError):
                Settings()

        with patch.dict(os.environ, {"PROPOSAL_CHECK_INTERVAL": "not_a_number"}):
            with pytest.raises(ValueError):
                Settings()

        with patch.dict(os.environ, {"MIN_TIME_BEFORE_DEADLINE": "not_a_number"}):
            with pytest.raises(ValueError):
                Settings()

        # Test invalid values for new agent run config fields
        with patch.dict(os.environ, {"MAX_PROPOSALS_PER_RUN": "not_a_number"}):
            with pytest.raises(ValueError):
                Settings()

        with patch.dict(os.environ, {"DEFAULT_CONFIDENCE_THRESHOLD": "invalid"}):
            with pytest.raises(ValueError):
                Settings()

        with patch.dict(os.environ, {"PROPOSAL_FETCH_TIMEOUT": "not_a_number"}):
            with pytest.raises(ValueError):
                Settings()

        with patch.dict(os.environ, {"VOTE_EXECUTION_TIMEOUT": "invalid"}):
            with pytest.raises(ValueError):
                Settings()

        with patch.dict(os.environ, {"MAX_RETRY_ATTEMPTS": "not_a_number"}):
            with pytest.raises(ValueError):
                Settings()

        with patch.dict(os.environ, {"RETRY_DELAY_SECONDS": "invalid"}):
            with pytest.raises(ValueError):
                Settings()

        # Test out-of-range values - Pydantic will catch these
        with patch.dict(os.environ, {"MAX_PROPOSALS_PER_RUN": "11"}):
            with pytest.raises(ValidationError):
                Settings()

        with patch.dict(os.environ, {"DEFAULT_CONFIDENCE_THRESHOLD": "1.5"}):
            with pytest.raises(ValidationError):
                Settings()

        with patch.dict(os.environ, {"PROPOSAL_FETCH_TIMEOUT": "0"}):
            with pytest.raises(ValidationError):
                Settings()

        with patch.dict(os.environ, {"VOTE_EXECUTION_TIMEOUT": "-1"}):
            with pytest.raises(ValidationError):
                Settings()

        with patch.dict(os.environ, {"MAX_RETRY_ATTEMPTS": "11"}):
            with pytest.raises(ValidationError):
                Settings()

        with patch.dict(os.environ, {"RETRY_DELAY_SECONDS": "0"}):
            with pytest.raises(ValidationError):
                Settings()

    def test_agent_run_config_boundary_values(self):
        """Test boundary values for agent run configuration."""
        # Test minimum valid values
        with patch.dict(os.environ, {
            "VOTE_CONFIDENCE_THRESHOLD": "0.0",
            "ACTIVITY_CHECK_INTERVAL": "1",
            "PROPOSAL_CHECK_INTERVAL": "1",
            "MIN_TIME_BEFORE_DEADLINE": "1",
            "MAX_PROPOSALS_PER_RUN": "1",
            "DEFAULT_CONFIDENCE_THRESHOLD": "0.0",
            "PROPOSAL_FETCH_TIMEOUT": "1",
            "VOTE_EXECUTION_TIMEOUT": "1",
            "MAX_RETRY_ATTEMPTS": "0",
            "RETRY_DELAY_SECONDS": "1"
        }):
            test_settings = Settings()
            assert test_settings.vote_confidence_threshold == 0.0
            assert test_settings.activity_check_interval == 1
            assert test_settings.proposal_check_interval == 1
            assert test_settings.min_time_before_deadline == 1
            assert test_settings.max_proposals_per_run == 1
            assert test_settings.default_confidence_threshold == 0.0
            assert test_settings.proposal_fetch_timeout == 1
            assert test_settings.vote_execution_timeout == 1
            assert test_settings.max_retry_attempts == 0
            assert test_settings.retry_delay_seconds == 1

        # Test maximum valid values
        with patch.dict(os.environ, {
            "VOTE_CONFIDENCE_THRESHOLD": "1.0",
            "ACTIVITY_CHECK_INTERVAL": "86400",  # 24 hours
            "PROPOSAL_CHECK_INTERVAL": "3600",   # 1 hour
            "MIN_TIME_BEFORE_DEADLINE": "86400",  # 24 hours
            "MAX_PROPOSALS_PER_RUN": "10",
            "DEFAULT_CONFIDENCE_THRESHOLD": "1.0",
            "PROPOSAL_FETCH_TIMEOUT": "300",  # 5 minutes
            "VOTE_EXECUTION_TIMEOUT": "600",  # 10 minutes
            "MAX_RETRY_ATTEMPTS": "10",
            "RETRY_DELAY_SECONDS": "60"  # 1 minute
        }):
            test_settings = Settings()
            assert test_settings.vote_confidence_threshold == 1.0
            assert test_settings.activity_check_interval == 86400
            assert test_settings.proposal_check_interval == 3600
            assert test_settings.min_time_before_deadline == 86400
            assert test_settings.max_proposals_per_run == 10
            assert test_settings.default_confidence_threshold == 1.0
            assert test_settings.proposal_fetch_timeout == 300
            assert test_settings.vote_execution_timeout == 600
            assert test_settings.max_retry_attempts == 10
            assert test_settings.retry_delay_seconds == 60