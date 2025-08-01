"""Test voting history persistence functionality with 10-item limit."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from services.agent_run_service import AgentRunService
from models import VoteDecision, VoteType, VotingStrategy


@pytest.mark.asyncio
async def test_voting_history_limited_to_10():
    """Test that voting history is limited to 10 most recent decisions.
    
    Why this test matters: The voting history should be limited to prevent
    unbounded growth of stored data while still providing sufficient context
    for strategic decision-making. 10 decisions provide enough historical
    context without overwhelming the system.
    """
    mock_state_manager = MagicMock()
    existing_history = [
        {"proposal_id": f"0x{i}", "vote": "FOR", "confidence": 0.8}
        for i in range(15)
    ]
    mock_state_manager.load_state = AsyncMock(return_value={
        "voting_history": existing_history
    })
    mock_state_manager.save_state = AsyncMock()
    
    service = AgentRunService(state_manager=mock_state_manager)
    await service.initialize()
    
    # Get voting history
    history = await service.get_voting_history()
    
    # Should only return 10 most recent
    assert len(history) == 10
    assert history[0].proposal_id == "0x5"  # Oldest in the 10
    assert history[-1].proposal_id == "0x14"  # Most recent


@pytest.mark.asyncio
async def test_voting_history_persistence():
    """Test that new votes are added and history is pruned.
    
    Why this test matters: This ensures that the voting history correctly
    adds new decisions while maintaining the 10-item limit by pruning
    older entries. This is critical for maintaining a consistent sliding
    window of recent voting behavior.
    """
    mock_state_manager = MagicMock()
    existing = [{"proposal_id": f"0x{i}", "vote": "FOR", "confidence": 0.7} for i in range(8)]
    mock_state_manager.load_state = AsyncMock(return_value={
        "voting_history": existing
    })
    mock_state_manager.save_state = AsyncMock()
    
    service = AgentRunService(state_manager=mock_state_manager)
    await service.initialize()
    
    # Add new decisions
    new_decisions = [
        VoteDecision(proposal_id=f"0xnew{i}", vote=VoteType.FOR, 
                    confidence=0.9, reasoning="New vote based on strategic analysis",
                    strategy_used=VotingStrategy.BALANCED)
        for i in range(3)
    ]
    
    await service.save_voting_decisions(new_decisions)
    
    # Verify save was called with 10 items (8 existing + 3 new - 1 pruned)
    save_calls = mock_state_manager.save_state.call_args_list
    assert len(save_calls) > 0
    # Find the call that saved voting_history (may not be the first one)
    voting_history_call = None
    for call in save_calls:
        if call[0][0] == "voting_history":  # Check first positional arg
            voting_history_call = call
            break
    assert voting_history_call is not None, "voting_history save_state call not found"
    # Get the data from the voting history call
    saved_data = voting_history_call[0][1]
    assert len(saved_data["voting_history"]) == 10
    assert saved_data["voting_history"][-1]["proposal_id"] == "0xnew2"


@pytest.mark.asyncio
async def test_voting_history_empty_initial_state():
    """Test that voting history works correctly with no existing history.
    
    Why this test matters: The system should gracefully handle the case
    where no voting history exists yet (new user or fresh start). This
    ensures the agent can start making decisions without prior context.
    """
    mock_state_manager = MagicMock()
    mock_state_manager.load_state = AsyncMock(return_value=None)
    mock_state_manager.save_state = AsyncMock()
    
    service = AgentRunService(state_manager=mock_state_manager)
    await service.initialize()
    
    # Get voting history
    history = await service.get_voting_history()
    
    # Should return empty list
    assert history == []
    
    # Add new decisions
    new_decisions = [
        VoteDecision(proposal_id="0x1", vote=VoteType.AGAINST, 
                    confidence=0.85, reasoning="First vote after careful evaluation",
                    strategy_used=VotingStrategy.CONSERVATIVE)
    ]
    
    await service.save_voting_decisions(new_decisions)
    
    # Verify save was called with 1 item
    save_calls = mock_state_manager.save_state.call_args_list
    assert len(save_calls) > 0
    # Find the call that saved voting_history
    voting_history_call = None
    for call in save_calls:
        if call[0][0] == "voting_history":  # Check first positional arg
            voting_history_call = call
            break
    assert voting_history_call is not None, "voting_history save_state call not found"
    # Get the data from the voting history call
    saved_data = voting_history_call[0][1]
    assert len(saved_data["voting_history"]) == 1
    assert saved_data["voting_history"][0]["proposal_id"] == "0x1"


@pytest.mark.asyncio
async def test_voting_history_preserves_decision_details():
    """Test that all decision details are preserved in history.
    
    Why this test matters: The voting history must preserve all relevant
    decision details (vote type, confidence, reasoning) to provide
    meaningful context for future strategic decisions. Loss of these
    details would reduce the effectiveness of pattern analysis.
    """
    mock_state_manager = MagicMock()
    mock_state_manager.load_state = AsyncMock(return_value={
        "voting_history": []
    })
    mock_state_manager.save_state = AsyncMock()
    
    service = AgentRunService(state_manager=mock_state_manager)
    await service.initialize()
    
    # Create decision with full details
    decision = VoteDecision(
        proposal_id="0xtest",
        vote=VoteType.ABSTAIN,
        confidence=0.65,
        reasoning="Insufficient information to make a clear decision",
        strategy_used=VotingStrategy.BALANCED
    )
    
    await service.save_voting_decisions([decision])
    
    # Verify all details are preserved
    save_calls = mock_state_manager.save_state.call_args_list
    # Find the call that saved voting_history
    voting_history_call = None
    for call in save_calls:
        if call[0][0] == "voting_history":  # Check first positional arg
            voting_history_call = call
            break
    assert voting_history_call is not None, "voting_history save_state call not found"
    # Get the data from the voting history call
    saved_data = voting_history_call[0][1]
    saved_decision = saved_data["voting_history"][0]
    
    assert saved_decision["proposal_id"] == "0xtest"
    assert saved_decision["vote"] == "ABSTAIN"
    assert saved_decision["confidence"] == 0.65
    assert saved_decision["reasoning"] == "Insufficient information to make a clear decision"


@pytest.mark.asyncio
async def test_voting_history_handles_malformed_data():
    """Test that voting history gracefully handles malformed stored data.
    
    Why this test matters: In production, stored data may become corrupted
    or be in an unexpected format. The system should handle these cases
    gracefully without crashing, allowing the agent to continue operating.
    """
    mock_state_manager = MagicMock()
    # Return malformed data
    mock_state_manager.load_state = AsyncMock(return_value={
        "voting_history": [
            {"proposal_id": "0x1", "vote": "FOR"},  # Missing confidence
            {"invalid": "data"},  # Completely wrong format
            {"proposal_id": "0x2", "vote": "AGAINST", "confidence": 0.8}  # Valid
        ]
    })
    mock_state_manager.save_state = AsyncMock()
    
    service = AgentRunService(state_manager=mock_state_manager)
    await service.initialize()
    
    # Get voting history - should filter out invalid entries
    history = await service.get_voting_history()
    
    # Should return 2 valid entries (0x1 with defaults and 0x2)
    # The first entry is missing confidence but gets a default value
    assert len(history) == 2
    assert history[0].proposal_id == "0x1"
    assert history[0].confidence == 0.0  # Default value
    assert history[1].proposal_id == "0x2"
    assert history[1].confidence == 0.8


@pytest.mark.asyncio
async def test_voting_patterns_analysis():
    """Test that voting patterns can be analyzed from history.
    
    Why this test matters: The voting history should support pattern
    analysis to identify trends in voting behavior. This analysis is
    crucial for the strategic briefing system to provide insights
    about historical voting tendencies.
    """
    mock_state_manager = MagicMock()
    mock_state_manager.load_state = AsyncMock(return_value={
        "voting_history": [
            {"proposal_id": f"0x{i}", "vote": "FOR" if i % 3 == 0 else "AGAINST", 
             "confidence": 0.7 + (i * 0.02)}
            for i in range(10)
        ]
    })
    
    service = AgentRunService(state_manager=mock_state_manager)
    await service.initialize()
    
    # Get voting patterns
    patterns = await service.get_voting_patterns()
    
    # Verify pattern analysis
    assert "vote_distribution" in patterns
    assert patterns["vote_distribution"]["FOR"] == 4  # 0, 3, 6, 9
    assert patterns["vote_distribution"]["AGAINST"] == 6
    assert "average_confidence" in patterns
    assert 0.7 <= patterns["average_confidence"] <= 0.9
    assert "total_votes" in patterns
    assert patterns["total_votes"] == 10