# CLAUDE.md - Test Suite Guidance

This file provides specific guidance for Claude Code when working with the test suite of the Quorum AI application. This complements the main CLAUDE.md file with testing-specific patterns and practices.

## Test Organization and Structure

### Test Naming Conventions
- **Test Files**: Follow pattern `test_*.py` for all test files
- **Test Classes**: Group related tests using descriptive class names with `Test` prefix
  - Example: `TestAIServiceInitialization`, `TestSnapshotServiceProperties`
- **Test Methods**: Use descriptive names that explain what is being tested
  - Format: `test_[component]_[scenario]_[expected_outcome]`
  - Example: `test_agent_run_service_initialization()`, `test_summarize_proposal_success()`

### Directory Structure
```
tests/
├── __init__.py
├── conftest.py                    # Global fixtures and configuration
├── fixtures/                     # Shared test fixtures
│   └── agent_fixtures.py         # Comprehensive agent test data
├── test_*.py                     # Individual test modules
└── ai_test_apis.py              # AI testing utilities
```

### Test Class Organization
- **Initialization Tests**: `TestServiceInitialization` - Test service setup and dependency injection
- **Property Tests**: `TestServiceProperties` - Test service attributes and basic functionality
- **Method Tests**: `TestServiceMethodName` - Test specific method behaviors
- **Integration Tests**: `TestServiceIntegration` - Test service interactions
- **Edge Case Tests**: `TestServiceEdgeCases` - Test boundary conditions and error scenarios

## Fixture Patterns and Test Data Management

### Core Fixtures (conftest.py)
```python
@pytest.fixture
async def async_client():
    """Create an async FastAPI test client with mocked dependencies."""

@pytest.fixture
def ai_service():
    """Create an AIService instance for testing."""

@pytest.fixture  
def sample_proposal():
    """Create a sample proposal with realistic test data."""

@pytest.fixture
def complex_proposal():
    """Create a complex proposal for advanced testing scenarios."""
```

### Agent Test Fixtures (fixtures/agent_fixtures.py)
The `AgentTestFixtures` class provides comprehensive test data generation:

- **Proposals**: `create_sample_proposal()`, `create_sample_proposals_batch()`, `create_edge_case_proposals()`
- **Spaces**: `create_sample_space_details()`
- **Voters**: `create_sample_voters()`
- **AI Responses**: `create_sample_ai_summary_response()`, `create_sample_ai_vote_response()`
- **User Preferences**: `create_user_preferences_variants()`
- **Mock Responses**: `create_mock_agent_responses()`, `generate_mock_tool_responses()`

### Fixture Usage Patterns
```python
# Use fixtures for consistent test data
def test_proposal_processing(sample_proposal):
    # Test with standardized proposal data

# Use agent fixtures for comprehensive scenarios  
def test_agent_voting_decision():
    proposals = AgentTestFixtures.create_sample_proposals_batch(3)
    preferences = AgentTestFixtures.create_user_preferences_variants()[0]
```

## Mocking Strategies for External Services

### Service Mocking Patterns
```python
# Common decorator pattern for service mocking
def mock_all_services(func):
    """Decorator to mock all services for AgentRunService tests."""
    return patch('services.agent_run_service.UserPreferencesService')(
        patch('services.agent_run_service.VotingService')(
            patch('services.agent_run_service.AIService')(
                patch('services.agent_run_service.SnapshotService')(func)
            )
        )
    )

# Use in test classes
class TestAgentRunService:
    @mock_all_services
    def test_service_method(self, mock_snapshot, mock_ai, mock_voting, mock_prefs):
        # Test implementation
```

### External API Mocking
- **Snapshot API**: Use `pytest_httpx.HTTPXMock` for GraphQL endpoint mocking
- **AI Services**: Mock `AIService._generate_proposal_summary()` and related methods
- **Blockchain**: Mock `Web3`, `Safe`, and account interactions

```python
# HTTP mocking example
def test_snapshot_api_call(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="POST",
        url="https://hub.snapshot.org/graphql",
        json={"data": {"proposals": []}}
    )
```

### AsyncMock Usage
Always use `AsyncMock` for async methods to prevent test failures:
```python
# Correct async mocking
service.get_proposal = AsyncMock(return_value=sample_proposal)
service.vote_on_proposal = AsyncMock(return_value=True)

# Set up in conftest.py for global services
main.agent_run_service.get_recent_decisions = AsyncMock()
main.snapshot_service.get_proposal = AsyncMock()
```

## Async Testing Patterns with pytest-asyncio

### Basic Async Test Structure
```python
@pytest.mark.asyncio
async def test_async_service_method(ai_service, sample_proposal):
    """Test async service methods with proper await syntax."""
    result = await ai_service.summarize_proposal(sample_proposal)
    
    assert result is not None
    assert isinstance(result, SummarizeResponse)
```

### Async Service Testing
```python
@pytest.mark.asyncio
async def test_agent_run_complete_workflow():
    """Test complete async workflow with multiple service calls."""
    # Mock all async dependencies
    with patch.object(service, 'fetch_proposals') as mock_fetch:
        mock_fetch.return_value = [sample_proposal]
        
        result = await service.run_agent(request)
        
        assert result.status == "completed"
```

### FastAPI Async Client Testing
```python
@pytest.mark.asyncio
async def test_api_endpoint(async_client):
    """Test API endpoints using async test client."""
    response = await async_client.post(
        "/agent-run",
        json={"space_id": "test.eth", "dry_run": True}
    )
    
    assert response.status_code == 200
```

## Test Coverage Requirements and Focus Areas

### Coverage Targets
- **Overall Coverage**: >90% (configured in pyproject.toml)
- **Critical Services**: 95% coverage required
  - `ai_service.py`
  - `agent_run_service.py` 
  - `snapshot_service.py`
  - `voting_service.py`

### Priority Testing Areas
1. **AI Decision Making**: Test voting decisions, confidence levels, risk assessment
2. **External API Integration**: Snapshot GraphQL queries, error handling
3. **Data Validation**: Pydantic model validation, edge cases
4. **Business Logic**: Proposal filtering, user preferences, voting strategies
5. **Error Scenarios**: Network failures, invalid data, timeout handling

### Coverage Commands
```bash
# Run tests with coverage
uv run pytest --cov=. --cov-report=html

# Check coverage for specific modules
uv run pytest --cov=services.ai_service --cov-report=term-missing
```

## Common Test Utilities and Helpers

### Model Validation Testing
```python
# Use ModelValidationHelper for consistent validation testing
def test_proposal_model_validation():
    with pytest.raises(ValidationError):
        Proposal(id="", title="Invalid")  # Empty ID should fail
```

### Time-Based Testing
```python
# Use fixed timestamps in tests for consistency
current_time = int(time.time())
proposal = AgentTestFixtures.create_sample_proposal(
    start=current_time - 3600,  # Started 1 hour ago
    end=current_time + 3600,    # Ends in 1 hour
)
```

### Mock File Operations
```python
@patch("builtins.open", new_callable=mock_open, read_data="mock_file_content")
def test_file_reading(mock_file):
    """Test file operations with mocked file content."""
    # Test file reading logic
```

## Integration vs Unit Test Approaches

### Unit Tests
- **Focus**: Individual methods and functions in isolation
- **Mocking**: Mock all external dependencies
- **Speed**: Fast execution (< 100ms per test)
- **Examples**: Model validation, utility functions, isolated service methods

```python
class TestAIServiceUnit:
    def test_format_proposal_content(self, ai_service, sample_proposal):
        """Unit test for content formatting logic."""
        content = ai_service._format_proposal_content(sample_proposal)
        assert len(content) > 0
        assert sample_proposal.title in content
```

### Integration Tests
- **Focus**: Service interactions and end-to-end workflows
- **Mocking**: Mock only external APIs, allow internal service communication
- **Speed**: Moderate execution (< 1s per test)  
- **Examples**: Agent run workflows, API endpoint testing

```python
class TestAgentRunIntegration:
    @pytest.mark.asyncio
    async def test_complete_voting_workflow(self):
        """Integration test for complete agent voting workflow."""
        # Test with real service instances, mock external APIs only
```

### Test File Naming
- Unit tests: `test_[service_name].py`
- Integration tests: `test_[service_name]_integration.py` or `test_integration_[workflow].py`
- Pearl logging tests: `test_[service_name]_pearl_logging.py`

## Pearl-Compliant Logging Tests

Many tests include Pearl logging verification:
```python
def test_service_pearl_logging(caplog):
    """Test that service produces Pearl-compliant log entries."""
    with caplog.at_level(logging.INFO):
        result = service.perform_action()
    
    # Verify structured logging format
    assert any("action_type" in record.message for record in caplog.records)
```

## Error Testing Patterns

### Exception Testing
```python
def test_service_handles_network_error():
    """Test service behavior when network errors occur."""
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.side_effect = httpx.NetworkError("Connection failed")
        
        with pytest.raises(SnapshotServiceError):
            await service.fetch_proposals("test.eth")
```

### Validation Error Testing
```python
def test_model_validation_errors():
    """Test that invalid data raises appropriate validation errors."""
    with pytest.raises(ValidationError) as exc_info:
        Proposal(id="test", scores=[-1.0])  # Negative scores invalid
    
    assert "scores" in str(exc_info.value)
```

## Test Execution Guidelines

### Running Tests
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_ai_service.py

# Run with verbose output and coverage
uv run pytest tests/test_ai_service.py -v --cov=services.ai_service

# Run tests matching pattern
uv run pytest -k "test_agent_run" -v
```

### Test Configuration
- Configuration in `pyproject.toml` under `[tool.pytest.ini_options]`
- Strict markers and warnings disabled for cleaner output
- Test discovery in `tests/` directory with `test_*.py` pattern

### Environment Setup
- Environment variables set in `conftest.py` before imports
- Test API keys and mock credentials configured globally
- Services mocked at module level to prevent actual API calls

## Best Practices for AI Assistants

1. **Always Read Tests First**: Understand existing patterns before adding new tests
2. **Use Existing Fixtures**: Leverage `AgentTestFixtures` for comprehensive test data
3. **Mock External Dependencies**: Never make real API calls in tests
4. **Test Edge Cases**: Include boundary conditions and error scenarios
5. **Follow Naming Conventions**: Use descriptive test names that explain intent
6. **Maintain Test Independence**: Each test should run in isolation
7. **Document Complex Logic**: Add docstrings explaining test purpose and importance
8. **Verify Coverage**: Ensure new code is adequately tested (>90% coverage)
9. **Use Appropriate Test Types**: Unit tests for logic, integration tests for workflows
10. **Pearl Compliance**: Include logging verification for service tests