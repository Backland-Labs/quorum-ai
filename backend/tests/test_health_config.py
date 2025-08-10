"""Test health configuration constants and exceptions for Olas Pearl compliance."""

import pytest
from unittest.mock import patch
import os

from config import Settings
from models import HealthCheckError, HealthServiceTimeoutError


class TestHealthConfigurationConstants:
    """Test health-related configuration constants."""

    def test_health_check_timeout_default_value(self):
        """Test that HEALTH_CHECK_TIMEOUT defaults to 50 milliseconds.
        
        This test verifies that the health check timeout constant is set to 50ms
        as required for Pearl compliance, ensuring health checks complete within
        the required timeframe for optimal agent performance.
        """
        settings = Settings()
        assert hasattr(settings, 'HEALTH_CHECK_TIMEOUT')
        assert settings.HEALTH_CHECK_TIMEOUT == 50

    def test_health_check_enabled_default_value(self):
        """Test that HEALTH_CHECK_ENABLED defaults to True.
        
        This test ensures that health checking is enabled by default, allowing
        the Pearl platform to monitor agent health status without additional
        configuration requirements.
        """
        settings = Settings()
        assert hasattr(settings, 'HEALTH_CHECK_ENABLED')
        assert settings.HEALTH_CHECK_ENABLED is True

    def test_pearl_log_format_default_value(self):
        """Test that PEARL_LOG_FORMAT has the correct Pearl-compliant format.
        
        This test verifies that the Pearl logging format constant matches the
        required format specification for Pearl platform compliance, ensuring
        proper log parsing and monitoring capabilities.
        """
        settings = Settings()
        assert hasattr(settings, 'PEARL_LOG_FORMAT')
        expected_format = "[%Y-%m-%d %H:%M:%S,%f] [%levelname] [agent] %message"
        assert settings.PEARL_LOG_FORMAT == expected_format

    def test_health_check_timeout_from_environment(self):
        """Test that HEALTH_CHECK_TIMEOUT can be overridden via environment variable.
        
        This test ensures that the health check timeout can be customized through
        environment configuration while maintaining type safety and validation.
        """
        test_timeout = 75
        with patch.dict(os.environ, {"HEALTH_CHECK_TIMEOUT": str(test_timeout)}):
            settings = Settings()
            assert settings.HEALTH_CHECK_TIMEOUT == test_timeout

    def test_health_check_enabled_from_environment(self):
        """Test that HEALTH_CHECK_ENABLED can be overridden via environment variable.
        
        This test verifies that health checking can be disabled through environment
        configuration for testing or debugging scenarios while maintaining proper
        boolean type conversion.
        """
        with patch.dict(os.environ, {"HEALTH_CHECK_ENABLED": "false"}):
            settings = Settings()
            assert settings.HEALTH_CHECK_ENABLED is False

        with patch.dict(os.environ, {"HEALTH_CHECK_ENABLED": "true"}):
            settings = Settings()
            assert settings.HEALTH_CHECK_ENABLED is True

    def test_health_check_timeout_validation(self):
        """Test that HEALTH_CHECK_TIMEOUT validates positive integer values.
        
        This test ensures that the health check timeout value is validated to be
        a positive integer, preventing configuration errors that could impact
        agent performance or Pearl compliance.
        """
        # Test valid positive values
        valid_timeouts = [1, 25, 50, 100, 1000]
        for timeout in valid_timeouts:
            with patch.dict(os.environ, {"HEALTH_CHECK_TIMEOUT": str(timeout)}):
                settings = Settings()
                assert settings.HEALTH_CHECK_TIMEOUT == timeout

        # Test invalid values should raise validation error
        invalid_timeouts = [-1, 0, "invalid"]
        for timeout in invalid_timeouts:
            with patch.dict(os.environ, {"HEALTH_CHECK_TIMEOUT": str(timeout)}):
                with pytest.raises((ValueError, TypeError)):
                    Settings()

    def test_pearl_log_format_from_environment(self):
        """Test that PEARL_LOG_FORMAT can be overridden via environment variable.
        
        This test verifies that the Pearl log format can be customized through
        environment configuration while maintaining string type validation.
        """
        custom_format = "[%Y-%m-%d %H:%M:%S] [%levelname] [custom] %message"
        with patch.dict(os.environ, {"PEARL_LOG_FORMAT": custom_format}):
            settings = Settings()
            assert settings.PEARL_LOG_FORMAT == custom_format


class TestHealthExceptions:
    """Test custom health exception classes."""

    def test_health_check_error_creation(self):
        """Test that HealthCheckError can be created with proper message and context.
        
        This test verifies that the HealthCheckError exception follows the existing
        exception patterns in the codebase, providing clear error messages and
        context for debugging health check failures.
        """
        error_message = "Health check failed for transaction manager"
        error_context = {"service": "SafeService", "timeout": 50}
        
        error = HealthCheckError(error_message, context=error_context)
        
        assert isinstance(error, Exception)
        assert str(error) == error_message
        assert error.context == error_context

    def test_health_check_error_without_context(self):
        """Test that HealthCheckError can be created without context.
        
        This test ensures that the HealthCheckError exception can be used in
        simple scenarios without requiring additional context, maintaining
        flexibility in error handling patterns.
        """
        error_message = "General health check failure"
        
        error = HealthCheckError(error_message)
        
        assert isinstance(error, Exception)
        assert str(error) == error_message
        assert error.context is None

    def test_health_service_timeout_error_creation(self):
        """Test that HealthServiceTimeoutError can be created with timeout information.
        
        This test verifies that the HealthServiceTimeoutError exception provides
        specific timeout-related context, helping with debugging timeout issues
        in health check operations.
        """
        error_message = "Health service operation timed out"
        timeout_ms = 50
        operation = "get_transaction_manager_status"
        
        error = HealthServiceTimeoutError(error_message, timeout_ms=timeout_ms, operation=operation)
        
        assert isinstance(error, HealthCheckError)  # Should inherit from HealthCheckError
        assert str(error) == error_message
        assert error.timeout_ms == timeout_ms
        assert error.operation == operation

    def test_health_service_timeout_error_inheritance(self):
        """Test that HealthServiceTimeoutError properly inherits from HealthCheckError.
        
        This test ensures that the exception hierarchy is properly structured,
        allowing for both specific timeout error handling and general health
        error handling patterns.
        """
        error = HealthServiceTimeoutError("Timeout occurred")
        
        assert isinstance(error, HealthCheckError)
        assert isinstance(error, Exception)

    def test_health_check_error_with_service_context(self):
        """Test HealthCheckError with service-specific context information.
        
        This test verifies that the HealthCheckError can carry service-specific
        context information, following the ExternalServiceError pattern mentioned
        in the error handling specification.
        """
        service_name = "HealthStatusService"
        error_message = "Failed to gather health status"
        context = {
            "service": service_name,
            "operation": "get_health_status",
            "timestamp": "2025-01-09T10:30:00Z"
        }
        
        error = HealthCheckError(error_message, context=context)
        
        assert error.context["service"] == service_name
        assert error.context["operation"] == "get_health_status"
        assert "timestamp" in error.context

    def test_health_service_timeout_error_default_values(self):
        """Test HealthServiceTimeoutError with default parameter values.
        
        This test ensures that the HealthServiceTimeoutError can be created with
        minimal parameters while providing sensible defaults for optional fields.
        """
        error_message = "Operation timed out"
        
        error = HealthServiceTimeoutError(error_message)
        
        assert str(error) == error_message
        assert error.timeout_ms is None
        assert error.operation is None
        assert error.context is None

    def test_exception_string_representation(self):
        """Test that exceptions have proper string representations.
        
        This test verifies that both exception classes provide clear and
        informative string representations for logging and debugging purposes.
        """
        health_error = HealthCheckError("Health check failed")
        timeout_error = HealthServiceTimeoutError("Timeout occurred", timeout_ms=50, operation="test")
        
        assert str(health_error) == "Health check failed"
        assert str(timeout_error) == "Timeout occurred"
        
        # Test that they can be used in string formatting
        assert f"Error: {health_error}" == "Error: Health check failed"
        assert f"Error: {timeout_error}" == "Error: Timeout occurred"