"""Tests for QuorumTracker configuration settings."""

import os
import pytest
from unittest.mock import patch

from config import Settings


class TestQuorumTrackerConfiguration:
    """Test QuorumTracker configuration settings."""

    def test_quorum_tracker_address_defaults_to_none(self):
        """Test that quorum_tracker_address defaults to None."""
        settings = Settings()
        assert settings.quorum_tracker_address is None

    def test_quorum_tracker_owner_defaults_to_none(self):
        """Test that quorum_tracker_owner defaults to None.""" 
        settings = Settings()
        assert settings.quorum_tracker_owner is None

    def test_quorum_tracker_address_loaded_from_env(self):
        """Test that quorum_tracker_address is loaded from environment variable."""
        test_address = "0x1234567890123456789012345678901234567890"
        with patch.dict(os.environ, {"QUORUM_TRACKER_ADDRESS": test_address}):
            settings = Settings()
            assert settings.quorum_tracker_address == test_address

    def test_quorum_tracker_owner_loaded_from_env(self):
        """Test that quorum_tracker_owner is loaded from environment variable."""
        test_owner = "0x0987654321098765432109876543210987654321"
        with patch.dict(os.environ, {"QUORUM_TRACKER_OWNER": test_owner}):
            settings = Settings()
            assert settings.quorum_tracker_owner == test_owner

    def test_invalid_quorum_tracker_address_raises_error(self):
        """Test that invalid quorum_tracker_address raises ValueError."""
        with patch.dict(os.environ, {"QUORUM_TRACKER_ADDRESS": "invalid_address"}):
            with pytest.raises(ValueError, match="Invalid contract address"):
                Settings()

    def test_invalid_quorum_tracker_owner_raises_error(self):
        """Test that invalid quorum_tracker_owner raises ValueError."""
        with patch.dict(os.environ, {"QUORUM_TRACKER_OWNER": "not_an_address"}):
            with pytest.raises(ValueError, match="Invalid contract address"):
                Settings()