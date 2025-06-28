"""Tests for FastAPI endpoints."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from httpx import AsyncClient

from main import app
from models import DAO, Proposal, ProposalState, ProposalSummary


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create an async FastAPI test client."""
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_dao():
    """Create a sample DAO for testing."""
    return DAO(
        id="dao-123",
        name="Test DAO",
        slug="test-dao",
        organization_id="org-123",
        description="A test DAO for governance",
        active_proposals_count=5,
        total_proposals_count=25,
    )


@pytest.fixture
def sample_proposal():
    """Create a sample proposal for testing."""
    return Proposal(
        id="prop-123",
        title="Test Proposal",
        description="A test proposal description",
        state=ProposalState.ACTIVE,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        start_block=1000,
        end_block=2000,
        votes_for="1000000",
        votes_against="250000",
        votes_abstain="50000",
        dao_id="dao-123",
        dao_name="Test DAO",
        url="https://tally.xyz/proposal/123",
    )


@pytest.fixture
def sample_proposal_summary():
    """Create a sample proposal summary for testing."""
    return ProposalSummary(
        proposal_id="prop-123",
        title="Test Proposal",
        summary="This is a test proposal summary",
        key_points=["Point 1", "Point 2", "Point 3"],
        risk_level="MEDIUM",
        recommendation="APPROVE with monitoring",
        confidence_score=0.85,
    )


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check_returns_ok(self, client: TestClient) -> None:
        """Test that health check endpoint returns OK status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_health_check_includes_version(self, client: TestClient) -> None:
        """Test that health check includes version information."""
        response = client.get("/health")

        data = response.json()
        assert "version" in data


class TestDAOEndpoints:
    """Test DAO-related endpoints."""

    @patch("main.tally_service.get_daos")
    def test_get_daos_success(
        self, mock_get_daos: Mock, client: TestClient, sample_dao: DAO
    ) -> None:
        """Test successful DAO listing."""
        mock_get_daos.return_value = ([sample_dao], None)

        response = client.get("/daos?organization_id=org-123")

        assert response.status_code == 200
        data = response.json()
        assert len(data["daos"]) == 1
        assert data["daos"][0]["id"] == "dao-123"
        assert data["daos"][0]["name"] == "Test DAO"

    @patch("main.tally_service.get_daos")
    def test_get_daos_with_pagination(
        self, mock_get_daos: Mock, client: TestClient, sample_dao: DAO
    ) -> None:
        """Test DAO listing with pagination parameters."""
        mock_get_daos.return_value = ([sample_dao], "cursor_123")

        response = client.get("/daos?organization_id=org-123&limit=10&after_cursor=cursor_20")

        assert response.status_code == 200
        mock_get_daos.assert_called_once_with(organization_id="org-123", limit=10, after_cursor="cursor_20")

    @patch("main.tally_service.get_daos")
    def test_get_daos_handles_service_error(
        self, mock_get_daos: Mock, client: TestClient
    ) -> None:
        """Test DAO listing handles service errors."""
        mock_get_daos.side_effect = Exception("Service error")

        response = client.get("/daos")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data

    @patch("main.tally_service.get_dao_by_id")
    def test_get_dao_by_id_success(
        self, mock_get_dao: Mock, client: TestClient, sample_dao: DAO
    ) -> None:
        """Test successful DAO retrieval by ID."""
        mock_get_dao.return_value = sample_dao

        response = client.get("/daos/dao-123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "dao-123"
        assert data["name"] == "Test DAO"

    @patch("main.tally_service.get_dao_by_id")
    def test_get_dao_by_id_not_found(
        self, mock_get_dao: Mock, client: TestClient
    ) -> None:
        """Test DAO retrieval when DAO not found."""
        mock_get_dao.return_value = None

        response = client.get("/daos/nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()


class TestProposalEndpoints:
    """Test proposal-related endpoints."""

    @patch("main.tally_service.get_proposals")
    def test_get_proposals_success(
        self, mock_get_proposals: Mock, client: TestClient, sample_proposal: Proposal
    ) -> None:
        """Test successful proposal listing."""
        mock_get_proposals.return_value = ([sample_proposal], 1)

        response = client.get("/proposals")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert len(data["proposals"]) == 1
        assert data["proposals"][0]["id"] == "prop-123"

    @patch("main.tally_service.get_proposals")
    def test_get_proposals_with_filters(
        self, mock_get_proposals: Mock, client: TestClient, sample_proposal: Proposal
    ) -> None:
        """Test proposal listing with filters."""
        mock_get_proposals.return_value = ([sample_proposal], 1)

        response = client.get(
            "/proposals?dao_id=dao-123&state=ACTIVE&limit=10&sort_by=created_date&sort_order=desc"
        )

        assert response.status_code == 200

        # Verify the service was called with correct filters
        call_args = mock_get_proposals.call_args[0][0]  # ProposalFilters object
        assert call_args.dao_id == "dao-123"
        assert call_args.state == ProposalState.ACTIVE
        assert call_args.limit == 10

    @patch("main.tally_service.get_proposals")
    def test_get_proposals_invalid_state_filter(
        self, mock_get_proposals: Mock, client: TestClient
    ) -> None:
        """Test proposal listing with invalid state filter."""
        response = client.get("/proposals?state=INVALID_STATE")

        assert response.status_code == 422  # Validation error

    @patch("main.tally_service.get_proposal_by_id")
    def test_get_proposal_by_id_success(
        self, mock_get_proposal: Mock, client: TestClient, sample_proposal: Proposal
    ) -> None:
        """Test successful proposal retrieval by ID."""
        mock_get_proposal.return_value = sample_proposal

        response = client.get("/proposals/prop-123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "prop-123"
        assert data["title"] == "Test Proposal"

    @patch("main.tally_service.get_proposal_by_id")
    def test_get_proposal_by_id_not_found(
        self, mock_get_proposal: Mock, client: TestClient
    ) -> None:
        """Test proposal retrieval when proposal not found."""
        mock_get_proposal.return_value = None

        response = client.get("/proposals/nonexistent")

        assert response.status_code == 404


class TestSummarizeEndpoints:
    """Test proposal summarization endpoints."""

    @patch("main.ai_service.summarize_multiple_proposals")
    @patch("main.tally_service.get_multiple_proposals")
    def test_summarize_proposals_success(
        self,
        mock_get_proposals: Mock,
        mock_summarize: Mock,
        client: TestClient,
        sample_proposal: Proposal,
        sample_proposal_summary: ProposalSummary,
    ) -> None:
        """Test successful proposal summarization."""
        mock_get_proposals.return_value = [sample_proposal]
        mock_summarize.return_value = [sample_proposal_summary]

        request_data = {
            "proposal_ids": ["prop-123"],
            "include_risk_assessment": True,
            "include_recommendations": True,
        }

        with patch("time.time", side_effect=[0, 1.5]):  # Mock processing time
            response = client.post("/proposals/summarize", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert len(data["summaries"]) == 1
        assert data["summaries"][0]["proposal_id"] == "prop-123"
        assert data["processing_time"] == 1.5
        assert "model_used" in data

    @patch("main.tally_service.get_multiple_proposals")
    def test_summarize_proposals_no_proposals_found(
        self, mock_get_proposals: Mock, client: TestClient
    ) -> None:
        """Test summarization when no proposals are found."""
        mock_get_proposals.return_value = []

        request_data = {"proposal_ids": ["nonexistent"]}

        response = client.post("/proposals/summarize", json=request_data)

        assert response.status_code == 404
        data = response.json()
        assert "no proposals found" in data["detail"].lower()

    def test_summarize_proposals_invalid_request(self, client: TestClient) -> None:
        """Test summarization with invalid request data."""
        # Empty proposal_ids list
        request_data = {"proposal_ids": []}

        response = client.post("/proposals/summarize", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_summarize_proposals_too_many_ids(self, client: TestClient) -> None:
        """Test summarization with too many proposal IDs."""
        request_data = {
            "proposal_ids": [f"prop-{i}" for i in range(51)]  # Exceeds limit
        }

        response = client.post("/proposals/summarize", json=request_data)

        assert response.status_code == 422  # Validation error

    @patch("main.ai_service.summarize_multiple_proposals")
    @patch("main.tally_service.get_multiple_proposals")
    def test_summarize_proposals_ai_service_error(
        self,
        mock_get_proposals: Mock,
        mock_summarize: Mock,
        client: TestClient,
        sample_proposal: Proposal,
    ) -> None:
        """Test summarization when AI service fails."""
        mock_get_proposals.return_value = [sample_proposal]
        mock_summarize.side_effect = Exception("AI service error")

        request_data = {"proposal_ids": ["prop-123"]}

        response = client.post("/proposals/summarize", json=request_data)

        assert response.status_code == 500
        data = response.json()
        assert "error" in data


class TestAsyncEndpoints:
    """Test async endpoint functionality."""

    @pytest.mark.asyncio
    @patch("main.tally_service.get_daos")
    async def test_async_get_daos(
        self, mock_get_daos: AsyncMock, async_client: AsyncClient, sample_dao: DAO
    ) -> None:
        """Test async DAO endpoint."""
        mock_get_daos.return_value = [sample_dao]

        response = await async_client.get("/daos")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    @pytest.mark.asyncio
    @patch("main.ai_service.summarize_multiple_proposals")
    @patch("main.tally_service.get_multiple_proposals")
    async def test_async_summarize_proposals(
        self,
        mock_get_proposals: AsyncMock,
        mock_summarize: AsyncMock,
        async_client: AsyncClient,
        sample_proposal: Proposal,
        sample_proposal_summary: ProposalSummary,
    ) -> None:
        """Test async proposal summarization."""
        mock_get_proposals.return_value = [sample_proposal]
        mock_summarize.return_value = [sample_proposal_summary]

        request_data = {"proposal_ids": ["prop-123"]}

        with patch("time.time", side_effect=[0, 1.0]):
            response = await async_client.post(
                "/proposals/summarize", json=request_data
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["summaries"]) == 1


class TestErrorHandling:
    """Test error handling across endpoints."""

    @patch("main.tally_service.get_daos")
    def test_internal_server_error_handling(
        self, mock_get_daos: Mock, client: TestClient
    ) -> None:
        """Test that internal server errors are handled properly."""
        mock_get_daos.side_effect = Exception("Database connection failed")

        response = client.get("/daos")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "message" in data

    def test_validation_error_handling(self, client: TestClient) -> None:
        """Test that validation errors return proper status codes."""
        # Invalid limit parameter
        response = client.get("/daos?limit=-1")

        assert response.status_code == 422

    def test_not_found_error_handling(self, client: TestClient) -> None:
        """Test that 404 errors are handled properly."""
        response = client.get("/nonexistent-endpoint")

        assert response.status_code == 404


class TestCORS:
    """Test CORS configuration."""

    def test_cors_headers_present(self, client: TestClient) -> None:
        """Test that CORS headers are present in responses."""
        response = client.options("/daos")

        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers


class TestRateLimiting:
    """Test rate limiting (if implemented)."""

    @pytest.mark.skip(reason="Rate limiting not yet implemented")
    def test_rate_limiting_applied(self, client: TestClient) -> None:
        """Test that rate limiting is applied to endpoints."""
        # Make multiple rapid requests
        responses = [client.get("/daos") for _ in range(100)]

        # Some should be rate limited
        rate_limited = [r for r in responses if r.status_code == 429]
        assert len(rate_limited) > 0
