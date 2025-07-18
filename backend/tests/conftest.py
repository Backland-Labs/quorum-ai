"""Pytest configuration and fixtures for the test suite."""

import pytest
from datetime import datetime
from unittest.mock import patch


@pytest.fixture
def mock_web3():
    """Create a mock Web3 instance for testing."""
    from unittest.mock import MagicMock
    return MagicMock()


@pytest.fixture
def mock_safe_instance():
    """Create a mock Safe instance for testing."""
    from unittest.mock import MagicMock
    return MagicMock()
