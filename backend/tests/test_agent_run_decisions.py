"""
Tests for GET /agent-run/decisions endpoint

This test module verifies that the agent decisions endpoint correctly:
1. Returns recent voting decisions from checkpoint files
2. Enriches decisions with proposal titles
3. Handles pagination via limit parameter
4. Gracefully handles empty decision history
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from backend.models import VoteDecision
import main


@pytest.mark.asyncio
@patch("main.snapshot_service.get_proposal")
@patch("main.agent_run_service.get_recent_decisions")
async def test_get_decisions_returns_correct_structure(
    mock_get_decisions: AsyncMock,
    mock_get_proposal: AsyncMock,
    async_client: AsyncClient
):
    """
    Test that the endpoint returns decisions with the expected structure.
    
    Why this test matters:
    - Ensures the API contract is maintained for frontend consumption
    - Verifies that all required fields are present in the response
    - Validates that proposal titles are properly enriched
    """
    # Arrange
    decision_data = {
        "proposal_id": "0x123",
        "vote": "FOR",
        "confidence": 0.9,
        "reasoning": "Strong alignment with our community priorities and values",
        "strategy_used": "balanced",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    mock_decision = VoteDecision(**{k: v for k, v in decision_data.items() if k != "timestamp"})
    
    mock_get_decisions.return_value = [(mock_decision, decision_data["timestamp"])]
    mock_get_proposal.return_value = {"title": "Test Proposal Title"}
    
    # Act
    response = await async_client.get("/agent-run/decisions")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "decisions" in data
    assert len(data["decisions"]) == 1
    
    decision = data["decisions"][0]
    assert decision["proposal_id"] == "0x123"
    assert decision["vote"] == "FOR"
    assert decision["confidence"] == 0.9
    assert decision["reasoning"] == "Strong alignment with our community priorities and values"
    assert decision["proposal_title"] == "Test Proposal Title"
    assert "timestamp" in decision


@pytest.mark.asyncio
@patch("main.snapshot_service.get_proposal")
@patch("main.agent_run_service.get_recent_decisions")
async def test_get_decisions_respects_limit_parameter(
    mock_get_decisions: AsyncMock,
    mock_get_proposal: AsyncMock,
    async_client: AsyncClient
):
    """
    Test that the limit query parameter correctly limits returned results.
    
    Why this test matters:
    - Ensures pagination works for frontend performance
    - Validates that the API respects client preferences
    - Prevents overwhelming the frontend with too much data
    """
    # Arrange
    mock_decisions = [
        (VoteDecision(
            proposal_id=f"0x{i}",
            vote="FOR" if i % 2 == 0 else "AGAINST",
            confidence=0.8 + (i * 0.01),
            reasoning=f"This is a detailed reasoning for proposal {i} that meets minimum length",
            strategy_used="balanced"
        ), datetime.now(timezone.utc).isoformat())
        for i in range(10)
    ]
    
    mock_get_decisions.return_value = mock_decisions[:3]  # Should return only 3
    mock_get_proposal.return_value = {"title": "Test Proposal"}
    
    # Act
    response = await async_client.get("/agent-run/decisions?limit=3")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data["decisions"]) == 3
    mock_get_decisions.assert_called_once_with(limit=3)


@pytest.mark.asyncio
@patch("main.snapshot_service.get_proposal")
@patch("main.agent_run_service.get_recent_decisions")
async def test_get_decisions_enriches_with_proposal_title(
    mock_get_decisions: AsyncMock,
    mock_get_proposal: AsyncMock,
    async_client: AsyncClient
):
    """
    Test that each decision is enriched with the proposal title from Snapshot.
    
    Why this test matters:
    - Verifies integration with SnapshotService
    - Ensures users see meaningful proposal names, not just IDs
    - Tests error handling when proposal lookup fails
    """
    # Arrange
    mock_decisions = [
        (VoteDecision(
            proposal_id="0x123",
            vote="FOR",
            confidence=0.9,
            reasoning="This proposal aligns well with our community values and goals",
            strategy_used="balanced"
        ), datetime.now(timezone.utc).isoformat()),
        (VoteDecision(
            proposal_id="0x456",
            vote="AGAINST",
            confidence=0.7,
            reasoning="This proposal does not align with our strategic priorities",
            strategy_used="balanced"
        ), datetime.now(timezone.utc).isoformat())
    ]
    
    mock_get_decisions.return_value = mock_decisions
    
    # First proposal found, second not found
    mock_get_proposal.side_effect = [
        {"title": "Proposal One"},
        None  # Proposal not found
    ]
    
    # Act
    response = await async_client.get("/agent-run/decisions")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["decisions"][0]["proposal_title"] == "Proposal One"
    assert data["decisions"][1]["proposal_title"] == "Unknown Proposal"  # Fallback


@pytest.mark.asyncio
@patch("main.agent_run_service.get_recent_decisions")
async def test_get_decisions_returns_empty_list_when_no_history(
    mock_get_decisions: AsyncMock,
    async_client: AsyncClient
):
    """
    Test that the endpoint gracefully handles the case with no decision history.
    
    Why this test matters:
    - Ensures new users don't see errors
    - Validates proper empty state handling
    - Tests that the frontend can handle empty responses
    """
    # Arrange
    mock_get_decisions.return_value = []
    
    # Act
    response = await async_client.get("/agent-run/decisions")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["decisions"] == []


@pytest.mark.asyncio
@patch("main.agent_run_service.get_recent_decisions")
async def test_get_decisions_handles_service_errors_gracefully(
    mock_get_decisions: AsyncMock,
    async_client: AsyncClient
):
    """
    Test that the endpoint handles service-level errors appropriately.
    
    Why this test matters:
    - Ensures robustness in production
    - Validates error response format
    - Tests that sensitive error details aren't exposed
    """
    # Arrange
    mock_get_decisions.side_effect = Exception("Internal service error")
    
    # Act
    response = await async_client.get("/agent-run/decisions")
    
    # Assert
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "Internal service error" not in data["detail"]  # Don't expose internal errors


@pytest.mark.asyncio
@patch("main.snapshot_service.get_proposal")
@patch("main.agent_run_service.get_recent_decisions")
async def test_get_decisions_default_limit_is_applied(
    mock_get_decisions: AsyncMock,
    mock_get_proposal: AsyncMock,
    async_client: AsyncClient
):
    """
    Test that a sensible default limit is applied when not specified.
    
    Why this test matters:
    - Prevents accidental API abuse
    - Ensures consistent behavior
    - Protects frontend performance
    """
    # Arrange
    mock_get_decisions.return_value = []
    mock_get_proposal.return_value = {"title": "Test"}
    
    # Act
    response = await async_client.get("/agent-run/decisions")
    
    # Assert
    assert response.status_code == 200
    # Should call with default limit of 5 (as per spec)
    mock_get_decisions.assert_called_once_with(limit=5)