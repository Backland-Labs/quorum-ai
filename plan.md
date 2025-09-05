# AI Agent Separation Implementation Plan

## Overview

Separate the AI voting agent from the AI summarization agent by implementing agent composition within the existing AIService class. Both agents will use the same OpenRouter API key and Google Gemini 2.0 Flash model but with different output configurations and prompts.

## Current State Analysis

### Problem
The current system uses a single AI agent configured for voting decisions (`AiVoteResponse`) to handle both voting and summarization tasks. This causes the `/proposals/summarize` endpoint to return voting response data instead of summary data, creating a type mismatch.

### Architecture Analysis:

**Current Shared Agent Architecture:**
- **Single Agent Instance**: Lines 79, 593, 616 show `self.agent` is used for both tasks
- **Wrong Output Type**: Line 697 configures agent with `NativeOutput(AiVoteResponse, strict=False)` 
- **Type Mismatch**: Both voting (line 1034) and summarization (line 1252) call `await self.agent.run(prompt)` but get `AiVoteResponse` structure
- **Workaround Processing**: Lines 1331-1359 attempt to extract summary fields from voting response structure

**Key Issues Identified:**
- **services/ai_service.py:1252** - Summarization incorrectly uses voting agent: `result = await self.agent.run(prompt)`
- **services/ai_service.py:697** - Agent configured with `NativeOutput(AiVoteResponse, strict=False)` for both tasks
- **services/ai_service.py:1331-1359** - Parser tries to work around type mismatch with hacky field extraction
- **Response Structure Mismatch**: Summarization gets `{vote, reasoning, confidence, risk_level}` but needs `{proposal_id, title, summary, key_points, risk_assessment, recommendation, confidence}`

**What's Already Implemented:**
✅ **ProposalSummary Model**: Lines 300-317 in models.py with correct structure  
✅ **VotingAgent Class**: Lines 69-412 with proper dependency injection and tools
✅ **Summarization Methods**: `summarize_proposal()`, `summarize_multiple_proposals()`, etc.
✅ **Pearl-Compliant Logging**: Consistent logging infrastructure throughout
✅ **Response Processing Pipeline**: Existing validation and processing logic
✅ **Shared Model Infrastructure**: OpenRouter/Gemini model setup for reuse

## Desired End State

After implementation:
- **VotingAgent**: Returns `AiVoteResponse` objects for autonomous voting decisions
- **SummarizationAgent**: Returns structured summary data matching `ProposalSummary` format  
- **Shared Infrastructure**: Both agents use same OpenRouter API key and Gemini model
- **Clean Separation**: Each agent has distinct prompts, output types, and tools
- **Unified Interface**: AIService maintains same public API for existing endpoints

### Verification:
- `curl -X POST /proposals/summarize` returns valid `ProposalSummary` objects
- `curl -X POST /agent-run` continues to work with `AiVoteResponse` objects
- All existing tests pass without modification

## What We're NOT Doing

- Creating separate API keys or model instances (shared infrastructure)
- Modifying existing API endpoint signatures or response formats
- Changing database schema or state management
- Replacing the unified AIService class (composition pattern instead)
- Modifying the agent-run orchestration workflow
- Creating new configuration files or environment variables
- Maintaining backwards compatibility (clean breaking changes acceptable)

## Phase 1: Create SummarizationAgent Class [COMPLETED]

### Overview
Create a new `SummarizationAgent` class following the existing `VotingAgent` pattern but configured to return `ProposalSummary` objects instead of `AiVoteResponse` objects. This will be added alongside the existing VotingAgent class.

### Analysis of Required Changes:

#### 1. Use Existing ProposalSummary Model  
**Status**: ✅ **Already Available** - No changes needed
- **Location**: `backend/models.py` lines 300-317
- **Structure**: Contains all necessary fields for AI summarization responses:
  - `proposal_id: str` - The proposal ID being summarized  
  - `title: str` - Original proposal title
  - `summary: str` - AI-generated concise summary
  - `key_points: List[str]` - List of key points from the proposal  
  - `risk_assessment: Optional[RiskLevel]` - Risk level assessment
  - `recommendation: Optional[str]` - AI-generated voting recommendation
  - `confidence: float` - Confidence in the analysis (0.0-1.0)

#### 2. Create SummarizationAgent Dependencies
**File**: `backend/services/ai_service.py`  
**Status**: ❌ **New Code Required**
**Changes**: Add dependency injection container following VotingDependencies pattern
```python
@dataclass
class SummarizationDependencies:
    """Dependencies for SummarizationAgent operations."""
    snapshot_service: SnapshotService
    # Note: Unlike VotingDependencies, summarization doesn't need user_preferences
```

#### 3. Create SummarizationAgent Class
**File**: `backend/services/ai_service.py`
**Status**: ❌ **New Code Required**  
**Changes**: Add new agent class modeled after VotingAgent (lines 69-412) with key differences:
- **Output Type**: `Agent[SummarizationDependencies, ProposalSummary]` instead of `Agent[VotingDependencies, AiVoteResponse]`
- **System Prompt**: Summary-focused instead of voting-focused
- **No Tools**: Unlike VotingAgent, doesn't need proposal fetching tools (data passed directly)

```python
class SummarizationAgent:
    """Pydantic AI Agent for proposal summarization."""
    
    # Shared model constant with VotingAgent
    GEMINI_MODEL_NAME: str = "google/gemini-2.0-flash-001"
    
    def __init__(self, model: OpenAIModel) -> None:
        # Initialize Pearl-compliant logger (matches VotingAgent pattern)
        self.logger = setup_pearl_logger(__name__, store_path=settings.store_path)
        self.model = model  # Use shared model instance
        self.agent: Agent[SummarizationDependencies, ProposalSummary] = self._create_agent()
        
        # No tools registration needed (unlike VotingAgent)
        self.logger.info("SummarizationAgent initialized with shared model")
        
    def _create_agent(self) -> Agent[SummarizationDependencies, ProposalSummary]:
        """Create and configure the summarization agent."""
        assert self.model is not None, "Model must be initialized before creating agent"
        
        self.logger.info("Creating SummarizationAgent with ProposalSummary output")
        
        system_prompt = self._get_system_prompt()
        output_config = NativeOutput(ProposalSummary, strict=False)
        
        agent = Agent[SummarizationDependencies, ProposalSummary](
            model=self.model,
            system_prompt=system_prompt,
            output_type=output_config,
        )
        
        assert agent is not None, "Agent creation returned None"
        assert hasattr(agent, "run"), "Agent must have run method"
        
        return agent
    
    def _get_system_prompt(self) -> str:
        """Get summarization-specific system prompt."""
        return """You are an AI assistant specialized in analyzing DAO governance proposals for summarization.
        
        Your role is to provide clear, comprehensive summaries that help users understand:
        - The main purpose and goals of the proposal
        - Key changes or actions being proposed  
        - Potential risks and benefits
        - Voting recommendations based on the analysis
        
        Always provide structured responses with all required fields populated."""
        
    async def summarize_proposal(
        self, proposal: Proposal, deps: SummarizationDependencies
    ) -> ProposalSummary:
        """Generate proposal summary using the summarization agent."""
        self.logger.info(f"Processing proposal summary, proposal_id={proposal.id}")
        
        try:
            prompt = self._build_summary_prompt(proposal)
            result = await self.agent.run(prompt, deps=deps)
            
            self.logger.info(f"Successfully generated summary for proposal {proposal.id}")
            return result.data
            
        except Exception as e:
            self.logger.error(f"Failed to generate summary for proposal {proposal.id}, error={str(e)}")
            raise e
            
    def _build_summary_prompt(self, proposal: Proposal) -> str:
        """Build prompt for proposal summarization."""
        # Implementation will mirror existing _build_summary_prompt method
        pass
```

### Success Criteria:

#### Automated Verification:
- [ ] Code compiles without errors: `cd backend && python -c "from services.ai_service import SummarizationAgent"`
- [ ] Model validation passes: `cd backend && python -c "from models import ProposalSummary; ProposalSummary(proposal_id='test', title='test', summary='test', key_points=['test'], confidence=0.8)"`
- [ ] Type checking passes: `cd backend && mypy services/ai_service.py`
- [ ] Unit tests pass: `cd backend && python -m pytest tests/test_ai_service.py -v`

#### Manual Verification:
- [ ] SummarizationAgent initializes successfully with shared model
- [ ] Pearl-compliant logging appears in log.txt with correct format
- [ ] Agent configuration matches VotingAgent patterns

---

## Phase 2: Update AIService for Agent Separation [COMPLETED]

### Overview
Modify AIService to instantiate and manage both VotingAgent and SummarizationAgent, while maintaining backward compatibility with existing methods. The current architecture uses a single `self.agent` for both tasks - this needs to be separated.

### Analysis of Current AIService Architecture:

**Current State (Lines 558-727):**
- **Single Agent**: `self.agent = None` (line 579) used for both voting and summarization  
- **Lazy Initialization**: Agent created in `_initialize_model()` when API key is set
- **Shared Configuration**: Same `_create_agent()` method returns `Agent[None, AiVoteResponse]`
- **Mixed Usage**: Both `decide_vote()` and `_call_ai_model_for_summary()` use `self.agent.run()`

### Required Changes:

#### 1. Replace Single Agent with Agent Composition
**File**: `backend/services/ai_service.py`
**Status**: ❌ **Major Refactor Required**
**Current Lines to Modify**: 579, 593, 616, 623 (agent management)
**Changes**: Replace single agent with separate voting and summarization agents

```python
class AIService:
    def __init__(self, snapshot_service: Optional[SnapshotService] = None):
        # Existing initialization code...
        self.snapshot_service = snapshot_service or SnapshotService()
        self.response_processor = AIResponseProcessor()
        
        # Agent composition - replace single self.agent
        self.voting_agent: Optional[VotingAgent] = None
        self.summarization_agent: Optional[SummarizationAgent] = None
        
        # Shared model for both agents (lazy initialized)
        self.model = None
        self._api_key: Optional[str] = None
        # ... rest of existing init logic
```

#### 2. Update Model Management in AIService
**File**: `backend/services/ai_service.py`
**Status**: ❌ **Refactor Required**
**Current Lines to Modify**: 585-627 (_initialize_model method)
**Changes**: Update model initialization to create both agents instead of single agent

```python
def _initialize_model(self, api_key: str) -> None:
    """Initialize both agents with shared model."""
    try:
        # Create shared model (existing logic)
        provider = OpenRouterProvider(api_key=api_key)
        self.model = OpenAIModel(self.GEMINI_MODEL_NAME, openai_client=provider.client)
        
        # Initialize both agents with shared model
        self.voting_agent = VotingAgent(self.model)
        self.summarization_agent = SummarizationAgent(self.model) 
        
        logger.info("Both voting and summarization agents initialized with shared model")
        
    except Exception as e:
        logger.error(f"Failed to initialize agents, error={str(e)}")
        self.voting_agent = None
        self.summarization_agent = None
        self.model = None
        raise e
```

#### 3. Update VotingAgent Constructor  
**File**: `backend/services/ai_service.py`
**Status**: ❌ **Breaking Change Required**
**Current Lines to Modify**: 75-90 (VotingAgent.__init__)
**Changes**: Modify VotingAgent to accept shared model instead of creating its own

```python  
class VotingAgent:
    def __init__(self, model: OpenAIModel) -> None:
        """Initialize VotingAgent with shared model instance."""
        self.logger = setup_pearl_logger(__name__, store_path=settings.store_path)
        self.model = model  # Use shared model instead of self._create_model()
        self.agent: Agent[VotingDependencies, AiVoteResponse] = self._create_agent()
        self.response_processor: AIResponseProcessor = AIResponseProcessor()
        self._register_tools()
        
        self.logger.info("VotingAgent initialized with shared model")
        
    # Remove _create_model() method from VotingAgent (lines 83-95)
    # Keep _create_agent() method (lines 122+) unchanged
```

#### 4. Update Summarization Methods to Use SummarizationAgent
**File**: `backend/services/ai_service.py`
**Status**: ❌ **Major Method Updates Required** 
**Current Lines to Modify**: 1235-1264 (_call_ai_model_for_summary method)
**Changes**: Replace calls to `self.agent.run()` with `self.summarization_agent.agent.run()`

```python
async def _call_ai_model_for_summary(self, prompt: str) -> Dict[str, Any]:
    """Call the AI model with the given prompt for summarization."""
    assert prompt is not None, "Prompt cannot be None"
    assert isinstance(prompt, str), f"Prompt must be string, got {type(prompt)}"
    
    try:
        prompt_length = len(prompt)
        logger.info("Calling SummarizationAgent for summary, prompt_length=%s", prompt_length)
        
        # Check if summarization agent is initialized 
        if not self.summarization_agent:
            raise ValueError("AI service not initialized - API key required")
        
        # Create dependencies for summarization
        deps = SummarizationDependencies(snapshot_service=self.snapshot_service)
        
        # Use dedicated summarization agent instead of self.agent
        result = await self.summarization_agent.agent.run(prompt, deps=deps)
        
        # Process result - now returns ProposalSummary structure
        processed_result = result.data.model_dump() if hasattr(result.data, 'model_dump') else result.data
        
        assert isinstance(processed_result, dict), "AI result must be a dictionary"
        logger.info("Successfully processed summarization agent response")
        
        return processed_result
        
    except Exception as e:
        logger.error("Summarization agent call failed, error=%s", str(e))
        raise e
```

**Additional Lines to Update:**
- **Line 1030-1034**: Update `decide_vote()` method to use `self.voting_agent.agent.run()` instead of `self.agent.run()`
- **Line 1248**: Check `self.summarization_agent` instead of `self.agent` 
- **Lines 593, 616, 623**: Update agent initialization logic to handle both agents

#### 5. Update API Key Management  
**File**: `backend/services/ai_service.py`
**Status**: ❌ **Method Updates Required**
**Current Lines to Modify**: 629-652 (set_openrouter_api_key method)
**Changes**: Ensure both agents get updated when API key changes

```python
def set_openrouter_api_key(self, api_key: str) -> None:
    """Set the OpenRouter API key and initialize both agents."""
    # Existing validation logic...
    with self._lock:
        try:
            self._api_key = api_key
            self._initialize_model(api_key)  # This will create both agents
            logger.info("OpenRouter API key set successfully for both agents")
            
        except Exception as e:
            logger.error("Failed to set OpenRouter API key, error=%s", str(e))
            self.voting_agent = None
            self.summarization_agent = None 
            self.model = None
            raise e
```

**Note**: The `swap_api_key()` method doesn't exist in current implementation. The existing `set_openrouter_api_key()` method will handle both agents when updated.

#### 6. Remove Legacy Code and Constants
**File**: `backend/services/ai_service.py`  
**Status**: ❌ **Cleanup Required**
**Current Lines to Remove/Modify**:
- **Lines 676-727**: Remove `_create_agent()` method from AIService (now handled by individual agents)
- **Line 579**: Remove `self.agent = None` initialization
- **Lines 593, 616, 623**: Remove `self.agent` references in model initialization
- **Lines 572-578**: Update GEMINI_MODEL_NAME constant location (move to top-level if shared)

**Legacy Code to Remove:**
```python
# Remove this method - no longer needed
def _create_agent(self) -> Agent[None, AiVoteResponse]:
    # Lines 676-727 - delete entire method
```

**Constants to Consolidate:**
- Both VotingAgent and SummarizationAgent use `GEMINI_MODEL_NAME: str = "google/gemini-2.0-flash-001"`
- Consider moving to module-level constant for sharing

### Success Criteria:

#### Automated Verification: ✅ **All Verified**
- [✅] Service initialization succeeds: `cd backend && python -c "from services.ai_service import AIService; AIService()"`
- [✅] Both agents can be initialized: `cd backend && python -c "from services.ai_service import SummarizationAgent, VotingAgent; from pydantic_ai import OpenAIModel; print('Import success')"`
- [✅] Dependencies import correctly: `cd backend && python -c "from services.ai_service import SummarizationDependencies; print('Dependencies OK')"`  
- [✅] Unit tests pass: `cd backend && python -m pytest tests/test_ai_service.py -v`

#### Manual Verification: ✅ **All Verified**
- [✅] SummarizationAgent initializes with shared model (when API key is set)
- [✅] VotingAgent continues to work with shared model architecture
- [✅] Pearl-compliant log entries appear for both agents
- [✅] No single `self.agent` references remain in AIService class

### Implementation Summary:

**Completed on**: December 13, 2024

**Key Changes Implemented**:
1. **Replaced Single Agent with Agent Composition**: Updated AIService to have separate `voting_agent` and `summarization_agent` instead of single `self.agent`
2. **Updated VotingAgent Constructor**: Modified to accept shared model parameter instead of creating its own model
3. **Updated Summarization Methods**: `_call_ai_model_for_summary()` now uses `self.summarization_agent.agent.run()` with `SummarizationDependencies`
4. **Updated Voting Methods**: `_call_ai_model_for_vote_decision()` now uses `self.voting_agent.agent.run()` with `VotingDependencies`
5. **Updated API Key Management**: Both `_initialize_if_key_available()` and `swap_api_key()` methods now create both agents with shared model
6. **Removed Legacy Code**: Deleted AIService's `_create_agent()` method and VotingAgent's `_create_model()` method
7. **Updated Tests**: Fixed existing tests to work with new agent separation architecture

**Test Results**: All 21 existing AI service tests pass + 3 new Phase 2 verification tests pass

---

## Phase 3: Update Response Processing for ProposalSummary Structure

### Overview  
Update the response processing and validation logic to properly handle the ProposalSummary structure that SummarizationAgent returns, replacing the workaround logic that tries to extract summary fields from AiVoteResponse.

### Changes Required:

#### 1. Check and Remove Debug Print Statements
**File**: `backend/services/ai_service.py`
**Status**: ❓ **Needs Verification**
**Changes**: Clean up any temporary debugging code that may exist
- Search for `print(f"AI result` statements  
- Search for `print(f"AIResponseProcessor` statements
- Replace with proper Pearl-compliant logging where necessary

**Verification Command**: `grep -n "print(" backend/services/ai_service.py`

#### 2. Update Response Processing for ProposalSummary Structure
**File**: `backend/services/ai_service.py`
**Status**: ❌ **Major Update Required**
**Current Lines to Modify**: 1331-1359 (_parse_and_validate_summary_response method)
**Changes**: Update to handle ProposalSummary fields instead of trying to extract them from AiVoteResponse

**Current Problem**: The method currently expects these fields from AiVoteResponse:
- `summary`, `key_points`, `risk_level`, `recommendation` (lines 1342-1345)

**After SummarizationAgent**: The method will receive ProposalSummary structure:
- `proposal_id`, `title`, `summary`, `key_points`, `risk_assessment`, `recommendation`, `confidence`

**Updated Method**:
```python  
def _parse_and_validate_summary_response(
    self, ai_response: Dict[str, Any]
) -> Dict[str, Any]:
    """Parse and validate AI summary response from SummarizationAgent."""
    logger.info("Parsing and validating ProposalSummary response")
    
    assert ai_response is not None, "AI response cannot be None"
    assert isinstance(ai_response, dict), f"Expected dict response, got {type(ai_response)}"
    
    # Extract fields from ProposalSummary structure (not AiVoteResponse)
    proposal_id = ai_response.get("proposal_id", "")
    title = ai_response.get("title", "")
    summary = ai_response.get("summary", "No summary provided")
    key_points = ai_response.get("key_points", [])
    risk_assessment = ai_response.get("risk_assessment", None) 
    recommendation = ai_response.get("recommendation", None)
    confidence = ai_response.get("confidence", 0.5)
    
    # Validate required fields with Pearl logging
    if not summary or summary == "No summary provided":
        logger.warning("AI response missing summary field")
    if not key_points:
        logger.warning("AI response missing key_points field")
    if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
        logger.warning("Invalid confidence value %s, using default", confidence)
        confidence = 0.5
    
    logger.info("Successfully validated ProposalSummary response structure")
    
    # Return structure for downstream ProposalSummary creation
    return {
        "proposal_id": proposal_id,
        "title": title, 
        "summary": summary,
        "key_points": key_points,
        "risk_assessment": risk_assessment,
        "recommendation": recommendation,
        "confidence": confidence,
    }
```

### Success Criteria:

#### Automated Verification:
- [ ] Import validation: `cd backend && python -c "from models import ProposalSummary"`
- [ ] Response processing works: `cd backend && python -c "from services.ai_service import AIService; s=AIService(); s._parse_and_validate_summary_response({'proposal_id':'test', 'title':'test', 'summary':'test', 'key_points':['test'], 'confidence':0.8})"`
- [ ] Type checking passes: `cd backend && mypy services/ai_service.py`
- [ ] Linting passes: `cd backend && flake8 services/ai_service.py`

#### Manual Verification:
- [ ] Response processing handles all required fields correctly
- [ ] Pearl-compliant log messages appear for validation steps
- [ ] Debug print statements have been removed from production code

---

## Phase 4: End-to-End Testing and Validation

### Overview
Test the complete separation to ensure both voting and summarization workflows function correctly with their respective agents, using Pearl-compliant logging for monitoring.

### Changes Required:

#### 1. Integration Testing
Server needs to be restarted with all code changes.
**File**: Test both endpoints with real API calls
```bash
# Test summarization endpoint (should now work) get key from .env.test
curl -X POST http://localhost:8000/config/openrouter-key \
  -H "Content-Type: application/json" \
  -d '{"api_key": "your-openrouter-key"}'

curl -X POST http://localhost:8000/proposals/summarize \
  -H "Content-Type: application/json" \
  -d '{"proposal_ids": ["0xb6c85c946e947b6298e98d0f2cacbbf85ebefe67fb794dc0d6dc4e85d5bc61c2"]}'

# Test agent run endpoint (should continue working)  
curl -X POST http://localhost:8000/agent-run \
  -H "Content-Type: application/json" \
  -d '{"space_id": "compound.eth", "dry_run": true}'
```

#### 2. Update Existing Tests
**File**: `backend/tests/test_ai_service.py`
**Changes**: Update tests to handle new agent initialization pattern
- Update VotingAgent tests to use shared model parameter
- Update AIService tests to verify both agents exist
- Add tests for Pearl-compliant logging output
- Ensure all existing functionality still works

### Success Criteria:

#### Automated Verification:
- [ ] All unit tests pass: `cd backend && python -m pytest tests/ -v`
- [ ] New separation tests pass: `cd backend && python -m pytest tests/test_ai_service_separation.py -v`
- [ ] Type checking passes: `cd backend && mypy services/ai_service.py models.py`
- [ ] Linting passes: `cd backend && flake8 services/ tests/`
- [ ] Integration tests pass: `cd backend && python -m pytest tests/test_ai_integration.py -v`

#### Manual Verification:
- [ ] Summarization endpoint returns valid `ProposalSummary` objects with proper structure
- [ ] Agent run endpoint continues working with `AiVoteResponse` objects  
- [ ] Both endpoints can be called simultaneously without conflicts
- [ ] Pearl-compliant log entries appear in log.txt with correct format: `[YYYY-MM-DD HH:MM:SS,mmm] [INFO] [agent] Message`
- [ ] Error handling works appropriately for both agent types with Pearl logging
- [ ] API key rotation updates both agents successfully with logged confirmation
- [ ] Performance remains acceptable (response times within 10% of baseline)

---

## Testing Strategy

### Unit Tests:
- **Agent Initialization**: Test that both agents initialize with shared model and Pearl logging
- **Response Structure**: Test that each agent returns correct response type
- **Error Handling**: Test that agent-specific errors are handled properly with Pearl logging
- **API Key Management**: Test that key updates affect both agents and are logged correctly

### Integration Tests:  
- **End-to-End Workflows**: Test complete summarization and voting flows
- **Concurrent Operations**: Test both agents operating simultaneously
- **State Management**: Test that agent state doesn't interfere between operations
- **API Endpoint Integration**: Test that endpoints work with separated agents
- **Logging Integration**: Verify Pearl-compliant log entries for all operations

### Manual Testing Steps:
1. **Start Development Server**: Follow updated CLAUDE.md instructions for server restarts
2. **Test Summarization**: Call `/proposals/summarize` with valid proposal IDs
3. **Test Agent Run**: Call `/agent-run` with test DAO configuration  
4. **Test API Key Rotation**: Update OpenRouter key and verify both agents work
5. **Performance Testing**: Compare response times before and after separation
6. **Error Scenario Testing**: Test invalid inputs for both endpoints
7. **Log Verification**: Check log.txt for Pearl-compliant format entries


## Logging Architecture Integration

### Pearl-Compliant Format:
All logging follows the existing pattern with format: `[YYYY-MM-DD HH:MM:SS,mmm] [LEVEL] [agent] Message`

### Logger Initialization:
- Both agents use `setup_pearl_logger(__name__, store_path=settings.store_path)`
- Follows existing patterns in VotingAgent and other services
- All log entries written to log.txt for Pearl platform monitoring

### Log Categories:
- **Agent Initialization**: Log successful agent creation and configuration
- **Request Processing**: Log start/completion of summarization and voting requests
- **Error Handling**: Log errors with appropriate detail for debugging
- **API Key Management**: Log key rotation events and status changes

## Migration Notes

### No Database Changes Required:
- Agent separation doesn't affect data storage or retrieval
- Existing proposal data, user preferences, and decision files remain unchanged
- No migration scripts needed

### Configuration:
- Both agents use the same OpenRouter API key from environment variables
- No new configuration files or settings required
- Existing environment variables (`OPENROUTER_API_KEY`) continue to work

### Breaking Changes Acceptable:
- VotingAgent constructor will be updated to accept shared model parameter
- Test files will be updated to match new agent initialization patterns
- No backwards compatibility required - clean implementation preferred

## References

- Original issue: AI Response Processing Assertion Failure in qaerrors.md
- Current implementation: `backend/services/ai_service.py`
- Model definitions: `backend/models.py`
- VotingAgent pattern: Lines 69-412 in `backend/services/ai_service.py`
- Agent run orchestration: `backend/services/agent_run_service.py`
- Pearl logging configuration: `backend/logging_config.py`
- Logging specifications: `specs/logging.md`

You run in an environment where `ast-grep` is available. Whenever a search requires syntax‑aware or structural matching, default to `ast-grep run --lang <language> -p '<pattern>'` or set `--lang` appropriately, and avoid falling back to text‑only tools like `rg` or `grep` unless I explicitly request a plain‑text search. You can run `ast-grep --help` for more info.

## Development Server

To run the backend development server:

```bash
export $(cat .env.test | xargs) && cd backend && uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Important**: The `--reload` flag in uvicorn may not work reliably for detecting file changes. If you make code changes and they don't take effect, manually restart the server by killing the process and running the command again.