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