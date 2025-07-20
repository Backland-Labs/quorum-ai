"""
State Transition Tracker Service

This service tracks agent state transitions, detects rapid transitions,
and persists state information for recovery. It integrates with Pearl
logging for observability in the Pearl App store environment.
"""

import asyncio
import json
import logging
import threading
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field


class AgentState(Enum):
    """Enumeration of all possible agent states."""
    IDLE = "idle"
    STARTING = "starting"
    LOADING_PREFERENCES = "loading_preferences"
    FETCHING_PROPOSALS = "fetching_proposals"
    FILTERING_PROPOSALS = "filtering_proposals"
    ANALYZING_PROPOSAL = "analyzing_proposal"
    DECIDING_VOTE = "deciding_vote"
    SUBMITTING_VOTE = "submitting_vote"
    COMPLETED = "completed"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"


class StateTransition(BaseModel):
    """Model representing a single state transition event."""
    from_state: AgentState
    to_state: AgentState
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StateTransitionTracker:
    """
    Tracks agent state transitions with persistence and analysis capabilities.
    
    This tracker provides thread-safe state management, rapid transition detection,
    and integration with Pearl logging for observability.
    """
    
    # Valid state transitions (from_state -> [allowed_to_states])
    VALID_TRANSITIONS = {
        AgentState.IDLE: [AgentState.STARTING, AgentState.SHUTTING_DOWN],
        AgentState.STARTING: [AgentState.LOADING_PREFERENCES, AgentState.ERROR, AgentState.IDLE],
        AgentState.LOADING_PREFERENCES: [AgentState.FETCHING_PROPOSALS, AgentState.ERROR, AgentState.IDLE],
        AgentState.FETCHING_PROPOSALS: [AgentState.FILTERING_PROPOSALS, AgentState.ERROR, AgentState.IDLE],
        AgentState.FILTERING_PROPOSALS: [AgentState.ANALYZING_PROPOSAL, AgentState.COMPLETED, AgentState.ERROR, AgentState.IDLE],
        AgentState.ANALYZING_PROPOSAL: [AgentState.DECIDING_VOTE, AgentState.ERROR, AgentState.IDLE],
        AgentState.DECIDING_VOTE: [AgentState.SUBMITTING_VOTE, AgentState.FILTERING_PROPOSALS, AgentState.ERROR, AgentState.IDLE],
        AgentState.SUBMITTING_VOTE: [AgentState.FILTERING_PROPOSALS, AgentState.COMPLETED, AgentState.ERROR, AgentState.IDLE],
        AgentState.COMPLETED: [AgentState.IDLE, AgentState.SHUTTING_DOWN],
        AgentState.ERROR: [AgentState.IDLE, AgentState.SHUTTING_DOWN],
        AgentState.SHUTTING_DOWN: [AgentState.IDLE],
    }
    
    def __init__(
        self,
        state_file_path: str = "agent_state.json",
        enable_pearl_logging: bool = False,
        max_history_size: Optional[int] = 100,
        fast_transition_threshold: float = 0.5,
        fast_transition_window: int = 5,
        state_manager: Optional[Any] = None,
        enable_state_manager: bool = False,
        migrate_from_file: bool = False
    ):
        """
        Initialize the state transition tracker.
        
        Args:
            state_file_path: Path to persist state information (legacy)
            enable_pearl_logging: Whether to enable Pearl logging integration
            max_history_size: Maximum number of transitions to keep in history
            fast_transition_threshold: Seconds threshold for fast transition detection
            fast_transition_window: Number of recent transitions to check for fast detection
            state_manager: StateManager instance for persistence
            enable_state_manager: Whether to use StateManager for persistence
            migrate_from_file: Whether to migrate from old file-based storage
        """
        self.state_file_path = Path(state_file_path)
        self.enable_pearl_logging = enable_pearl_logging
        self.max_history_size = max_history_size
        self.fast_transition_threshold = fast_transition_threshold
        self.fast_transition_window = fast_transition_window
        self.state_manager = state_manager
        self.enable_state_manager = enable_state_manager
        self.migrate_from_file = migrate_from_file
        
        # Thread safety
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()
        
        # Initialize Pearl logger if enabled
        self.pearl_logger = None
        if enable_pearl_logging:
            try:
                # Try to import Pearl logger setup if available
                from logging_config import setup_pearl_logger
                self.pearl_logger = setup_pearl_logger("state_transition_tracker")
                # Add the log_state_transition method
                self.pearl_logger.log_state_transition = self._log_state_transition_fallback
            except (ImportError, AttributeError):
                # Fall back to standard logging if Pearl logger not available
                self.pearl_logger = logging.getLogger("state_transition_tracker")
                self.pearl_logger.log_state_transition = self._log_state_transition_fallback
        
        # Initialize state (synchronous for backward compatibility)
        if not enable_state_manager:
            self._load_or_initialize_state()
    
    def _log_state_transition_fallback(self, from_state: str, to_state: str, metadata: Dict[str, Any]):
        """Fallback method for logging state transitions when PearlLogger is not available."""
        self.pearl_logger.info(
            f"State transition: {from_state} -> {to_state}",
            extra={"metadata": metadata}
        )
    
    def _load_or_initialize_state(self):
        """Load state from file or initialize with defaults."""
        if self.state_file_path.exists():
            try:
                with open(self.state_file_path, 'r') as f:
                    data = json.load(f)
                
                # Restore state
                self.current_state = AgentState(data["current_state"])
                self.last_transition_time = datetime.fromisoformat(data["last_transition_time"])
                
                # Restore transition history
                self.transition_history: List[StateTransition] = []
                for transition_data in data.get("transition_history", []):
                    transition = StateTransition(
                        from_state=AgentState(transition_data["from_state"]),
                        to_state=AgentState(transition_data["to_state"]),
                        timestamp=datetime.fromisoformat(transition_data["timestamp"]),
                        metadata=transition_data.get("metadata", {})
                    )
                    self.transition_history.append(transition)
            except Exception:
                # If loading fails, initialize defaults
                self._initialize_defaults()
        else:
            self._initialize_defaults()
    
    def _initialize_defaults(self):
        """Initialize tracker with default values."""
        self.current_state = AgentState.IDLE
        self.last_transition_time = datetime.now()
        self.transition_history: List[StateTransition] = []
    
    def record_transition(
        self,
        new_state: AgentState,
        metadata: Optional[Dict[str, Any]] = None,
        validate_transition: bool = False
    ):
        """
        Record a state transition.
        
        Args:
            new_state: The new state to transition to
            metadata: Optional metadata about the transition
            validate_transition: Whether to validate the transition is allowed
        
        Raises:
            ValueError: If validate_transition is True and transition is invalid
        """
        with self._lock:
            # Validate transition if requested
            if validate_transition:
                if self.current_state in self.VALID_TRANSITIONS:
                    allowed_states = self.VALID_TRANSITIONS[self.current_state]
                    if new_state not in allowed_states:
                        raise ValueError(
                            f"Invalid state transition: {self.current_state.value} -> {new_state.value}"
                        )
            
            # Create transition record
            transition = StateTransition(
                from_state=self.current_state,
                to_state=new_state,
                timestamp=datetime.now(),
                metadata=metadata or {}
            )
            
            # Update state
            self.current_state = new_state
            self.last_transition_time = transition.timestamp
            
            # Add to history with size limit
            self.transition_history.append(transition)
            if self.max_history_size and len(self.transition_history) > self.max_history_size:
                self.transition_history = self.transition_history[-self.max_history_size:]
            
            # Log with Pearl if enabled
            if self.pearl_logger:
                self.pearl_logger.log_state_transition(
                    from_state=transition.from_state.value,
                    to_state=transition.to_state.value,
                    metadata=transition.metadata
                )
            
            # Persist state
            self._persist_state()
    
    def _persist_state(self):
        """Persist current state to file (legacy method)."""
        if self.enable_state_manager:
            # Use async method instead
            return
            
        state_data = {
            "current_state": self.current_state.value,
            "last_transition_time": self.last_transition_time.isoformat(),
            "transition_history": [
                {
                    "from_state": t.from_state.value,
                    "to_state": t.to_state.value,
                    "timestamp": t.timestamp.isoformat(),
                    "metadata": t.metadata
                }
                for t in self.transition_history
            ]
        }
        
        with open(self.state_file_path, 'w') as f:
            json.dump(state_data, f, indent=2)
    
    @property
    def seconds_since_last_transition(self) -> float:
        """Get seconds elapsed since the last transition."""
        return (datetime.now() - self.last_transition_time).total_seconds()
    
    def is_transitioning_fast(self) -> bool:
        """
        Check if the agent is transitioning between states too quickly.
        
        Returns:
            True if recent transitions are happening faster than threshold
        """
        if len(self.transition_history) < self.fast_transition_window:
            return False
        
        # Check recent transitions
        recent_transitions = self.transition_history[-self.fast_transition_window:]
        
        for i in range(1, len(recent_transitions)):
            time_diff = (recent_transitions[i].timestamp - recent_transitions[i-1].timestamp).total_seconds()
            if time_diff >= self.fast_transition_threshold:
                return False
        
        return True
    
    def get_recent_transitions(self, seconds: float) -> List[StateTransition]:
        """
        Get transitions that occurred within the specified time window.
        
        Args:
            seconds: Number of seconds to look back
            
        Returns:
            List of recent transitions
        """
        cutoff_time = datetime.now() - timedelta(seconds=seconds)
        return [
            t for t in self.transition_history
            if t.timestamp >= cutoff_time
        ]
    
    def clear_history(self):
        """Clear transition history while preserving current state."""
        with self._lock:
            self.transition_history.clear()
            self._persist_state()
    
    def is_in_error_state(self) -> bool:
        """Check if the tracker is currently in an error state."""
        return self.current_state == AgentState.ERROR
    
    def get_error_count(self) -> int:
        """Get the number of times the agent has entered an error state."""
        return sum(1 for t in self.transition_history if t.to_state == AgentState.ERROR)
    
    def get_state_durations(self) -> Dict[AgentState, float]:
        """
        Calculate how long the agent spent in each state.
        
        Returns:
            Dictionary mapping states to total duration in seconds
        """
        durations: Dict[AgentState, float] = {}
        
        for i in range(len(self.transition_history)):
            transition = self.transition_history[i]
            
            # Calculate duration until next transition
            if i + 1 < len(self.transition_history):
                next_transition = self.transition_history[i + 1]
                duration = (next_transition.timestamp - transition.timestamp).total_seconds()
                
                # Add duration to the state we transitioned TO (not from)
                if transition.to_state in durations:
                    durations[transition.to_state] += duration
                else:
                    durations[transition.to_state] = duration
        
        return durations
    
    def get_transition_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about state transitions.
        
        Returns:
            Dictionary containing transition statistics
        """
        stats = {
            "total_transitions": len(self.transition_history),
            "state_counts": {},
            "transition_pairs": []
        }
        
        # Count occurrences of each state
        state_counts: Dict[AgentState, int] = {}
        transition_pairs: Dict[tuple, int] = {}
        
        for transition in self.transition_history:
            # Count destination states
            if transition.to_state in state_counts:
                state_counts[transition.to_state] += 1
            else:
                state_counts[transition.to_state] = 1
            
            # Count transition pairs
            pair = (transition.from_state, transition.to_state)
            if pair in transition_pairs:
                transition_pairs[pair] += 1
            else:
                transition_pairs[pair] = 1
        
        stats["state_counts"] = state_counts
        stats["transition_pairs"] = list(transition_pairs.keys())
        
        return stats
    
    def transition(self, new_state: AgentState, metadata: Optional[Dict[str, Any]] = None):
        """
        Synchronous wrapper for record_transition for backward compatibility.
        
        This method is provided for backward compatibility with existing code
        that uses the synchronous transition method.
        
        Args:
            new_state: The new state to transition to
            metadata: Optional metadata about the transition
        """
        # For synchronous compatibility, we call the sync version
        self.record_transition(new_state, metadata, validate_transition=False)
        
        # If using state manager, also persist to state manager asynchronously
        if self.enable_state_manager and self.state_manager:
            try:
                # Create a new event loop task to persist state
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Schedule the coroutine as a task
                    asyncio.create_task(self._persist_to_state_manager())
                else:
                    # Run in a new event loop if none is running
                    asyncio.run(self._persist_to_state_manager())
            except Exception:
                # Fallback to file persistence if async fails
                pass
    
    # Async methods for StateManager integration
    
    async def async_initialize(self):
        """
        Asynchronously initialize the tracker with StateManager support.
        
        This method loads existing state from StateManager or migrates
        from file-based storage if requested.
        """
        if not self.enable_state_manager:
            # Use synchronous initialization for backward compatibility
            self._load_or_initialize_state()
            return
        
        # Try to load from StateManager first
        loaded = await self._load_from_state_manager()
        
        if not loaded and self.migrate_from_file and self.state_file_path.exists():
            # Migrate from file-based storage
            await self._migrate_from_file_storage()
        elif not loaded:
            # Initialize with defaults
            self._initialize_defaults()
            await self._persist_to_state_manager()
    
    async def _load_from_state_manager(self) -> bool:
        """
        Load state from StateManager.
        
        Returns:
            True if state was successfully loaded, False otherwise
        """
        try:
            data = await self.state_manager.load_state("agent_state_transitions")
            if data:
                # Restore state
                self.current_state = AgentState(data["current_state"])
                self.last_transition_time = datetime.fromisoformat(data["last_transition_time"])
                
                # Restore transition history
                self.transition_history = []
                for transition_data in data.get("transition_history", []):
                    transition = StateTransition(
                        from_state=AgentState(transition_data["from_state"]),
                        to_state=AgentState(transition_data["to_state"]),
                        timestamp=datetime.fromisoformat(transition_data["timestamp"]),
                        metadata=transition_data.get("metadata", {})
                    )
                    self.transition_history.append(transition)
                
                return True
        except Exception as e:
            if self.pearl_logger:
                self.pearl_logger.error(f"Failed to load state from StateManager: {e}")
        
        return False
    
    async def _migrate_from_file_storage(self):
        """Migrate state from file-based storage to StateManager."""
        try:
            # Load from file
            self._load_or_initialize_state()
            
            # Save to StateManager
            await self._persist_to_state_manager()
            
            # Backup old file
            backup_path = self.state_file_path.with_suffix('.backup')
            self.state_file_path.rename(backup_path)
            
            if self.pearl_logger:
                self.pearl_logger.info(f"Migrated state from {self.state_file_path} to StateManager")
        except Exception as e:
            if self.pearl_logger:
                self.pearl_logger.error(f"Failed to migrate state: {e}")
            self._initialize_defaults()
    
    async def _persist_to_state_manager(self):
        """Persist current state to StateManager."""
        state_data = {
            "current_state": self.current_state.value,
            "last_transition_time": self.last_transition_time.isoformat(),
            "transition_history": [
                {
                    "from_state": t.from_state.value,
                    "to_state": t.to_state.value,
                    "timestamp": t.timestamp.isoformat(),
                    "metadata": t.metadata
                }
                for t in self.transition_history
            ]
        }
        
        try:
            await self.state_manager.save_state("agent_state_transitions", state_data)
        except Exception as e:
            if self.pearl_logger:
                self.pearl_logger.error(f"Failed to persist state to StateManager: {e}")
    
    async def async_record_transition(
        self,
        new_state: AgentState,
        metadata: Optional[Dict[str, Any]] = None,
        validate_transition: bool = False
    ):
        """
        Asynchronously record a state transition.
        
        This method is thread-safe and uses StateManager for persistence
        when enabled.
        
        Args:
            new_state: The new state to transition to
            metadata: Optional metadata about the transition
            validate_transition: Whether to validate the transition is allowed
        
        Raises:
            ValueError: If validate_transition is True and transition is invalid
        """
        async with self._async_lock:
            # Validate transition if requested
            if validate_transition:
                if self.current_state in self.VALID_TRANSITIONS:
                    allowed_states = self.VALID_TRANSITIONS[self.current_state]
                    if new_state not in allowed_states:
                        raise ValueError(
                            f"Invalid state transition: {self.current_state.value} -> {new_state.value}"
                        )
            
            # Create transition record
            transition = StateTransition(
                from_state=self.current_state,
                to_state=new_state,
                timestamp=datetime.now(),
                metadata=metadata or {}
            )
            
            # Update state
            self.current_state = new_state
            self.last_transition_time = transition.timestamp
            
            # Add to history with size limit
            self.transition_history.append(transition)
            if self.max_history_size and len(self.transition_history) > self.max_history_size:
                self.transition_history = self.transition_history[-self.max_history_size:]
            
            # Log with Pearl if enabled
            if self.pearl_logger:
                self.pearl_logger.log_state_transition(
                    from_state=transition.from_state.value,
                    to_state=transition.to_state.value,
                    metadata=transition.metadata
                )
            
            # Persist state
            if self.enable_state_manager:
                await self._persist_to_state_manager()
            else:
                self._persist_state()
    
