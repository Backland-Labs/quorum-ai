# Lessons Learned

## AI Service Enum Serialization Issue (September 2025)

### Problem Description

The proposal summarization endpoint (`/proposals/summarize`) was failing with the error:
```
AssertionError: AI result must be a dictionary
```

### Root Cause Analysis

The issue occurred in `ai_service.py` at line 1339 in the `_call_ai_model_for_summary` method. The AI service was returning a valid `ProposalSummary` Pydantic model, but when using `model_dump()` to convert it to a dictionary, the `RiskLevel` enum was not being properly serialized.

**Debug output revealed:**
- `result.output` was correctly typed as `ProposalSummary`
- `hasattr(result.output, 'model_dump')` returned `True`
- `processed_result` after `model_dump()` was a dict, BUT
- The `risk_assessment` field contained `<RiskLevel.LOW: 'LOW'>` (enum object) instead of `"LOW"` (string)

### The Fix

Changed the model serialization from:
```python
processed_result = (
    result.output.model_dump()
    if hasattr(result.output, "model_dump")
    else result.output
)
```

To:
```python
processed_result = (
    result.output.model_dump(mode='json')
    if hasattr(result.output, "model_dump")
    else result.output
)
```

### Why This Fixed It

The `mode='json'` parameter in Pydantic's `model_dump()` method forces proper JSON serialization of all field types, including enums. Without this parameter, enum values remain as enum objects rather than being converted to their string representations.

The `RiskLevel` enum is properly defined as:
```python
class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
```

But `model_dump()` without the `mode='json'` parameter doesn't automatically serialize enums to their string values.

### Key Learnings

1. **Always use `model_dump(mode='json')`** when converting Pydantic models to dictionaries for JSON serialization, especially when the model contains enums.

2. **Debug enum serialization issues** by checking if enum objects are appearing in the output instead of their string values.

3. **Test endpoint responses thoroughly** - the assertion error was masking the actual enum serialization issue.

4. **Pydantic enum handling** - Even when enums inherit from `str, Enum`, the default `model_dump()` behavior may not serialize them as expected for JSON APIs.

### Files Changed

- `backend/services/ai_service.py` - Line 1334: Added `mode='json'` parameter to `model_dump()` call

### Testing Verification

After the fix, the `/proposals/summarize` endpoint returned properly formatted JSON:
```json
{
  "summaries": [{
    "proposal_id": "0x...",
    "title": "test25090104",
    "summary": "...",
    "key_points": [...],
    "risk_assessment": "LOW",  // Now a string, not an enum object
    "recommendation": "...",
    "confidence": 0.85
  }],
  "processing_time": 2.996,
  "model_used": "openai:gpt-4o-mini"
}
```

### Prevention

- Add unit tests that verify enum serialization in API responses
- Consider using Pydantic's JSON schema validation in tests
- Document the requirement to use `mode='json'` for API serialization throughout the codebase

## AI Service Dependency Injection Issue (January 2025)

### Problem Description

The agent-run endpoint was failing with a 401 "User not found" error when making voting decisions, even after successfully setting the OpenRouter API key via the `/config/openrouter-key` endpoint.

**Error observed:**
```
Failed to make voting decisions: status_code: 401, model_name: google/gemini-2.0-flash-001, body: {'message': 'User not found.', 'code': 401}
```

### Root Cause Analysis

The issue was in the service dependency injection pattern:

1. **Global AIService in main.py**: The `ai_service` global instance was correctly receiving the API key via `swap_api_key()` and initializing its voting agents properly.

2. **AgentRunService creating its own instance**: The `AgentRunService` was creating its own `AIService` instance in its constructor instead of using the shared global instance:
   ```python
   # In AgentRunService.__init__()
   self.ai_service = AIService()  # Creates new instance without API key
   ```

3. **API key isolation**: When the `/config/openrouter-key` endpoint called `ai_service.swap_api_key()`, it only updated the global instance, not the instance inside `AgentRunService`.

### The Fix

**Step 1:** Modified `AgentRunService.__init__()` to accept dependency injection:
```python
def __init__(self, state_manager=None, ai_service=None) -> None:
    """Initialize AgentRunService with required dependencies.

    Args:
        state_manager: Optional StateManager instance for state persistence  
        ai_service: Optional AIService instance for shared configuration
    """
    self.snapshot_service = SnapshotService()
    self.ai_service = ai_service or AIService()  # Use injected or create new
    # ... rest of initialization
```

**Step 2:** Updated `main.py` to pass the shared instance:
```python
# Initialize services with state manager where needed
ai_service = AIService()
agent_run_service = AgentRunService(state_manager=state_manager, ai_service=ai_service)
```

### Why This Fixed It

- The `AgentRunService` now uses the same `AIService` instance that receives API key updates
- When `swap_api_key()` is called on the global instance, the voting agents are properly initialized with the new API key
- The agent-run workflow uses the correctly configured AI service for making voting decisions

### Key Learnings

1. **Use dependency injection over service creation** - Services should accept dependencies as parameters rather than creating their own instances, especially for shared state like API keys.

2. **Shared configuration must be truly shared** - When services need to share configuration (like API keys), they must use the same instance, not separate instances.

3. **Test service integration points** - Integration tests should verify that configuration changes (like API key updates) propagate correctly to all dependent services.

4. **Debug by tracing service instances** - When debugging service configuration issues, trace whether different parts of the application are using the same or different service instances.

### Files Changed

- `backend/services/agent_run_service.py` - Added `ai_service` parameter to `__init__()`
- `backend/main.py` - Updated `AgentRunService` initialization to pass shared `ai_service` instance

### Testing Verification

After the fix, the agent-run endpoint successfully:
- Analyzed 2 proposals from sharingblock.eth
- Made voting decisions using the authenticated Gemini model
- Generated detailed reasoning and confidence scores
- Completed execution in 3.7 seconds with no errors

### Prevention

- Use dependency injection patterns consistently across all services
- Document shared service instances and their configuration requirements  
- Add integration tests that verify configuration propagation across service boundaries
- Consider using a proper dependency injection container for complex service graphs