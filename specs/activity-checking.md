# Activity Checking Specification

## Overview

The activity checking system in the Quorum AI agent provides comprehensive monitoring and tracking of agent activities to ensure compliance with OLAS staking requirements and Pearl platform standards. This specification details the implementation, data flows, and integration points for activity monitoring throughout the system.

## Purpose

The activity checking infrastructure serves three primary purposes:

1. **OLAS Compliance**: Ensures the agent meets daily on-chain activity requirements for staking rewards
2. **Pearl Platform Monitoring**: Provides real-time health status and state transition tracking for Pearl observability
3. **Operational Integrity**: Monitors system health, blockchain connectivity, and agent state transitions

## Architecture

### Core Components

#### 1. ActivityService (`backend/services/activity_service.py`)

The ActivityService manages daily activity tracking for OLAS staking compliance.

**Key Responsibilities:**
- Track last activity date and transaction hash
- Determine if daily activity is required
- Persist activity state to local storage
- Provide compliance status reports

**State Management:**
- Persistent storage in `activity_tracker.json`
- Uses Pearl STORE_PATH when available
- Atomic file operations with error recovery

**Key Methods:**
- `is_daily_activity_needed()`: Returns boolean indicating if activity is required today
- `mark_activity_completed(tx_hash)`: Records successful activity with transaction hash
- `get_activity_status()`: Returns current activity state and requirements
- `check_olas_compliance()`: Provides compliance status with required actions

#### 2. HealthStatusService (`backend/services/health_status_service.py`)

Orchestrates comprehensive health monitoring across all system components.

**Health Check Components:**
- **Transaction Manager Health**: Tests blockchain connectivity via SafeService
- **Agent Health**: Evaluates staking compliance and fund availability
- **Rounds Information**: Provides recent state transition history

**Implementation Details:**
- Parallel health checks using `asyncio.gather()`
- 50ms timeout for individual health checks
- Graceful degradation with safe defaults
- Pearl-compliant response formatting

#### 3. StateTransitionTracker (`backend/services/state_transition_tracker.py`)

Monitors and validates agent state transitions during operations.

**State Machine:**
```
IDLE ↔ STARTING → LOADING_PREFERENCES → FETCHING_PROPOSALS → 
FILTERING_PROPOSALS → ANALYZING_PROPOSAL → DECIDING_VOTE → 
SUBMITTING_VOTE → COMPLETED → IDLE
```

**Features:**
- Thread-safe state updates with locking
- Configurable transition history (default: 100 transitions)
- Fast transition detection (threshold: 5 seconds)
- Pearl-compliant logging of all transitions

## Data Flow

### Health Check Request Flow

1. **Request Reception** (`main.py:301`)
   - GET request to `/healthcheck` endpoint
   - Initiates parallel health checks

2. **Data Collection** (`health_status_service.py:70-75`)
   ```python
   tm_health, agent_health, rounds_info = await asyncio.gather(
       self._check_transaction_manager_health(),
       self._check_agent_health(),
       self._get_rounds_info(),
       return_exceptions=True,
   )
   ```

3. **Activity Status Retrieval** (`activity_service.py:156`)
   - Loads current activity state from persistent storage
   - Calculates if daily activity is needed
   - Returns compliance status

4. **Response Aggregation** (`health_status_service.py:86-90`)
   - Combines all health check results
   - Formats Pearl-compliant response
   - Includes AttestationTracker statistics if configured

### Agent Run Activity Flow

1. **State Initialization** (`agent_run_service.py:143`)
   - Transition from IDLE to STARTING
   - Initialize operation metadata

2. **Operation Execution** (`agent_run_service.py:200-255`)
   - Progress through defined state transitions
   - Each state change logged with metadata
   - Automatic error recovery to IDLE state

3. **Activity Completion** (`agent_run_service.py:996-1053`)
   - Create attestation for successful votes
   - No automatic activity registration (simplified from QuorumTracker)
   - Update activity tracker if daily requirement met

## Configuration

### Environment Variables

```bash
# Health Check Configuration
HEALTH_CHECK_ENABLED=true        # Enable/disable health monitoring
HEALTH_CHECK_TIMEOUT=50          # Timeout in milliseconds for health checks
HEALTH_CHECK_PORT=8716           # Port for health check endpoint

# Activity Tracking
ACTIVITY_CHECK_INTERVAL=3600     # Interval in seconds for activity verification
STORE_PATH=/path/to/store        # Pearl storage path for persistent data

# State Transition Monitoring
FAST_TRANSITION_THRESHOLD=5      # Seconds threshold for rapid transition detection
MAX_TRANSITION_HISTORY=100       # Maximum transitions to retain in memory
```

### Pearl Platform Requirements

#### Required Health Response Fields
```json
{
  "is_healthy": true,
  "seconds_since_last_transition": 45,
  "is_transitioning_fast": false,
  "last_transition_from": "idle",
  "last_transition_to": "starting"
}
```

#### Optional Pearl Fields
```json
{
  "is_tm_healthy": true,
  "agent_health": {
    "needs_staking": false,
    "needs_activity": false,
    "last_activity_date": "2025-08-30",
    "has_sufficient_funds": true
  },
  "rounds": [
    {
      "from_state": "idle",
      "to_state": "starting",
      "timestamp": "2025-08-30T10:00:00Z"
    }
  ]
}
```

## Integration Points

### 1. AttestationTracker Integration

When `ATTESTATION_TRACKER_ADDRESS` is configured:
- Health endpoint includes attestation statistics
- Reports multisig wallet activity count
- Provides contract address for verification

### 2. Pearl Logging Standards

All activity-related events follow Pearl logging format:
```
[2025-08-30 10:00:00,000] [INFO] [agent] Activity check completed: daily_activity_needed=false
```

### 3. Safe Service Integration

Activity checking integrates with SafeService for:
- Blockchain connectivity verification
- Transaction submission for activities
- Multisig wallet balance monitoring

## Error Handling

### Graceful Degradation Strategy

1. **Health Check Failures**
   - Individual check failures don't cascade
   - Returns safe defaults for failed components
   - Maintains system availability

2. **Activity State Corruption**
   - Initializes with safe defaults if state file corrupted
   - Logs warnings for debugging
   - Continues operation without historical data

3. **State Transition Validation**
   - Optional validation against defined transitions
   - Logs invalid transitions as warnings
   - Allows operation to continue

### Recovery Mechanisms

1. **Automatic State Recovery**
   - ERROR state automatically transitions to IDLE
   - Prevents stuck states during failures
   - Maintains system responsiveness

2. **Persistent State Rebuilding**
   - Recreates activity state file if missing
   - Uses current date as baseline
   - Ensures continuity of tracking

## Performance Considerations

### Optimization Strategies

1. **Parallel Health Checks**
   - All health checks execute concurrently
   - Maximum 50ms timeout per check
   - Total response time <100ms target

2. **Caching**
   - Activity status cached for check interval
   - State transitions cached in memory
   - Reduces file I/O operations

3. **Thread Safety**
   - Lock-based synchronization for state updates
   - Prevents race conditions in concurrent access
   - Maintains data consistency

### Resource Management

1. **Memory Usage**
   - Limited transition history (100 entries default)
   - Automatic cleanup of old transitions
   - Minimal memory footprint

2. **File Operations**
   - Atomic writes with temporary files
   - Minimized disk I/O frequency
   - Error recovery without data loss

## Testing Strategy

### Unit Tests

1. **ActivityService Tests** (`test_activity_service.py`)
   - Activity requirement calculation
   - State persistence and recovery
   - Compliance status reporting

2. **HealthStatusService Tests** (`test_health_status_service.py`)
   - Parallel health check execution
   - Timeout handling
   - Pearl response formatting

3. **StateTransitionTracker Tests** (`test_state_transition_tracker.py`)
   - State machine validation
   - Fast transition detection
   - Thread safety verification

### Integration Tests

1. **End-to-End Health Check** (`test_healthcheck_endpoint.py`)
   - Full request/response cycle
   - Performance benchmarking
   - Error scenario handling

2. **Agent Run Activity** (`test_agent_run_service.py`)
   - State transition flow
   - Activity completion tracking
   - Error recovery paths

## Future Enhancements

### Planned Improvements

1. **Advanced Analytics**
   - Historical activity trend analysis
   - Predictive maintenance alerts
   - Performance optimization recommendations

2. **Enhanced Monitoring**
   - Real-time activity dashboards
   - Custom alert thresholds
   - Integration with external monitoring systems

3. **Distributed Tracking**
   - Multi-agent activity coordination
   - Cross-system activity correlation
   - Centralized compliance reporting

### Extensibility Points

1. **Custom Activity Types**
   - Plugin architecture for new activity types
   - Configurable activity requirements
   - Dynamic compliance rules

2. **External Integrations**
   - Webhook notifications for activity events
   - Third-party monitoring service integration
   - Custom reporting formats

## Security Considerations

### Data Protection

1. **Activity State Security**
   - Local file storage only
   - No sensitive data in activity records
   - Transaction hashes for verification

2. **Health Endpoint Security**
   - Read-only operations
   - No authentication required (public health status)
   - Rate limiting recommended for production

### Audit Trail

1. **Activity Logging**
   - All activities logged with timestamps
   - Transaction hashes for on-chain verification
   - Pearl-compliant audit trail

2. **State Transition History**
   - Complete transition record maintained
   - Metadata for debugging and analysis
   - Tamper-evident logging

## Conclusion

The activity checking system provides a robust foundation for ensuring OLAS compliance, Pearl platform monitoring, and operational integrity. Through its modular design, graceful error handling, and comprehensive monitoring capabilities, it enables the autonomous agent to maintain reliable operation while meeting all platform requirements.