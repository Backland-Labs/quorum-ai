# Minimal MVP Implementation Plan: Proactive AI Agent Enhancement (Issue #142)

## Summary

Transform the AI agent from passive to proactive governance decision-making by adding strategic briefing capabilities, persistent voting history, and proposal evaluation tools. This MVP focuses on the core functionality needed to make the agent autonomous and intelligent in its decision-making process.

## Current State Analysis

**Existing Architecture:**
- AIService with Pydantic AI using Google Gemini 2.0 Flash via OpenRouter
- AgentRunService orchestrating voting workflow
- StateManager for persistent storage (already implemented)
- Service-oriented async/await architecture
- Pearl-compliant logging system

**Key Services to Enhance:**
- `/Users/max/code/quorum-ai/backend/services/ai_service.py` - Core AI decision making
- `/Users/max/code/quorum-ai/backend/services/agent_run_service.py` - Workflow orchestration
- StateManager integration for voting history persistence

## Development Approach

**Test-Driven Development (TDD):**
- Write tests first for each component before implementation
- Focus on behavior and expected outcomes
- Use existing test patterns and fixtures
- Target >90% test coverage for new code

## MVP Implementation Plan

### Phase 1: Strategic Briefing System (Core Enhancement) ✅ IMPLEMENTED

**Goal:** Add contextual briefing capabilities to the AI agent

**Status:** ✅ Implemented on 2025-08-01
- Created StrategicBriefing model with comprehensive validation
- Implemented generate_strategic_briefing method in AIService
- Added _get_strategic_system_prompt for enhanced prompts
- Full test coverage with 6 comprehensive tests
- Ready for integration with AgentRunService

**Test First (TDD):**
```python
# backend/tests/test_ai_service_strategic.py
import pytest
from backend.services.ai_service import AIService
from backend.models import Proposal, UserPreferences, VoteDecision, VotingStrategy

@pytest.mark.asyncio
async def test_generate_strategic_briefing():
    """Test that strategic briefing incorporates preferences and history."""
    ai_service = AIService()

    # Setup test data
    proposals = [Proposal(id="0x1", title="Test Proposal")]
    preferences = UserPreferences(
        strategy=VotingStrategy.BALANCED,
        participation_rate=0.5
    )
    history = [
        VoteDecision(
            proposal_id="0x0",
            vote=VoteType.FOR,
            confidence=0.9,
            reasoning="Previous vote"
        )
    ]

    # Generate briefing
    briefing = await ai_service.generate_strategic_briefing(
        proposals, preferences, history
    )

    # Verify briefing contains key elements
    assert "voting strategy: BALANCED" in briefing.lower()
    assert "recent voting history" in briefing.lower()
    assert "1 active proposal" in briefing.lower()

@pytest.mark.asyncio
async def test_strategic_system_prompt_includes_briefing():
    """Test that system prompt properly includes strategic briefing."""
    ai_service = AIService()
    briefing = "Strategic context: Conservative approach needed"

    prompt = ai_service._get_strategic_system_prompt(
        briefing, VotingStrategy.CONSERVATIVE
    )

    assert briefing in prompt
    assert "conservative" in prompt.lower()
```

**Implementation:**
1. **Enhance AIService with Strategic Context**
   - Modify existing `_get_system_prompt()` method to include strategic briefing
   - Add `generate_strategic_briefing()` method to AIService
   - Integrate user preferences and voting history into prompts

**Files to Modify:**
- `/Users/max/code/quorum-ai/backend/services/ai_service.py`
- `/Users/max/code/quorum-ai/backend/tests/test_ai_service_strategic.py` (new)

**Key Changes:**
```python
# Add strategic briefing method to AIService
async def generate_strategic_briefing(
    self,
    proposals: List[Proposal],
    user_preferences: UserPreferences,
    voting_history: List[VoteDecision]
) -> StrategicBriefing:
    """Generate strategic briefing based on context."""
    # Analyze recent voting patterns
    # Summarize current governance landscape
    # Provide strategic recommendations

# Enhance system prompt to include briefing context
def _get_strategic_system_prompt(
    self,
    briefing: StrategicBriefing,
    strategy: VotingStrategy
) -> str:
    """Enhanced system prompt with strategic context."""
```

### Phase 2: Persistent Voting History (Foundation) ✅ IMPLEMENTED

**Goal:** Track and persist voting decisions for strategic analysis (limit to 10 most recent)

**Status:** ✅ Implemented on 2025-08-01
- Implemented get_voting_history() method with 10-item limit
- Implemented save_voting_decisions() with automatic pruning
- Added get_voting_patterns() for pattern analysis
- Full test coverage with all tests passing
- StateManager integration complete

**Test First (TDD):**
```python
# backend/tests/test_agent_run_voting_history.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.services.agent_run_service import AgentRunService
from backend.models import VoteDecision, VoteType, VotingStrategy

@pytest.mark.asyncio
async def test_voting_history_limited_to_10():
    """Test that voting history is limited to 10 most recent decisions."""
    mock_state_manager = MagicMock()
    existing_history = [
        {"proposal_id": f"0x{i}", "vote": "FOR", "confidence": 0.8}
        for i in range(15)
    ]
    mock_state_manager.load_state = AsyncMock(return_value={
        "voting_history": existing_history
    })
    mock_state_manager.save_state = AsyncMock()

    service = AgentRunService(state_manager=mock_state_manager)

    # Get voting history
    history = await service.get_voting_history()

    # Should only return 10 most recent
    assert len(history) == 10
    assert history[0].proposal_id == "0x5"  # Oldest in the 10
    assert history[-1].proposal_id == "0x14"  # Most recent

@pytest.mark.asyncio
async def test_voting_history_persistence():
    """Test that new votes are added and history is pruned."""
    mock_state_manager = MagicMock()
    existing = [{"proposal_id": f"0x{i}", "vote": "FOR"} for i in range(8)]
    mock_state_manager.load_state = AsyncMock(return_value={
        "voting_history": existing
    })
    mock_state_manager.save_state = AsyncMock()

    service = AgentRunService(state_manager=mock_state_manager)

    # Add new decisions
    new_decisions = [
        VoteDecision(proposal_id=f"0xnew{i}", vote=VoteType.FOR,
                    confidence=0.9, reasoning="New vote")
        for i in range(3)
    ]

    await service.save_voting_decisions(new_decisions)

    # Verify save was called with 10 items (8 existing + 3 new - 1 pruned)
    saved_data = mock_state_manager.save_state.call_args[0][1]
    assert len(saved_data["voting_history"]) == 10
    assert saved_data["voting_history"][-1]["proposal_id"] == "0xnew2"
```

**Implementation:**
1. **Extend Existing StateManager Integration**
   - AgentRunService already has StateManager integration
   - Enhance existing checkpoint system to include voting history aggregation
   - Add voting history retrieval methods with 10-item limit
   - Implement automatic pruning on save

**Files to Modify:**
- `/Users/max/code/quorum-ai/backend/services/agent_run_service.py` (enhance existing methods)
- `/Users/max/code/quorum-ai/backend/tests/test_agent_run_voting_history.py` (new)

**Key Changes:**
```python
# Enhance existing methods in AgentRunService
async def get_voting_history(self, limit: int = 10) -> List[VoteDecision]:
    """Get recent voting history from checkpoints (max 10)."""
    # Load from StateManager
    # Convert to VoteDecision objects
    # Return only the most recent 10

async def save_voting_decisions(self, decisions: List[VoteDecision]) -> None:
    """Save new voting decisions and maintain 10-item history."""
    # Load existing history
    # Append new decisions
    # Prune to keep only 10 most recent
    # Save back to StateManager

async def get_voting_patterns(self) -> Dict[str, Any]:
    """Analyze voting patterns from history."""
    # Use the 10 most recent votes for pattern analysis
```

### Phase 3: Proposal Evaluation Tools (Intelligence Layer) ✅ IMPLEMENTED

**Goal:** Add intelligent proposal analysis tools using Pydantic AI's tool decorator

**Status:** ✅ Implemented on 2025-08-01
- Created ProposalEvaluationService with 5 core evaluation tools
- All tests passing with comprehensive coverage
- Ready for integration with AIService

**Test First (TDD):**
```python
# backend/tests/test_proposal_evaluation_service.py
import pytest
from backend.services.proposal_evaluation_service import ProposalEvaluationService
from backend.models import Proposal, VoteDecision
import re

@pytest.mark.asyncio
async def test_analyze_proposal_impact():
    """Test proposal impact analysis tool."""
    service = ProposalEvaluationService()
    proposal = Proposal(
        id="0x1",
        title="Increase Treasury Allocation",
        body="Allocate 500,000 USDC for development",
        choices=["For", "Against"]
    )

    impact = await service.analyze_proposal_impact(proposal)

    assert impact["has_financial_impact"] is True
    assert impact["estimated_amount"] == 500000
    assert impact["impact_level"] in ["high", "medium", "low"]

@pytest.mark.asyncio
async def test_assess_treasury_implications():
    """Test treasury impact assessment with regex patterns."""
    service = ProposalEvaluationService()

    # Test various financial patterns
    test_cases = [
        ("Request 1,000,000 DAI", {"amount": 1000000, "currency": "DAI"}),
        ("Allocate $2.5M USDC", {"amount": 2500000, "currency": "USDC"}),
        ("Transfer 50 ETH", {"amount": 50, "currency": "ETH"}),
        ("No financial impact", None)
    ]

    for body, expected in test_cases:
        proposal = Proposal(id="0x1", title="Test", body=body)
        result = await service.assess_treasury_implications(proposal)

        if expected is None:
            assert result["treasury_impact"] is None
        else:
            assert result["treasury_impact"]["amount"] == expected["amount"]
            assert result["treasury_impact"]["currency"] == expected["currency"]

@pytest.mark.asyncio
async def test_check_proposal_precedent():
    """Test precedent checking against voting history."""
    service = ProposalEvaluationService()
    proposal = Proposal(id="0x1", title="Treasury Allocation")

    history = [
        VoteDecision(
            proposal_id="0x0",
            vote=VoteType.FOR,
            confidence=0.9,
            reasoning="Supported similar treasury proposal"
        )
    ]

    precedent = await service.check_proposal_precedent(proposal, history)

    assert precedent["has_precedent"] is True
    assert precedent["similar_votes"] == 1
    assert precedent["historical_stance"] == "supportive"
```

**Implementation:**
1. **Create Evaluation Tools Module**
   - New service: `ProposalEvaluationService`
   - Implement 5 core evaluation tools
   - Tools will be integrated into AIService agent

**New Files:**
- `/Users/max/code/quorum-ai/backend/services/proposal_evaluation_service.py`
- `/Users/max/code/quorum-ai/backend/tests/test_proposal_evaluation_service.py`

**Key Tools Implementation:**
```python
# backend/services/proposal_evaluation_service.py
from typing import Dict, Any, List, Optional
import re
from backend.models import Proposal, VoteDecision

class ProposalEvaluationService:
    """Service for evaluating governance proposals."""

    async def analyze_proposal_impact(self, proposal: Proposal) -> Dict[str, Any]:
        """Analyze potential impact of proposal."""
        # Check for financial keywords
        # Assess governance changes
        # Return impact assessment

    async def assess_treasury_implications(self, proposal: Proposal) -> Dict[str, Any]:
        """Assess treasury and financial impact using regex."""
        # Pattern matching for amounts and currencies
        # Support multiple formats (1M, 1,000,000, etc.)
        patterns = [
            r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*([A-Z]{3,4})',  # 1,000,000 USDC
            r'\$(\d+(?:\.\d+)?)[MK]?\s*([A-Z]{3,4})',      # $2.5M USDC
            r'(\d+(?:\.\d+)?)[MK]\s*([A-Z]{3,4})',         # 1M DAI
        ]

    async def evaluate_governance_risk(self, proposal: Proposal) -> Dict[str, Any]:
        """Evaluate governance and protocol risks."""
        # Check for parameter changes
        # Assess voting power implications
        # Return risk assessment

    async def check_proposal_precedent(
        self, proposal: Proposal, history: List[VoteDecision]
    ) -> Dict[str, Any]:
        """Check against voting history precedents."""
        # Find similar proposals in history
        # Analyze voting patterns
        # Return precedent analysis

    async def analyze_community_sentiment(self, proposal: Proposal) -> Dict[str, Any]:
        """Analyze voting patterns and community response."""
        # Check current voting status
        # Analyze participation rate
        # Return sentiment analysis
```

**Integration with AIService:**
```python
# Modification to ai_service.py
from backend.services.proposal_evaluation_service import ProposalEvaluationService

class AIService:
    def __init__(self):
        # ... existing init ...
        self.evaluation_service = ProposalEvaluationService()

    def _create_agent_with_tools(self, context: Dict[str, Any]) -> Agent:
        """Create agent with evaluation tools."""
        # Tool wrapper functions for Pydantic AI
        async def analyze_impact(proposal_id: str) -> Dict[str, Any]:
            proposal = context["proposals_map"].get(proposal_id)
            return await self.evaluation_service.analyze_proposal_impact(proposal)

        # Register tools with agent
        tools = [analyze_impact, ...]  # Add all wrapped tools
```

### Phase 4: Integration and Enhancement ✅ IMPLEMENTED

**Goal:** Connect all components into cohesive proactive system

**Status:** ✅ Implemented on 2025-08-01
- Created comprehensive integration tests with 10 test cases
- Enhanced execute_agent_run with strategic briefing integration
- Implemented make_strategic_decision with context awareness
- Added _create_agent_with_tools stub for future tool integration
- Full Pearl-compliant logging throughout workflow
- All integration tests passing

**Test First (TDD):**
```python
# backend/tests/test_agent_run_integration.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.services.agent_run_service import AgentRunService
from backend.models import AgentRunRequest, Proposal, VoteDecision

@pytest.mark.asyncio
async def test_proactive_workflow_integration():
    """Test full proactive workflow with all components."""
    # Mock dependencies
    mock_state_manager = MagicMock()
    mock_ai_service = MagicMock()
    mock_snapshot_service = MagicMock()

    # Setup test data
    proposals = [
        Proposal(id="0x1", title="Treasury Proposal",
                body="Request 100,000 USDC", state="active")
    ]
    voting_history = [
        VoteDecision(proposal_id="0x0", vote=VoteType.FOR,
                    confidence=0.8, reasoning="Previous decision")
    ]

    # Mock methods
    mock_snapshot_service.get_proposals = AsyncMock(return_value=proposals)
    mock_state_manager.load_state = AsyncMock(return_value={
        "voting_history": [vh.model_dump() for vh in voting_history]
    })

    # Mock strategic briefing
    mock_ai_service.generate_strategic_briefing = AsyncMock(
        return_value=StrategicBriefing(
            summary="Conservative approach recommended",
            key_insights=["High treasury impact detected"],
            historical_patterns={"treasury_votes": "cautious"},
            recommendations=["Vote against high-value proposals"]
        )
    )

    # Mock AI decision with tools
    mock_ai_service.make_strategic_decision = AsyncMock(
        return_value=[
            VoteDecision(
                proposal_id="0x1",
                vote=VoteType.AGAINST,
                confidence=0.85,
                reasoning="High treasury impact, following conservative strategy"
            )
        ]
    )

    service = AgentRunService(
        state_manager=mock_state_manager,
        ai_service=mock_ai_service,
        snapshot_service=mock_snapshot_service
    )

    # Execute proactive run
    request = AgentRunRequest(space_id="test.eth", dry_run=True)
    response = await service.execute_agent_run(request)

    # Verify workflow
    assert response.proposals_analyzed == 1
    assert len(response.votes_cast) == 1
    assert response.votes_cast[0].vote == VoteType.AGAINST

    # Verify strategic briefing was generated
    mock_ai_service.generate_strategic_briefing.assert_called_once()

    # Verify voting history was loaded
    assert mock_state_manager.load_state.called

    # Verify AI used strategic context
    mock_ai_service.make_strategic_decision.assert_called_with(
        proposals=proposals,
        user_preferences=ANY,
        briefing=ANY,
        voting_history=voting_history
    )

@pytest.mark.asyncio
async def test_voting_history_updated_after_run():
    """Test that voting history is updated after successful run."""
    # Similar setup...
    # Verify that new decisions are saved to voting history
    # Verify pruning to 10 items
```

**Implementation:**
1. **Enhance AgentRunService Workflow**
   - Modify existing `execute_agent_run()` method
   - Add strategic briefing step before proposal analysis
   - Integrate evaluation tools into decision-making process
   - Update voting history after decisions

**Files to Modify:**
- `/Users/max/code/quorum-ai/backend/services/agent_run_service.py`
- `/Users/max/code/quorum-ai/backend/services/ai_service.py`
- `/Users/max/code/quorum-ai/backend/tests/test_agent_run_integration.py` (new)

**Key Enhancements:**
```python
# Enhance existing execute_agent_run method
async def execute_agent_run(self, request: AgentRunRequest) -> AgentRunResponse:
    # ... existing setup code ...

    # Load voting history (limited to 10)
    voting_history = await self.get_voting_history()

    # Generate strategic briefing
    briefing = await self.ai_service.generate_strategic_briefing(
        filtered_proposals, user_preferences, voting_history
    )

    # Log strategic briefing for Pearl compliance
    self.logger.info(
        "Generated strategic briefing",
        extra={
            "briefing_summary": briefing.summary,
            "insights_count": len(briefing.key_insights),
            "history_size": len(voting_history)
        }
    )

    # Enhanced decision making with tools and briefing
    vote_decisions = await self.ai_service.make_strategic_decision(
        proposals=filtered_proposals,
        user_preferences=user_preferences,
        briefing=briefing,
        voting_history=voting_history
    )

    # Execute votes (if not dry run)
    if not request.dry_run:
        # ... existing voting code ...

    # Update voting history with new decisions
    await self.save_voting_decisions(vote_decisions)

    # ... rest of response building ...
```

**AIService Enhancement:**
```python
# Add to ai_service.py
async def make_strategic_decision(
    self,
    proposals: List[Proposal],
    user_preferences: UserPreferences,
    briefing: StrategicBriefing,
    voting_history: List[VoteDecision]
) -> List[VoteDecision]:
    """Make voting decisions using strategic context and tools."""
    # Create agent with tools
    agent = self._create_agent_with_tools({
        "proposals_map": {p.id: p for p in proposals},
        "voting_history": voting_history
    })

    # Enhanced prompt with briefing
    prompt = self._build_strategic_prompt(
        proposals, user_preferences, briefing
    )

    # Run agent with tools
    result = await agent.run(prompt)

    return result.data  # List of VoteDecisions
```

## Technical Implementation Details

### Leveraging Existing Patterns

**StateManager Integration:**
- Use existing checkpoint system in AgentRunService
- Extend existing `get_recent_decisions()` method
- Leverage existing `save_checkpoint_state()` pattern

**AIService Enhancement:**
- Build on existing Pydantic AI agent architecture
- Use existing prompt building patterns
- Extend existing `decide_vote()` method with strategic context

**Error Handling:**
- Follow existing error handling patterns in AgentRunService
- Use existing Pearl-compliant logging
- Maintain existing graceful degradation approach

### Data Models

**Reuse Existing Models:**
- `VoteDecision` - already tracks voting history
- `UserPreferences` - already contains strategy preferences
- `Proposal` - existing proposal structure
- `AgentRunRequest/Response` - existing workflow models

**Minimal New Models:**
```python
# Add to existing models.py
class StrategicBriefing(BaseModel):
    """Strategic briefing for agent decision making."""
    summary: str
    key_insights: List[str]
    historical_patterns: Dict[str, Any]
    recommendations: List[str]

class ProposalEvaluation(BaseModel):
    """Comprehensive proposal evaluation."""
    proposal_id: str
    impact_score: float
    risk_score: float
    precedent_analysis: Dict[str, Any]
    evaluation_summary: str
```


## What's NOT Included in This MVP

**Excluded Features (for future iterations):**
- Advanced machine learning models for pattern recognition
- Complex sentiment analysis beyond basic voting pattern analysis
- Real-time proposal monitoring/alerts
- Advanced risk scoring algorithms
- Multi-space cross-analysis
- Dashboard UI enhancements
- Advanced reporting features
- Complex governance simulation tools

## Implementation Sequence (TDD Approach)

### Step 1: Voting History Foundation ✅ COMPLETED
**Why First:** This is the simplest, most self-contained component that other features depend on.

1. ✅ **Write tests** for voting history persistence (`test_agent_run_voting_history.py`)
2. ✅ **Implement** `get_voting_history()` and `save_voting_decisions()` with 10-item limit
3. ✅ **Verify** StateManager integration works correctly
4. ✅ **Run tests** to ensure functionality - All 6 tests passing

### Step 2: Proposal Evaluation Tools
**Why Second:** These tools are independent services that will be used by the AI agent.

1. **Write tests** for each evaluation tool (`test_proposal_evaluation_service.py`)
2. **Create** ProposalEvaluationService class
3. **Implement** the 5 core evaluation methods with treasury regex patterns
4. **Test** each tool in isolation

### Step 3: Strategic Briefing System
**Why Third:** This builds on voting history and prepares context for the AI.

1. **Write tests** for strategic briefing generation (`test_ai_service_strategic.py`)
2. **Implement** `generate_strategic_briefing()` method
3. **Enhance** system prompts to include briefing
4. **Test** briefing incorporates history and preferences

### Step 4: AI Tool Integration
**Why Fourth:** Connect evaluation tools to the AI agent.

1. **Write tests** for tool-enabled agent
2. **Implement** `_create_agent_with_tools()` method
3. **Create** tool wrapper functions for Pydantic AI
4. **Test** agent can call tools during decision making

### Step 5: Full Workflow Integration
**Why Last:** This brings all components together.

1. **Write integration tests** (`test_agent_run_integration.py`)
2. **Enhance** `execute_agent_run()` with full proactive workflow
3. **Implement** `make_strategic_decision()` in AIService
4. **Run end-to-end tests** with all components

## Risk Mitigation

**Technical Risks:**
- **Tool Integration Complexity:** Use Pydantic AI's built-in tool system following documentation
- **State Management:** Leverage existing robust StateManager implementation

**Implementation Risks:**
- **Scope Creep:** Stick strictly to 5 core evaluation tools, basic briefing
- **Over-Engineering:** Build on existing patterns, minimal new abstractions
- **Testing Complexity:** Follow existing test patterns, focus on core functionality

## Success Criteria

**MVP Success Metrics:**
1. Agent generates strategic briefings incorporating user preferences and last 10 votes
2. Agent persists and retrieves exactly 10 most recent voting decisions
3. Agent makes more informed decisions using evaluation tools
4. All existing functionality continues to work without regression

**Quality Gates:**
- All existing tests pass (100% backwards compatibility)
- New functionality has >90% test coverage (TDD approach)
- Each component has comprehensive unit tests written before implementation
- Integration tests verify full proactive workflow
- Pearl-compliant logging shows strategic briefing and tool usage
- State persistence correctly maintains 10-item voting history

**Acceptance Testing:**
1. **Voting History:** Verify only 10 most recent votes are persisted
2. **Evaluation Tools:** Each tool correctly analyzes proposals
3. **Strategic Briefing:** Incorporates history, preferences, and insights
4. **Tool Usage:** AI agent successfully calls evaluation tools
5. **End-to-End:** Complete workflow from briefing to vote execution

## Testing Strategy (TDD Focus)

**Test File Structure:**
```
backend/tests/
├── test_agent_run_voting_history.py    # Step 1: Voting history tests
├── test_proposal_evaluation_service.py  # Step 2: Evaluation tools tests
├── test_ai_service_strategic.py        # Step 3: Strategic briefing tests
├── test_agent_run_integration.py       # Step 5: Full integration tests
└── conftest.py                         # Shared fixtures
```

**Test Coverage Requirements:**
- Each new method must have tests written BEFORE implementation
- Minimum 90% coverage for new code
- Test both happy paths and edge cases
- Mock external dependencies (Snapshot API, AI models)
- Use existing test fixtures and patterns

## Key Implementation Notes

### Treasury Pattern Matching
The treasury impact analysis must support multiple formats:
- Standard: "500,000 USDC", "1,000,000 DAI"
- Shorthand: "$2.5M USDC", "1M DAI", "500K USDC"
- Simple: "50 ETH", "100 WETH"
- Handle comma-separated numbers and decimal amounts

### Voting History Constraints
- Exactly 10 most recent decisions (not 100 as in original plan)
- Pruning happens on every save operation
- History includes: proposal_id, vote, confidence, reasoning, timestamp
- Used for pattern analysis and precedent checking

### Tool Integration Pattern
- Tools are methods in ProposalEvaluationService
- AIService wraps tools for Pydantic AI compatibility
- Tools receive proposal context and return structured analysis
- AI agent decides when and which tools to use

## Dependencies

- Existing codebase patterns (already implemented)
- Pydantic AI tool system (already configured)
- StateManager (already implemented)
- No external API changes required

This MVP provides a focused, test-driven approach to making the AI agent proactive while maintaining simplicity and leveraging existing architecture. The 10-vote history limit keeps the system lightweight while still providing sufficient context for strategic decision-making.
