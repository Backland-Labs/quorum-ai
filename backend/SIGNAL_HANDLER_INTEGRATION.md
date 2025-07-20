# Signal Handler and State Manager Integration Summary

## Overview
Successfully integrated the Signal Handler and State Manager services into the main Quorum AI application to provide graceful shutdown capabilities and persistent state management.

## Changes Made

### 1. main.py Updates
- Imported `StateManager`, `SignalHandler`, and `ShutdownCoordinator`
- Added global instances for these services
- Modified lifespan context manager to:
  - Initialize StateManager first (as other services depend on it)
  - Pass StateManager to services that need it (AgentRunService, UserPreferencesService)
  - Register signal handlers during startup
  - Register services with ShutdownCoordinator
  - Check for recovery from previous runs
  - Execute graceful shutdown on application exit
  - Clean up StateManager resources

### 2. AgentRunService Updates
- Modified constructor to accept optional `state_manager` parameter
- Added tracking for active runs (`_active_run`, `_current_run_data`)
- Implemented required shutdown protocol methods:
  - `shutdown()`: Saves state during shutdown and closes resources
  - `save_state()`: Persists current service state
  - `stop()`: Gracefully stops the service
- Added checkpoint saving during agent runs
- Save shutdown state if interrupted during active run

### 3. UserPreferencesService Updates
- Modified constructor to accept optional `state_manager` parameter
- Added preferences cache to reduce file I/O
- Updated `load_preferences()` to:
  - Try loading from StateManager first
  - Fall back to file-based loading
  - Migrate file-based preferences to StateManager
- Updated `save_preferences()` to:
  - Save to StateManager when available
  - Maintain file-based storage for backward compatibility
- Implemented shutdown protocol methods:
  - `shutdown()`: Saves cached preferences
  - `save_state()`: Persists current preferences
  - `stop()`: Gracefully stops the service

### 4. VotingService Updates
- Added tracking for active votes (placeholder for future enhancement)
- Implemented shutdown protocol methods:
  - `shutdown()`: Logs any active votes during shutdown
  - `save_state()`: No-op (votes are atomic operations)
  - `stop()`: Clears active vote tracking
  - `get_active_votes()`: Returns list of active votes
  - `complete_vote()`: Placeholder for future implementation
  - `cancel_vote()`: Placeholder for future implementation

### 5. StateManager Updates
- Added shutdown protocol methods:
  - `shutdown()`: Cleans up resources
  - `save_state()`: No-op (StateManager manages others' state)
  - `stop()`: Cleans up resources

## Benefits

1. **Graceful Shutdown**: Application can now handle SIGTERM/SIGINT signals gracefully, saving state before exit
2. **State Persistence**: Services can save and restore state using a centralized state manager
3. **Recovery Support**: Application can detect and recover from previous unexpected shutdowns
4. **Backward Compatibility**: File-based storage is maintained alongside StateManager for smooth migration
5. **Pearl Compliance**: Ready for deployment in Pearl containers with proper lifecycle management

## Testing

Created `test_signal_handling.py` to verify the integration:
```bash
uv run python test_signal_handling.py
# In another terminal: kill -TERM <PID>
```

## Next Steps

1. Add more comprehensive state checkpointing in AgentRunService
2. Implement vote tracking in VotingService for better shutdown coordination
3. Add metrics for shutdown duration and recovery success
4. Consider adding health checks that respect shutdown state