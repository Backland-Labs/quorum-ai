"""Tests for the /proposals/{id}/top-voters endpoint."""

import pytest
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient

from main import app
from services.tally_service import TallyService
from services.ai_service import AIService
from models import ProposalVoter, VoteType, Proposal, ProposalState


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    # Initialize global services for testing
    import main

    main.tally_service = Mock(spec=TallyService)
    main.ai_service = Mock(spec=AIService)
    return TestClient(app)


@pytest.fixture
def sample_voters():
    """Create sample voter data for testing."""
    return [
        ProposalVoter(
            address="0x1234567890abcdef1234567890abcdef12345678",
            amount="1000000000000000000000",
            vote_type=VoteType.FOR,
        ),
        ProposalVoter(
            address="0xabcdef1234567890abcdef1234567890abcdef12",
            amount="500000000000000000000",
            vote_type=VoteType.AGAINST,
        ),
        ProposalVoter(
            address="0x9876543210fedcba9876543210fedcba98765432",
            amount="250000000000000000000",
            vote_type=VoteType.ABSTAIN,
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

    def test_response_model_validation(self, client: TestClient, sample_voters):
        """Test that the endpoint returns data in the correct format."""
        # Arrange
        proposal_id = "test-proposal-123"
        import main

        main.tally_service.get_proposal_votes = AsyncMock(return_value=sample_voters)

        # Act
        response = client.get(f"/proposals/{proposal_id}/top-voters")

        # Assert
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
        assert first_voter["address"] == sample_voters[0].address
        assert first_voter["amount"] == sample_voters[0].amount
        assert first_voter["vote_type"] == sample_voters[0].vote_type.value

    def test_limit_parameter_default(self, client: TestClient, sample_voters):
        """Test that the limit parameter defaults to 10."""
        # Arrange
        proposal_id = "test-proposal-123"
        import main

        main.tally_service.get_proposal_votes = AsyncMock(return_value=sample_voters)

        # Act
        response = client.get(f"/proposals/{proposal_id}/top-voters")

        # Assert
        assert response.status_code == 200
        # Verify the service was called with default limit
        main.tally_service.get_proposal_votes.assert_called_once_with(proposal_id, 10)

    def test_limit_parameter_custom(self, client: TestClient, sample_voters):
        """Test that custom limit parameter is passed correctly."""
        # Arrange
        proposal_id = "test-proposal-123"
        custom_limit = 25
        import main

        main.tally_service.get_proposal_votes = AsyncMock(return_value=sample_voters)

        # Act
        response = client.get(
            f"/proposals/{proposal_id}/top-voters?limit={custom_limit}"
        )

        # Assert
        assert response.status_code == 200
        # Verify the service was called with custom limit
        main.tally_service.get_proposal_votes.assert_called_once_with(
            proposal_id, custom_limit
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

        # Mock get_proposal_by_id to return None (not found)
        main.tally_service.get_proposal_by_id = AsyncMock(return_value=None)
        main.tally_service.get_proposal_votes = AsyncMock(return_value=[])

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
        main.tally_service.get_proposal_votes = AsyncMock(
            side_effect=Exception("Service unavailable")
        )

        # Act
        response = client.get(f"/proposals/{proposal_id}/top-voters")

        # Assert
        assert response.status_code == 500
        assert "Failed to fetch proposal top voters" in response.json()["detail"]
