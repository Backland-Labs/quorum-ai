"""Tests for the /proposals/{id}/top-voters endpoint."""

import pytest
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient

from main import app
from services.ai_service import AIService
from services.snapshot_service import SnapshotService
from models import ProposalVoter, VoteType, Proposal, ProposalState, Vote


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    # Initialize global services for testing
    import main

    main.ai_service = Mock(spec=AIService)
    main.snapshot_service = Mock(spec=SnapshotService)
    return TestClient(app)


@pytest.fixture
def sample_voters():
    """Create sample voter data for testing."""
    return [
        Vote(
            id="vote1",
            voter="0x1234567890abcdef1234567890abcdef12345678",
            choice=1,  # 1=For
            vp=1000.0,
            vp_by_strategy=[1000.0],
            created=1698681600,
        ),
        Vote(
            id="vote2",
            voter="0xabcdef1234567890abcdef1234567890abcdef12",
            choice=2,  # 2=Against
            vp=500.0,
            vp_by_strategy=[500.0],
            created=1698681700,
        ),
        Vote(
            id="vote3",
            voter="0x9876543210fedcba9876543210fedcba98765432",
            choice=3,  # 3=Abstain
            vp=250.0,
            vp_by_strategy=[250.0],
            created=1698681800,
        ),
    ]


class TestProposalTopVotersEndpoint:
    """Test suite for the proposal top voters endpoint."""

    def test_endpoint_exists(self, client: TestClient):
        """Test that the endpoint exists and returns a response."""
        # Arrange - endpoint path
        endpoint_path = "/proposals/test-proposal-id/top-voters"

        # Act - make request
        response = client.get(endpoint_path)

        # Assert - endpoint should exist (not 404 for missing route)
        # We expect 500 since we haven't mocked the service yet
        assert response.status_code != 404

    def test_response_model_validation(self, client: TestClient, sample_voters, sample_proposal):
        """Test that the endpoint returns data in the correct format."""
        # Arrange
        proposal_id = "test-proposal-123"
        import main

        main.snapshot_service.get_votes = AsyncMock(return_value=sample_voters)
        main.snapshot_service.get_proposal = AsyncMock(return_value=sample_proposal)

        # Act
        response = client.get(f"/proposals/{proposal_id}/top-voters")

        # Assert
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.content}")
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "proposal_id" in data
        assert "voters" in data
        assert data["proposal_id"] == proposal_id
        assert isinstance(data["voters"], list)
        assert len(data["voters"]) == 3

        # Verify voter structure
        first_voter = data["voters"][0]
        assert "address" in first_voter
        assert "amount" in first_voter
        assert "vote_type" in first_voter
        assert first_voter["address"] == sample_voters[0].voter
        assert first_voter["vote_type"] == VoteType.FOR.value  # choice=1 maps to FOR

    def test_limit_parameter_default(self, client: TestClient, sample_voters, sample_proposal):
        """Test that the limit parameter defaults to 10."""
        # Arrange
        proposal_id = "test-proposal-123"
        import main

        main.snapshot_service.get_votes = AsyncMock(return_value=sample_voters)
        main.snapshot_service.get_proposal = AsyncMock(return_value=sample_proposal)

        # Act
        response = client.get(f"/proposals/{proposal_id}/top-voters")

        # Assert
        assert response.status_code == 200
        # Verify the service was called with default limit
        main.snapshot_service.get_votes.assert_called_once_with(proposal_id, first=10)

    def test_limit_parameter_custom(self, client: TestClient, sample_voters, sample_proposal):
        """Test that custom limit parameter is passed correctly."""
        # Arrange
        proposal_id = "test-proposal-123"
        custom_limit = 25
        import main

        main.snapshot_service.get_votes = AsyncMock(return_value=sample_voters)
        main.snapshot_service.get_proposal = AsyncMock(return_value=sample_proposal)

        # Act
        response = client.get(
            f"/proposals/{proposal_id}/top-voters?limit={custom_limit}"
        )

        # Assert
        assert response.status_code == 200
        # Verify the service was called with custom limit
        main.snapshot_service.get_votes.assert_called_once_with(
            proposal_id, first=custom_limit
        )

    def test_limit_parameter_validation_too_low(self, client: TestClient):
        """Test that limit below 1 returns validation error."""
        # Arrange
        proposal_id = "test-proposal-123"

        # Act
        response = client.get(f"/proposals/{proposal_id}/top-voters?limit=0")

        # Assert
        assert response.status_code == 422
        error_detail = response.json()["detail"][0]
        assert error_detail["type"] == "greater_than_equal"
        assert error_detail["loc"] == ["query", "limit"]

    def test_limit_parameter_validation_too_high(self, client: TestClient):
        """Test that limit above 50 returns validation error."""
        # Arrange
        proposal_id = "test-proposal-123"

        # Act
        response = client.get(f"/proposals/{proposal_id}/top-voters?limit=51")

        # Assert
        assert response.status_code == 422
        error_detail = response.json()["detail"][0]
        assert error_detail["type"] == "less_than_equal"
        assert error_detail["loc"] == ["query", "limit"]

    def test_404_when_proposal_not_found(self, client: TestClient):
        """Test that 404 is returned when proposal doesn't exist."""
        # Arrange
        proposal_id = "non-existent-proposal"
        import main

        # Mock get_proposal to return None (not found)
        main.snapshot_service.get_proposal = AsyncMock(return_value=None)
        main.snapshot_service.get_votes = AsyncMock(return_value=[])

        # Act
        response = client.get(f"/proposals/{proposal_id}/top-voters")

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_500_on_service_error(self, client: TestClient):
        """Test that 500 is returned on service errors."""
        # Arrange
        proposal_id = "error-proposal"
        import main

        # Mock the service to raise an exception
        main.snapshot_service.get_votes = AsyncMock(
            side_effect=Exception("Service unavailable")
        )

        # Act
        response = client.get(f"/proposals/{proposal_id}/top-voters")

        # Assert
        assert response.status_code == 500
        assert "Failed to fetch proposal top voters" in response.json()["detail"]

    def test_top_voters_with_snapshot_data(self, client: TestClient, sample_snapshot_votes):
        """Test top voters endpoint using Snapshot data - RED phase."""
        # Arrange
        proposal_id = "0x586de5bf366820c4369c041b0bbad2254d78fafe1dcc1528c1ed661bb4dfb671"
        import main

        # Mock snapshot_service.get_votes to return Snapshot votes
        main.snapshot_service.get_votes = AsyncMock(return_value=sample_snapshot_votes)
        # Mock the proposal exists check
        main.snapshot_service.get_proposal = AsyncMock(return_value=Mock(state="active"))

        # Act
        response = client.get(f"/proposals/{proposal_id}/top-voters")

        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert data["proposal_id"] == proposal_id
        assert "voters" in data
        assert len(data["voters"]) == 2
        
        # Verify first voter (highest voting power)
        first_voter = data["voters"][0]
        assert first_voter["address"] == "0xB933AEe47C438f22DE0747D57fc239FE37878Dd1"
        assert first_voter["amount"].startswith("13301332647183")  # Check prefix due to floating point precision
        assert first_voter["vote_type"] == "FOR"  # choice=1 maps to FOR
