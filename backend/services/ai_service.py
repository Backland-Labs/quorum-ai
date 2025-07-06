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
        # Placeholder implementation - will be enhanced in later cycles
        return {
            "vote": "FOR",
            "confidence": 0.8,
            "reasoning": f"Decision made using {strategy.value} strategy for proposal: {proposal.title}",
            "risk_level": "MEDIUM"
        }


