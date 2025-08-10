"""Tests for environment variable helper function."""

import os
import pytest
from unittest.mock import patch

from utils.env_helper import get_env_with_prefix


class TestGetEnvWithPrefix:
    """Test the environment variable helper function with prefix fallback."""

    def test_prefixed_takes_precedence_over_non_prefixed(self):
        """Test that prefixed environment variables take precedence over non-prefixed ones.
        
        This is the CORE business logic - if both prefixed and non-prefixed exist,
        the prefixed version must be returned. This is critical for Pearl integration.
        """
        with patch.dict(os.environ, {
            "CONNECTION_CONFIGS_CONFIG_TEST_KEY": "prefixed_value",
            "TEST_KEY": "non_prefixed_value"
        }):
            result = get_env_with_prefix("TEST_KEY")
            assert result == "prefixed_value"

    def test_fallback_to_non_prefixed_when_prefixed_missing(self):
        """Test fallback to non-prefixed when prefixed doesn't exist.
        
        This ensures backward compatibility - existing deployments without
        prefixed variables should continue to work.
        """
        with patch.dict(os.environ, {"TEST_KEY": "non_prefixed_value"}, clear=True):
            result = get_env_with_prefix("TEST_KEY")
            assert result == "non_prefixed_value"

    def test_returns_default_when_neither_exists(self):
        """Test that default value is returned when neither prefixed nor non-prefixed exist.
        
        This is a critical edge case - the function must handle missing variables gracefully.
        """
        with patch.dict(os.environ, {}, clear=True):
            result = get_env_with_prefix("NONEXISTENT_KEY", default="default_value")
            assert result == "default_value"