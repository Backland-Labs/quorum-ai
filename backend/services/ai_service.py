"""AI service for proposal analysis with dual functionality: summarization and autonomous voting."""

import asyncio
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Optional

from pydantic_ai import Agent, NativeOutput, RunContext
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
    UserPreferences,
    VotingDecisionFile,
)
from services.snapshot_service import SnapshotService
from services.state_manager import StateManager

# Constants for AI response parsing
DEFAULT_VOTE_FALLBACK = "ABSTAIN"
DEFAULT_CONFIDENCE_FALLBACK = 0.5
DEFAULT_REASONING_FALLBACK = "No reasoning provided"
DEFAULT_RISK_LEVEL_FALLBACK = "MEDIUM"
VALID_VOTE_TYPES = ["FOR", "AGAINST", "ABSTAIN"]
VALID_RISK_LEVELS = ["LOW", "MEDIUM", "HIGH"]

# Constants for tool optimization
MAX_PROPOSAL_BODY_LENGTH = 500  # Characters to include in proposal summaries


class DecisionFileError(Exception):
    """Custom exception for decision file operations."""
    
    def __init__(self, message: str, file_path: Optional[str] = None):
        self.file_path = file_path
        super().__init__(message)


@dataclass
class VotingDependencies:
    """Dependency injection container for VotingAgent tools."""

    snapshot_service: SnapshotService
    user_preferences: UserPreferences
    state_manager: Optional[StateManager] = None

    def __post_init__(self):
        """Runtime assertions for dependency validation."""
        assert self.snapshot_service is not None, "SnapshotService required"
        assert self.user_preferences is not None, "UserPreferences required"


class VotingAgent:
    """Pydantic AI Agent for autonomous voting decisions."""

    # Model configuration constants
    GEMINI_MODEL_NAME = "google/gemini-2.0-flash-001"

    def __init__(self):
        """Initialize the VotingAgent with model, agent, and tools."""
        self.logger = setup_pearl_logger(__name__)
        self.model = self._create_model()
        self.agent = self._create_agent()
        self.response_processor = AIResponseProcessor()
        self._register_tools()

    def _create_model(self) -> Any:
        """Create the AI model with OpenRouter configuration."""
        self.logger.info("Creating AI model for VotingAgent")

        # Runtime assertion: validate API key configuration
        assert settings.openrouter_api_key, "OpenRouter API key is not configured"
        assert isinstance(
            settings.openrouter_api_key, str
        ), f"API key must be string, got {type(settings.openrouter_api_key)}"

        try:
            # Create OpenRouter provider
            provider = OpenRouterProvider(api_key=settings.openrouter_api_key)

            # Create model with provider
            model = OpenAIModel(self.GEMINI_MODEL_NAME, provider=provider)

            # Get model type name for logging
            model_type_name = type(model).__name__
            self.logger.info(
                "Successfully created OpenRouter model for VotingAgent, model_type=%s",
                model_type_name,
            )

            # Runtime assertion: validate model creation
            assert model is not None, "OpenRouter model creation returned None"
            assert hasattr(model, "__class__"), "Model must be a valid object instance"

            return model
        except Exception as e:
            error_message = str(e)
            error_type = type(e).__name__
            self.logger.error(
                "Failed to create OpenRouter model for VotingAgent, error=%s, error_type=%s",
                error_message,
                error_type,
            )
            raise

    def _create_agent(self) -> Agent:
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

            self.logger.info(
                "Creating Pydantic AI VotingAgent, model_type=%s, model_value=%s",
                model_type_name,
                model_value,
            )

            # Create agent with configuration
            system_prompt = self._get_base_system_prompt()
            output_config = NativeOutput(AiVoteResponse, strict=False)

            agent = Agent(
                model=self.model,
                system_prompt=system_prompt,
                output_type=output_config,
            )

            # Extract agent type for logging
            agent_type_name = type(agent).__name__
            self.logger.info(
                "Successfully created Pydantic AI VotingAgent, agent_type=%s",
                agent_type_name,
            )

            # Runtime assertion: validate agent creation
            assert agent is not None, "Agent creation returned None"
            assert hasattr(agent, "run"), "Agent must have run method"

            return agent
        except Exception as e:
            error_message = str(e)
            error_type = type(e).__name__
            model_type_name = type(self.model).__name__

            self.logger.error(
                "Failed to create Pydantic AI VotingAgent, error=%s, error_type=%s, model_type=%s",
                error_message,
                error_type,
                model_type_name,
            )
            raise

    def _get_base_system_prompt(self) -> str:
        """Get the base system prompt for the AI agent."""
        return """
        You are an expert DAO governance analyst specializing in autonomous voting decisions.

        Your role is to make voting decisions on behalf of autonomous agents using
        specified strategies (conservative, balanced, or aggressive). Consider proposal
        content, risk factors, and strategic alignment when deciding.

        Always:
        - Be objective, factual, and consider both benefits and potential drawbacks
        - Use clear reasoning that explains your decision
        - Provide confidence scores that reflect the certainty of your analysis
        - Consider the voting strategy when making decisions
        """

    def _get_system_prompt_for_strategy(self, strategy: VotingStrategy) -> str:
        """Get the strategy-specific system prompt for the given voting strategy."""
        base_prompt = self._get_base_system_prompt()

        strategy_prompts = {
            VotingStrategy.CONSERVATIVE: """
            Conservative Strategy Guidelines:
            - Prioritize safety and stability of the protocol
            - Vote AGAINST proposals with high risk or uncertain outcomes
            - Support only well-tested, incremental improvements
            - Require strong evidence and community consensus
            - Favor proposals that protect existing stakeholders
            """,
            VotingStrategy.BALANCED: """
            Balanced Strategy Guidelines:
            - Weigh risks and benefits equally
            - Support proposals with reasonable risk-reward ratios
            - Consider both short-term impact and long-term vision
            - Look for proposals with broad community support
            - Balance innovation with stability
            """,
            VotingStrategy.AGGRESSIVE: """
            Aggressive Strategy Guidelines:
            - Focus on growth and innovation opportunities
            - Accept higher risks for potentially higher rewards
            - Support proposals that drive adoption and expansion
            - Favor bold changes that could provide competitive advantages
            - Prioritize long-term growth over short-term stability
            """,
        }

        return (
            base_prompt
            + "\n\n"
            + strategy_prompts.get(strategy, strategy_prompts[VotingStrategy.BALANCED])
        )

    def _proposal_to_dict(self, proposal: Proposal, include_full_body: bool = False) -> Dict[str, Any]:
        """Convert a Proposal object to a dictionary optimized for agent consumption.
        
        Args:
            proposal: The Proposal object to convert
            include_full_body: Whether to include the full proposal body
            
        Returns:
            Dictionary representation of the proposal
        """
        body = proposal.body
        if not include_full_body and len(body) > MAX_PROPOSAL_BODY_LENGTH:
            body = body[:MAX_PROPOSAL_BODY_LENGTH] + "..."
            
        return {
            'id': proposal.id,
            'title': proposal.title,
            'body': body,
            'choices': proposal.choices,
            'author': proposal.author,
            'start': proposal.start,
            'end': proposal.end,
            'state': getattr(proposal, 'state', None),
            'space': getattr(proposal, 'space', None),
            'type': getattr(proposal, 'type', None),
            'scores': proposal.scores,
            'scores_total': proposal.scores_total,
            'votes': proposal.votes,
            'created': getattr(proposal, 'created', None),
            'updated': getattr(proposal, 'updated', None),
            'snapshot': getattr(proposal, 'snapshot', None),
            'privacy': getattr(proposal, 'privacy', None),
            'link': getattr(proposal, 'link', None)
        }

    def _register_tools(self):
        """Register agent tools for Snapshot integration."""
        
        @self.agent.tool
        async def query_active_proposals(
            ctx: RunContext[VotingDependencies], 
            space_id: str
        ) -> List[Dict[str, Any]]:
            """Fetch active proposals for a given space.
            
            Args:
                ctx: Agent runtime context with dependencies
                space_id: The ID of the Snapshot space to query
                
            Returns:
                List of proposal dictionaries with key fields
            """
            self.logger.debug(
                "query_active_proposals tool called, space_id=%s", space_id
            )
            
            # Runtime assertions
            assert ctx.deps is not None, "Dependencies must be available"
            assert ctx.deps.snapshot_service is not None, "SnapshotService must be available"
            assert space_id, "space_id must not be empty"
            
            try:
                # Use the injected SnapshotService to fetch proposals
                proposals = await ctx.deps.snapshot_service.get_proposals(
                    space_id=space_id, 
                    state="active"
                )
                
                # Convert proposals to dictionaries optimized for agent consumption
                result = [self._proposal_to_dict(proposal) for proposal in proposals]
                
                self.logger.info(
                    "query_active_proposals returned %d proposals for space_id=%s",
                    len(result),
                    space_id
                )
                return result
                
            except Exception as e:
                self.logger.error(
                    "Error in query_active_proposals tool, space_id=%s, error=%s",
                    space_id,
                    str(e)
                )
                raise
        
        @self.agent.tool
        async def get_proposal_details(
            ctx: RunContext[VotingDependencies],
            proposal_id: str
        ) -> Dict[str, Any]:
            """Get comprehensive details for a specific proposal.
            
            Args:
                ctx: Agent runtime context with dependencies
                proposal_id: The ID of the proposal to fetch
                
            Returns:
                Dictionary with comprehensive proposal data
            """
            self.logger.debug(
                "get_proposal_details tool called, proposal_id=%s", proposal_id
            )
            
            # Runtime assertions
            assert ctx.deps is not None, "Dependencies must be available"
            assert ctx.deps.snapshot_service is not None, "SnapshotService must be available"
            assert proposal_id, "proposal_id must not be empty"
            
            try:
                # Fetch the proposal using SnapshotService
                proposal = await ctx.deps.snapshot_service.get_proposal(proposal_id)
                
                # Return comprehensive proposal data with full body
                result = self._proposal_to_dict(proposal, include_full_body=True)
                
                self.logger.info(
                    "get_proposal_details returned data for proposal_id=%s",
                    proposal_id
                )
                return result
                
            except Exception as e:
                self.logger.error(
                    "Error in get_proposal_details tool, proposal_id=%s, error=%s", 
                    proposal_id,
                    str(e)
                )
                raise
        
        @self.agent.tool
        async def get_voting_power(
            ctx: RunContext[VotingDependencies],
            address: str,
            space_id: str
        ) -> float:
            """Calculate voting power for an address in a space.
            
            Args:
                ctx: Agent runtime context with dependencies
                address: The blockchain address to check
                space_id: The Snapshot space ID
                
            Returns:
                Float representing the voting power
            """
            self.logger.debug(
                "get_voting_power tool called, address=%s, space_id=%s",
                address,
                space_id
            )
            
            # Runtime assertions
            assert ctx.deps is not None, "Dependencies must be available"
            assert address, "address must not be empty"
            assert space_id, "space_id must not be empty"
            
            try:
                # For now, use a simple implementation
                # In future, this would integrate with actual voting power calculation
                if hasattr(ctx.deps.snapshot_service, 'calculate_voting_power'):
                    power = await ctx.deps.snapshot_service.calculate_voting_power(
                        address=address,
                        space_id=space_id
                    )
                else:
                    # Default implementation if method doesn't exist
                    self.logger.warning(
                        "SnapshotService.calculate_voting_power not implemented, returning default"
                    )
                    power = 0.0
                
                self.logger.info(
                    "get_voting_power returned %f for address=%s in space_id=%s",
                    power,
                    address,
                    space_id
                )
                return power
                
            except Exception as e:
                self.logger.error(
                    "Error in get_voting_power tool, address=%s, space_id=%s, error=%s",
                    address,
                    space_id,
                    str(e)
                )
                raise


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

    def __init__(self, snapshot_service: Optional[SnapshotService] = None) -> None:
        """Initialize the AI service with configured model."""
        # Runtime assertion: validate initialization state
        assert (
            settings.openrouter_api_key is not None
        ), "OpenRouter API key must be configured for AI service"
        assert (
            len(settings.openrouter_api_key.strip()) > 0
        ), "OpenRouter API key cannot be empty"

        # Initialize services
        self.snapshot_service = snapshot_service or SnapshotService()
        
        # Initialize VotingAgent for refactored architecture
        self.voting_agent = VotingAgent()

        # Maintain backward compatibility with existing model/agent
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
        strategy: Optional[VotingStrategy] = None,
        user_preferences: Optional[UserPreferences] = None,
        save_to_file: bool = True,
    ) -> VoteDecision:
        """Make a voting decision for a proposal using the specified strategy."""
        # Runtime assertion: validate input parameters
        assert proposal is not None, "Proposal cannot be None"
        assert isinstance(
            proposal, Proposal
        ), f"Expected Proposal object, got {type(proposal)}"
        
        # Determine strategy from user_preferences or parameter
        if user_preferences:
            strategy = user_preferences.voting_strategy
        elif strategy is None:
            strategy = VotingStrategy.BALANCED  # Default strategy
            
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

                # Save to file if requested
                if save_to_file:
                    decision_file = VotingDecisionFile(
                        proposal_id=proposal.id,
                        proposal_title=proposal.title,
                        space_id=proposal.space_id or "unknown",
                        vote=vote_decision.vote.value,
                        confidence=vote_decision.confidence,
                        risk_level=vote_decision.risk_assessment,
                        reasoning=vote_decision.reasoning.split(". "),
                        voting_strategy=strategy,
                        dry_run=False  # Set based on context
                    )
                    
                    try:
                        await self.save_decision_file(decision_file)
                    except DecisionFileError as e:
                        # Log error but don't fail the decision
                        logger.error(f"Failed to save decision file: {e}")

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
        """Generate voting decision for a proposal using the specified strategy.
        
        This method uses the Pydantic AI VotingAgent to make autonomous voting
        decisions based on the provided strategy and proposal details.
        """
        # Create dependencies for agent execution
        deps = self._create_voting_dependencies(strategy)
        
        # Build strategy-specific prompt with proposal details
        prompt = self._build_agent_prompt(proposal, strategy)
        
        # Execute agent with structured output
        result = await self.voting_agent.agent.run(prompt, deps=deps)
        
        # Extract and format the structured response
        formatted_response = self._format_agent_response(result.data)

        # Validate response through existing processor
        return self.response_processor.parse_and_validate_vote_response(
            formatted_response
        )
    
    def _create_voting_dependencies(self, strategy: VotingStrategy) -> VotingDependencies:
        """Create VotingDependencies for agent execution with the given strategy."""
        return VotingDependencies(
            snapshot_service=self.snapshot_service,
            user_preferences=UserPreferences(
                voting_strategy=strategy,
                confidence_threshold=0.7,
                max_proposals_per_run=5,
                blacklisted_proposers=[],
                whitelisted_proposers=[],
            )
        )
    
    def _build_agent_prompt(self, proposal: Proposal, strategy: VotingStrategy) -> str:
        """Build a comprehensive prompt for the voting agent."""
        system_prompt = self.voting_agent._get_system_prompt_for_strategy(strategy)
        
        # Truncate body for token efficiency
        truncated_body = proposal.body[:MAX_PROPOSAL_BODY_LENGTH]
        if len(proposal.body) > MAX_PROPOSAL_BODY_LENGTH:
            truncated_body += "..."
        
        proposal_details = [
            f"Analyze proposal: {proposal.title}",
            "",
            "Proposal Details:",
            f"- ID: {proposal.id}",
            f"- Body: {truncated_body}",
            f"- State: {proposal.state}",
            f"- Choices: {', '.join(proposal.choices)}",
            f"- Scores: {proposal.scores}",
            f"- Author: {proposal.author}",
        ]
        
        return f"{system_prompt}\n\n" + "\n".join(proposal_details)
    
    def _format_agent_response(self, ai_response: AiVoteResponse) -> Dict[str, Any]:
        """Format the agent's structured response for the response processor."""
        return {
            "vote": ai_response.vote,
            "reasoning": ai_response.reasoning,
            "confidence": ai_response.confidence,
            "risk_level": ai_response.risk_level,
        }

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
        **Space:** {proposal.space_id}
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
            
            # Check if API key is configured
            if not settings.openrouter_api_key:
                logger.error("OpenRouter API key is not configured")
                raise ValueError("OpenRouter API key is not configured. Please set OPENROUTER_API_KEY environment variable.")

            with log_span(
                logger, "ai_multiple_proposal_summaries", proposal_count=proposal_count
            ):
                logger.info(
                    "Starting multiple proposal summarization, proposal_count=%s, model_type=%s",
                    proposal_count,
                    model_type_name,
                )

                # Create tasks for concurrent processing
                logger.debug("Creating summary tasks for concurrent processing")
                summary_tasks = self._create_summary_tasks(proposals)
                
                logger.debug(f"Executing {len(summary_tasks)} concurrent summary tasks")
                summaries = await asyncio.gather(*summary_tasks, return_exceptions=True)
                
                # Check for any exceptions in the results
                errors = [s for s in summaries if isinstance(s, Exception)]
                if errors:
                    logger.error(f"Errors occurred during summarization: {errors}")
                    raise errors[0]
                
                # Filter out any None values
                summaries = [s for s in summaries if s is not None]

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
            import traceback
            tb_str = ''.join(traceback.format_exception(type(e), e, e.__traceback__))

            logger.error(
                "Failed to summarize multiple proposals, proposal_count=%s, error=%s, error_type=%s\nTraceback:\n%s",
                len(proposals),
                error_message,
                error_type,
                tb_str,
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

    async def save_decision_file(
        self,
        decision: VotingDecisionFile,
        base_path: Optional[Path] = None
    ) -> Path:
        """Save voting decision to file atomically."""
        
        # Prepare file path
        output_dir = base_path or Path(settings.store_path or ".") / settings.decision_output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp and proposal ID
        timestamp = decision.timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"decision_{timestamp}_{decision.proposal_id[:8]}.json"
        final_path = output_dir / filename
        
        # Calculate checksum
        decision_dict = decision.model_dump(exclude={"checksum"})
        checksum = self._calculate_checksum(decision_dict)
        decision.checksum = checksum
        
        # Atomic write using temporary file
        temp_path = None
        try:
            temp_fd, temp_path = tempfile.mkstemp(dir=output_dir, suffix=".tmp")
            with os.fdopen(temp_fd, "w") as f:
                json.dump(decision.model_dump(), f, indent=2, default=str)
            
            # Atomic rename
            Path(temp_path).replace(final_path)
            
            logger.info(f"Decision file saved: {final_path}")
            return final_path
            
        except PermissionError as e:
            # Clean up temp file on error
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
            raise DecisionFileError(
                f"Permission denied saving decision file: {e}",
                file_path=str(final_path)
            )
        except (OSError, IOError) as e:
            # Clean up temp file on error
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
            raise DecisionFileError(
                f"Failed to save decision file: {e}",
                file_path=str(final_path)
            )

    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """Calculate SHA256 checksum for decision data."""
        json_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()

    async def cleanup_old_decision_files(self, decisions_dir: Path) -> int:
        """Remove old decision files exceeding max_decision_files limit."""
        if not decisions_dir.exists():
            return 0
            
        # Get all decision files sorted by modification time
        decision_files = sorted(
            decisions_dir.glob("decision_*.json"),
            key=lambda f: f.stat().st_mtime
        )
        
        # Calculate how many to remove
        files_to_remove = len(decision_files) - settings.max_decision_files
        if files_to_remove <= 0:
            return 0
            
        # Remove oldest files
        removed_count = 0
        for file_path in decision_files[:files_to_remove]:
            try:
                file_path.unlink()
                removed_count += 1
            except Exception as e:
                logger.error(f"Failed to remove old decision file {file_path}: {e}")
                
        retained_count = len(decision_files) - removed_count
        logger.info(
            f"[agent] Decision file cleanup: removed {removed_count} old files, "
            f"retained {retained_count} recent files"
        )
        
        return removed_count
