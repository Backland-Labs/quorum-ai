# Implementation Plan: /agent-run Endpoint

## Overview
This plan outlines the implementation of a new `/agent-run` endpoint that will provide autonomous agent functionality for the Quorum AI application. The endpoint will take a Snapshot space ID, fetch active proposals, read user preferences, make voting decisions, and cast votes automatically.

## Implementation Approach
This implementation follows Test-Driven Development (TDD) principles. Each issue should be implemented by writing tests first, then implementing the functionality to make tests pass.

---

## Issue 1: Create Data Models for Agent Run
**Priority**: High
**Estimated Time**: 2-3 hours
**Dependencies**: None

### Description
Create Pydantic models for the agent run request and response following existing patterns in `models.py`.

### Acceptance Criteria
- [x] `AgentRunRequest` model with validation
- [x] `AgentRunResponse` model with comprehensive status
- [x] `UserPreferences` model for user_preferences.txt
- [x] All models follow existing code style and validation patterns
- [x] Models include proper docstrings and field descriptions

### Implementation Details
```python
class AgentRunRequest(BaseModel):
    space_id: str = Field(..., description="Snapshot space ID to monitor")
    dry_run: bool = Field(default=False, description="If true, simulate without voting")

class AgentRunResponse(BaseModel):
    space_id: str
    proposals_analyzed: int
    votes_cast: List[VoteDecision]
    user_preferences_applied: bool
    execution_time: float
    errors: List[str] = []
    next_check_time: Optional[datetime] = None

class UserPreferences(BaseModel):
    voting_strategy: VotingStrategy = VotingStrategy.BALANCED
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    max_proposals_per_run: int = Field(default=3, ge=1, le=10)
    blacklisted_proposers: List[str] = []
    whitelisted_proposers: List[str] = []
```

### Testing Requirements
- [x] Unit tests for model validation
- [x] Test field constraints and default values
- [x] Test serialization/deserialization
- [x] Test error cases for invalid inputs

**Status: COMPLETED** ✅
- All three models (`AgentRunRequest`, `AgentRunResponse`, `UserPreferences`) have been implemented with comprehensive validation
- Full test coverage with 20 passing tests covering all validation scenarios
- Models follow existing code style and patterns from the codebase
- Proper docstrings and field descriptions included
- Runtime assertions for critical validation points

---

## Issue 2: Implement User Preferences File Management
**Priority**: High
**Estimated Time**: 3-4 hours
**Dependencies**: Issue 1

### Description
Create a service to manage user preferences stored in `user_preferences.txt` file, following the existing file-based persistence patterns.

### Acceptance Criteria
- [x] `UserPreferencesService` class in `services/user_preferences_service.py`
- [x] Read preferences from `user_preferences.txt`
- [x] Write preferences with atomic file operations
- [x] Handle missing file with sensible defaults
- [x] Follow existing error handling patterns
- [x] Proper logging for all operations

### Implementation Details
```python
class UserPreferencesService:
    def __init__(self, preferences_file: str = "user_preferences.txt"):
        self.preferences_file = preferences_file

    async def load_preferences(self) -> UserPreferences:
        """Load user preferences from file, return defaults if not found."""

    async def save_preferences(self, preferences: UserPreferences) -> None:
        """Save preferences to file using atomic write."""

    async def update_preference(self, key: str, value: Any) -> None:
        """Update a single preference value."""
```

### Testing Requirements (TDD)
- [x] Write tests first for all methods
- [x] Test file not found scenario
- [x] Test invalid JSON handling
- [x] Test atomic write operations
- [x] Test concurrent access scenarios
- [x] Mock file system operations

**Status: COMPLETED** ✅
- `UserPreferencesService` class implemented with full file-based persistence
- Atomic write operations using temporary files for data consistency
- Comprehensive error handling with graceful fallbacks to defaults
- Full test coverage with 24 passing tests covering all scenarios
- Proper logging with Logfire integration for all operations
- Thread-safe operations and concurrent access handling
- Robust validation for all preference updates

---

## Issue 3: Create Agent Run Service
**Priority**: High
**Estimated Time**: 4-5 hours
**Dependencies**: Issues 1, 2

### Description
Create the core service that orchestrates the agent run workflow, integrating with existing services.

### Acceptance Criteria
- [x] `AgentRunService` class in `services/agent_run_service.py`
- [x] Fetch top 3 active proposals from Snapshot
- [x] Load and apply user preferences
- [x] Generate voting decisions using AI service
- [x] Execute votes via voting service
- [x] Comprehensive error handling and logging
- [x] Return detailed execution summary

### Implementation Details
```python
class AgentRunService:
    def __init__(self,
                 snapshot_service: SnapshotService,
                 ai_service: AIService,
                 voting_service: VotingService,
                 preferences_service: UserPreferencesService):
        # Initialize dependencies

    async def execute_agent_run(self, request: AgentRunRequest) -> AgentRunResponse:
        """Execute complete agent run workflow."""

    async def _fetch_active_proposals(self, space_id: str, limit: int) -> List[Proposal]:
        """Fetch top active proposals from Snapshot."""

    async def _make_voting_decisions(self, proposals: List[Proposal],
                                   preferences: UserPreferences) -> List[VoteDecision]:
        """Generate voting decisions using AI service."""

    async def _execute_votes(self, decisions: List[VoteDecision],
                           dry_run: bool) -> List[VoteDecision]:
        """Execute votes via voting service."""
```

### Testing Requirements (TDD)
- [x] Write comprehensive unit tests first
- [x] Mock all external service dependencies
- [x] Test each workflow step independently
- [x] Test error scenarios and rollback
- [x] Test dry run mode
- [x] Integration tests with real services (mocked external APIs)

**Status: COMPLETED** ✅
- Complete `AgentRunService` implementation with full async workflow orchestration
- Production-ready service with comprehensive error handling and logging
- Full integration with existing services (SnapshotService, AIService, VotingService, UserPreferencesService)
- Comprehensive test coverage with 20 passing tests covering all functionality
- Proper runtime assertions and validation throughout
- Support for dry run mode and user preference filtering
- Logfire integration for full observability and monitoring

---

## Issue 4: Implement API Endpoint
**Priority**: High
**Estimated Time**: 2-3 hours
**Dependencies**: Issues 1, 2, 3

### Description
Add the `/agent-run` POST endpoint to `main.py` following existing API patterns.

### Acceptance Criteria
- [ ] POST endpoint at `/agent-run`
- [ ] Proper request/response model binding
- [ ] Async implementation
- [ ] Logfire span tracking
- [ ] Comprehensive error handling
- [ ] Proper HTTP status codes
- [ ] OpenAPI documentation

### Implementation Details
```python
@app.post("/agent-run", response_model=AgentRunResponse)
async def agent_run(request: AgentRunRequest) -> AgentRunResponse:
    """Execute autonomous agent voting workflow."""
    with logfire.span("agent_run", space_id=request.space_id):
        try:
            # Initialize services
            # Execute agent run
            # Return response
        except Exception as e:
            logfire.error("Agent run failed", error=str(e))
            raise HTTPException(status_code=500, detail="Agent run failed")
```

### Testing Requirements (TDD)
- Write API tests using TestClient
- Test request/response serialization
- Test error handling and status codes
- Test authentication if required
- Test rate limiting considerations
- Integration tests with full stack

---

## Issue 5: Add Proposal Filtering and Ranking
**Priority**: Medium
**Estimated Time**: 3-4 hours
**Dependencies**: Issue 3

### Description
Enhance the agent run service to intelligently filter and rank proposals based on user preferences and proposal metadata.

### Acceptance Criteria
- [ ] Filter proposals by user whitelist/blacklist
- [ ] Rank proposals by urgency (time until deadline)
- [ ] Consider proposal voting power requirements
- [ ] Skip proposals below confidence threshold
- [ ] Implement proposal scoring algorithm
- [ ] Add proposal filtering metrics to response

### Implementation Details
```python
class ProposalFilter:
    def __init__(self, preferences: UserPreferences):
        self.preferences = preferences

    def filter_proposals(self, proposals: List[Proposal]) -> List[Proposal]:
        """Filter proposals based on user preferences."""

    def rank_proposals(self, proposals: List[Proposal]) -> List[Proposal]:
        """Rank proposals by importance and urgency."""

    def calculate_proposal_score(self, proposal: Proposal) -> float:
        """Calculate proposal priority score."""
```

### Testing Requirements (TDD)
- Test filtering logic with various preferences
- Test ranking algorithm with different scenarios
- Test edge cases (empty lists, tied scores)
- Test performance with large proposal lists

---

## Issue 6: Add Comprehensive Logging and Monitoring
**Priority**: Medium
**Estimated Time**: 2-3 hours
**Dependencies**: Issues 1-4

### Description
Implement detailed logging and monitoring for the agent run functionality.

### Acceptance Criteria
- [ ] Structured logging for all agent decisions
- [ ] Logfire spans for performance monitoring
- [ ] Audit trail for all votes cast
- [ ] Error categorization and reporting
- [ ] Performance metrics collection
- [ ] Security event logging (never log private keys)

### Implementation Details
```python
class AgentRunLogger:
    def log_agent_start(self, space_id: str, preferences: UserPreferences):
        """Log agent run initiation."""

    def log_proposal_analysis(self, proposal: Proposal, decision: VoteDecision):
        """Log individual proposal analysis."""

    def log_vote_execution(self, decision: VoteDecision, success: bool):
        """Log vote execution result."""

    def log_agent_completion(self, summary: AgentRunResponse):
        """Log agent run completion summary."""
```

### Testing Requirements (TDD)
- Test logging output format and content
- Test that sensitive data is never logged
- Test log levels and filtering
- Test performance impact of logging

---

## Issue 7: Add Configuration Management
**Priority**: Medium
**Estimated Time**: 2-3 hours
**Dependencies**: Issue 2

### Description
Extend the configuration system to support agent run settings.

### Acceptance Criteria
- [ ] Add agent run configuration to `config.py`
- [ ] Environment variable support for key settings
- [ ] Configuration validation
- [ ] Default configuration values
- [ ] Configuration hot-reloading support

### Implementation Details
```python
class AgentRunConfig:
    max_proposals_per_run: int = 3
    default_confidence_threshold: float = 0.7
    proposal_fetch_timeout: int = 30
    vote_execution_timeout: int = 60
    max_retry_attempts: int = 3
    retry_delay_seconds: int = 5
```

### Testing Requirements (TDD)
- Test configuration loading from environment
- Test configuration validation
- Test default value handling
- Test configuration error cases

---

## Issue 8: Implement Rate Limiting and Throttling
**Priority**: Low
**Estimated Time**: 2-3 hours
**Dependencies**: Issue 4

### Description
Add rate limiting to prevent abuse of the agent run endpoint.

### Acceptance Criteria
- [ ] Rate limiting per IP address
- [ ] Rate limiting per authenticated user
- [ ] Configurable rate limits
- [ ] Proper HTTP response codes (429)
- [ ] Rate limit headers in responses
- [ ] Integration with existing middleware

### Testing Requirements (TDD)
- Test rate limiting enforcement
- Test rate limit reset behavior
- Test bypass for admin users
- Test rate limit configuration

---

## Issue 9: Add Health Checks and Metrics
**Priority**: Low
**Estimated Time**: 1-2 hours
**Dependencies**: Issue 6

### Description
Extend health check endpoint to include agent run system status.

### Acceptance Criteria
- [ ] Agent run service health check
- [ ] User preferences file accessibility check
- [ ] External service connectivity check
- [ ] Performance metrics endpoint
- [ ] System resource usage monitoring

### Testing Requirements (TDD)
- Test health check responses
- Test failure detection
- Test metrics collection accuracy

---

## Issue 10: Create Integration Tests
**Priority**: Medium
**Estimated Time**: 3-4 hours
**Dependencies**: All previous issues

### Description
Create comprehensive integration tests for the complete agent run workflow.

### Acceptance Criteria
- [ ] End-to-end test with test Snapshot space
- [ ] Test complete workflow from API to vote execution
- [ ] Test error recovery and rollback
- [ ] Test with various user preference configurations
- [ ] Load testing for performance validation
- [ ] Container deployment testing

### Testing Requirements (TDD)
- Full integration test suite
- Performance benchmarks
- Failure scenario testing
- Mock external service integration
- Container environment testing

---

## Implementation Order
1. **Phase 1 (Core)**: Issues 1-4 (Essential functionality)
2. **Phase 2 (Enhancement)**: Issues 5-7 (Improved functionality)
3. **Phase 3 (Production)**: Issues 8-10 (Production readiness)

## Dependencies Summary
- External: Snapshot GraphQL API, AI Service (OpenRouter)
- Internal: Existing services (SnapshotService, AIService, VotingService)
- Infrastructure: File system access, logging system

## Risk Mitigation
- **API Rate Limits**: Implement exponential backoff and caching
- **Service Failures**: Comprehensive error handling and retry logic
- **Data Persistence**: Atomic file operations and backup strategies
- **Security**: Input validation and secure credential handling
- **Performance**: Async operations and resource monitoring

## Success Metrics
- Agent run completion rate > 95%
- Average execution time < 30 seconds
- Zero security incidents
- Test coverage > 90%
- API response time < 2 seconds
