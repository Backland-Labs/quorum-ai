"""AI service for proposal analysis with dual functionality: summarization and autonomous voting."""

import asyncio
import json
from typing import Dict, List, Any

from pydantic_ai import Agent, NativeOutput
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from config import settings
from logging_config import setup_pearl_logger, log_span

# Initialize Pearl-compliant logger
logger = setup_pearl_logger(__name__)
from models import (
    Proposal,
    ProposalSummary,
    VoteDecision,
    VoteType,
    VotingStrategy,
    RiskLevel,
    AiVoteResponse,
    StrategicBriefing,
    UserPreferences,
)

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
            logger.debug("Processing AI result with output attribute")
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
        except Exception as e:
            raise e

    def parse_and_validate_vote_response(
        self, ai_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse and validate AI vote response."""
        # Runtime assertion: validate input parameters
        assert ai_response is not None, "AI response cannot be None"
        assert isinstance(
            ai_response, dict
        ), f"Expected dict response, got {type(ai_response)}"

        # Extract raw values with defaults
        raw_values = self._extract_raw_response_values(ai_response)

        # Validate and sanitize all values
        validated_response = self._validate_and_sanitize_response(raw_values)

        # Runtime assertion: validate output structure
        assert isinstance(validated_response, dict), "Validated response must be dict"
        assert (
            "vote" in validated_response
        ), "Validated response must contain 'vote' key"
        assert (
            "confidence" in validated_response
        ), "Validated response must contain 'confidence' key"

        return validated_response

    def _extract_raw_response_values(
        self, ai_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract raw values from AI response with defaults."""
        confidence_raw = ai_response.get("confidence", DEFAULT_CONFIDENCE_FALLBACK)
        parsed_confidence = self._parse_confidence_value(confidence_raw)

        return {
            "vote": ai_response.get("vote", DEFAULT_VOTE_FALLBACK),
            "confidence": parsed_confidence,
            "reasoning": ai_response.get("reasoning", DEFAULT_REASONING_FALLBACK),
            "risk_level": ai_response.get("risk_level", DEFAULT_RISK_LEVEL_FALLBACK),
        }

    def _validate_and_sanitize_response(
        self, raw_values: Dict[str, Any]
    ) -> Dict[str, Any]:
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
        return (
            risk_level
            if risk_level in VALID_RISK_LEVELS
            else DEFAULT_RISK_LEVEL_FALLBACK
        )

    def _create_fallback_response(self, reasoning: str) -> Dict[str, Any]:
        """Create a fallback response when AI output cannot be parsed."""
        return {
            "vote": DEFAULT_VOTE_FALLBACK,
            "confidence": DEFAULT_CONFIDENCE_FALLBACK,
            "reasoning": reasoning,
            "risk_level": DEFAULT_RISK_LEVEL_FALLBACK,
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
    """,
}


class AIService:
    """Service for AI-powered proposal analysis with dual functionality:

    1. Proposal summarization for human users
    2. Autonomous voting decisions for AI agents

    Supports multiple voting strategies and provides comprehensive proposal analysis.
    """

    def __init__(self) -> None:
        """Initialize the AI service with configured model."""
        # Runtime assertion: validate initialization state
        assert (
            settings.openrouter_api_key is not None
        ), "OpenRouter API key must be configured for AI service"
        assert (
            len(settings.openrouter_api_key.strip()) > 0
        ), "OpenRouter API key cannot be empty"

        self.model = self._create_model()
        self.agent = self._create_agent()
        # Cache service removed for autonomous voting focus
        self.response_processor = AIResponseProcessor()

    def _create_model(self) -> Any:
        """Create the AI model with OpenRouter configuration."""
        # Constants for model configuration
        GEMINI_MODEL_NAME = "google/gemini-2.0-flash-001"
        DEFAULT_MODEL_FALLBACK = "openai:gpt-4o-mini"

        logger.info("Creating AI model")

        # Runtime assertion: validate API key configuration
        assert settings.openrouter_api_key, "OpenRouter API key is not configured"
        assert isinstance(
            settings.openrouter_api_key, str
        ), f"API key must be string, got {type(settings.openrouter_api_key)}"

        if settings.openrouter_api_key:
            logger.info("Using OpenRouter")
            try:
                # Create OpenRouter provider
                provider = OpenRouterProvider(api_key=settings.openrouter_api_key)

                # Create model with provider
                model = OpenAIModel(GEMINI_MODEL_NAME, provider=provider)

                # Get model type name for logging
                model_type_name = type(model).__name__
                logger.info(
                    "Successfully created OpenRouter model, model_type=%s",
                    model_type_name,
                )

                # Runtime assertion: validate model creation
                assert model is not None, "OpenRouter model creation returned None"
                assert hasattr(
                    model, "__class__"
                ), "Model must be a valid object instance"

                return model
            except Exception as e:
                error_message = str(e)
                error_type = type(e).__name__
                logger.error(
                    "Failed to create OpenRouter model, error=%s, error_type=%s",
                    error_message,
                    error_type,
                )
                raise
        else:
            logger.warning("No AI API keys configured, using default model")
            return DEFAULT_MODEL_FALLBACK  # TODO: need to fix how this is handled

    def _create_agent(self) -> Any:
        """Create and configure the Pydantic AI agent."""
        # Runtime assertion: validate preconditions
        assert self.model is not None, "Model must be initialized before creating agent"
        assert hasattr(
            self, "model"
        ), "Model attribute must exist before agent creation"

        try:
            # Extract model information for logging
            model_type_name = type(self.model).__name__
            model_value = str(self.model)

            logger.info(
                "Creating Pydantic AI agent, model_type=%s, model_value=%s",
                model_type_name,
                model_value,
            )

            # Create agent with configuration
            system_prompt = self._get_system_prompt()
            output_config = NativeOutput(AiVoteResponse, strict=False)

            agent = Agent(
                model=self.model,
                system_prompt=system_prompt,
                output_type=output_config,
            )

            # Extract agent type for logging
            agent_type_name = type(agent).__name__
            logger.info(
                "Successfully created Pydantic AI agent, agent_type=%s", agent_type_name
            )

            # Runtime assertion: validate agent creation
            assert agent is not None, "Agent creation returned None"
            assert hasattr(agent, "run"), "Agent must have run method"

            return agent
        except Exception as e:
            error_message = str(e)
            error_type = type(e).__name__
            model_type_name = type(self.model).__name__

            logger.error(
                "Failed to create Pydantic AI agent, error=%s, error_type=%s, model_type=%s",
                error_message,
                error_type,
                model_type_name,
            )
            raise

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the AI agent."""
        return """
        You are an expert DAO governance analyst with dual capabilities:

        1. PROPOSAL SUMMARIZATION: Analyze proposals and provide clear, concise summaries
           in plain English for human users. Extract key points, assess risks, and provide
           recommendations to help community members make informed decisions.

        2. AUTONOMOUS VOTING: Make voting decisions on behalf of autonomous agents using
           specified strategies (conservative, balanced, or aggressive). Consider proposal
           content, risk factors, and strategic alignment when deciding.

        For both functions:
        - Be objective, factual, and consider both benefits and potential drawbacks
        - Use clear, non-technical language that any community member can understand
        - Provide well-reasoned analysis based on the proposal content and context
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
        assert isinstance(
            proposal, Proposal
        ), f"Expected Proposal object, got {type(proposal)}"
        assert strategy is not None, "VotingStrategy cannot be None"
        assert isinstance(
            strategy, VotingStrategy
        ), f"Expected VotingStrategy enum, got {type(strategy)}"

        try:
            # Extract logging context
            model_type_name = type(self.model).__name__
            strategy_value = strategy.value

            with log_span(
                logger,
                "ai_vote_decision",
                proposal_id=proposal.id,
                strategy=strategy_value,
            ):
                logger.info(
                    "Starting vote decision making, proposal_id=%s, proposal_title=%s, strategy=%s, model_type=%s",
                    proposal.id,
                    proposal.title,
                    strategy_value,
                    model_type_name,
                )

                # Generate decision data
                decision_data = await self._generate_vote_decision(proposal, strategy)

                # Extract decision values for logging
                vote_value = decision_data.get("vote")
                confidence_value = decision_data.get("confidence")
                risk_level_value = decision_data.get("risk_level")

                logger.info(
                    "Successfully generated vote decision, proposal_id=%s, vote=%s, confidence=%s, risk_level=%s",
                    proposal.id,
                    vote_value,
                    confidence_value,
                    risk_level_value,
                )

                # Create vote decision object
                vote_decision = self._create_vote_decision_from_data(
                    proposal.id, decision_data, strategy
                )

                # Runtime assertion: validate output
                assert vote_decision is not None, "VoteDecision creation returned None"
                assert (
                    vote_decision.proposal_id == proposal.id
                ), "VoteDecision proposal_id mismatch"
                assert hasattr(
                    vote_decision, "vote"
                ), "VoteDecision must have vote attribute"

                return vote_decision

        except Exception as e:
            error_message = str(e)
            error_type = type(e).__name__

            logger.error(
                "Failed to make vote decision, proposal_id=%s, proposal_title=%s, strategy=%s, error=%s, error_type=%s",
                proposal.id,
                proposal.title,
                strategy.value,
                error_message,
                error_type,
            )
            raise e

    def _create_vote_decision_from_data(
        self, proposal_id: str, decision_data: Dict[str, Any], strategy: VotingStrategy
    ) -> VoteDecision:
        """Create VoteDecision object from decision data."""
        return VoteDecision(
            proposal_id=proposal_id,
            vote=VoteType(decision_data["vote"]),
            confidence=decision_data["confidence"],
            reasoning=decision_data["reasoning"],
            risk_assessment=RiskLevel(decision_data["risk_level"]),
            strategy_used=strategy,
        )

    async def _generate_vote_decision(
        self,
        proposal: Proposal,
        strategy: VotingStrategy,
    ) -> Dict[str, Any]:
        """Generate voting decision for a proposal using the specified strategy."""
        prompt = self._build_vote_decision_prompt(proposal, strategy)
        ai_response = await self._call_ai_model(
            prompt
        )  # Use legacy method for test compatibility

        # Handle both dict and object responses for compatibility
        if isinstance(ai_response, dict):
            # Already a dict, use as-is but rename 'vote' to 'vote_decision' for consistency
            formatted_response = {
                "vote": ai_response.get("vote", "ABSTAIN"),
                "reasoning": ai_response.get("reasoning", "No reasoning provided"),
                "confidence": ai_response.get("confidence", 0.5),
                "risk_level": ai_response.get("risk_level", "MEDIUM"),
            }
        else:
            # Object response, convert to dict
            formatted_response = {
                "vote": getattr(ai_response, "vote", "ABSTAIN"),
                "reasoning": getattr(ai_response, "reasoning", "No reasoning provided"),
                "confidence": getattr(ai_response, "confidence", 0.5),
                "risk_level": getattr(ai_response, "risk_level", "MEDIUM"),
            }

        return self.response_processor.parse_and_validate_vote_response(
            formatted_response
        )

    def _parse_vote_response(self, ai_response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate AI vote response.

        This method is a wrapper around the response processor for backwards compatibility.
        """
        return self.response_processor.parse_and_validate_vote_response(ai_response)

    async def _call_ai_model(self, prompt: str) -> Any:
        """Legacy method name for backward compatibility with tests."""
        return await self._call_ai_model_for_vote_decision(prompt)

    def _build_vote_decision_prompt(
        self, proposal: Proposal, strategy: VotingStrategy
    ) -> str:
        """Build the complete prompt for vote decision including strategy-specific instructions."""
        strategy_prompt = self._get_strategy_prompt(strategy)
        proposal_info = self._format_proposal_info(proposal)

        return f"""
        {strategy_prompt}

        Please analyze the following DAO proposal and make a voting decision:

        {proposal_info}
        """

    def _format_proposal_info(self, proposal: Proposal) -> str:
        """Format proposal information for the AI prompt."""
        vote_breakdown = self._extract_vote_breakdown(proposal)
        proposal_description = self._get_proposal_description(proposal)

        return f"""**Proposal Title:** {proposal.title}
        **Network:** {proposal.network} ({proposal.symbol})
        **Current Status:** {proposal.state}

        **Voting Results:**
        - Votes For: {vote_breakdown['for']:,.0f}
        - Votes Against: {vote_breakdown['against']:,.0f}
        - Abstain: {vote_breakdown['abstain']:,.0f}
        - Total Votes: {proposal.votes}

        **Proposal Description:**
        {proposal_description}"""

    def _extract_vote_breakdown(self, proposal: Proposal) -> Dict[str, float]:
        """Extract individual vote counts from proposal scores array."""
        votes_for = proposal.scores[0] if len(proposal.scores) > 0 else 0
        votes_against = proposal.scores[1] if len(proposal.scores) > 1 else 0
        votes_abstain = proposal.scores[2] if len(proposal.scores) > 2 else 0

        return {"for": votes_for, "against": votes_against, "abstain": votes_abstain}

    def _get_proposal_description(self, proposal: Proposal) -> str:
        """Get proposal description with fallback."""
        return getattr(proposal, "body", "No description available")

    async def _call_ai_model_for_vote_decision(self, prompt: str) -> Dict[str, Any]:
        """Call the AI model with the given prompt."""
        # Runtime assertion: validate input
        assert prompt is not None, "Prompt cannot be None"
        assert isinstance(prompt, str), f"Prompt must be string, got {type(prompt)}"

        try:
            prompt_length = len(prompt)
            logger.info(
                "Calling AI model for vote decision, prompt_length=%s", prompt_length
            )

            # Call AI model and process result
            result = await self.agent.run(prompt)
            processed_result = self.response_processor.process_ai_result(result)

            # Runtime assertion: validate output
            assert isinstance(processed_result, dict), "AI result must be a dictionary"

            return processed_result
        except Exception as e:
            error_message = str(e)
            logger.error("AI model call failed, error=%s", error_message)
            raise

    async def summarize_proposal(self, proposal: Proposal) -> ProposalSummary:
        """Generate a summary for a single proposal."""
        # Runtime assertion: validate input parameters
        assert proposal is not None, "Proposal cannot be None"
        assert isinstance(
            proposal, Proposal
        ), f"Expected Proposal object, got {type(proposal)}"

        # Constants for default values
        DEFAULT_CONFIDENCE_SCORE = 0.85
        DEFAULT_RECOMMENDATION = ""

        try:
            # Extract model type for logging
            model_type_name = type(self.model).__name__

            with log_span(logger, "ai_proposal_summary", proposal_id=proposal.id):
                logger.info(
                    "Starting proposal summarization, proposal_id=%s, proposal_title=%s, model_type=%s",
                    proposal.id,
                    proposal.title,
                    model_type_name,
                )

                # Generate summary data
                summary_data = await self._generate_proposal_summary(proposal)

                # Extract metrics for logging
                summary_text = summary_data.get("summary", "")
                key_points_list = summary_data.get("key_points", [])
                summary_length = len(summary_text)
                key_points_count = len(key_points_list)

                logger.info(
                    "Successfully generated proposal summary, proposal_id=%s, summary_length=%s, key_points_count=%s",
                    proposal.id,
                    summary_length,
                    key_points_count,
                )

                # Create proposal summary object
                proposal_summary = self._create_proposal_summary_from_data(
                    proposal,
                    summary_data,
                    DEFAULT_CONFIDENCE_SCORE,
                    DEFAULT_RECOMMENDATION,
                )

                # Runtime assertion: validate output
                assert (
                    proposal_summary is not None
                ), "ProposalSummary creation returned None"
                assert (
                    proposal_summary.proposal_id == proposal.id
                ), "ProposalSummary proposal_id mismatch"
                assert hasattr(
                    proposal_summary, "summary"
                ), "ProposalSummary must have summary attribute"

                return proposal_summary

        except Exception as e:
            error_message = str(e)
            error_type = type(e).__name__

            logger.error(
                "Failed to summarize proposal, proposal_id=%s, proposal_title=%s, error=%s, error_type=%s",
                proposal.id,
                proposal.title,
                error_message,
                error_type,
            )
            raise e

    def _create_proposal_summary_from_data(
        self,
        proposal: Proposal,
        summary_data: Dict[str, Any],
        default_confidence: float,
        default_recommendation: str,
    ) -> ProposalSummary:
        """Create ProposalSummary object from summary data."""
        return ProposalSummary(
            proposal_id=proposal.id,
            title=proposal.title,
            summary=summary_data["summary"],
            key_points=summary_data["key_points"],
            risk_level=summary_data["risk_level"],
            recommendation=summary_data.get("recommendation", default_recommendation),
            confidence_score=default_confidence,
        )

    async def summarize_multiple_proposals(
        self, proposals: List[Proposal]
    ) -> List[ProposalSummary]:
        """Generate summaries for multiple proposals concurrently."""
        # Runtime assertion: validate input parameters
        assert proposals is not None, "Proposals list cannot be None"
        assert isinstance(
            proposals, list
        ), f"Expected list of Proposals, got {type(proposals)}"
        assert len(proposals) > 0, "Proposals list cannot be empty"

        try:
            # Extract context for logging
            proposal_count = len(proposals)
            model_type_name = type(self.model).__name__

            with log_span(
                logger, "ai_multiple_proposal_summaries", proposal_count=proposal_count
            ):
                logger.info(
                    "Starting multiple proposal summarization, proposal_count=%s, model_type=%s",
                    proposal_count,
                    model_type_name,
                )

                # Create tasks for concurrent processing
                summary_tasks = self._create_summary_tasks(proposals)
                summaries = await asyncio.gather(*summary_tasks)

                # Extract summary count for validation
                summary_count = len(summaries)

                logger.info(
                    "Successfully generated multiple proposal summaries, proposal_count=%s, summary_count=%s",
                    proposal_count,
                    summary_count,
                )

                # Runtime assertion: validate output
                assert (
                    summary_count == proposal_count
                ), "Summary count must match proposal count"
                assert all(
                    isinstance(s, ProposalSummary) for s in summaries
                ), "All items must be ProposalSummary objects"

                return summaries

        except Exception as e:
            error_message = str(e)
            error_type = type(e).__name__

            logger.error(
                "Failed to summarize multiple proposals, proposal_count=%s, error=%s, error_type=%s",
                len(proposals),
                error_message,
                error_type,
            )
            raise e

    def _create_summary_tasks(self, proposals: List[Proposal]) -> List:
        """Create async tasks for summarizing proposals."""
        return [self.summarize_proposal(proposal) for proposal in proposals]

    async def _generate_proposal_summary(self, proposal: Proposal) -> Dict[str, Any]:
        """Generate summary data for a proposal."""
        prompt = self._build_summary_prompt(proposal)
        ai_response = await self._call_ai_model_for_summary(prompt)
        return self._parse_and_validate_summary_response(ai_response)

    async def _call_ai_model_for_summary(self, prompt: str) -> Dict[str, Any]:
        """Call the AI model with the given prompt for summarization."""
        # Runtime assertion: validate input
        assert prompt is not None, "Prompt cannot be None"
        assert isinstance(prompt, str), f"Prompt must be string, got {type(prompt)}"

        try:
            prompt_length = len(prompt)
            logger.info(
                "Calling AI model for summarization, prompt_length=%s", prompt_length
            )

            # Call AI model and process result
            result = await self.agent.run(prompt)
            processed_result = self.response_processor.process_ai_result(result)

            # Runtime assertion: validate output
            assert isinstance(processed_result, dict), "AI result must be a dictionary"

            return processed_result
        except Exception as e:
            error_message = str(e)
            logger.error(
                "AI model call failed for summarization, error=%s", error_message
            )
            raise

    def _build_summary_prompt(self, proposal: Proposal) -> str:
        """Build the complete prompt for proposal summarization."""
        proposal_info = self._format_proposal_info(proposal)
        json_format = self._get_summary_json_format()

        return f"""
        Please analyze the following DAO proposal and provide a comprehensive summary:

        {proposal_info}

        {json_format}
        """

    def _get_summary_json_format(self) -> str:
        """Get the JSON response format specification for summarization."""
        return """Please respond in the following JSON format:
        {
            "summary": "A comprehensive summary of the proposal in 2-3 sentences",
            "key_points": ["Key point 1", "Key point 2", "Key point 3"],
            "risk_level": "LOW|MEDIUM|HIGH",
            "recommendation": "Optional recommendation for voters"
        }"""

    def _parse_and_validate_summary_response(
        self, ai_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse and validate AI summary response."""
        # Runtime assertion: validate input parameters
        assert ai_response is not None, "AI response cannot be None"
        assert isinstance(
            ai_response, dict
        ), f"Expected dict response, got {type(ai_response)}"

        # Extract raw values with defaults
        summary = ai_response.get("summary", "No summary provided")
        key_points = ai_response.get("key_points", [])
        risk_level = ai_response.get("risk_level", DEFAULT_RISK_LEVEL_FALLBACK)
        recommendation = ai_response.get("recommendation", "")

        # Validate risk level
        validated_risk_level = self.response_processor._validate_risk_level(risk_level)

        # Ensure key_points is a list
        if not isinstance(key_points, list):
            key_points = [str(key_points)] if key_points else []

        validated_response = {
            "summary": summary,
            "key_points": key_points,
            "risk_level": validated_risk_level,
            "recommendation": recommendation,
        }

        # Runtime assertion: validate output structure
        assert isinstance(validated_response, dict), "Validated response must be dict"
        assert (
            "summary" in validated_response
        ), "Validated response must contain 'summary' key"
        assert (
            "key_points" in validated_response
        ), "Validated response must contain 'key_points' key"

        return validated_response

    async def generate_strategic_briefing(
        self,
        proposals: List[Proposal],
        user_preferences: UserPreferences,
        voting_history: List[VoteDecision],
    ) -> StrategicBriefing:
        """Generate a strategic briefing based on current context.

        Analyzes user preferences, voting history, and active proposals to
        create a comprehensive briefing that will guide the AI agent's
        decision-making process.

        Args:
            proposals: List of active proposals to analyze
            user_preferences: User's voting preferences and strategy
            voting_history: Recent voting decisions (up to 10)

        Returns:
            StrategicBriefing with insights and recommendations
        """
        # Runtime assertions
        assert proposals is not None, "Proposals list cannot be None"
        assert user_preferences is not None, "User preferences cannot be None"
        assert voting_history is not None, "Voting history cannot be None"
        assert isinstance(
            proposals, list
        ), f"Expected list of proposals, got {type(proposals)}"
        assert (
            user_preferences.__class__.__name__ == "UserPreferences"
        ), f"Expected UserPreferences, got {type(user_preferences)}"
        assert isinstance(
            voting_history, list
        ), f"Expected list of VoteDecision, got {type(voting_history)}"

        # Analyze voting history patterns
        historical_patterns = self._analyze_voting_patterns(voting_history)

        # Generate summary based on context
        summary = self._create_strategic_summary(
            proposals, user_preferences, historical_patterns
        )

        # Extract key insights
        key_insights = self._extract_key_insights(
            proposals, user_preferences, voting_history, historical_patterns
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            proposals, user_preferences, historical_patterns
        )

        return StrategicBriefing(
            summary=summary,
            key_insights=key_insights,
            historical_patterns=historical_patterns,
            recommendations=recommendations,
        )

    def _analyze_voting_patterns(
        self, voting_history: List[VoteDecision]
    ) -> Dict[str, Any]:
        """Analyze voting history to identify patterns."""
        if not voting_history:
            return {
                "total_votes": 0,
                "for_votes": 0,
                "against_votes": 0,
                "abstain_votes": 0,
                "average_confidence": 0.0,
                "risk_distribution": {"LOW": 0, "MEDIUM": 0, "HIGH": 0},
                "voting_pattern": "No history available",
            }

        # Count vote types
        vote_counts = {"FOR": 0, "AGAINST": 0, "ABSTAIN": 0}
        risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        total_confidence = 0.0

        for decision in voting_history:
            vote_counts[decision.vote.value] += 1
            risk_counts[decision.risk_assessment.value] += 1
            total_confidence += decision.confidence

        # Analyze patterns
        total_votes = len(voting_history)
        patterns = {
            "total_votes": total_votes,
            "for_votes": vote_counts["FOR"],
            "against_votes": vote_counts["AGAINST"],
            "abstain_votes": vote_counts["ABSTAIN"],
            "average_confidence": round(total_confidence / total_votes, 3)
            if total_votes > 0
            else 0.0,
            "risk_distribution": risk_counts,
        }

        # Determine voting pattern
        if vote_counts["FOR"] > vote_counts["AGAINST"] * 2:
            patterns["voting_pattern"] = "Generally supportive"
        elif vote_counts["AGAINST"] > vote_counts["FOR"] * 2:
            patterns["voting_pattern"] = "Generally cautious"
        else:
            patterns["voting_pattern"] = "Balanced approach"

        # Check for treasury-related patterns
        treasury_votes = [
            d for d in voting_history if "treasury" in d.reasoning.lower()
        ]
        if treasury_votes:
            treasury_against = sum(
                1 for d in treasury_votes if d.vote == VoteType.AGAINST
            )
            patterns["treasury_stance"] = (
                "cautious"
                if treasury_against > len(treasury_votes) / 2
                else "supportive"
            )

        return patterns

    def _create_strategic_summary(
        self,
        proposals: List[Proposal],
        user_preferences: UserPreferences,
        historical_patterns: Dict[str, Any],
    ) -> str:
        """Create a comprehensive strategic summary."""
        proposal_count = len(proposals)
        strategy = user_preferences.voting_strategy.value

        # Base summary components
        summary_parts = [
            f"Strategic briefing for {proposal_count} active proposal{'s' if proposal_count != 1 else ''}",
            f"using {strategy} voting strategy.",
        ]

        # Add preference details
        summary_parts.append(
            f"Confidence threshold: {user_preferences.confidence_threshold}"
        )

        # Add historical context
        if historical_patterns["total_votes"] > 0:
            summary_parts.append(
                f"Recent voting history shows {historical_patterns['voting_pattern'].lower()} "
                f"with {historical_patterns['total_votes']} votes cast."
            )
        else:
            summary_parts.append("No voting history available - new agent deployment.")

        return " ".join(summary_parts)

    def _extract_key_insights(
        self,
        proposals: List[Proposal],
        user_preferences: UserPreferences,
        voting_history: List[VoteDecision],
        historical_patterns: Dict[str, Any],
    ) -> List[str]:
        """Extract key insights from current context."""
        insights = []

        # Insight about voting history
        if historical_patterns["total_votes"] > 0:
            avg_confidence = historical_patterns["average_confidence"]
            if avg_confidence > 0.8:
                insights.append("Recent votes show high confidence in decisions")
            elif avg_confidence < 0.6:
                insights.append(
                    "Recent votes show lower confidence, suggesting complex proposals"
                )

            # Risk pattern insight
            risk_dist = historical_patterns["risk_distribution"]
            if risk_dist["HIGH"] > risk_dist["LOW"] + risk_dist["MEDIUM"]:
                insights.append("Recent proposals have been high-risk")
            elif risk_dist["LOW"] > risk_dist["MEDIUM"] + risk_dist["HIGH"]:
                insights.append("Recent proposals have been low-risk")
        else:
            insights.append("No historical voting data to analyze patterns")

        # Insights about current proposals
        if user_preferences.blacklisted_proposers:
            blacklisted_proposals = [
                p
                for p in proposals
                if p.author in user_preferences.blacklisted_proposers
            ]
            if blacklisted_proposals:
                insights.append(
                    f"{len(blacklisted_proposals)} proposal(s) from blacklisted authors detected"
                )

        if user_preferences.whitelisted_proposers:
            whitelisted_proposals = [
                p
                for p in proposals
                if p.author in user_preferences.whitelisted_proposers
            ]
            if whitelisted_proposals:
                insights.append(
                    f"{len(whitelisted_proposals)} proposal(s) from whitelisted authors available"
                )

        # Treasury pattern insight
        if "treasury_stance" in historical_patterns:
            insights.append(
                f"Historical treasury proposal stance: {historical_patterns['treasury_stance']}"
            )

        # Strategy-specific insights
        if user_preferences.voting_strategy == VotingStrategy.CONSERVATIVE:
            insights.append("Conservative strategy prioritizes risk mitigation")
        elif user_preferences.voting_strategy == VotingStrategy.AGGRESSIVE:
            insights.append("Aggressive strategy favors growth opportunities")
        else:
            insights.append("Balanced strategy seeks optimal risk-reward ratio")

        return insights

    def _generate_recommendations(
        self,
        proposals: List[Proposal],
        user_preferences: UserPreferences,
        historical_patterns: Dict[str, Any],
    ) -> List[str]:
        """Generate strategic recommendations based on analysis."""
        recommendations = []

        # Recommendation based on voting strategy
        if user_preferences.voting_strategy == VotingStrategy.CONSERVATIVE:
            recommendations.append("Maintain conservative stance on treasury proposals")
            recommendations.append("Prioritize proposals with proven track records")
        elif user_preferences.voting_strategy == VotingStrategy.AGGRESSIVE:
            recommendations.append("Consider innovative proposals for growth potential")
            recommendations.append("Accept higher risk for potential rewards")
        else:
            recommendations.append("Evaluate each proposal on merit and alignment")
            recommendations.append("Balance risk and reward in voting decisions")

        # Recommendations based on preferences
        if user_preferences.whitelisted_proposers:
            recommendations.append("Prioritize proposals from whitelisted authors")

        if user_preferences.blacklisted_proposers:
            recommendations.append("Avoid proposals from blacklisted authors")

        # Recommendations based on history
        if historical_patterns["total_votes"] > 0:
            if historical_patterns["average_confidence"] < 0.7:
                recommendations.append(
                    "Consider more thorough analysis for complex proposals"
                )

            if (
                "treasury_stance" in historical_patterns
                and historical_patterns["treasury_stance"] == "cautious"
            ):
                recommendations.append(
                    "Continue cautious approach to treasury requests"
                )

        # Confidence threshold recommendation
        recommendations.append(
            f"Only vote on proposals with confidence above {user_preferences.confidence_threshold}"
        )

        return recommendations

    def _get_strategic_system_prompt(
        self, briefing: StrategicBriefing, strategy: VotingStrategy
    ) -> str:
        """Get enhanced system prompt including strategic briefing.

        Creates a comprehensive system prompt that includes the base agent
        instructions, strategy-specific guidance, and the strategic briefing
        context for improved decision-making.
        """
        # Get base system prompt
        base_prompt = self._get_system_prompt()

        # Get strategy-specific prompt
        strategy_prompt = self._get_strategy_prompt(strategy)

        # Format briefing content
        briefing_content = f"""
STRATEGIC BRIEFING:
{briefing.summary}

KEY INSIGHTS:
{chr(10).join(f"- {insight}" for insight in briefing.key_insights)}

RECOMMENDATIONS:
{chr(10).join(f"- {rec}" for rec in briefing.recommendations)}

HISTORICAL PATTERNS:
- Total votes analyzed: {briefing.historical_patterns.get('total_votes', 0)}
- Average confidence: {briefing.historical_patterns.get('average_confidence', 0):.2f}
- Voting pattern: {briefing.historical_patterns.get('voting_pattern', 'No pattern available')}
"""

        # Combine all prompts
        return f"{base_prompt}\n\n{strategy_prompt}\n\n{briefing_content}"

    async def decide_votes(
        self, proposals: List[Proposal], user_preferences: UserPreferences
    ) -> List[VoteDecision]:
        """Make voting decisions for multiple proposals.
        
        Args:
            proposals: List of proposals to vote on
            user_preferences: User voting preferences
            
        Returns:
            List of VoteDecision objects
        """
        # Process each proposal with the user's strategy
        decisions = []
        for proposal in proposals:
            decision = await self.decide_vote(proposal, user_preferences.voting_strategy)
            decisions.append(decision)
        return decisions

    async def make_strategic_decision(
        self,
        proposals: List[Proposal],
        user_preferences: UserPreferences,
        briefing: StrategicBriefing,
        voting_history: List[VoteDecision]
    ) -> List[VoteDecision]:
        """Make voting decisions using strategic context and evaluation tools.
        
        This enhanced method uses the strategic briefing and voting history
        to make more informed decisions. It also integrates evaluation tools
        for comprehensive proposal analysis.
        
        Args:
            proposals: List of proposals to vote on
            user_preferences: User voting preferences
            briefing: Strategic briefing with context and recommendations
            voting_history: Recent voting history for pattern analysis
            
        Returns:
            List of VoteDecision objects with strategic reasoning
        """
        decisions = []
        
        # If no briefing available, fall back to regular decision making
        if not briefing:
            return await self.decide_votes(proposals, user_preferences)
        
        # Process each proposal with strategic context
        for proposal in proposals:
            # Use enhanced system prompt with briefing
            enhanced_prompt = self._get_strategic_system_prompt(
                briefing, user_preferences.voting_strategy
            )
            
            # Build proposal-specific prompt
            proposal_prompt = self._build_vote_prompt(proposal)
            
            # Create agent with enhanced context
            agent = Agent(
                model=self.model,
                result_type=AiVoteResponse,
                system_prompt=enhanced_prompt
            )
            
            # Run the agent to get decision
            result = await agent.run(proposal_prompt)
            
            # Process the result
            vote_data = self.response_processor.process_vote_response(result)
            
            # Create VoteDecision with strategic context
            decision = VoteDecision(
                proposal_id=proposal.id,
                vote=vote_data["vote"],
                confidence=vote_data["confidence"],
                reasoning=vote_data["reasoning"],
                risk_assessment=vote_data["risk_assessment"],
                strategy_used=user_preferences.voting_strategy
            )
            
            decisions.append(decision)
            
            # Log strategic decision
            logger.info(
                "Made strategic decision for proposal",
                extra={
                    "proposal_id": proposal.id,
                    "vote": decision.vote.value,
                    "confidence": decision.confidence,
                    "strategy": user_preferences.voting_strategy.value,
                    "briefing_available": True
                }
            )
        
        return decisions

    def _create_agent_with_tools(self, context: Dict[str, Any]) -> Agent:
        """Create an AI agent with evaluation tools for enhanced decision making.
        
        This method will be implemented to integrate ProposalEvaluationService
        tools with the Pydantic AI agent for comprehensive proposal analysis.
        
        Args:
            context: Context dictionary containing proposals and voting history
            
        Returns:
            Agent configured with evaluation tools
        """
        # TODO: Implement tool integration with ProposalEvaluationService
        # For now, return regular agent
        return self.agent
