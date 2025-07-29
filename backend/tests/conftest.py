"""Pytest configuration and fixtures for the test suite."""

import os
import sys
from pathlib import Path

# Add backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from datetime import datetime
from unittest.mock import patch
from httpx import AsyncClient

# Set test environment variables before imports
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")


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


@pytest.fixture
async def async_client():
    """Create an async FastAPI test client."""
    from httpx import ASGITransport
    from unittest.mock import Mock, AsyncMock
    from main import app
    import main
    from services.agent_run_service import AgentRunService
    from services.snapshot_service import SnapshotService
    
    # Initialize global services for testing
    if not hasattr(main, 'agent_run_service') or main.agent_run_service is None:
        main.agent_run_service = Mock(spec=AgentRunService)
    if not hasattr(main, 'snapshot_service') or main.snapshot_service is None:
        main.snapshot_service = Mock(spec=SnapshotService)
    
    # Ensure get_recent_decisions is an async mock
    main.agent_run_service.get_recent_decisions = AsyncMock()
    # Ensure get_proposal is an async mock  
    main.snapshot_service.get_proposal = AsyncMock()
    
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
