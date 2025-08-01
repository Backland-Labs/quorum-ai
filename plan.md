# Implementation Plan: Refactor AI Service to Use Pydantic AI Agents

**GitHub Issue**: #145
**Branch**: `feature/pydantic-ai-agents-145`
**Status**: In Progress
**Task 1 Completed**: 2025-08-01

## Overview

Refactor the current AI service architecture from manual prompt/response handling to a structured Pydantic AI Agent system with tools, dependency injection, and file-based output workflows. This refactoring will improve code maintainability, testing coverage, and enable more sophisticated autonomous voting capabilities while maintaining full backward compatibility.

**Pydantic AI Tools Docs**: https://github.com/pydantic/pydantic-ai/blob/main/docs/tools.md

## Files to be Modified/Created

### Core Implementation Files
- [ ] `backend/services/ai_service.py` - **MODIFY**: Add VotingAgent class and VotingDependencies
- [ ] `backend/models.py` - **MODIFY**: Add VotingDecisionFile model if needed
- [ ] `backend/config.py` - **MODIFY**: Add file output configuration settings

### Test Files
- [ ] `tests/test_ai_service.py` - **MODIFY**: Update existing tests for agent architecture
- [ ] `tests/test_voting_agent.py` - **CREATE**: New comprehensive agent test suite
- [ ] `tests/fixtures/agent_fixtures.py` - **CREATE**: Test fixtures for agent testing

### Integration Files
- [ ] `backend/services/agent_run_service.py` - **MODIFY**: Update to handle file-based decisions (if needed)
- [ ] `backend/main.py` - **MODIFY**: Update dependency injection if needed

### Documentation Files
- [ ] `specs/ai-service.md` - **MODIFY**: Update specification to reflect agent architecture
- [ ] `CLAUDE.md` - **MODIFY**: Update development commands and architecture notes

## Current Architecture Analysis

**Existing Implementation** (`backend/services/ai_service.py`):
- Manual prompt building in `_build_vote_decision_prompt()`
- Direct OpenRouter/Gemini 2.0 Flash integration via Pydantic AI
- Manual response parsing in `AIResponseProcessor` class
- Three voting strategies: conservative, balanced, aggressive
- Integration with `AgentRunService` for autonomous workflow
- Pearl-compliant logging with structured spans
- Returns `VoteDecision` objects with confidence scores and reasoning

**Integration Points**:
- Called by `AgentRunService.execute_agent_run()` for autonomous voting
- Uses `SnapshotService` for proposal data via REST API calls
- Supports both summarization and voting decision modes
- Existing test coverage >90% across multiple test files

## Target Architecture

**New Pydantic AI Agent System**:
1. **`VotingAgent`** class using `pydantic_ai.Agent`
2. **`VotingDependencies`** dataclass for dependency injection
3. **Agent Tools** for Snapshot API interactions:
   - `query_active_proposals` - Fetch proposals by space/status
   - `get_proposal_details` - Get detailed proposal content
   - `get_voting_power` - Calculate user voting power
4. **Structured Output** using existing `AiVoteResponse` model
5. **File-based Decision Workflow** for integration with external systems
6. **Dynamic System Prompts** based on user preferences and strategies

## Implementation Tasks

### P0 - Critical Path (Must Complete First)

#### **Task 1: Create VotingDependencies and Agent Infrastructure** ✅ COMPLETED
**Priority**: P0

**Files Modified**:
- `backend/services/ai_service.py` - Add VotingDependencies dataclass and VotingAgent class
- `backend/config.py` - Add agent configuration settings

**Acceptance Criteria**:
- [x] `VotingDependencies` dataclass with `SnapshotService` and `UserPreferences`
- [x] `VotingAgent` class using `pydantic_ai.Agent`
- [x] Agent configured with Google Gemini 2.0 Flash via OpenRouter
- [x] Dynamic system prompt generation based on voting strategy
- [x] Maintains existing Pearl logging integration

**Test Cases**:
- Agent initialization with valid dependencies
- System prompt generation for each voting strategy
- Model configuration validation
- Error handling for missing dependencies

**Implementation Steps**:
1. Create `VotingDependencies` dataclass in `backend/services/ai_service.py`
2. Implement `VotingAgent` class with `pydantic_ai.Agent`
3. Move strategy prompts to agent system prompt generation
4. Add runtime assertions for initialization validation
5. Write unit tests for agent creation and configuration

**Dependencies**: None

---

#### **Task 2: Implement Agent Tools for Snapshot Integration** ✅ COMPLETED
**Priority**: P0
**Status**: Completed - 2025-08-01

**Files Modified**:
- `backend/services/ai_service.py` - Add agent tool methods using `@agent.tool` decorator ✅
- `tests/test_voting_agent.py` - Create initial tool tests ✅

**Acceptance Criteria**:
- [x] `query_active_proposals` tool with space filtering using `@agent.tool` decorator ✅
- [x] `get_proposal_details` tool for comprehensive proposal data ✅
- [x] `get_voting_power` tool for user voting power calculation ✅
- [x] Tools use existing `SnapshotService` methods via `RunContext[VotingDependencies]` ✅
- [x] Proper error handling and logging for tool execution ✅
- [x] Tool responses optimized for agent consumption ✅

**Test Cases**:
- Each tool executes successfully with valid inputs ✅
- Error handling for network failures and invalid data ✅
- Tool integration with `SnapshotService` methods ✅
- Response validation and type checking ✅

**Implementation Notes**:
- Implemented all three tools with `@agent.tool` decorators in `_register_tools()` method
- Added runtime assertions for dependency validation in each tool
- Created helper method `_proposal_to_dict()` for consistent proposal data conversion
- Added constant `MAX_PROPOSAL_BODY_LENGTH` for proposal body truncation
- All tests passing with 100% coverage of tool functionality
- Refactored for code quality following DRY principles

**Dependencies**: Task 1 (VotingDependencies needed for tool injection) ✅

---

#### **Task 3: Migrate Vote Decision Logic to Agent**
**Priority**: P0

**Files Modified**:
- `backend/services/ai_service.py` - Update `decide_vote()` method
- `tests/test_ai_service.py` - Update existing tests

**Acceptance Criteria**:
- [ ] `decide_vote()` method uses new `VotingAgent` instead of manual prompts
- [ ] Structured output using existing `AiVoteResponse` model
- [ ] Response validation maintains existing `AIResponseProcessor` logic
- [ ] All voting strategies work through agent tools
- [ ] Backward compatibility with existing `VoteDecision` creation

**Test Cases**:
- Vote decisions for each strategy (conservative/balanced/aggressive)
- Response validation and error handling
- Integration with existing `_create_vote_decision_from_data()`
- Tool usage within agent execution

**Implementation Steps**:
1. Update `decide_vote()` to use `agent.run()` with proper dependencies
2. Configure agent `result_type` to `AiVoteResponse`
3. Integrate agent response with existing response processor
4. Maintain existing error handling patterns
5. Preserve all runtime assertions and logging

**Dependencies**: Task 1, Task 2 (Agent and tools needed)

---

### P1 - Important (Complete After P0)

#### **Task 4: Add File-based Decision Output**
**Priority**: P1

**Files Modified**:
- `backend/services/ai_service.py` - Add file output logic
- `backend/models.py` - Add VotingDecisionFile model
- `backend/config.py` - Add file path configuration

**Acceptance Criteria**:
- [ ] Agent decisions written to structured JSON files
- [ ] File output includes proposal ID, decision, confidence, reasoning
- [ ] File location configurable via environment variables
- [ ] Integration with existing `AgentRunService` workflow
- [ ] Proper file handling and error recovery

**Test Cases**:
- Decision files created with correct JSON structure
- File permission and disk space error handling
- Concurrent file access handling
- Integration with agent run workflow

**Implementation Steps**:
1. Add file output logic to `decide_vote()` method
2. Create JSON serialization for vote decisions
3. Add configuration for output file location
4. Implement error handling for file I/O operations
5. Update `AgentRunService` to read decision files if needed

**Dependencies**: Task 3 (Agent decision logic must exist)

---

#### **Task 5: Comprehensive Agent Testing Suite**
**Priority**: P1

**Files Modified**:
- `tests/test_voting_agent.py` - Complete comprehensive test suite
- `tests/fixtures/agent_fixtures.py` - Create agent test fixtures
- `tests/test_ai_service.py` - Update integration tests

**Acceptance Criteria**:
- [ ] Unit tests for all agent tools with mocked dependencies
- [ ] Integration tests for agent voting workflow
- [ ] Test coverage remains >90% overall
- [ ] Performance tests for agent response times
- [ ] Error scenario testing for all failure modes

**Test Cases**:
- Agent tool execution with various proposal types
- Error handling for Snapshot API failures
- Vote decision validation across all strategies
- File output verification and error recovery
- Memory and performance impact assessment

**Implementation Steps**:
1. Create `test_voting_agent.py` with comprehensive test suite
2. Mock all `SnapshotService` interactions for tool testing
3. Add integration tests with real agent execution
4. Implement performance benchmarks for decision making
5. Verify existing tests still pass with agent refactoring

**Dependencies**: Task 1, Task 2, Task 3 (All core agent functionality)

## Success Criteria

- [ ] All existing API endpoints maintain identical contracts
- [ ] Backward compatibility with `AgentRunService` integration
- [ ] Test coverage remains >90% with comprehensive agent tool testing
- [ ] Pearl-compliant logging patterns preserved
- [ ] All three voting strategies (conservative/balanced/aggressive) supported
- [ ] File-based decision output for workflow integration
- [ ] Error handling maintains `ExternalServiceError` patterns
- [ ] Container deployment compatibility preserved

## Technical Implementation Details

### Backward Compatibility Strategy
- Maintain existing `AIService` public interface unchanged
- Preserve all existing method signatures and return types
- Keep existing error handling and logging patterns
- Ensure `AgentRunService` integration works without changes

### Performance Considerations
- Agent tool execution should not exceed current response times
- Batch operations for multiple proposals where possible
- Efficient caching of repeated Snapshot API calls
- Memory usage monitoring for large proposal datasets

### Risk Mitigation
- Comprehensive testing at each phase prevents regression
- Gradual migration allows rollback at any point
- Existing `AIResponseProcessor` provides validation safety net
- Pearl-compliant logging ensures observability throughout migration

## Validation Checklist

Before marking this issue complete, verify:
- [ ] All existing tests pass without modification
- [ ] New agent tests achieve >90% coverage
- [ ] API endpoints return identical responses
- [ ] `AgentRunService` integration works unchanged
- [ ] Pearl logging maintains same structure and detail level
- [ ] Container deployment works with new dependencies
- [ ] Performance benchmarks meet or exceed current metrics
- [ ] Error handling covers all identified failure modes
