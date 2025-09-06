# AGENTS.md - Backend Services

Quick reference for AI agents working with the Quorum AI service layer.

## Core Services

- **snapshot_service.py** - Fetches DAO proposals from Snapshot GraphQL API
- **ai_service.py** - AI-powered proposal analysis and voting decisions
- **agent_run_service.py** - Orchestrates complete voting workflow
- **voting_service.py** - EIP-712 signatures and vote submission
- **state_manager.py** - Atomic state persistence with migrations
- **user_preferences_service.py** - User voting configuration
- **key_manager.py** - Secure key management
- **safe_service.py** - Safe wallet integration

## Commands

```bash
# Run service tests
uv run pytest backend/tests/test_*_service.py -v

# Run with coverage
uv run pytest backend/tests/test_ai_service.py --cov=backend/services

# Lint services
pre-commit run --files backend/services/*.py
```

## Required Patterns

### 1. Service Initialization
```python
class ServiceName:
    def __init__(self, dependency=None):
        self.logger = setup_pearl_logger(__name__)
        assert dependency is not None, "Dependency cannot be None"
        self.client = httpx.AsyncClient(timeout=settings.timeout)
        self.logger.info("ServiceName initialized")
```

### 2. Async Resource Management
```python
async def __aenter__(self):
    return self

async def __aexit__(self, exc_type, exc_val, exc_tb):
    await self.close()

async def close(self):
    if self.client:
        await self.client.aclose()
```

### 3. Error Handling
```python
class ServiceNameError(Exception):
    pass

try:
    result = await operation()
except SpecificError as e:
    self.logger.error("Operation failed, error=%s", str(e))
    raise ServiceNameError(f"Context: {str(e)}") from e
```

### 4. Pearl Logging
```python
with log_span(self.logger, "operation_name", param=value):
    self.logger.info("Starting operation, param=%s", value)
    result = await perform_operation()
    self.logger.info("Completed, result_count=%s", len(result))
```

### 5. Runtime Assertions
```python
def critical_method(self, param: str) -> List[Result]:
    assert param is not None, "Parameter cannot be None"
    assert isinstance(param, str), f"Expected string, got {type(param)}"
    return result
```

## Service Dependencies

```
AgentRunService (orchestrator)
    ├── SnapshotService (data fetching)
    ├── AIService (decisions)
    ├── VotingService (execution)
    ├── UserPreferencesService (config)
    └── StateManager (persistence)
```

## Critical Rules

### DO:
- ✅ Use Pearl-compliant logging from `logging_config.py`
- ✅ Include runtime assertions (minimum 2 per critical method)
- ✅ Implement async resource cleanup
- ✅ Use dependency injection
- ✅ Keep methods under 60 lines
- ✅ Use structured logging with key-value pairs

### DON'T:
- ❌ Use `print()` - use logger instead
- ❌ Catch bare `except:`
- ❌ Create circular dependencies
- ❌ Forget to close async resources
- ❌ Store secrets in code
- ❌ Skip error logging

## Service Notes

**SnapshotService**
- GraphQL client for Snapshot API
- Implements retry logic
- Caches with TTL

**AIService**
- Google Gemini 2.0 Flash via OpenRouter
- Summarization + voting decisions
- JSON audit trail

**AgentRunService**
- Main workflow orchestrator
- State transition tracking
- Comprehensive error handling

**VotingService**
- EIP-712 signature creation
- EOA and Safe wallet support
- Snapshot vote submission

**StateManager**
- Atomic operations
- Migration support
- Checkpoint/rollback

## Common Tasks

### Add New Service
1. Create in `backend/services/`
2. Follow initialization pattern
3. Add async context manager if needed
4. Create test in `backend/tests/`

### Modify Service
1. Check coverage: `uv run pytest test_<service>.py --cov`
2. Follow existing patterns
3. Add runtime assertions
4. Update tests

### Test Service
1. Mock dependencies for unit tests
2. Mark integration tests: `@pytest.mark.integration`
3. Test error paths
4. Test resource cleanup

## Performance Tips

- Use `asyncio.gather()` for parallel ops
- Implement connection pooling
- Cache expensive AI operations
- Batch process when possible

## Debug Commands

```bash
# View logs
tail -f logs/agent_run.log

# Debug mode
DEBUG=true uv run main.py

# Test specific method
uv run python -c "from backend.services.ai_service import AIService; import asyncio; asyncio.run(AIService().test())"
```

## Common Issues

1. **Resource leaks** → Check async context manager
2. **State issues** → Verify atomic operations
3. **API failures** → Check retry logic
4. **No logs** → Ensure Pearl logger setup
5. **Test failures** → Check mock configuration
