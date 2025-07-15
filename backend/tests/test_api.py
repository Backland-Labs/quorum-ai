"""Tests for FastAPI endpoints."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from httpx import AsyncClient

from main import app
from models import (
    Proposal,
    ProposalState,
    ProposalSummary,
)
from services.ai_service import AIService
from services.snapshot_service import SnapshotService


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    # Initialize global services for testing
    import main

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


class TestProposalEndpoints:
    """Test proposal-related endpoints."""

    @patch("main.snapshot_service.get_proposal")
    def test_get_proposal_by_id_with_snapshot_data(
        self, mock_get_proposal: Mock, client: TestClient, sample_snapshot_proposal: Proposal
    ) -> None:
        """Test proposal retrieval by ID using Snapshot data."""
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
        """Test proposals listing using Snapshot data."""
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
    @patch("main.snapshot_service.get_proposal")
    def test_summarize_proposals_with_snapshot_data(
        self,
        mock_get_proposal: Mock,
        mock_summarize: Mock,
        client: TestClient,
        sample_snapshot_proposal: Proposal,
    ) -> None:
        """Test proposal summarization using Snapshot data."""
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

        # Verify we called snapshot service
        mock_get_proposal.assert_called_once_with(proposal_id)

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


class TestErrorHandling:
    """Test error handling across endpoints."""

    def test_validation_error_handling(self, client: TestClient) -> None:
        """Test that validation errors return proper status codes."""
        # Invalid limit parameter
        response = client.get("/proposals?space_id=test&limit=-1")

        assert response.status_code == 422

    def test_not_found_error_handling(self, client: TestClient) -> None:
        """Test that 404 errors are handled properly."""
        response = client.get("/nonexistent-endpoint")

        assert response.status_code == 404