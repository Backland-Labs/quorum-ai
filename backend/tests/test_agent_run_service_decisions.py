"""
Tests for AgentRunService decision retrieval methods

This test module verifies that the AgentRunService correctly:
1. Reads and aggregates decisions from multiple checkpoint files
2. Sorts decisions by timestamp in reverse chronological order
3. Applies limit correctly
4. Handles missing or corrupted checkpoint files gracefully
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from backend.models import VoteDecision
from backend.services.agent_run_service import AgentRunService
from backend.services.state_manager import StateManager


@pytest.fixture
def agent_run_service():
    """Create an AgentRunService instance for testing."""
    from services.state_manager import StateManager
    from unittest.mock import AsyncMock
    
    state_manager = Mock(spec=StateManager)
    # Add async methods
    state_manager.list_files = AsyncMock()
    state_manager.load_state = AsyncMock()
    
    service = AgentRunService(state_manager=state_manager)
    yield service


@pytest.mark.asyncio
async def test_get_recent_decisions_aggregates_from_multiple_checkpoints(agent_run_service):
    """
    Test that decisions are correctly aggregated from multiple space checkpoints.
    
    Why this test matters:
    - Ensures we collect decisions across all spaces the agent monitors
    - Validates that the aggregation logic works correctly
    - Tests that we don't miss decisions from any checkpoint file
    """
    # Arrange
    now = datetime.now(timezone.utc)
    
    checkpoint1 = {
        "run_id": "run-1",
        "space_id": "space1.eth",
        "votes_cast": [
            {
                "proposal_id": "0x1",
                "vote": "FOR",
                "confidence": 0.9,
                "reasoning": "Good proposal that aligns with community values and strategic goals",
                "strategy_used": "balanced",
                "timestamp": (now - timedelta(hours=1)).isoformat()
            }
        ],
        "completed_at": (now - timedelta(hours=1)).isoformat()
    }
    
    checkpoint2 = {
        "run_id": "run-2",
        "space_id": "space2.eth",
        "votes_cast": [
            {
                "proposal_id": "0x2",
                "vote": "AGAINST",
                "confidence": 0.8,
                "reasoning": "This proposal does not align with our strategic priorities and goals",
                "strategy_used": "balanced",
                "timestamp": (now - timedelta(minutes=30)).isoformat()
            },
            {
                "proposal_id": "0x3",
                "vote": "FOR",
                "confidence": 0.85,
                "reasoning": "Decent proposal that provides moderate value to the community",
                "strategy_used": "balanced",
                "timestamp": (now - timedelta(minutes=20)).isoformat()
            }
        ],
        "completed_at": now.isoformat()
    }
    
    # Mock state manager to return our test checkpoints
    mock_state_files = [
        ("agent_checkpoint_space1.eth.json", checkpoint1),
        ("agent_checkpoint_space2.eth.json", checkpoint2),
        ("some_other_file.json", {})  # Should be ignored
    ]
    
    with patch.object(agent_run_service.state_manager, 'list_files') as mock_list_files, \
         patch.object(agent_run_service.state_manager, 'load_state') as mock_load:
        
        mock_list_files.return_value = [f[0] for f in mock_state_files]
        
        def mock_load_state(key, **kwargs):
            # The implementation strips the .json extension
            filename = key + '.json'
            for name, data in mock_state_files:
                if name == filename:
                    return data
            return {}
        
        mock_load.side_effect = mock_load_state
        
        # Act
        decisions = await agent_run_service.get_recent_decisions(limit=10)
        
        # Assert
        assert len(decisions) == 3
        # Should be sorted by timestamp, most recent first
        assert decisions[0][0].proposal_id == "0x3"
        assert decisions[1][0].proposal_id == "0x2"
        assert decisions[2][0].proposal_id == "0x1"


@pytest.mark.asyncio
async def test_get_recent_decisions_respects_limit(agent_run_service):
    """
    Test that the limit parameter correctly restricts the number of returned decisions.
    
    Why this test matters:
    - Ensures API pagination works correctly
    - Validates that we don't return more data than requested
    - Tests that the most recent decisions are prioritized
    """
    # Arrange
    now = datetime.now(timezone.utc)
    
    checkpoint = {
        "run_id": "run-1",
        "space_id": "space.eth",
        "votes_cast": [
            {
                "proposal_id": f"0x{i}",
                "vote": "FOR",
                "confidence": 0.8,
                "reasoning": f"This is a detailed reasoning for proposal {i} that meets minimum length requirements",
                "strategy_used": "balanced",
                "timestamp": (now - timedelta(hours=i)).isoformat()
            }
            for i in range(10)
        ],
        "completed_at": now.isoformat()
    }
    
    with patch.object(agent_run_service.state_manager, 'list_files') as mock_list_files, \
         patch.object(agent_run_service.state_manager, 'load_state') as mock_load:
        
        mock_list_files.return_value = ["agent_checkpoint_space.eth.json"]
        mock_load.return_value = checkpoint
        
        # Act
        decisions = await agent_run_service.get_recent_decisions(limit=3)
        
        # Assert
        assert len(decisions) == 3
        # Should get the 3 most recent (0x0, 0x1, 0x2)
        assert decisions[0][0].proposal_id == "0x0"
        assert decisions[1][0].proposal_id == "0x1"
        assert decisions[2][0].proposal_id == "0x2"


@pytest.mark.asyncio
async def test_get_recent_decisions_handles_empty_checkpoints(agent_run_service):
    """
    Test that the method handles checkpoints with no votes gracefully.
    
    Why this test matters:
    - Ensures robustness when agent hasn't voted yet
    - Validates that empty checkpoints don't cause errors
    - Tests that we can handle various checkpoint states
    """
    # Arrange
    checkpoint_no_votes = {
        "run_id": "run-1",
        "space_id": "space.eth",
        "votes_cast": [],  # Empty votes list
        "completed_at": datetime.now(timezone.utc).isoformat()
    }
    
    checkpoint_missing_votes = {
        "run_id": "run-2",
        "space_id": "space2.eth",
        # Missing votes_cast key entirely
        "completed_at": datetime.now(timezone.utc).isoformat()
    }
    
    with patch.object(agent_run_service.state_manager, 'list_files') as mock_list_files, \
         patch.object(agent_run_service.state_manager, 'load_state') as mock_load:
        
        mock_list_files.return_value = [
            "agent_checkpoint_space.eth.json",
            "agent_checkpoint_space2.eth.json"
        ]
        mock_load.side_effect = [checkpoint_no_votes, checkpoint_missing_votes]
        
        # Act
        decisions = await agent_run_service.get_recent_decisions(limit=5)
        
        # Assert
        assert len(decisions) == 0  # Should return empty list, not error


@pytest.mark.asyncio
async def test_get_recent_decisions_handles_corrupted_checkpoint_files(agent_run_service):
    """
    Test that corrupted checkpoint files are handled gracefully.
    
    Why this test matters:
    - Ensures system resilience to file corruption
    - Validates error recovery mechanisms
    - Tests that one bad file doesn't break everything
    """
    # Arrange
    good_checkpoint = {
        "run_id": "run-1",
        "space_id": "good.eth",
        "votes_cast": [
            {
                "proposal_id": "0x1",
                "vote": "FOR",
                "confidence": 0.9,
                "reasoning": "Good proposal that benefits the community and aligns with values",
                "strategy_used": "balanced",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ],
        "completed_at": datetime.now(timezone.utc).isoformat()
    }
    
    with patch.object(agent_run_service.state_manager, 'list_files') as mock_list_files, \
         patch.object(agent_run_service.state_manager, 'load_state') as mock_load:
        
        mock_list_files.return_value = [
            "agent_checkpoint_bad.eth.json",
            "agent_checkpoint_good.eth.json"
        ]
        # First file throws error, second is good
        mock_load.side_effect = [
            Exception("Corrupted file"),
            good_checkpoint
        ]
        
        # Act
        decisions = await agent_run_service.get_recent_decisions(limit=5)
        
        # Assert
        assert len(decisions) == 1  # Should still get decision from good file
        assert decisions[0][0].proposal_id == "0x1"


@pytest.mark.asyncio
async def test_get_recent_decisions_sorts_by_timestamp_correctly(agent_run_service):
    """
    Test that decisions are correctly sorted by timestamp in reverse chronological order.
    
    Why this test matters:
    - Ensures users see the most recent decisions first
    - Validates timestamp parsing and comparison
    - Tests sorting across different checkpoint files
    """
    # Arrange
    base_time = datetime.now(timezone.utc)
    
    checkpoint1 = {
        "run_id": "run-1",
        "space_id": "space1.eth",
        "votes_cast": [
            {
                "proposal_id": "old",
                "vote": "FOR",
                "confidence": 0.9,
                "reasoning": "Old decision with detailed reasoning that meets minimum requirements",
                "strategy_used": "balanced",
                "timestamp": (base_time - timedelta(days=2)).isoformat()
            },
            {
                "proposal_id": "newest",
                "vote": "FOR",
                "confidence": 0.9,
                "reasoning": "Newest decision with comprehensive analysis and clear benefits",
                "strategy_used": "balanced",
                "timestamp": base_time.isoformat()
            }
        ],
        "completed_at": base_time.isoformat()
    }
    
    checkpoint2 = {
        "run_id": "run-2",
        "space_id": "space2.eth",
        "votes_cast": [
            {
                "proposal_id": "middle",
                "vote": "AGAINST",
                "confidence": 0.8,
                "reasoning": "Middle decision with balanced analysis of pros and cons for community",
                "strategy_used": "balanced",
                "timestamp": (base_time - timedelta(days=1)).isoformat()
            }
        ],
        "completed_at": (base_time - timedelta(days=1)).isoformat()
    }
    
    with patch.object(agent_run_service.state_manager, 'list_files') as mock_list_files, \
         patch.object(agent_run_service.state_manager, 'load_state') as mock_load:
        
        mock_list_files.return_value = [
            "agent_checkpoint_space1.eth.json",
            "agent_checkpoint_space2.eth.json"
        ]
        mock_load.side_effect = [checkpoint1, checkpoint2]
        
        # Act
        decisions = await agent_run_service.get_recent_decisions(limit=10)
        
        # Assert
        assert len(decisions) == 3
        assert decisions[0][0].proposal_id == "newest"
        assert decisions[1][0].proposal_id == "middle"
        assert decisions[2][0].proposal_id == "old"


@pytest.mark.asyncio
async def test_get_recent_decisions_validates_decision_format(agent_run_service):
    """
    Test that invalid decision formats in checkpoints are handled properly.
    
    Why this test matters:
    - Ensures data integrity
    - Tests Pydantic validation is applied
    - Validates that bad data doesn't crash the system
    """
    # Arrange
    checkpoint_with_invalid_decisions = {
        "run_id": "run-1",
        "space_id": "space.eth",
        "votes_cast": [
            {
                # Valid decision
                "proposal_id": "0x1",
                "vote": "FOR",
                "confidence": 0.9,
                "reasoning": "Valid proposal with clear benefits and alignment with objectives",
                "strategy_used": "balanced",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            {
                # Invalid: missing required fields
                "proposal_id": "0x2",
                "vote": "INVALID_VOTE_TYPE"  # Invalid enum value
                # Missing confidence, reasoning, timestamp
            },
            {
                # Invalid: wrong type
                "proposal_id": "0x3",
                "vote": "FOR",
                "confidence": "not_a_number",  # Should be float
                "reasoning": "Test proposal that meets validation requirements for demonstration",
                "strategy_used": "balanced",
                "timestamp": "invalid_timestamp"
            }
        ],
        "completed_at": datetime.now(timezone.utc).isoformat()
    }
    
    with patch.object(agent_run_service.state_manager, 'list_files') as mock_list_files, \
         patch.object(agent_run_service.state_manager, 'load_state') as mock_load:
        
        mock_list_files.return_value = ["agent_checkpoint_space.eth.json"]
        mock_load.return_value = checkpoint_with_invalid_decisions
        
        # Act
        decisions = await agent_run_service.get_recent_decisions(limit=5)
        
        # Assert
        # Should only get the valid decision
        assert len(decisions) == 1
        assert decisions[0][0].proposal_id == "0x1"