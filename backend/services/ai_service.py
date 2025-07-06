"""AI service for proposal summarization using Pydantic AI."""

import asyncio
import hashlib
import json
from typing import Dict, List, Any, Optional, Union

import logfire
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from config import settings
from models import Proposal, ProposalSummary, VoteDecision, VoteType, VotingStrategy, RiskLevel
from services.cache_service import CacheService


# Constants for AI response parsing
DEFAULT_VOTE_FALLBACK = "ABSTAIN"
DEFAULT_CONFIDENCE_FALLBACK = 0.5
DEFAULT_REASONING_FALLBACK = "No reasoning provided"
DEFAULT_RISK_LEVEL_FALLBACK = "MEDIUM"
VALID_VOTE_TYPES = ["FOR", "AGAINST", "ABSTAIN"]
VALID_RISK_LEVELS = ["LOW", "MEDIUM", "HIGH"]


class AIResponseProcessor:
    """Cohesive class for handling AI response processing and validation."""
    
    def __init__(self):
        """Initialize the response processor."""
        # Runtime assertion: validate constants are properly configured
        assert VALID_VOTE_TYPES, "Valid vote types must be configured"
        assert VALID_RISK_LEVELS, "Valid risk levels must be configured"
    
    def process_ai_result(self, result: Any) -> Dict[str, Any]:
        """Process the AI model result and extract output."""
        # Runtime assertion: validate input
        assert result is not None, "AI result cannot be None"
        
        if hasattr(result, "output"):
            return self._extract_output_data(result.output)
        else:
            return self._create_fallback_response(str(result))
    
    def _extract_output_data(self, output: Any) -> Dict[str, Any]:
        """Extract and parse output data from AI response."""
        if isinstance(output, str):
            return self._parse_json_output(output)
        return output
    
    def _parse_json_output(self, output: str) -> Dict[str, Any]:
        """Parse JSON output from AI response."""
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return self._create_fallback_response(output)
    
    def parse_and_validate_vote_response(self, ai_response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate AI vote response."""
        # Runtime assertion: validate input parameters
        assert ai_response is not None, "AI response cannot be None"
        assert isinstance(ai_response, dict), f"Expected dict response, got {type(ai_response)}"
        
        # Extract raw values with defaults
        raw_values = self._extract_raw_response_values(ai_response)
        
        # Validate and sanitize all values
        validated_response = self._validate_and_sanitize_response(raw_values)
        
        # Runtime assertion: validate output structure
        assert isinstance(validated_response, dict), "Validated response must be dict"
        assert "vote" in validated_response, "Validated response must contain 'vote' key"
        assert "confidence" in validated_response, "Validated response must contain 'confidence' key"
        
        return validated_response
    
    def _extract_raw_response_values(self, ai_response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract raw values from AI response with defaults."""
        confidence_raw = ai_response.get("confidence", DEFAULT_CONFIDENCE_FALLBACK)
        parsed_confidence = self._parse_confidence_value(confidence_raw)
        
        return {
            "vote": ai_response.get("vote", DEFAULT_VOTE_FALLBACK),
            "confidence": parsed_confidence,
            "reasoning": ai_response.get("reasoning", DEFAULT_REASONING_FALLBACK),
            "risk_level": ai_response.get("risk_level", DEFAULT_RISK_LEVEL_FALLBACK),
        }
    
    def _validate_and_sanitize_response(self, raw_values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize all response values."""
        validated_vote = self._validate_vote_type(raw_values["vote"])
        clamped_confidence = max(0.0, min(1.0, raw_values["confidence"]))
        validated_risk_level = self._validate_risk_level(raw_values["risk_level"])
        
        return {
            "vote": validated_vote,
            "confidence": clamped_confidence,
            "reasoning": raw_values["reasoning"],
            "risk_level": validated_risk_level,
        }

    def _parse_confidence_value(self, confidence_raw: Any) -> float:
        """Parse confidence value from AI response with error handling."""
        try:
            return float(confidence_raw)
        except (ValueError, TypeError):
            return DEFAULT_CONFIDENCE_FALLBACK

    def _validate_vote_type(self, vote: str) -> str:
        """Validate and sanitize vote type value."""
        return vote if vote in VALID_VOTE_TYPES else DEFAULT_VOTE_FALLBACK

    def _validate_risk_level(self, risk_level: str) -> str:
        """Validate and sanitize risk level value."""
        return risk_level if risk_level in VALID_RISK_LEVELS else DEFAULT_RISK_LEVEL_FALLBACK

    def _create_fallback_response(self, reasoning: str) -> Dict[str, Any]:
        """Create a fallback response when AI output cannot be parsed."""
        return {
            "vote": DEFAULT_VOTE_FALLBACK,
            "confidence": DEFAULT_CONFIDENCE_FALLBACK,
            "reasoning": reasoning,
            "risk_level": DEFAULT_RISK_LEVEL_FALLBACK
        }


# Strategy-specific prompts for voting decisions
STRATEGY_PROMPTS = {
    VotingStrategy.CONSERVATIVE: """
    You are a conservative DAO voter. Prioritize:
    - Treasury protection
    - Minimal risk
    - Proven track records
    Vote AGAINST proposals with high risk or unproven teams.
    """,
    VotingStrategy.BALANCED: """
    You are a balanced DAO voter. Consider:
    - Risk vs reward tradeoffs
    - Community benefit
    - Long-term sustainability
    """,
    VotingStrategy.AGGRESSIVE: """
    You are a growth-oriented DAO voter. Favor:
    - Innovation and experimentation
    - Growth opportunities
    - New initiatives
    Vote FOR proposals that could drive growth.
    """
}


class AIService:
    """Service for AI-powered proposal analysis and summarization."""

    def __init__(self, cache_service: Optional[CacheService] = None) -> None:
        """Initialize the AI service with configured model."""
        # Runtime assertion: validate initialization state
        assert settings.openrouter_api_key is not None, "OpenRouter API key must be configured for AI service"
        assert len(settings.openrouter_api_key.strip()) > 0, "OpenRouter API key cannot be empty"
        
        self.model = self._create_model()
        self.agent = self._create_agent()
        self.cache_service = None  # Cache service removed
        self.response_processor = AIResponseProcessor()
        
        # Runtime assertion: validate successful initialization
        assert self.model is not None, "AI model must be successfully initialized"
        assert self.agent is not None, "AI agent must be successfully initialized"

    def _create_model(self) -> Any:
        """Create the AI model with OpenRouter configuration."""
        logfire.info(
            "Creating AI model",
        )

        # Runtime assertion: validate API key configuration
        assert settings.openrouter_api_key, "OpenRouter API key is not configured"
        assert isinstance(settings.openrouter_api_key, str), f"API key must be string, got {type(settings.openrouter_api_key)}"

        if settings.openrouter_api_key:
            logfire.info("Using OpenRouter with Claude 3.5 Sonnet")
            try:
                model = OpenAIModel(
                    "openrouter/auto",
                    provider=OpenRouterProvider(api_key=settings.openrouter_api_key),
                )
                logfire.info(
                    "Successfully created OpenRouter model", model_type=str(type(model))
                )
                
                # Runtime assertion: validate model creation
                assert model is not None, "OpenRouter model creation returned None"
                
                return model
            except Exception as e:
                logfire.error(
                    "Failed to create OpenRouter model",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise
        else:
            logfire.warning("No AI API keys configured, using default model")
            return "openai:gpt-4o-mini"  # TODO: need to fix how this is handled

    def _create_agent(self) -> Agent:
        """Create and configure the Pydantic AI agent."""
        # Runtime assertion: validate preconditions
        assert self.model is not None, "Model must be initialized before creating agent"
        assert hasattr(self, 'model'), "Model attribute must exist before agent creation"
        
        try:
            logfire.info(
                "Creating Pydantic AI agent",
                model_type=str(type(self.model)),
                model_value=str(self.model),
            )

            agent = Agent(
                model=self.model,
                system_prompt=self._get_system_prompt(),
            )

            logfire.info(
                "Successfully created Pydantic AI agent", agent_type=str(type(agent))
            )
            
            # Runtime assertion: validate agent creation
            assert agent is not None, "Agent creation returned None"
            assert hasattr(agent, 'run'), "Agent must have run method for API calls"
            
            return agent
        except Exception as e:
            logfire.error(
                "Failed to create Pydantic AI agent",
                error=str(e),
                error_type=type(e).__name__,
                model_type=str(type(self.model)),
            )
            raise

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the AI agent."""
        return """
        You are an expert DAO governance analyst. Your job is to analyze blockchain governance
        proposals and provide clear, concise summaries in plain English.

        For each proposal, you should:
        1. Summarize the main purpose and changes proposed
        2. Extract key points that voters should know
        3. Assess risks if requested
        4. Provide recommendations if requested

        Always be objective, factual, and consider both benefits and potential drawbacks.
        Use clear, non-technical language that any community member can understand.
        """

    def _get_strategy_prompt(self, strategy: VotingStrategy) -> str:
        """Get the strategy-specific prompt for the given voting strategy."""
        return STRATEGY_PROMPTS.get(strategy, STRATEGY_PROMPTS[VotingStrategy.BALANCED])

    async def decide_vote(
        self,
        proposal: Proposal,
        strategy: VotingStrategy,
    ) -> VoteDecision:
        """Make a voting decision for a proposal using the specified strategy."""
        # Runtime assertion: validate input parameters
        assert proposal is not None, "Proposal cannot be None"
        assert isinstance(proposal, Proposal), f"Expected Proposal object, got {type(proposal)}"
        assert strategy is not None, "VotingStrategy cannot be None"
        assert isinstance(strategy, VotingStrategy), f"Expected VotingStrategy enum, got {type(strategy)}"
        
        try:
            with logfire.span("ai_vote_decision", proposal_id=proposal.id, strategy=strategy.value):
                logfire.info(
                    "Starting vote decision making",
                    proposal_id=proposal.id,
                    proposal_title=proposal.title,
                    strategy=strategy.value,
                    model_type=str(type(self.model)),
                )

                decision_data = await self._generate_vote_decision(proposal, strategy)

                logfire.info(
                    "Successfully generated vote decision",
                    proposal_id=proposal.id,
                    vote=decision_data.get("vote"),
                    confidence=decision_data.get("confidence"),
                    risk_level=decision_data.get("risk_level"),
                )

                vote_decision = VoteDecision(
                    proposal_id=proposal.id,
                    vote=VoteType(decision_data["vote"]),
                    confidence=decision_data["confidence"],
                    reasoning=decision_data["reasoning"],
                    risk_assessment=RiskLevel(decision_data["risk_level"]),
                    strategy_used=strategy,
                )
                
                # Runtime assertion: validate output
                assert vote_decision is not None, "VoteDecision creation returned None"
                assert vote_decision.proposal_id == proposal.id, "VoteDecision proposal_id mismatch"
                
                return vote_decision

        except Exception as e:
            logfire.error(
                "Failed to make vote decision",
                proposal_id=proposal.id,
                proposal_title=proposal.title,
                strategy=strategy.value,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise e

    async def _generate_vote_decision(
        self,
        proposal: Proposal,
        strategy: VotingStrategy,
    ) -> Dict[str, Any]:
        """Generate voting decision for a proposal using the specified strategy."""
        prompt = self._build_vote_decision_prompt(proposal, strategy)
        ai_response = await self._call_ai_model(prompt)  # Use legacy method for test compatibility
        return self.response_processor.parse_and_validate_vote_response(ai_response)

    async def _call_ai_model(self, prompt: str) -> Dict[str, Any]:
        """Legacy method name for backward compatibility with tests."""
        return await self._call_ai_model_for_vote_decision(prompt)


    def _build_vote_decision_prompt(self, proposal: Proposal, strategy: VotingStrategy) -> str:
        """Build the complete prompt for vote decision including strategy-specific instructions."""
        strategy_prompt = self._get_strategy_prompt(strategy)
        proposal_info = self._format_proposal_info(proposal)
        json_format = self._get_json_response_format()
        
        return f"""
        {strategy_prompt}
        
        Please analyze the following DAO proposal and make a voting decision:

        {proposal_info}

        {json_format}
        """
    
    def _format_proposal_info(self, proposal: Proposal) -> str:
        """Format proposal information for the AI prompt."""
        return f"""**Proposal Title:** {proposal.title}
        **DAO:** {proposal.dao_name}
        **Current Status:** {proposal.state.value}
        
        **Voting Results:**
        - Votes For: {proposal.votes_for}
        - Votes Against: {proposal.votes_against}
        - Abstain: {proposal.votes_abstain}

        **Proposal Description:**
        {proposal.description}"""
    
    def _get_json_response_format(self) -> str:
        """Get the JSON response format specification."""
        return """Please respond in the following JSON format:
        {
            "vote": "FOR|AGAINST|ABSTAIN",
            "confidence": 0.85,
            "reasoning": "Brief explanation for your vote decision",
            "risk_level": "LOW|MEDIUM|HIGH"
        }"""

    async def _call_ai_model_for_vote_decision(self, prompt: str) -> Dict[str, Any]:
        """Call the AI model with the given prompt."""
        try:
            logfire.info("Calling AI model for vote decision", prompt_length=len(prompt))
            
            result = await self.agent.run(prompt)
            return self.response_processor.process_ai_result(result)
        except Exception as e:
            logfire.error("AI model call failed", error=str(e))
            raise
    
    # Legacy method for backward compatibility with tests
    def _parse_and_validate_vote_response(self, ai_response: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy method - delegates to response processor."""
        return self.response_processor.parse_and_validate_vote_response(ai_response)
    
    # Legacy method for backward compatibility with tests
    def _parse_vote_response(self, ai_response: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy method - delegates to response processor."""
        return self.response_processor.parse_and_validate_vote_response(ai_response)


