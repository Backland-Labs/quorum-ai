"""
Tests for State Persistence Integration

This test module verifies that StateTransitionTracker properly integrates
with StateManager for persistent state storage across agent restarts.
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock

import pytest

from backend.services.state_manager import StateManager
from backend.services.state_transition_tracker import (
    AgentState, 
    StateTransition, 
    StateTransitionTracker
)


class TestStateTransitionTrackerPersistence:
    """Test suite for StateTransitionTracker persistence using StateManager."""
    
    @pytest.fixture
    async def state_manager(self, tmp_path, monkeypatch):
        """Create a StateManager instance for testing."""
        # Set STORE_PATH to use temporary directory
        monkeypatch.setenv("STORE_PATH", str(tmp_path))
        state_manager = StateManager()
        yield state_manager
        await state_manager.cleanup()
    
    @pytest.fixture
    def tracker_with_state_manager(self, state_manager):
        """Create a StateTransitionTracker that uses StateManager."""
        # This will need to be modified to accept state_manager
        tracker = StateTransitionTracker(
            state_manager=state_manager,
            enable_state_manager=True
        )
        return tracker
    
    @pytest.mark.asyncio
    async def test_tracker_saves_state_through_state_manager(self, state_manager, tmp_path):
        """
        Test that StateTransitionTracker saves its state through StateManager.
        
        This test verifies that when state transitions occur, the tracker
        properly persists its state using the StateManager service rather
        than directly writing to files.
        """
        # Create tracker with StateManager integration
        tracker = StateTransitionTracker(
            state_manager=state_manager,
            enable_state_manager=True
        )
        
        # Initialize the tracker asynchronously
        await tracker.async_initialize()
        
        # Record a transition
        await tracker.async_record_transition(
            new_state=AgentState.STARTING,
            metadata={"reason": "test"}
        )
        
        # Verify state was saved through StateManager
        saved_state = await state_manager.load_state("agent_state_transitions")
        
        assert saved_state is not None
        assert saved_state["current_state"] == AgentState.STARTING.value
        assert len(saved_state["transition_history"]) == 1
        assert saved_state["transition_history"][0]["to_state"] == AgentState.STARTING.value
    
    @pytest.mark.asyncio
    async def test_tracker_loads_state_from_state_manager(self, state_manager):
        """
        Test that StateTransitionTracker loads previous state from StateManager.
        
        This test ensures that when a tracker is initialized, it properly
        loads any existing state from the StateManager, allowing recovery
        after restarts.
        """
        # Save some state data through StateManager
        test_state = {
            "current_state": AgentState.ANALYZING_PROPOSAL.value,
            "last_transition_time": datetime.now(timezone.utc).isoformat(),
            "transition_history": [
                {
                    "from_state": AgentState.IDLE.value,
                    "to_state": AgentState.STARTING.value,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {}
                },
                {
                    "from_state": AgentState.STARTING.value,
                    "to_state": AgentState.ANALYZING_PROPOSAL.value,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {"proposal_id": "test-123"}
                }
            ]
        }
        
        await state_manager.save_state("agent_state_transitions", test_state)
        
        # Create new tracker that should load the state
        tracker = StateTransitionTracker(
            state_manager=state_manager,
            enable_state_manager=True
        )
        await tracker.async_initialize()
        
        # Verify state was loaded correctly
        assert tracker.current_state == AgentState.ANALYZING_PROPOSAL
        assert len(tracker.transition_history) == 2
        assert tracker.transition_history[1].metadata["proposal_id"] == "test-123"
    
    @pytest.mark.asyncio
    async def test_tracker_handles_corrupted_state_gracefully(self, state_manager, tmp_path):
        """
        Test that tracker handles corrupted state data gracefully.
        
        This test verifies that if the saved state is corrupted or invalid,
        the tracker initializes with defaults and continues operating normally.
        """
        # Save corrupted state data directly to the state file
        state_file = tmp_path / "state" / "agent_state_transitions.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text("{ invalid json data")
        
        # Create tracker - should handle corruption gracefully
        tracker = StateTransitionTracker(
            state_manager=state_manager,
            enable_state_manager=True
        )
        await tracker.async_initialize()
        
        # Should initialize with defaults
        assert tracker.current_state == AgentState.IDLE
        assert len(tracker.transition_history) == 0
    
    @pytest.mark.asyncio
    async def test_tracker_maintains_history_size_limit(self, state_manager):
        """
        Test that tracker properly maintains history size limits when persisting.
        
        This test ensures that the transition history doesn't grow unbounded
        and that old entries are properly removed when the limit is reached.
        """
        # Create tracker with small history limit
        tracker = StateTransitionTracker(
            state_manager=state_manager,
            enable_state_manager=True,
            max_history_size=5
        )
        
        # Initialize the tracker
        await tracker.async_initialize()
        
        # Record more transitions than the limit
        states = [
            AgentState.STARTING,
            AgentState.LOADING_PREFERENCES,
            AgentState.FETCHING_PROPOSALS,
            AgentState.FILTERING_PROPOSALS,
            AgentState.ANALYZING_PROPOSAL,
            AgentState.DECIDING_VOTE,
            AgentState.SUBMITTING_VOTE,
            AgentState.COMPLETED
        ]
        
        for state in states:
            await tracker.async_record_transition(state)
        
        # Verify history is limited
        assert len(tracker.transition_history) == 5
        
        # Verify persisted state also has limited history
        saved_state = await state_manager.load_state("agent_state_transitions")
        assert len(saved_state["transition_history"]) == 5
        
        # Verify we kept the most recent transitions
        assert saved_state["transition_history"][-1]["to_state"] == AgentState.COMPLETED.value
    
    @pytest.mark.asyncio
    async def test_concurrent_state_updates_are_serialized(self, state_manager):
        """
        Test that concurrent state updates are properly serialized.
        
        This test verifies that when multiple transitions happen concurrently,
        they are properly serialized and all transitions are recorded.
        """
        tracker = StateTransitionTracker(
            state_manager=state_manager,
            enable_state_manager=True
        )
        
        # Initialize the tracker
        await tracker.async_initialize()
        
        # Create concurrent transition tasks
        async def record_transition(state: AgentState, delay: float):
            await asyncio.sleep(delay)
            await tracker.async_record_transition(state)
        
        # Start multiple concurrent transitions
        tasks = [
            record_transition(AgentState.STARTING, 0.01),
            record_transition(AgentState.LOADING_PREFERENCES, 0.02),
            record_transition(AgentState.FETCHING_PROPOSALS, 0.03),
        ]
        
        await asyncio.gather(*tasks)
        
        # All transitions should be recorded
        assert len(tracker.transition_history) == 3
        
        # Verify order is maintained
        states = [t.to_state for t in tracker.transition_history]
        assert states == [
            AgentState.STARTING,
            AgentState.LOADING_PREFERENCES,
            AgentState.FETCHING_PROPOSALS
        ]
    
    @pytest.mark.asyncio
    async def test_state_migration_from_old_format(self, state_manager):
        """
        Test that tracker can migrate from old file-based format to StateManager.
        
        This test ensures backward compatibility when upgrading from
        file-based persistence to StateManager-based persistence.
        """
        # Create old-style state file
        old_state_file = Path("agent_state.json")
        old_state_data = {
            "current_state": "analyzing_proposal",
            "last_transition_time": datetime.now(timezone.utc).isoformat(),
            "transition_history": [
                {
                    "from_state": "idle",
                    "to_state": "analyzing_proposal",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {"migrated": False}
                }
            ]
        }
        
        with open(old_state_file, 'w') as f:
            json.dump(old_state_data, f)
        
        try:
            # Create tracker with migration enabled
            tracker = StateTransitionTracker(
                state_manager=state_manager,
                enable_state_manager=True,
                migrate_from_file=True,
                state_file_path=str(old_state_file)
            )
            await tracker.async_initialize()
            
            # Verify state was migrated
            assert tracker.current_state == AgentState.ANALYZING_PROPOSAL
            assert len(tracker.transition_history) == 1
            
            # Verify state is now in StateManager
            saved_state = await state_manager.load_state("agent_state_transitions")
            assert saved_state is not None
            assert saved_state["current_state"] == "analyzing_proposal"
            
            # Verify old file was backed up or removed
            assert not old_state_file.exists() or old_state_file.with_suffix('.backup').exists()
            
        finally:
            # Cleanup
            if old_state_file.exists():
                old_state_file.unlink()
            backup_file = old_state_file.with_suffix('.backup')
            if backup_file.exists():
                backup_file.unlink()
    
    @pytest.mark.asyncio
    async def test_state_persistence_with_error_recovery(self, state_manager):
        """
        Test that tracker properly persists error states and recovery.
        
        This test verifies that error transitions are properly saved and
        that the tracker can recover from error states after restart.
        """
        tracker = StateTransitionTracker(
            state_manager=state_manager,
            enable_state_manager=True
        )
        
        # Initialize the tracker
        await tracker.async_initialize()
        
        # Simulate error during operation
        await tracker.async_record_transition(AgentState.STARTING)
        await tracker.async_record_transition(
            AgentState.ERROR,
            metadata={
                "error": "Connection timeout",
                "previous_state": "starting",
                "retry_count": 0
            }
        )
        
        # Verify error state is persisted
        saved_state = await state_manager.load_state("agent_state_transitions")
        assert saved_state["current_state"] == "error"
        assert saved_state["transition_history"][-1]["metadata"]["error"] == "Connection timeout"
        
        # Simulate restart and recovery
        new_tracker = StateTransitionTracker(
            state_manager=state_manager,
            enable_state_manager=True
        )
        await new_tracker.async_initialize()
        
        # Should load error state
        assert new_tracker.current_state == AgentState.ERROR
        assert new_tracker.is_in_error_state()
        
        # Record recovery
        await new_tracker.async_record_transition(
            AgentState.IDLE,
            metadata={"recovered": True}
        )
        
        # Verify recovery is persisted
        saved_state = await state_manager.load_state("agent_state_transitions")
        assert saved_state["current_state"] == "idle"
        assert saved_state["transition_history"][-1]["metadata"]["recovered"] is True
    
    @pytest.mark.asyncio
    async def test_get_persisted_statistics(self, state_manager):
        """
        Test that statistics are calculated correctly from persisted state.
        
        This test verifies that after loading state from persistence,
        the tracker can still calculate accurate statistics.
        """
        # Create and save state with history
        test_transitions = []
        states = [
            (AgentState.IDLE, AgentState.STARTING),
            (AgentState.STARTING, AgentState.LOADING_PREFERENCES),
            (AgentState.LOADING_PREFERENCES, AgentState.ERROR),
            (AgentState.ERROR, AgentState.IDLE),
            (AgentState.IDLE, AgentState.STARTING),
            (AgentState.STARTING, AgentState.COMPLETED)
        ]
        
        base_time = datetime.now(timezone.utc)
        for i, (from_state, to_state) in enumerate(states):
            test_transitions.append({
                "from_state": from_state.value,
                "to_state": to_state.value,
                "timestamp": (base_time + timedelta(seconds=i * 10)).isoformat(),
                "metadata": {}
            })
        
        test_state = {
            "current_state": AgentState.COMPLETED.value,
            "last_transition_time": test_transitions[-1]["timestamp"],
            "transition_history": test_transitions
        }
        
        await state_manager.save_state("agent_state_transitions", test_state)
        
        # Load state in new tracker
        tracker = StateTransitionTracker(
            state_manager=state_manager,
            enable_state_manager=True
        )
        await tracker.async_initialize()
        
        # Get statistics
        stats = tracker.get_transition_statistics()
        
        # Verify statistics are correct
        assert stats["total_transitions"] == 6
        assert tracker.get_error_count() == 1
        
        # Verify state durations can be calculated
        durations = tracker.get_state_durations()
        assert AgentState.STARTING in durations
        assert AgentState.ERROR in durations