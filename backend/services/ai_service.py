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
        self.model = self._create_model()
        self.agent = self._create_agent()
        self.cache_service = None  # Cache service removed

    def _create_model(self) -> Any:
        """Create the AI model with OpenRouter configuration."""
        logfire.info(
            "Creating AI model",
        )

        assert settings.openrouter_api_key, "OpenRouter API key is not configured"

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

                return VoteDecision(
                    proposal_id=proposal.id,
                    vote=VoteType(decision_data["vote"]),
                    confidence=decision_data["confidence"],
                    reasoning=decision_data["reasoning"],
                    risk_assessment=RiskLevel(decision_data["risk_level"]),
                    strategy_used=strategy,
                )

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
        ai_response = await self._call_ai_model(prompt)
        return self._parse_vote_response(ai_response)

    def _build_vote_decision_prompt(self, proposal: Proposal, strategy: VotingStrategy) -> str:
        """Build the complete prompt for vote decision including strategy-specific instructions."""
        strategy_prompt = self._get_strategy_prompt(strategy)
        
        base_prompt = f"""
        {strategy_prompt}
        
        Please analyze the following DAO proposal and make a voting decision:

        **Proposal Title:** {proposal.title}
        **DAO:** {proposal.dao_name}
        **Current Status:** {proposal.state.value}
        
        **Voting Results:**
        - Votes For: {proposal.votes_for}
        - Votes Against: {proposal.votes_against}
        - Abstain: {proposal.votes_abstain}

        **Proposal Description:**
        {proposal.description}

        Please respond in the following JSON format:
        {{
            "vote": "FOR|AGAINST|ABSTAIN",
            "confidence": 0.85,
            "reasoning": "Brief explanation for your vote decision",
            "risk_level": "LOW|MEDIUM|HIGH"
        }}
        """
        return base_prompt

    async def _call_ai_model(self, prompt: str) -> Dict[str, Any]:
        """Call the AI model with the given prompt."""
        try:
            logfire.info("Calling AI model for vote decision", prompt_length=len(prompt))
            
            result = await self.agent.run(prompt)
            
            if hasattr(result, "output"):
                if isinstance(result.output, str):
                    import json
                    try:
                        return json.loads(result.output)
                    except json.JSONDecodeError:
                        # Fallback for non-JSON responses
                        return {
                            "vote": "ABSTAIN",
                            "confidence": 0.5,
                            "reasoning": result.output,
                            "risk_level": "MEDIUM"
                        }
                return result.output
            else:
                # Fallback response
                return {
                    "vote": "ABSTAIN",
                    "confidence": 0.5,
                    "reasoning": str(result),
                    "risk_level": "MEDIUM"
                }
        except Exception as e:
            logfire.error("AI model call failed", error=str(e))
            raise

    def _parse_vote_response(self, ai_response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate AI vote response."""
        # Parse confidence with error handling for non-numeric values
        confidence_raw = ai_response.get("confidence", 0.5)
        try:
            confidence = float(confidence_raw)
        except (ValueError, TypeError):
            confidence = 0.5  # Default fallback for non-numeric values
        
        parsed = {
            "vote": ai_response.get("vote", "ABSTAIN"),
            "confidence": confidence,
            "reasoning": ai_response.get("reasoning", "No reasoning provided"),
            "risk_level": ai_response.get("risk_level", "MEDIUM"),
        }
        
        # Validate vote value
        valid_votes = ["FOR", "AGAINST", "ABSTAIN"]
        if parsed["vote"] not in valid_votes:
            parsed["vote"] = "ABSTAIN"
        
        # Validate and clamp confidence
        parsed["confidence"] = max(0.0, min(1.0, parsed["confidence"]))
        
        # Validate risk level
        valid_risk_levels = ["LOW", "MEDIUM", "HIGH"]
        if parsed["risk_level"] not in valid_risk_levels:
            parsed["risk_level"] = "MEDIUM"
            
        return parsed


