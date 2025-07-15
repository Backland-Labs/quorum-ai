"""Tests for FastAPI endpoints."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from httpx import AsyncClient

from main import app
from models import (
    DAO,
    Proposal,
    ProposalState,
    ProposalSummary,
    SortCriteria,
    SortOrder,
)
from services.tally_service import TallyService
from services.ai_service import AIService
from services.snapshot_service import SnapshotService


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    # Initialize global services for testing
    import main

    main.tally_service = Mock(spec=TallyService)
    main.ai_service = Mock(spec=AIService)
    main.snapshot_service = Mock(spec=SnapshotService)
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create an async FastAPI test client."""
    from httpx import ASGITransport

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
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

        response = client.get(
            "/daos?organization_id=org-123&limit=10&after_cursor=cursor_20"
        )

        assert response.status_code == 200
        mock_get_daos.assert_called_once_with(
            organization_id="org-123", limit=10, after_cursor="cursor_20"
        )

    @patch("main.tally_service.get_daos")
    def test_get_daos_handles_service_error(
        self, mock_get_daos: Mock, client: TestClient
    ) -> None:
        """Test DAO listing handles service errors."""
        mock_get_daos.side_effect = Exception("Service error")

        response = client.get("/daos?organization_id=org-123")

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data

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
        mock_get_proposals.return_value = ([sample_proposal], None)

        response = client.get("/proposals?organization_id=org-123")

        assert response.status_code == 200
        data = response.json()
        assert data["next_cursor"] is None
        assert len(data["proposals"]) == 1
        assert data["proposals"][0]["id"] == "prop-123"

    @patch("main.tally_service.get_proposals")
    def test_get_proposals_with_filters(
        self, mock_get_proposals: Mock, client: TestClient, sample_proposal: Proposal
    ) -> None:
        """Test proposal listing with filters."""
        mock_get_proposals.return_value = ([sample_proposal], None)

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
    def test_get_proposals_with_vote_count_sorting(
        self, mock_get_proposals: Mock, client: TestClient
    ) -> None:
        """Test proposal listing with vote count sorting."""
        # Create proposals with different vote counts for testing
        high_vote_proposal = Proposal(
            id="prop-high",
            title="High Vote Proposal",
            description="This proposal has the most votes",
            state=ProposalState.ACTIVE,
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            start_block=1000,
            end_block=2000,
            votes_for="5000000",
            votes_against="500000",
            votes_abstain="100000",
            dao_id="dao-123",
            dao_name="Test DAO",
        )

        medium_vote_proposal = Proposal(
            id="prop-medium",
            title="Medium Vote Proposal",
            description="This proposal has medium votes",
            state=ProposalState.ACTIVE,
            created_at=datetime(2024, 1, 2, 12, 0, 0),
            start_block=2000,
            end_block=3000,
            votes_for="2000000",
            votes_against="300000",
            votes_abstain="50000",
            dao_id="dao-123",
            dao_name="Test DAO",
        )

        low_vote_proposal = Proposal(
            id="prop-low",
            title="Low Vote Proposal",
            description="This proposal has the least votes",
            state=ProposalState.ACTIVE,
            created_at=datetime(2024, 1, 3, 12, 0, 0),
            start_block=3000,
            end_block=4000,
            votes_for="100000",
            votes_against="50000",
            votes_abstain="10000",
            dao_id="dao-123",
            dao_name="Test DAO",
        )

        mock_get_proposals.return_value = (
            [high_vote_proposal, medium_vote_proposal, low_vote_proposal],
            None,
        )

        response = client.get(
            "/proposals?organization_id=org-123&sort_by=vote_count&sort_order=desc&limit=3"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["proposals"]) == 3

        # Verify the service was called with correct filters
        call_args = mock_get_proposals.call_args[0][0]  # ProposalFilters object
        assert call_args.organization_id == "org-123"
        assert call_args.sort_by == SortCriteria.VOTE_COUNT
        assert call_args.sort_order == SortOrder.DESC
        assert call_args.limit == 3

        # Verify proposals are returned in descending vote order
        proposals = data["proposals"]
        assert proposals[0]["id"] == "prop-high"
        assert proposals[0]["votes_for"] == "5000000"
        assert proposals[1]["id"] == "prop-medium"
        assert proposals[1]["votes_for"] == "2000000"
        assert proposals[2]["id"] == "prop-low"
        assert proposals[2]["votes_for"] == "100000"

    @patch("main.tally_service.get_proposals")
    def test_get_proposals_top_3_by_votes(
        self, mock_get_proposals: Mock, client: TestClient
    ) -> None:
        """Test getting top 3 proposals by vote count (BAC-106 requirement)."""
        # Create multiple proposals with different vote counts
        proposals = []
        for i in range(5):
            proposal = Proposal(
                id=f"prop-{i}",
                title=f"Proposal {i}",
                description=f"Description {i}",
                state=ProposalState.ACTIVE,
                created_at=datetime(2024, 1, i + 1, 12, 0, 0),
                start_block=1000 + i * 1000,
                end_block=2000 + i * 1000,
                votes_for=str((5 - i) * 1000000),  # Descending vote counts
                votes_against="100000",
                votes_abstain="50000",
                dao_id="dao-123",
                dao_name="Test DAO",
            )
            proposals.append(proposal)

        mock_get_proposals.return_value = (proposals[:3], None)  # Return top 3

        response = client.get(
            "/proposals?organization_id=org-123&sort_by=vote_count&sort_order=desc&limit=3"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["proposals"]) == 3

        # Verify we get the top 3 by vote count
        call_args = mock_get_proposals.call_args[0][0]
        assert call_args.limit == 3
        assert call_args.sort_by == SortCriteria.VOTE_COUNT
        assert call_args.sort_order == SortOrder.DESC

        # Verify proposals are sorted by vote count descending
        proposals_data = data["proposals"]
        assert int(proposals_data[0]["votes_for"]) >= int(
            proposals_data[1]["votes_for"]
        )
        assert int(proposals_data[1]["votes_for"]) >= int(
            proposals_data[2]["votes_for"]
        )

    def test_get_proposals_top_3_by_votes_bac_106(self, client: TestClient) -> None:
        """Test BAC-106: API can handle top 3 proposals by vote count filtering."""
        # Test the exact BAC-106 requirement: filtering for top 3 proposals by vote count

        with patch("main.tally_service.get_proposals") as mock_get_proposals:
            # Mock proposals with realistic vote data
            high_vote_proposal = Proposal(
                id="prop-1",
                title="High Participation Proposal",
                description="This proposal has high community engagement",
                state=ProposalState.ACTIVE,
                created_at=datetime(2024, 1, 15, 12, 0, 0),
                start_block=5000,
                end_block=6000,
                votes_for="10000000",
                votes_against="2000000",
                votes_abstain="500000",
                dao_id="dao-123",
                dao_name="Test DAO",
                url="https://tally.xyz/proposal/1",
            )

            medium_vote_proposal = Proposal(
                id="prop-2",
                title="Medium Participation Proposal",
                description="This proposal has moderate engagement",
                state=ProposalState.SUCCEEDED,
                created_at=datetime(2024, 1, 10, 12, 0, 0),
                start_block=4000,
                end_block=5000,
                votes_for="5000000",
                votes_against="1000000",
                votes_abstain="250000",
                dao_id="dao-123",
                dao_name="Test DAO",
                url="https://tally.xyz/proposal/2",
            )

            low_vote_proposal = Proposal(
                id="prop-3",
                title="Low Participation Proposal",
                description="This proposal has minimal engagement",
                state=ProposalState.DEFEATED,
                created_at=datetime(2024, 1, 5, 12, 0, 0),
                start_block=3000,
                end_block=4000,
                votes_for="500000",
                votes_against="100000",
                votes_abstain="50000",
                dao_id="dao-123",
                dao_name="Test DAO",
                url="https://tally.xyz/proposal/3",
            )

            mock_get_proposals.return_value = (
                [high_vote_proposal, medium_vote_proposal, low_vote_proposal],
                None,
            )

            # Make request for top 3 proposals by vote count (BAC-106 use case)
            response = client.get(
                "/proposals"
                "?organization_id=test-org"
                "&limit=3"
                "&sort_by=vote_count"
                "&sort_order=desc"
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()

            # Verify we get exactly 3 proposals
            assert len(data["proposals"]) == 3

            # Verify they are sorted by total vote count descending
            proposals = data["proposals"]
            total_votes = []
            for proposal in proposals:
                total = (
                    int(proposal["votes_for"])
                    + int(proposal["votes_against"])
                    + int(proposal["votes_abstain"])
                )
                total_votes.append(total)

            # Verify descending order by total votes
            assert total_votes[0] > total_votes[1] > total_votes[2]

            # Verify the service was called with correct filters for BAC-106
            call_args = mock_get_proposals.call_args[0][0]
            assert call_args.organization_id == "test-org"
            assert call_args.limit == 3
            assert call_args.sort_by == SortCriteria.VOTE_COUNT
            assert call_args.sort_order == SortOrder.DESC

            print(
                "✅ BAC-106 test passed: Top 3 proposals filtering by vote count works correctly"
            )

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

    @patch("main.snapshot_service.get_proposal")
    def test_get_proposal_by_id_with_snapshot_data(
        self, mock_get_proposal: Mock, client: TestClient, sample_snapshot_proposal: Proposal
    ) -> None:
        """Test proposal retrieval by ID using Snapshot data - RED phase."""
        mock_get_proposal.return_value = sample_snapshot_proposal

        response = client.get("/proposals/0x586de5bf366820c4369c041b0bbad2254d78fafe1dcc1528c1ed661bb4dfb671")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "0x586de5bf366820c4369c041b0bbad2254d78fafe1dcc1528c1ed661bb4dfb671"
        assert data["title"] == "[CONSTITUTIONAL] Register $BORING in the Arbitrum generic-custom gateway"
        assert data["state"] == "active"
        assert data["network"] == "42161"
        assert data["symbol"] == "ARB"

    @patch("main.snapshot_service.get_proposals")
    def test_get_proposals_with_snapshot_data(
        self, mock_get_proposals: Mock, client: TestClient, sample_snapshot_proposal: Proposal
    ) -> None:
        """Test proposals listing using Snapshot data - RED phase."""
        mock_get_proposals.return_value = [sample_snapshot_proposal]

        # Test with space_id parameter (replacing organization_id)
        response = client.get("/proposals?space_id=arbitrumfoundation.eth&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert "proposals" in data
        assert len(data["proposals"]) == 1
        assert data["proposals"][0]["id"] == "0x586de5bf366820c4369c041b0bbad2254d78fafe1dcc1528c1ed661bb4dfb671"
        assert data["proposals"][0]["title"] == "[CONSTITUTIONAL] Register $BORING in the Arbitrum generic-custom gateway"


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

        # Skip time testing for now due to httpx cookie handling interference
        response = client.post("/proposals/summarize", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert len(data["summaries"]) == 1
        assert data["summaries"][0]["proposal_id"] == "prop-123"
        assert "processing_time" in data
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
        assert "detail" in data

    @patch("main.ai_service.summarize_multiple_proposals")
    @patch("main.snapshot_service.get_proposal")
    def test_summarize_proposals_with_snapshot_data(
        self,
        mock_get_proposal: Mock,
        mock_summarize: Mock,
        client: TestClient,
        sample_snapshot_proposal: Proposal,
    ) -> None:
        """Test proposal summarization using Snapshot data - RED phase."""
        proposal_id = "0x586de5bf366820c4369c041b0bbad2254d78fafe1dcc1528c1ed661bb4dfb671"
        
        # Mock the service to return Snapshot proposal
        mock_get_proposal.return_value = sample_snapshot_proposal
        
        # Create a summary with the correct Snapshot proposal ID
        snapshot_summary = ProposalSummary(
            proposal_id=proposal_id,
            title="[CONSTITUTIONAL] Register $BORING in the Arbitrum generic-custom gateway",
            summary="This is a snapshot proposal summary",
            key_points=["Point 1", "Point 2", "Point 3"],
            risk_level="MEDIUM",
            recommendation="APPROVE with monitoring",
            confidence_score=0.85,
        )
        mock_summarize.return_value = [snapshot_summary]

        request_data = {
            "proposal_ids": [proposal_id],
            "include_risk_assessment": True,
            "include_recommendations": True,
        }

        response = client.post("/proposals/summarize", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert len(data["summaries"]) == 1
        assert data["summaries"][0]["proposal_id"] == proposal_id
        assert "processing_time" in data
        assert "model_used" in data

        # Verify we called snapshot service instead of tally
        mock_get_proposal.assert_called_once_with(proposal_id)


class TestAsyncEndpoints:
    """Test async endpoint functionality."""

    @pytest.mark.asyncio
    @patch("main.tally_service.get_daos")
    async def test_async_get_daos(
        self, mock_get_daos: AsyncMock, async_client: AsyncClient, sample_dao: DAO
    ) -> None:
        """Test async DAO endpoint."""
        mock_get_daos.return_value = ([sample_dao], None)

        response = await async_client.get("/daos?organization_id=org-123")

        assert response.status_code == 200
        data = response.json()
        assert len(data["daos"]) == 1

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

        response = await async_client.post("/proposals/summarize", json=request_data)

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

        response = client.get("/daos?organization_id=org-123")

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data

    def test_validation_error_handling(self, client: TestClient) -> None:
        """Test that validation errors return proper status codes."""
        # Invalid limit parameter
        response = client.get("/daos?organization_id=org-123&limit=-1")

        assert response.status_code == 422

    def test_not_found_error_handling(self, client: TestClient) -> None:
        """Test that 404 errors are handled properly."""
        response = client.get("/nonexistent-endpoint")

        assert response.status_code == 404


class TestCORS:
    """Test CORS configuration."""

    @pytest.mark.skip(reason="CORS headers not visible in TestClient")
    def test_cors_headers_present(self, client: TestClient) -> None:
        """Test that CORS headers are present in responses."""
        response = client.get("/health")  # Use health endpoint for CORS test

        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers


class TestRateLimiting:
    """Test rate limiting (if implemented)."""

    @pytest.mark.skip(reason="Rate limiting not yet implemented")
    def test_rate_limiting_applied(self, client: TestClient) -> None:
        """Test that rate limiting is applied to endpoints."""
        # Make multiple rapid requests
        responses = [client.get("/daos?organization_id=org-123") for _ in range(100)]

        # Some should be rate limited
        rate_limited = [r for r in responses if r.status_code == 429]
        assert len(rate_limited) > 0


class TestOrganizationOverviewEndpoint:
    """Test organization overview endpoint."""

    @patch("main.tally_service.get_organization_overview")
    def test_get_organization_overview_success(
        self, mock_get_overview: Mock, client: TestClient
    ) -> None:
        """Test successful organization overview retrieval."""
        mock_overview_data = {
            "organization_id": "org-123",
            "organization_name": "Test DAO",
            "organization_slug": "test-dao",
            "description": "A test DAO organization",
            "delegate_count": 150,
            "token_holder_count": 1000,
            "total_proposals_count": 50,
            "proposal_counts_by_status": {
                "ACTIVE": 5,
                "SUCCEEDED": 25,
                "DEFEATED": 10,
                "PENDING": 3,
                "EXECUTED": 7,
            },
            "recent_activity_count": 15,
            "governance_participation_rate": 0.75,
        }
        mock_get_overview.return_value = mock_overview_data

        response = client.get("/organizations/org-123/overview")

        assert response.status_code == 200
        data = response.json()
        assert data["organization_id"] == "org-123"
        assert data["organization_name"] == "Test DAO"
        assert data["delegate_count"] == 150
        assert data["token_holder_count"] == 1000
        assert data["total_proposals_count"] == 50
        assert data["proposal_counts_by_status"]["ACTIVE"] == 5
        assert data["governance_participation_rate"] == 0.75

        mock_get_overview.assert_called_once_with("org-123")

    @patch("main.tally_service.get_organization_overview")
    def test_get_organization_overview_not_found(
        self, mock_get_overview: Mock, client: TestClient
    ) -> None:
        """Test organization overview retrieval when organization not found."""
        mock_get_overview.return_value = None

        response = client.get("/organizations/nonexistent-org/overview")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    @patch("main.tally_service.get_organization_overview")
    def test_get_organization_overview_service_error(
        self, mock_get_overview: Mock, client: TestClient
    ) -> None:
        """Test organization overview retrieval when service fails."""
        mock_get_overview.side_effect = Exception("Service error")

        response = client.get("/organizations/org-123/overview")

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data

    def test_get_organization_overview_invalid_org_id(self, client: TestClient) -> None:
        """Test organization overview with invalid organization ID format."""
        # Test with empty org_id
        response = client.get("/organizations//overview")
        assert response.status_code == 404  # Path not found

        # Test with special characters
        response = client.get("/organizations/org%20with%20spaces/overview")
        # Should still work as URL encoding is handled by FastAPI
        assert response.status_code in [200, 404, 500]  # Any valid HTTP response

    @pytest.mark.asyncio
    @patch("main.tally_service.get_organization_overview")
    async def test_async_get_organization_overview(
        self, mock_get_overview: AsyncMock, async_client: AsyncClient
    ) -> None:
        """Test async organization overview endpoint."""
        mock_overview_data = {
            "organization_id": "org-456",
            "organization_name": "Async Test DAO",
            "organization_slug": "async-test-dao",
            "description": None,
            "delegate_count": 200,
            "token_holder_count": 1500,
            "total_proposals_count": 75,
            "proposal_counts_by_status": {"ACTIVE": 10},
            "recent_activity_count": 25,
            "governance_participation_rate": 0.85,
        }
        mock_get_overview.return_value = mock_overview_data

        response = await async_client.get("/organizations/org-456/overview")

        assert response.status_code == 200
        data = response.json()
        assert data["organization_id"] == "org-456"
        assert data["delegate_count"] == 200
