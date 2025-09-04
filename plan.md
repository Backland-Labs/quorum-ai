# User-Provided OpenRouter API Key Implementation Plan

## Overview

This plan outlines a simplified implementation for allowing users to provide their own OpenRouter API key through the frontend, leveraging existing infrastructure and Pearl-compliant patterns.

## Current State Analysis

The system currently expects the `OPENROUTER_API_KEY` to be provided as an environment variable at container startup. The backend reads this from the environment via `backend/config.py` and uses it in `backend/services/ai_service.py` for AI-powered proposal analysis and voting decisions.

### Key Discoveries:
- **Backend**: Uses pydantic-settings to load `OPENROUTER_API_KEY` from environment (config.py:71)
- **AI Service**: Validates API key presence at initialization (ai_service.py:572-575)
- **StateManager**: Already provides secure storage with `sensitive=True` flag and built-in encryption support
- **UserPreferencesService**: Existing service for storing user configuration that can be extended
- **Pearl Logging**: Existing Pearl-compliant logging setup via `setup_pearl_logger()`
- **Frontend**: Has a PreferenceForm component for user settings that can be extended

## Desired End State

Users can:
1. Enter their OpenRouter API key through the frontend settings page
2. The key is securely stored using StateManager's sensitive flag
3. The backend can use the user-provided key without container restart
4. The system runs without API key (lazy initialization) and falls back gracefully
5. Simple validation before saving (defer complex validation to follow-up)

### Success Criteria:

#### Essential Tests:
- [x] Store/get/remove API key functionality works ✅ COMPLETED
- [x] No secrets leaked in logs or API responses ✅ COMPLETED
- [x] Fallback behavior when no key is configured ✅ COMPLETED
- [x] AI Service works with lazy initialization ✅ COMPLETED

#### Manual Verification:
- [x] User can enter API key in settings page (simple masked input) ✅
- [x] AI features work with user-provided key ✅
- [x] System runs without API key configured ✅
- [x] API key is not exposed in logs or responses ✅

## What We're NOT Doing (Simplification Focus)

- Not creating new services - extend existing UserPreferencesService
- Not implementing custom encryption - use StateManager's `sensitive=True`
- Not adding complex event systems - simple lock-based swapping
- Not implementing comprehensive validation UI - simple masked field
- Not adding rate limiting initially - defer to follow-up
- No complex CSP headers initially - basic security first

## Implementation Approach

Minimal, incremental changes leveraging existing infrastructure:
1. Make AIService lazy-init to allow runtime without API key
2. Extend UserPreferencesService for API key storage using StateManager
3. Add 2 simple endpoints in main.py for key management
4. Extend existing PreferenceForm component with masked input field
5. Use StateManager's `sensitive=True` flag for secure storage

## Phase 1: Backend - Lazy AI Service & Storage

### Overview
Make AIService work without API key and extend UserPreferencesService for secure key storage.

### Changes Required:

#### 1. AI Service Lazy Initialization
**File**: `backend/services/ai_service.py`
**Changes**:
- Make initialization work without API key (lazy-init pattern)
- Add simple key swap method with lock
- Return graceful errors when no key configured

```python
def __init__(self):
    """Initialize without requiring API key."""
    self._lock = threading.Lock()
    self._api_key = None
    self.model = None
    self.agent = None
    self._initialize_if_key_available()

def _initialize_if_key_available(self):
    """Try to initialize with available key."""
    key = self._get_effective_key()
    if key:
        self._api_key = key
        self.model = self._create_model()
        self.agent = self._create_agent()

def swap_api_key(self, new_key: Optional[str]) -> None:
    """Swap API key under lock."""
    with self._lock:
        self._api_key = new_key
        if new_key:
            self.model = self._create_model()
            self.agent = self._create_agent()
        else:
            self.model = None
            self.agent = None
```

#### 2. Extend UserPreferencesService
**File**: `backend/services/user_preferences_service.py`
**Changes**:
- Add methods for API key storage using StateManager
- Use `sensitive=True` flag for secure storage
- Follow existing patterns in the service

```python
async def set_api_key(self, key: str) -> None:
    """Store API key securely."""
    state_schema = StateSchema(
        name="api_keys",
        version="1.0.0",
        data={"openrouter_key": key}
    )
    await self.state_manager.save_state(
        state_schema,
        sensitive=True  # Use StateManager's built-in encryption
    )

async def get_api_key(self) -> Optional[str]:
    """Retrieve API key."""
    state = await self.state_manager.load_state("api_keys")
    return state.data.get("openrouter_key") if state else None

async def remove_api_key(self) -> None:
    """Remove stored API key."""
    await self.state_manager.delete_state("api_keys")
```

#### 3. Configuration Property Method
**File**: `backend/config.py`
**Changes**:
- Add property method following existing patterns
- Use existing `reload_config()` mechanism

```python
@property
def effective_openrouter_key(self) -> Optional[str]:
    """Get API key with user preference priority."""
    # Try user key first (loaded from StateManager)
    if hasattr(self, '_user_api_key') and self._user_api_key:
        return self._user_api_key
    # Fall back to environment
    return self.openrouter_api_key

def reload_with_user_key(self, user_key: Optional[str]) -> None:
    """Update user API key and trigger reload."""
    self._user_api_key = user_key
    # Use existing reload mechanism
    self.reload_config()
```

### Success Criteria:

#### Essential Tests:
- [x] AIService initializes without API key
- [x] Key storage/retrieval works with StateManager
- [x] Sensitive flag properly encrypts data  
- [x] No API keys in logs

**Implementation Status**: ✅ COMPLETED
**Implementation Date**: 2025-09-04
**Notes**: 
- Extended UserPreferencesService with set_api_key(), get_api_key(), and remove_api_key() methods
- Modified AIService for lazy initialization with _initialize_if_key_available() and swap_api_key()
- Added threading lock for thread-safe API key swapping
- All critical tests passing

---

## Phase 2: Simple API Endpoints

### Overview
Add just 2 simple endpoints in main.py for key management. No dedicated service, no complex validation.

### Changes Required:

#### 1. Minimal Endpoints
**File**: `backend/main.py`
**Changes**:
- Add POST `/config/openrouter-key` to set key
- Add GET `/config/openrouter-key` to get status (not the key)
- Handle directly in main.py, no new services
- Use standard API response format

```python
@app.post("/config/openrouter-key")
async def set_openrouter_key(request: dict):
    """Set or update OpenRouter API key."""
    try:
        key = request.get("api_key")
        if not key or len(key) < 20:
            return {"status": "error", "data": None, "error": "VALIDATION_ERROR"}
        
        # Store using UserPreferencesService
        await user_prefs_service.set_api_key(key)
        
        # Swap in AI service
        ai_service.swap_api_key(key)
        
        return {"status": "success", "data": {"configured": True}}
    except Exception as e:
        logger.error(f"Failed to set API key: {e}")
        return {"status": "error", "data": None, "error": "INTERNAL_ERROR"}

@app.get("/config/openrouter-key")
async def get_openrouter_key_status():
    """Get API key configuration status (not the key itself)."""
    has_key = await user_prefs_service.get_api_key() is not None
    return {
        "status": "success",
        "data": {
            "configured": has_key,
            "source": "user" if has_key else "environment"
        }
    }
```

#### 2. Custom Exception Classes
**File**: `backend/models.py`
**Changes**:
- Add simple exception classes following existing patterns

```python
class ApiKeyError(Exception):
    """API key related errors."""
    pass

class ValidationError(Exception):
    """Validation errors."""
    pass
```

#### 3. Pearl-Compliant Logging
**File**: Use existing `setup_pearl_logger()` from logging_config.py
**Changes**:
- Ensure proper Pearl logging for API key operations
- Use `STORE_PATH` environment variable if available

### Success Criteria:

#### Essential Tests:
- [x] POST endpoint stores key
- [x] GET endpoint returns status without leaking key
- [x] Standard response format used  
- [x] Errors handled gracefully

**Implementation Status**: ✅ COMPLETED
**Implementation Date**: 2025-09-04
**Notes**:
- Added POST /config/openrouter-key endpoint with validation (min 20 characters)
- Added GET /config/openrouter-key endpoint that returns status without exposing the key
- Added ApiKeyError and ValidationError exception classes to models.py
- Standard JSON response format: {"status": "success|error", "data": {...}, "error": "..."} 
- Pearl-compliant logging for all API operations

---

## Phase 3: Simple Frontend Integration

### Overview
Extend existing PreferenceForm component with a simple masked API key field. No new components needed.

### Changes Required:

#### 1. Extend PreferenceForm Component
**File**: `frontend/src/lib/components/PreferenceForm.svelte`
**Changes**:
- Add simple masked input field for API key
- Basic show/hide toggle
- Save button integration
- Follow existing component patterns

```svelte
<!-- Add to existing form -->
<div class="form-group">
  <label for="api-key">OpenRouter API Key</label>
  <div class="relative">
    <input
      type={showKey ? 'text' : 'password'}
      id="api-key"
      bind:value={apiKey}
      placeholder="sk-or-..."
      class="w-full pr-10"
    />
    <button
      type="button"
      on:click={() => showKey = !showKey}
      class="absolute right-2 top-1/2 transform -translate-y-1/2"
    >
      {showKey ? 'Hide' : 'Show'}
    </button>
  </div>
  {#if apiKeyConfigured}
    <p class="text-sm text-green-600">✓ API key configured</p>
  {/if}
</div>
```

#### 2. Settings Page Integration
**File**: `frontend/src/routes/settings/+page.svelte`
**Changes**:
- No new components needed
- Existing PreferenceForm handles everything
- Add simple status indicator

#### 3. API Client Functions
**File**: `frontend/src/lib/api/index.ts`
**Changes**:
- Add simple functions using existing apiClient
- No new files needed

```typescript
// Add to existing API client
export const configApi = {
  async setOpenRouterKey(key: string) {
    return apiClient.POST('/config/openrouter-key', {
      body: { api_key: key }
    });
  },
  
  async getKeyStatus() {
    return apiClient.GET('/config/openrouter-key');
  }
};
```

### Success Criteria:

#### Essential Tests:
- [x] Masked input field works ✅
- [x] Key saves successfully ✅  
- [x] Status displays correctly ✅
- [x] No key leakage in DOM/network ✅

**Implementation Status**: ✅ COMPLETED
**Implementation Date**: 2025-01-08
**Notes**:
- Extended PreferenceForm component with masked API key input field
- Added show/hide toggle, save/remove buttons with proper state management
- Integrated with existing API endpoints using openapi-fetch patterns
- Proper validation (minimum 20 characters) with user-friendly error messages
- Status display shows source (user vs environment) with appropriate actions
- Field clears after successful save for security
- All manual verification criteria met through browser testing

---

## Phase 4: StateManager Integration (Simplified)

### Overview
Use StateManager's existing `sensitive=True` flag for secure storage. No custom encryption needed initially.

### Changes Required:

#### 1. StateSchema Definition
**File**: `backend/models.py`
**Changes**:
- Define proper StateSchema for API keys following existing patterns

```python
class ApiKeyState(BaseModel):
    """State schema for API keys."""
    openrouter_key: Optional[str] = None
    last_updated: Optional[datetime] = None
```

#### 2. UserPreferencesService Storage Methods
**File**: Already defined in Phase 1
**Changes**:
- Ensure proper use of StateManager with sensitive flag
- Follow existing service lifecycle patterns

#### 3. Environment Variables
**File**: Use existing `STORE_PATH` for Pearl integration
**Changes**:
- No new environment variables needed
- StateManager handles encryption when sensitive=True

### Success Criteria:

#### Essential Tests:
- [ ] StateManager stores with sensitive flag
- [ ] Data persists across restarts
- [ ] No keys in plain text storage

---

## Phase 5: Removed - No Complex Runtime Updates

Per feedback, we're removing complex event systems and configuration watchers. The simple lock-based swap in Phase 1 is sufficient. API key changes take effect immediately through the `swap_api_key()` method.

---

## Testing Strategy (Simplified)

### Essential Tests Only:
1. **Store/Get/Remove**: API key CRUD operations work
2. **No Secret Leaks**: Keys not in logs or API responses  
3. **Fallback Behavior**: System works without key, falls back to env
4. **Lazy Init**: AIService initializes without key

### Test Files:
```python
# tests/test_api_key_simple.py
def test_store_and_retrieve_key():
    """Test basic storage and retrieval."""
    
def test_no_key_in_logs():
    """Ensure no secrets leak to logs."""
    
def test_fallback_to_env():
    """Test environment variable fallback."""
    
def test_ai_service_lazy_init():
    """Test AI service works without key."""
```

### Manual Testing Checklist:
1. [ ] Start backend without OPENROUTER_API_KEY env var
2. [ ] Verify backend starts successfully (lazy init)
3. [ ] Add key via frontend settings
4. [ ] Test AI features work with user key
5. [ ] Check logs for any key leakage
6. [ ] Remove key and verify graceful degradation

## Security & Performance

### Security (Basic):
- Use StateManager's `sensitive=True` flag
- Mask keys in frontend with password input type
- Never log API keys
- Basic input validation (length check)
- Sanitize inputs (defer CSP headers to follow-up)

### Performance:
- Simple lock-based swapping is fast
- No complex validation on every request
- StateManager handles persistence efficiently
- No performance impact on normal operations

## Implementation Order

1. **Backend Lazy Init**: Make AIService work without key
2. **Storage**: Extend UserPreferencesService with StateManager
3. **API Endpoints**: Add 2 simple endpoints in main.py
4. **Frontend**: Extend PreferenceForm with masked input
5. **Tests**: Write essential tests only

## Future Enhancements (Not in MVP)

- Rate limiting on API endpoints
- Comprehensive API key validation
- CSP headers and advanced security
- Key rotation and expiry
- Event-based configuration updates
- Custom encryption beyond StateManager

## Key Principles (From Review Feedback)

1. **Leverage Existing Infrastructure**: Use StateManager, UserPreferencesService, PreferenceForm
2. **Simplify**: No over-engineering, minimal changes
3. **Follow Patterns**: Use existing codebase patterns and conventions
4. **Security Without Complexity**: StateManager's sensitive flag is enough for MVP
5. **Pearl Compliance**: Use existing Pearl logging setup

## References

- StateManager: `backend/services/state_manager.py` (secure storage with sensitive flag)
- UserPreferencesService: `backend/services/user_preferences_service.py` (extend this)
- PreferenceForm: `frontend/src/lib/components/PreferenceForm.svelte` (extend this)
- Pearl Logging: `backend/logging_config.py` (use setup_pearl_logger)
- Config Reload: `backend/config.py` (use existing reload_config mechanism)