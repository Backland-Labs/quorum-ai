"""
Test module for StateTransitionTracker service.

This module contains comprehensive tests for the StateTransitionTracker service,
which is responsible for tracking agent state transitions, detecting rapid
transitions, and persisting state information for recovery.

These tests follow TDD methodology and are written before the implementation
to define the expected behavior of the service.
"""

import asyncio
import json
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.state_transition_tracker import (
    AgentState,
    StateTransition,
    StateTransitionTracker,
)


class TestAgentStateEnum:
    """
    Test the AgentState enum to ensure all required states are present.
    
    This is important because the agent needs to track various operational
    states throughout its lifecycle, and missing states could lead to
    undefined behavior.
    """

    def test_agent_state_enum_has_all_required_states(self):
        """
        Verify that the AgentState enum contains all necessary states.
        
        Why: The agent must be able to represent all possible operational
        states to properly track its behavior and make decisions.
        """
        required_states = [
            "IDLE",
            "STARTING",
            "LOADING_PREFERENCES",
            "FETCHING_PROPOSALS",
            "FILTERING_PROPOSALS",
            "ANALYZING_PROPOSAL",
            "DECIDING_VOTE",
            "SUBMITTING_VOTE",
            "COMPLETED",
            "ERROR",
            "SHUTTING_DOWN",
        ]
        
        for state_name in required_states:
            assert hasattr(AgentState, state_name), f"AgentState enum missing {state_name}"
            
    def test_agent_state_enum_values_are_unique(self):
        """
        Ensure all AgentState enum values are unique.
        
        Why: Duplicate enum values could cause state tracking confusion
        and lead to incorrect behavior in state-dependent logic.
        """
        state_values = [state.value for state in AgentState]
        assert len(state_values) == len(set(state_values)), "AgentState enum has duplicate values"


class TestStateTransition:
    """
    Test the StateTransition data model.
    
    This model represents a single state transition event with metadata
    about when it occurred and what states were involved.
    """

    def test_state_transition_model_structure(self):
        """
        Verify the StateTransition model has all required fields.
        
        Why: The model must capture complete information about each
        transition for proper tracking and analysis.
        """
        transition = StateTransition(
            from_state=AgentState.IDLE,
            to_state=AgentState.STARTING,
            timestamp=datetime.now(),
            metadata={"reason": "User initiated"}
        )
        
        assert hasattr(transition, "from_state")
        assert hasattr(transition, "to_state")
        assert hasattr(transition, "timestamp")
        assert hasattr(transition, "metadata")
        
    def test_state_transition_json_serialization(self):
        """
        Test that StateTransition can be serialized to/from JSON.
        
        Why: State transitions need to be persisted to disk for recovery
        and audit purposes, requiring JSON serialization.
        """
        transition = StateTransition(
            from_state=AgentState.IDLE,
            to_state=AgentState.STARTING,
            timestamp=datetime.now(),
            metadata={"reason": "Test"}
        )
        
        # Should be able to convert to dict and back
        transition_dict = transition.model_dump()
        assert isinstance(transition_dict, dict)
        
        # Should be able to create from dict
        restored = StateTransition.model_validate(transition_dict)
        assert restored.from_state == transition.from_state
        assert restored.to_state == transition.to_state


class TestStateTransitionTracker:
    """
    Test the main StateTransitionTracker service.
    
    This service is responsible for tracking state changes, detecting
    rapid transitions, and persisting state for recovery.
    """

    @pytest.fixture
    def temp_state_file(self):
        """Create a temporary file for state persistence testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def tracker(self, temp_state_file):
        """Create a StateTransitionTracker instance for testing."""
        return StateTransitionTracker(state_file_path=temp_state_file)

    def test_tracker_initialization(self, tracker):
        """
        Test that the tracker initializes with correct default state.
        
        Why: The tracker must start in a known state (IDLE) to ensure
        predictable behavior when the agent starts.
        """
        assert tracker.current_state == AgentState.IDLE
        assert tracker.last_transition_time is not None
        assert len(tracker.transition_history) == 0

    def test_record_state_transition(self, tracker):
        """
        Test recording a state transition updates all relevant fields.
        
        Why: Accurate state tracking is essential for monitoring agent
        behavior and making decisions based on current state.
        """
        initial_time = tracker.last_transition_time
        
        # Record a transition
        tracker.record_transition(AgentState.STARTING, {"reason": "test"})
        
        assert tracker.current_state == AgentState.STARTING
        assert tracker.last_transition_time > initial_time
        assert len(tracker.transition_history) == 1
        
        transition = tracker.transition_history[0]
        assert transition.from_state == AgentState.IDLE
        assert transition.to_state == AgentState.STARTING
        assert transition.metadata == {"reason": "test"}

    def test_seconds_since_last_transition(self, tracker):
        """
        Test calculation of time since last transition.
        
        Why: This metric is crucial for detecting stuck states and
        implementing timeouts for various operations.
        """
        # Set a known transition time
        past_time = datetime.now() - timedelta(seconds=10)
        tracker.last_transition_time = past_time
        
        seconds = tracker.seconds_since_last_transition
        assert 9.5 <= seconds <= 10.5  # Allow small variance for test execution

    def test_is_transitioning_fast_detection(self, tracker):
        """
        Test detection of rapid state transitions.
        
        Why: Rapid transitions often indicate errors or infinite loops,
        and detecting them allows the agent to take corrective action.
        """
        # Initially should not be transitioning fast
        assert not tracker.is_transitioning_fast()
        
        # Record multiple rapid transitions
        for i in range(10):
            tracker.record_transition(
                AgentState.STARTING if i % 2 == 0 else AgentState.IDLE
            )
            time.sleep(0.01)  # Very short delay
        
        # Should now detect fast transitions
        assert tracker.is_transitioning_fast()

    def test_is_transitioning_fast_with_normal_pace(self, tracker):
        """
        Test that normal-paced transitions are not flagged as fast.
        
        Why: We need to avoid false positives that could trigger
        unnecessary error handling or throttling.
        """
        # Record transitions with normal delays
        states = [AgentState.STARTING, AgentState.LOADING_PREFERENCES, 
                  AgentState.FETCHING_PROPOSALS]
        
        for state in states:
            tracker.record_transition(state)
            time.sleep(0.6)  # Slightly more than threshold
        
        assert not tracker.is_transitioning_fast()

    def test_state_persistence(self, tracker, temp_state_file):
        """
        Test that state is persisted to disk after transitions.
        
        Why: Persistence enables recovery after crashes and provides
        an audit trail of agent behavior.
        """
        # Record some transitions
        tracker.record_transition(AgentState.STARTING)
        tracker.record_transition(AgentState.LOADING_PREFERENCES)
        
        # Verify file was created and contains data
        assert os.path.exists(temp_state_file)
        
        with open(temp_state_file, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data["current_state"] == AgentState.LOADING_PREFERENCES.value
        assert len(saved_data["transition_history"]) == 2

    def test_state_recovery_from_file(self, temp_state_file):
        """
        Test that tracker can recover state from a persisted file.
        
        Why: Recovery is essential for resuming operations after
        unexpected shutdowns or crashes.
        """
        # Create a state file with known data
        past_time = (datetime.now() - timedelta(minutes=5)).isoformat()
        state_data = {
            "current_state": AgentState.ANALYZING_PROPOSAL.value,
            "last_transition_time": past_time,
            "transition_history": [
                {
                    "from_state": AgentState.IDLE.value,
                    "to_state": AgentState.STARTING.value,
                    "timestamp": past_time,
                    "metadata": {"recovered": True}
                }
            ]
        }
        
        with open(temp_state_file, 'w') as f:
            json.dump(state_data, f)
        
        # Create new tracker that should load the state
        tracker = StateTransitionTracker(state_file_path=temp_state_file)
        
        assert tracker.current_state == AgentState.ANALYZING_PROPOSAL
        assert len(tracker.transition_history) == 1
        assert tracker.transition_history[0].metadata == {"recovered": True}

    def test_thread_safe_operations(self, temp_state_file):
        """
        Test that state transitions are thread-safe.
        
        Why: The agent may have multiple components trying to update
        state concurrently, requiring thread-safe operations.
        """
        import threading
        
        # Create tracker with unlimited history for this test
        tracker = StateTransitionTracker(
            state_file_path=temp_state_file,
            max_history_size=None  # No limit for this test
        )
        
        transitions_per_thread = 100
        num_threads = 5
        
        def transition_worker(thread_id):
            for i in range(transitions_per_thread):
                state = AgentState.STARTING if i % 2 == 0 else AgentState.IDLE
                tracker.record_transition(state, {"thread": thread_id, "iteration": i})
        
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=transition_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should have recorded all transitions
        expected_transitions = transitions_per_thread * num_threads
        assert len(tracker.transition_history) == expected_transitions

    @pytest.mark.asyncio
    async def test_async_state_transitions(self, tracker):
        """
        Test that tracker works correctly with async operations.
        
        Why: The agent uses async/await patterns extensively, so the
        tracker must work correctly in async contexts.
        """
        async def async_transition():
            tracker.record_transition(AgentState.FETCHING_PROPOSALS)
            await asyncio.sleep(0.1)
            tracker.record_transition(AgentState.ANALYZING_PROPOSAL)
        
        await async_transition()
        
        assert tracker.current_state == AgentState.ANALYZING_PROPOSAL
        assert len(tracker.transition_history) == 2

    def test_transition_history_limit(self, tracker):
        """
        Test that transition history has a reasonable size limit.
        
        Why: Without a limit, long-running agents could accumulate
        excessive memory usage from unbounded history.
        """
        # Record many transitions
        for i in range(1000):
            state = AgentState.STARTING if i % 2 == 0 else AgentState.IDLE
            tracker.record_transition(state)
        
        # History should be limited (e.g., last 100 transitions)
        assert len(tracker.transition_history) <= 100

    def test_get_recent_transitions(self, tracker):
        """
        Test retrieval of recent transitions for analysis.
        
        Why: Analyzing recent transitions helps detect patterns
        and diagnose issues in agent behavior.
        """
        # Record some transitions
        states = [
            AgentState.STARTING,
            AgentState.LOADING_PREFERENCES,
            AgentState.FETCHING_PROPOSALS,
            AgentState.ERROR,
        ]
        
        for state in states:
            tracker.record_transition(state)
            time.sleep(0.1)
        
        # Get recent transitions
        recent = tracker.get_recent_transitions(seconds=0.5)
        assert len(recent) >= 3  # Should include most recent transitions

    def test_clear_transition_history(self, tracker):
        """
        Test clearing transition history while preserving current state.
        
        Why: Clearing history can be useful for testing or when
        history becomes irrelevant after certain operations.
        """
        # Record some transitions
        tracker.record_transition(AgentState.STARTING)
        tracker.record_transition(AgentState.LOADING_PREFERENCES)
        
        current_state = tracker.current_state
        
        # Clear history
        tracker.clear_history()
        
        assert len(tracker.transition_history) == 0
        assert tracker.current_state == current_state

    @patch('logging_config.setup_pearl_logger')
    def test_pearl_logger_integration(self, mock_setup_pearl_logger, tracker):
        """
        Test that state transitions are logged via Pearl logger.
        
        Why: Pearl-compliant logging is required for observability
        in the Pearl App store environment.
        """
        mock_logger = MagicMock()
        # Create a mock method for log_state_transition
        mock_logger.log_state_transition = MagicMock()
        mock_setup_pearl_logger.return_value = mock_logger
        
        # Create tracker with Pearl logging enabled
        tracker_with_logging = StateTransitionTracker(
            state_file_path="test.json",
            enable_pearl_logging=True
        )
        
        # Record a transition
        tracker_with_logging.record_transition(
            AgentState.STARTING,
            {"reason": "test"}
        )
        
        # Verify Pearl logger info method was called for state transition
        assert mock_logger.info.call_count >= 1
        # Check that a state transition message was logged
        logged_messages = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("State transition:" in msg for msg in logged_messages)

    def test_error_state_handling(self, tracker):
        """
        Test special handling for ERROR state transitions.
        
        Why: Error states need special handling to capture diagnostic
        information and potentially trigger recovery mechanisms.
        """
        # Transition to error state
        error_metadata = {
            "error_type": "NetworkError",
            "message": "Failed to connect to API",
            "traceback": "..."
        }
        
        tracker.record_transition(AgentState.ERROR, error_metadata)
        
        assert tracker.current_state == AgentState.ERROR
        
        # Should be able to query if in error state
        assert tracker.is_in_error_state()
        
        # Should track error count
        assert tracker.get_error_count() == 1

    def test_state_duration_tracking(self, tracker):
        """
        Test tracking how long the agent spends in each state.
        
        Why: Duration metrics help identify bottlenecks and optimize
        agent performance by focusing on slow operations.
        """
        # Record transitions with delays
        tracker.record_transition(AgentState.STARTING)
        time.sleep(0.5)
        tracker.record_transition(AgentState.LOADING_PREFERENCES)
        time.sleep(0.3)
        tracker.record_transition(AgentState.IDLE)
        
        # Get duration statistics
        durations = tracker.get_state_durations()
        
        assert AgentState.STARTING in durations
        assert 0.4 <= durations[AgentState.STARTING] <= 0.6
        assert AgentState.LOADING_PREFERENCES in durations
        assert 0.2 <= durations[AgentState.LOADING_PREFERENCES] <= 0.4

    def test_invalid_state_transition_validation(self, tracker):
        """
        Test that invalid state transitions are detected.
        
        Why: Some state transitions don't make logical sense (e.g.,
        IDLE -> SUBMITTING_VOTE) and should be prevented or flagged.
        """
        # Define invalid transitions
        with pytest.raises(ValueError, match="Invalid state transition"):
            tracker.record_transition(
                AgentState.SUBMITTING_VOTE,
                validate_transition=True
            )

    def test_get_transition_graph(self, tracker):
        """
        Test generation of state transition graph/statistics.
        
        Why: Visualizing transition patterns helps understand agent
        behavior and identify unusual patterns.
        """
        # Record various transitions
        transitions = [
            AgentState.STARTING,
            AgentState.LOADING_PREFERENCES,
            AgentState.FETCHING_PROPOSALS,
            AgentState.IDLE,
            AgentState.STARTING,
            AgentState.ERROR,
            AgentState.IDLE,
        ]
        
        for state in transitions:
            tracker.record_transition(state)
        
        # Get transition statistics
        stats = tracker.get_transition_statistics()
        
        assert stats["total_transitions"] == len(transitions)
        assert AgentState.IDLE in stats["state_counts"]
        assert stats["state_counts"][AgentState.IDLE] == 2
        assert (AgentState.STARTING, AgentState.ERROR) in stats["transition_pairs"]