# CLAUDE.md - Service Layer Guidance

This file provides specific guidance for working with the service layer of the Quorum AI autonomous voting application. These services implement the core business logic for DAO proposal analysis, AI-powered decision making, and vote execution.

## Service Architecture Overview

The service layer follows a **service-oriented architecture** with clear separation of concerns:

- **Data Services**: `snapshot_service.py`, `safe_service.py` - External API integrations
- **AI Services**: `ai_service.py` - AI-powered proposal analysis and autonomous voting
- **Orchestration Services**: `agent_run_service.py` - Coordinates the complete voting workflow
- **Voting Services**: `voting_service.py`, `voter.py`, `voter_olas.py` - Vote execution and submission
- **State Services**: `state_manager.py`, `user_preferences_service.py` - Data persistence and configuration
- **Utility Services**: `proposal_filter.py`, `key_manager.py`, `signal_handler.py` - Supporting functionality

## Core Service Patterns

### 1. Service Initialization Pattern
All services follow a consistent initialization pattern:

```python
class ServiceName:
    def __init__(self, dependency_injection_params=None):
        # Initialize Pearl-compliant logger
        self.logger = setup_pearl_logger(__name__)

        # Initialize dependencies with runtime assertions
        assert dependency is not None, "Dependency cannot be None"

        # Set up async client resources if needed
        self.client = httpx.AsyncClient(timeout=settings.timeout)

        self.logger.info("ServiceName initialized")
```

**Key Points:**
- Use Pearl-compliant logging from `logging_config.py`
- Include runtime assertions for critical dependencies
- Initialize async resources properly
- Log initialization completion

### 2. Async Context Manager Pattern
Services that manage async resources implement the async context manager protocol:

```python
async def __aenter__(self) -> "ServiceName":
    return self

async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
    await self.close()

async def close(self) -> None:
    if self.client:
        await self.client.aclose()
```

**Example:** `SnapshotService` manages HTTP client resources

### 3. Error Handling Pattern
Services define custom exception hierarchies and use comprehensive error handling:

```python
# Custom exceptions for better error handling
class ServiceNameError(Exception):
    """Base exception for ServiceName errors."""
    pass

class NetworkError(ServiceNameError):
    """Raised when network operations fail."""
    pass

# Error handling with logging
try:
    result = await some_operation()
except SpecificException as e:
    self.logger.error("Operation failed, error=%s", str(e))
    raise ServiceSpecificError(f"Detailed error context: {str(e)}") from e
```

**Key Services with Custom Exceptions:**
- `SnapshotService`: `SnapshotServiceError`, `NetworkError`, `GraphQLError`
- `AgentRunService`: `ProposalFetchError`, `VotingDecisionError`, `VoteExecutionError`
- `AIService`: `DecisionFileError`

### 4. Logging and Observability Pattern
All services use Pearl-compliant logging with structured metadata:

```python
with log_span(self.logger, "operation_name", param1=value1, param2=value2):
    self.logger.info(
        "Operation started, param1=%s, param2=%s",
        value1, value2
    )

    result = await perform_operation()

    self.logger.info(
        "Operation completed successfully, result_count=%s",
        len(result)
    )
```

**Logging Standards:**
- Use structured logging with key-value pairs
- Include operation context in log messages
- Log both success and failure cases
- Use `log_span` for operation tracing

### 5. Runtime Assertions Pattern
Critical methods include runtime assertions for validation:

```python
def critical_method(self, input_param: str) -> List[Result]:
    # Runtime assertions for critical method validation
    assert input_param is not None, "Input parameter cannot be None"
    assert isinstance(input_param, str), f"Expected string, got {type(input_param)}"
    assert input_param.strip(), "Input parameter must be non-empty string"

    # Perform operation...

    # Validate output
    assert isinstance(result, list), f"Expected list result, got {type(result)}"
    assert all(isinstance(r, Result) for r in result), "All items must be Result objects"

    return result
```

## Service Dependencies and Integrations

### Core Dependencies

**SnapshotService** (`snapshot_service.py`)
- **Purpose**: Fetches DAO proposal data from Snapshot GraphQL API
- **Dependencies**: `httpx`, `config.settings`, `models`
- **Key Methods**: `get_proposals()`, `get_proposal()`, `get_votes()`
- **Integration Point**: Used by `AIService` and `AgentRunService`

**AIService** (`ai_service.py`)
- **Purpose**: AI-powered proposal analysis and autonomous voting decisions
- **Dependencies**: `pydantic_ai`, `OpenRouterProvider`, `SnapshotService`
- **Key Methods**: `decide_vote()`, `summarize_proposal()`
- **Integration Point**: Core decision engine used by `AgentRunService`

**VotingService** (`voting_service.py`)
- **Purpose**: EIP-712 signature creation and vote submission to Snapshot
- **Dependencies**: `web3`, `eth_account`, `KeyManager`
- **Key Methods**: `vote_on_proposal()`, `create_snapshot_vote_message()`
- **Integration Point**: Vote execution endpoint used by `AgentRunService`

**AgentRunService** (`agent_run_service.py`)
- **Purpose**: Orchestrates complete autonomous voting workflow
- **Dependencies**: All above services plus state management
- **Key Methods**: `execute_agent_run()`
- **Integration Point**: Main orchestration service called by API endpoints

### State Management Dependencies

**StateManager** (`state_manager.py`)
- **Purpose**: Atomic state persistence with migration support
- **Dependencies**: Standard library only
- **Key Methods**: `save_state()`, `load_state()`, `save_checkpoint()`
- **Integration Point**: Used by multiple services for persistence

**UserPreferencesService** (`user_preferences_service.py`)
- **Purpose**: User voting configuration management
- **Dependencies**: `StateManager`, `models.UserPreferences`
- **Key Methods**: `load_preferences()`, `save_preferences()`
- **Integration Point**: Configuration provider for `AgentRunService`

## Service Interaction Patterns

### 1. Orchestration Pattern (AgentRunService)
The agent run service orchestrates multiple services in a specific workflow:

```python
async def execute_agent_run(self, request: AgentRunRequest) -> AgentRunResponse:
    # Step 1: Load configuration
    user_preferences = await self.user_preferences_service.load_preferences()

    # Step 2: Fetch and filter data
    proposals = await self.snapshot_service.get_proposals(space_ids=[request.space_id])
    filtered_proposals = await self._filter_and_rank_proposals(proposals, user_preferences)

    # Step 3: Make AI decisions
    decisions = await self._make_voting_decisions(filtered_proposals, user_preferences)

    # Step 4: Execute votes
    final_decisions = await self._execute_votes(decisions, request.space_id, request.dry_run)

    return AgentRunResponse(...)
```

### 2. Dependency Injection Pattern
Services are injected as dependencies rather than created internally:

```python
# Good: Dependency injection allows testing and flexibility
class AgentRunService:
    def __init__(self, state_manager=None, ai_service=None):
        self.ai_service = ai_service or AIService()
        self.state_manager = state_manager

# Avoid: Hard dependencies make testing difficult
class BadService:
    def __init__(self):
        self.ai_service = AIService()  # Hard dependency
```

### 3. State Transition Tracking Pattern
Complex operations use state transition tracking for observability:

```python
# Track state transitions during long operations
self.state_tracker.transition(AgentState.STARTING, {"run_id": run_id})
self.state_tracker.transition(AgentState.FETCHING_PROPOSALS, {"spaces": [space_id]})
self.state_tracker.transition(AgentState.ANALYZING_PROPOSAL, {"proposal_id": proposal.id})
```

## Testing Approaches for Services

### 1. Unit Testing with Mocks
Test individual services in isolation using mocks for external dependencies:

```python
@pytest.mark.asyncio
async def test_snapshot_service_get_proposals():
    # Create mock HTTP client
    mock_client = Mock()
    mock_response = Mock()
    mock_response.json.return_value = {"data": {"proposals": []}}
    mock_client.post.return_value = mock_response

    # Test with mocked dependency
    service = SnapshotService()
    service.client = mock_client

    result = await service.get_proposals(["test-space"])
    assert isinstance(result, list)
```

### 2. Integration Testing with Real Dependencies
Test service interactions with external APIs using test configurations:

```python
@pytest.mark.integration
async def test_ai_service_integration():
    # Use test API keys and test data
    ai_service = AIService()
    test_proposal = create_test_proposal()

    # Test real AI service integration
    decision = await ai_service.decide_vote(test_proposal)
    assert isinstance(decision, VoteDecision)
    assert decision.confidence >= 0.0
```

### 3. Service Orchestration Testing
Test complex workflows using service mocks:

```python
@pytest.mark.asyncio
async def test_agent_run_orchestration():
    # Mock all service dependencies
    mock_snapshot = Mock()
    mock_ai = Mock()
    mock_voting = Mock()

    # Configure mocks to return expected values
    mock_snapshot.get_proposals.return_value = [test_proposal]
    mock_ai.decide_vote.return_value = test_decision
    mock_voting.vote_on_proposal.return_value = {"success": True}

    # Test orchestration logic
    service = AgentRunService()
    service.snapshot_service = mock_snapshot
    service.ai_service = mock_ai
    service.voting_service = mock_voting

    result = await service.execute_agent_run(test_request)
    assert result.success
```

## Common Pitfalls to Avoid

### 1. Resource Management
**Problem**: Forgetting to close async HTTP clients
```python
# Bad: Resource leak
class BadService:
    def __init__(self):
        self.client = httpx.AsyncClient()
    # Missing close() method

# Good: Proper resource management
class GoodService:
    def __init__(self):
        self.client = httpx.AsyncClient()

    async def close(self):
        await self.client.aclose()
```

### 2. Error Handling
**Problem**: Catching exceptions too broadly and losing context
```python
# Bad: Loses error context
try:
    result = await external_service.call()
except Exception:
    return None  # Silent failure, no logging

# Good: Specific error handling with context
try:
    result = await external_service.call()
except SpecificServiceError as e:
    self.logger.error("External service failed, error=%s", str(e))
    raise ServiceError(f"Operation failed: {str(e)}") from e
```

### 3. State Consistency
**Problem**: Not using atomic operations for state updates
```python
# Bad: Non-atomic state update
def bad_update_state(self, data):
    self.save_partial_state(data.part1)  # Can fail here
    self.save_partial_state(data.part2)  # Leaving inconsistent state

# Good: Atomic state operations
async def good_update_state(self, data):
    async with self.state_manager.transaction():
        await self.state_manager.save_state("complete_state", data)
```

### 4. Logging Antipatterns
**Problem**: Inconsistent or insufficient logging
```python
# Bad: Inconsistent logging
def bad_method(self):
    print(f"Starting operation")  # Wrong logging method
    result = do_work()
    # Missing success/failure logging

# Good: Structured Pearl-compliant logging
def good_method(self):
    self.logger.info("Operation started, param=%s", param_value)
    try:
        result = do_work()
        self.logger.info("Operation completed, result_count=%s", len(result))
        return result
    except Exception as e:
        self.logger.error("Operation failed, error=%s", str(e))
        raise
```

### 5. Dependency Management
**Problem**: Circular dependencies between services
```python
# Bad: Circular dependency
class ServiceA:
    def __init__(self):
        self.service_b = ServiceB()  # ServiceB also imports ServiceA

# Good: Use dependency injection or event patterns
class ServiceA:
    def __init__(self, service_b=None):
        self.service_b = service_b  # Injected dependency
```

## Service Configuration Standards

### Environment Variables
Services should use centralized configuration from `config.py`:
- Use `settings.service_specific_config` rather than direct `os.getenv()`
- Provide sensible defaults for optional configuration
- Validate required configuration at service initialization

### Timeouts and Retries
- **HTTP Services**: Use configured timeouts from `settings.request_timeout`
- **AI Services**: Implement exponential backoff for rate limiting
- **Database Services**: Use connection pooling and retry logic

### Security Considerations
- **Key Management**: Use `KeyManager` service for sensitive data
- **API Keys**: Store in environment variables, never commit to code
- **State Persistence**: Mark sensitive data appropriately in `StateManager`

## Performance Optimization

### Async Patterns
- Use `asyncio.gather()` for concurrent operations when possible
- Implement proper connection pooling for external APIs
- Use async context managers for resource cleanup

### Caching Strategies
- **AI Service**: Consider caching expensive AI operations by proposal hash
- **Snapshot Service**: Cache proposal data with appropriate TTL
- **State Manager**: Use in-memory caching for frequently accessed data

### Batch Processing
- **AI Service**: Process multiple proposals concurrently with `summarize_multiple_proposals()`
- **Voting Service**: Batch vote submissions where possible
- **State Management**: Use batch operations for multiple state updates

This service layer implements the core autonomous voting logic with proper separation of concerns, comprehensive error handling, and robust observability. Always prioritize code clarity and maintainability when extending or modifying these services.
