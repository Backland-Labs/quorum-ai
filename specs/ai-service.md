# AI Service Specification

## Overview

This document defines the architecture, implementation standards, and operational requirements for the AI Service in the Quorum AI application. The service provides dual functionality: proposal summarization for human users and autonomous voting decisions for DAO governance.

## Architecture

### Service Design

The AI Service follows a modular architecture with clear separation of concerns:

```
AIService (Main Service)
├── AIResponseProcessor (Response handling)
├── Pydantic AI Agent (LLM interface)
├── Model Configuration (Provider setup)
└── Strategy Management (Voting behaviors)
```

### Technology Stack

- **Framework**: Pydantic AI
- **Model Provider**: OpenRouter (primary) / Anthropic (fallback)
- **Default Model**: Google Gemini 2.0 Flash
- **Response Format**: Structured Pydantic models
- **Async Support**: Full async/await implementation

## Core Components

### 1. AIService Class

**Purpose**: Main service orchestrating AI operations

**Responsibilities**:
- Model initialization and configuration
- Agent creation and management
- Proposal summarization
- Voting decision making
- Error handling and logging

**Implementation**:
```python
class AIService:
    def __init__(self):
        self.model = self._create_model()
        self.response_processor = AIResponseProcessor()
        self.agent = self._create_agent()
        
        logfire.info(
            "AIService initialized",
            model_type=str(type(self.model))
        )
```

### 2. AIResponseProcessor Class

**Purpose**: Handle AI response parsing and validation

**Key Methods**:
- `process_ai_result()`: Extract and process raw AI output
- `parse_and_validate_vote_response()`: Validate voting decisions
- `_validate_and_sanitize_response()`: Ensure response integrity

**Validation Rules**:
```python
VALID_VOTE_TYPES = ["FOR", "AGAINST", "ABSTAIN"]
VALID_RISK_LEVELS = ["LOW", "MEDIUM", "HIGH"]
DEFAULT_CONFIDENCE_FALLBACK = 0.5
```

### 3. Model Configuration

**Provider Priority**:
1. OpenRouter (via OpenAI-compatible API)
2. Anthropic (direct integration)
3. Fallback to default model

**Configuration**:
```python
def _create_model(self):
    if settings.openrouter_api_key:
        return OpenAIModel(
            "google/gemini-2.0-flash-001",
            provider=OpenRouterProvider(
                api_key=settings.openrouter_api_key
            )
        )
```

## Functional Specifications

### Proposal Summarization

**Purpose**: Generate human-readable summaries of DAO proposals

**Input**: Single or multiple `Proposal` objects

**Output**: `ProposalSummary` with:
- Concise summary (2-3 sentences)
- Key points (3-5 bullet points)
- Risk assessment (level + factors)
- Voting recommendation (optional)

**Implementation**:
```python
async def summarize_proposal(
    self,
    proposal: Proposal,
    include_risk_assessment: bool = True,
    include_recommendations: bool = True
) -> ProposalSummary:
    """Generate AI summary for a single proposal."""
    
    # Runtime assertions
    assert proposal is not None
    assert isinstance(proposal, Proposal)
    
    prompt = self._build_summarization_prompt(
        proposal,
        include_risk_assessment,
        include_recommendations
    )
    
    with logfire.span("ai_proposal_summary", proposal_id=proposal.id):
        result = await self.agent.run(prompt)
        return self._process_summary_response(result, proposal.id)
```

### Autonomous Voting

**Purpose**: Make voting decisions based on configurable strategies

**Voting Strategies**:

1. **Conservative** (Risk-averse)
   - Prioritizes protocol stability
   - Votes against high-risk proposals
   - Requires high confidence (>0.8)
   - Default: ABSTAIN on uncertainty

2. **Balanced** (Moderate)
   - Weighs risks vs benefits
   - Considers community impact
   - Moderate confidence threshold (>0.6)
   - Flexible decision making

3. **Aggressive** (Growth-focused)
   - Favors innovation and expansion
   - Accepts calculated risks
   - Lower confidence threshold (>0.4)
   - Bias toward action

**Decision Process**:
```python
async def decide_vote(
    self,
    proposal: Proposal,
    strategy: VotingStrategy,
) -> VoteDecision:
    """Make autonomous voting decision."""
    
    # Build strategy-specific prompt
    strategy_prompt = self._get_strategy_prompt(strategy)
    prompt = self._build_vote_decision_prompt(
        proposal, 
        strategy_prompt
    )
    
    # Get AI decision
    with logfire.span(
        "ai_vote_decision",
        proposal_id=proposal.id,
        strategy=strategy.value
    ):
        result = await self.agent.run(prompt)
        return self._process_vote_response(result, proposal, strategy)
```

## Response Models

### ProposalSummary

```python
class ProposalSummary(BaseModel):
    proposal_id: str
    summary: str  # 2-3 sentences
    key_points: List[str]  # 3-5 points
    risk_assessment: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Risk level and factors"
    )
    voting_recommendation: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Recommendation with reasoning"
    )
```

### VoteDecision

```python
class VoteDecision(BaseModel):
    proposal_id: str
    vote: VoteType  # FOR, AGAINST, ABSTAIN
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    risk_factors: List[str]
    strategy_alignment: str
```

### AiVoteResponse

```python
class AiVoteResponse(BaseModel):
    vote: str
    confidence: float = Field(ge=0.0, le=1.0) 
    reasoning: str
    risk_level: str
    key_factors: List[str]
    benefits: List[str]
    concerns: List[str]
```

## Error Handling

### Error Types

1. **Model Initialization Errors**
   - Missing API keys
   - Invalid provider configuration
   - Network connectivity issues

2. **Runtime Errors**
   - AI model timeouts
   - Invalid responses
   - Parsing failures

3. **Validation Errors**
   - Invalid vote types
   - Confidence out of range
   - Missing required fields

## Best Practices

### 1. Prompt Design

- Keep prompts focused and specific
- Include relevant context
- Specify output format clearly
- Test prompts with edge cases

### 2. Response Handling

- Always validate AI outputs
- Implement graceful fallbacks
- Log unexpected responses
- Monitor response quality
