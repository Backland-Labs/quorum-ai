"""Pytest configuration and fixtures for the test suite."""

import os
import sys
from pathlib import Path

# Add backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
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
    if not hasattr(main, "agent_run_service") or main.agent_run_service is None:
        main.agent_run_service = Mock(spec=AgentRunService)
    if not hasattr(main, "snapshot_service") or main.snapshot_service is None:
        main.snapshot_service = Mock(spec=SnapshotService)

    # Ensure get_recent_decisions is an async mock
    main.agent_run_service.get_recent_decisions = AsyncMock()
    # Ensure get_proposal is an async mock
    main.snapshot_service.get_proposal = AsyncMock()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def ai_service():
    """Create an AIService instance for testing."""
    from services.ai_service import AIService

    return AIService()


@pytest.fixture
def sample_proposal():
    """Create a sample proposal for testing."""
    from models import Proposal, ProposalState
    import time

    current_time = int(time.time())
    return Proposal(
        id="prop-123",
        title="Sample Proposal",
        body="This is a test proposal",
        start=current_time - 3600,  # Started 1 hour ago
        end=current_time + 3600,  # Ends in 1 hour
        state=ProposalState.ACTIVE,
        choices=["For", "Against", "Abstain"],
        votes=100,
        author="0x1234567890123456789012345678901234567890",
        created=current_time - 7200,  # Created 2 hours ago
        scores_total=100.0,
        scores=[60.0, 30.0, 10.0],
    )


@pytest.fixture
def complex_proposal():
    """Create a complex proposal for testing."""
    from models import Proposal, ProposalState
    import time

    current_time = int(time.time())
    return Proposal(
        id="prop-456",
        title="Complex Proposal",
        body="This is a more complex test proposal with multiple aspects",
        start=current_time - 3600,
        end=current_time + 3600,
        state=ProposalState.ACTIVE,
        choices=["For", "Against", "Abstain"],
        votes=500,
        author="0x4567890123456789012345678901234567890123",
        created=current_time - 7200,
        scores_total=500.0,
        scores=[300.0, 150.0, 50.0],
    )
