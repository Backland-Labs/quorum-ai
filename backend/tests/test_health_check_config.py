"""
Tests for health check configuration feature.

This test suite verifies that the health check endpoint can be configured
via environment variables to support different deployment scenarios.
"""
import os
import pytest
from unittest.mock import patch
from config import Settings


class TestHealthCheckConfiguration:
    """Test health check configuration via environment variables."""
    
    def test_default_health_check_port(self):
        """
        Test that HEALTH_CHECK_PORT defaults to 8716 when not set.
        
        This is important because Pearl platform expects port 8716 by default.
        The default ensures compatibility without explicit configuration.
        """
        settings = Settings()
        assert settings.HEALTH_CHECK_PORT == 8716
    
    def test_custom_health_check_port_from_env(self):
        """
        Test that HEALTH_CHECK_PORT can be overridden via environment variable.
        
        This is important for deployment flexibility - different environments
        may require different ports due to conflicts or routing requirements.
        """
        with patch.dict(os.environ, {"HEALTH_CHECK_PORT": "9000"}):
            settings = Settings()
            assert settings.HEALTH_CHECK_PORT == 9000
    
    def test_default_health_check_path(self):
        """
        Test that HEALTH_CHECK_PATH defaults to /healthcheck.
        
        This is important because Pearl platform expects this specific path.
        The default ensures compatibility without explicit configuration.
        """
        settings = Settings()
        assert settings.HEALTH_CHECK_PATH == "/healthcheck"
    
    def test_custom_health_check_path_from_env(self):
        """
        Test that HEALTH_CHECK_PATH can be overridden via environment variable.
        
        This is important for deployment flexibility - some environments may
        require different paths due to routing or proxy configurations.
        """
        with patch.dict(os.environ, {"HEALTH_CHECK_PATH": "/api/v1/health"}):
            settings = Settings()
            assert settings.HEALTH_CHECK_PATH == "/api/v1/health"
    
    def test_default_fast_transition_threshold(self):
        """
        Test that FAST_TRANSITION_THRESHOLD defaults to 5 seconds.
        
        This is important for determining when state transitions are happening
        too quickly, which may indicate a problem with the agent.
        """
        settings = Settings()
        assert settings.FAST_TRANSITION_THRESHOLD == 5
    
    def test_custom_fast_transition_threshold_from_env(self):
        """
        Test that FAST_TRANSITION_THRESHOLD can be overridden via environment variable.
        
        This is important for tuning the health check sensitivity based on
        the specific workload and expected transition patterns.
        """
        with patch.dict(os.environ, {"FAST_TRANSITION_THRESHOLD": "10"}):
            settings = Settings()
            assert settings.FAST_TRANSITION_THRESHOLD == 10
    
    def test_fast_transition_threshold_type_conversion(self):
        """
        Test that FAST_TRANSITION_THRESHOLD is properly converted to int.
        
        This is important because environment variables are strings,
        but we need an integer for comparison operations.
        """
        with patch.dict(os.environ, {"FAST_TRANSITION_THRESHOLD": "3"}):
            settings = Settings()
            assert isinstance(settings.FAST_TRANSITION_THRESHOLD, int)
            assert settings.FAST_TRANSITION_THRESHOLD == 3
    
    def test_invalid_port_raises_error(self):
        """
        Test that invalid port values raise a configuration error.
        
        This is important for fail-fast behavior - we want to catch
        configuration errors at startup rather than runtime.
        """
        with patch.dict(os.environ, {"HEALTH_CHECK_PORT": "invalid"}):
            with pytest.raises(ValueError):
                Settings()
    
    def test_invalid_threshold_raises_error(self):
        """
        Test that invalid threshold values raise a configuration error.
        
        This is important for fail-fast behavior - we want to catch
        configuration errors at startup rather than runtime.
        """
        with patch.dict(os.environ, {"FAST_TRANSITION_THRESHOLD": "not-a-number"}):
            with pytest.raises(ValueError):
                Settings()
    
    def test_port_range_validation(self):
        """
        Test that port values must be in valid range (1-65535).
        
        This is important to prevent configuration errors that would
        cause the service to fail at startup.
        """
        # Test port too low
        with patch.dict(os.environ, {"HEALTH_CHECK_PORT": "0"}):
            with pytest.raises(ValueError, match="must be between 1 and 65535"):
                Settings()
        
        # Test port too high
        with patch.dict(os.environ, {"HEALTH_CHECK_PORT": "70000"}):
            with pytest.raises(ValueError, match="must be between 1 and 65535"):
                Settings()
        
        # Test valid port at boundaries
        with patch.dict(os.environ, {"HEALTH_CHECK_PORT": "1"}):
            settings = Settings()
            assert settings.HEALTH_CHECK_PORT == 1
            
        with patch.dict(os.environ, {"HEALTH_CHECK_PORT": "65535"}):
            settings = Settings()
            assert settings.HEALTH_CHECK_PORT == 65535