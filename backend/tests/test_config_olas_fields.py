"""Tests for new Olas-specific configuration fields."""

import os
import pytest
from unittest.mock import patch
from pydantic import ValidationError

from config import Settings


class TestOlasConfigFields:
    """Test new Olas-specific configuration fields with prefix support."""

    def test_voting_strategy_validation_accepts_valid_values(self):
        """Test that voting_strategy field accepts valid enum values.
        
        This is CORE business logic - the voting strategy must be validated
        to prevent invalid configurations that could cause voting failures.
        """
        with patch.dict(os.environ, {"VOTING_STRATEGY": "balanced"}, clear=True):
            settings = Settings()
            assert settings.voting_strategy == "balanced"
        
        with patch.dict(os.environ, {"VOTING_STRATEGY": "conservative"}, clear=True):
            settings = Settings()
            assert settings.voting_strategy == "conservative"
            
        with patch.dict(os.environ, {"VOTING_STRATEGY": "aggressive"}, clear=True):
            settings = Settings()
            assert settings.voting_strategy == "aggressive"

    def test_voting_strategy_validation_rejects_invalid_values(self):
        """Test that voting_strategy field rejects invalid values.
        
        This is a critical edge case - invalid voting strategies could cause
        the autonomous voting system to fail in unpredictable ways.
        """
        with patch.dict(os.environ, {"VOTING_STRATEGY": "invalid_strategy"}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "Invalid voting strategy" in str(exc_info.value)

    def test_new_fields_load_from_prefixed_environment_variables(self):
        """Test that new Olas fields load from prefixed environment variables.
        
        This tests the integration between the new fields and the prefix system,
        which is critical for Pearl deployment compatibility.
        """
        with patch.dict(os.environ, {
            "CONNECTION_CONFIGS_CONFIG_SNAPSHOT_API_KEY": "prefixed_api_key",
            "CONNECTION_CONFIGS_CONFIG_VOTING_STRATEGY": "conservative",
            "CONNECTION_CONFIGS_CONFIG_DAO_ADDRESSES": "0x123,0x456"
        }, clear=True):
            settings = Settings()
            assert settings.snapshot_api_key == "prefixed_api_key"
            assert settings.voting_strategy == "conservative"
            assert settings.dao_addresses == ["0x123", "0x456"]