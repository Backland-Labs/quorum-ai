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
from models import Proposal, ProposalSummary
from services.cache_service import CacheService


class AIService:
    """Service for AI-powered proposal analysis and summarization."""

    def __init__(self, cache_service: Optional[CacheService] = None) -> None:
        """Initialize the AI service with configured model."""
        self.model = self._create_model()
        self.agent = self._create_agent()
        self.cache_service = cache_service

    def _create_model(self) -> Any:
        """Create the AI model with OpenRouter configuration."""
        logfire.info(
            "Creating AI model",
        )

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
            # Fallback to direct provider if OpenRouter key not available
            if settings.anthropic_api_key:
                logfire.info("Using direct Anthropic API")
                return "anthropic:claude-3-5-sonnet"
            elif settings.openai_api_key:
                logfire.info("Using direct OpenAI API")
                return "openai:gpt-4o-mini"
            else:
                logfire.warning("No AI API keys configured, using default model")
                return "openai:gpt-4o-mini"

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

    async def summarize_proposal(
        self,
        proposal: Proposal,
        include_risk_assessment: bool = True,
        include_recommendations: bool = True,
    ) -> ProposalSummary:
        """Summarize a single proposal using AI."""

        try:
            with logfire.span("ai_proposal_summary", proposal_id=proposal.id):
                logfire.info(
                    "Starting proposal summarization",
                    proposal_id=proposal.id,
                    proposal_title=proposal.title,
                    model_type=str(type(self.model)),
                    has_openrouter_key=bool(settings.openrouter_api_key),
                    has_anthropic_key=bool(settings.anthropic_api_key),
                    has_openai_key=bool(settings.openai_api_key),
                )

                summary_data = await self._generate_summary(
                    proposal, include_risk_assessment, include_recommendations
                )

                logfire.info(
                    "Successfully generated proposal summary",
                    proposal_id=proposal.id,
                    summary_length=len(summary_data.get("summary", "")),
                    key_points_count=len(summary_data.get("key_points", [])),
                    risk_level=summary_data.get("risk_level"),
                    confidence_score=summary_data.get("confidence_score"),
                )

                return ProposalSummary(
                    proposal_id=proposal.id,
                    title=proposal.title,
                    summary=summary_data["summary"],
                    key_points=summary_data["key_points"],
                    risk_level=summary_data["risk_level"],
                    recommendation=summary_data["recommendation"],
                    confidence_score=summary_data["confidence_score"],
                )

        except Exception as e:
            logfire.error(
                "Failed to summarize proposal",
                proposal_id=proposal.id,
                proposal_title=proposal.title,
                error=str(e),
                error_type=type(e).__name__,
                model_type=str(type(self.model)),
                has_openrouter_key=bool(settings.openrouter_api_key),
            )
            raise e

    async def summarize_multiple_proposals(
        self,
        proposals: List[Proposal],
        include_risk_assessment: bool = True,
        include_recommendations: bool = True,
    ) -> List[ProposalSummary]:
        """Summarize multiple proposals concurrently with caching and distributed locking."""
        if not proposals:
            return []

        # Check cache for existing results
        cache_result = await self._check_cache_for_summaries(
            proposals, include_risk_assessment, include_recommendations
        )
        if cache_result:
            return cache_result

        # Acquire processing lock and handle concurrency
        lock_result = await self._acquire_processing_lock(
            proposals, include_risk_assessment, include_recommendations
        )

        # If we got a cached result while waiting for lock, return it
        if isinstance(lock_result, list):  # Cached summaries
            return lock_result

        cache_key, lock_key, lock_acquired = lock_result

        try:
            # Process proposals and cache results
            return await self._process_and_cache_summaries(
                proposals, include_risk_assessment, include_recommendations, cache_key
            )
        finally:
            await self._release_processing_lock(lock_key, lock_acquired)

    async def _check_cache_for_summaries(
        self,
        proposals: List[Proposal],
        include_risk_assessment: bool,
        include_recommendations: bool,
    ) -> Optional[List[ProposalSummary]]:
        """Check cache for existing proposal summaries."""
        if not self.cache_service:
            return None

        cache_key = self._generate_cache_key(
            proposals, include_risk_assessment, include_recommendations
        )
        cached_result = await self.cache_service.get(cache_key)

        if cached_result:
            logfire.info("Cache hit for AI summary", cache_key=cache_key)
            return [ProposalSummary(**summary_data) for summary_data in cached_result]

        return None

    async def _acquire_processing_lock(
        self,
        proposals: List[Proposal],
        include_risk_assessment: bool,
        include_recommendations: bool,
    ) -> Union[tuple[str, str, bool], List[ProposalSummary]]:
        """Acquire distributed lock for AI processing."""
        if not self.cache_service:
            return None, None, False

        cache_key = self._generate_cache_key(
            proposals, include_risk_assessment, include_recommendations
        )
        lock_key = f"ai_processing:{cache_key}"

        # Try to acquire lock to prevent duplicate processing
        lock_acquired = await self.cache_service.acquire_lock(
            lock_key, timeout_seconds=300
        )

        if not lock_acquired:
            # Wait for concurrent processing and check cache again
            cached_result = await self._wait_for_concurrent_processing(
                cache_key, lock_key
            )
            if cached_result:
                return cached_result  # Return cached summaries directly

        return cache_key, lock_key, lock_acquired

    async def _wait_for_concurrent_processing(
        self, cache_key: str, lock_key: str
    ) -> Optional[List[ProposalSummary]]:
        """Wait for concurrent AI processing and check cache."""
        logfire.info(
            "Waiting for concurrent AI processing to complete", lock_key=lock_key
        )
        wait_successful = await self.cache_service.wait_for_lock(
            lock_key, max_wait_seconds=10
        )

        if wait_successful:
            cached_result = await self.cache_service.get(cache_key)
            if cached_result:
                logfire.info("Cache hit after waiting for lock", cache_key=cache_key)
                return [
                    ProposalSummary(**summary_data) for summary_data in cached_result
                ]

        logfire.info("Proceeding with AI processing after lock wait", lock_key=lock_key)
        return None

    async def _process_and_cache_summaries(
        self,
        proposals: List[Proposal],
        include_risk_assessment: bool,
        include_recommendations: bool,
        cache_key: Optional[str],
    ) -> List[ProposalSummary]:
        """Process proposals with AI and cache the results."""
        # Generate AI summaries concurrently
        summaries = await self._generate_ai_summaries(
            proposals, include_risk_assessment, include_recommendations
        )

        # Cache the results if cache service is available
        await self._cache_summaries(summaries, cache_key)

        return summaries

    async def _generate_ai_summaries(
        self,
        proposals: List[Proposal],
        include_risk_assessment: bool,
        include_recommendations: bool,
    ) -> List[ProposalSummary]:
        """Generate AI summaries for proposals concurrently."""
        tasks = [
            self.summarize_proposal(
                proposal, include_risk_assessment, include_recommendations
            )
            for proposal in proposals
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        summaries = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logfire.error(
                    "Failed to summarize proposal in batch",
                    proposal_id=proposals[i].id,
                    error=str(result),
                )
                continue
            summaries.append(result)

        return summaries

    async def _cache_summaries(
        self, summaries: List[ProposalSummary], cache_key: Optional[str]
    ) -> None:
        """Cache the generated summaries."""
        if self.cache_service and summaries and cache_key:
            cache_data = [summary.dict() for summary in summaries]
            await self.cache_service.set(cache_key, cache_data, expire_seconds=14400)
            logfire.info(
                "Cache set for AI summary", cache_key=cache_key, count=len(summaries)
            )

    async def _release_processing_lock(
        self, lock_key: Optional[str], lock_acquired: bool
    ) -> None:
        """Release the distributed processing lock."""
        if self.cache_service and lock_key and lock_acquired:
            await self.cache_service.release_lock(lock_key)
            logfire.info("Released AI processing lock", lock_key=lock_key)

    def _generate_cache_key(
        self,
        proposals: List[Proposal],
        include_risk_assessment: bool,
        include_recommendations: bool,
    ) -> str:
        """Generate a cache key based on proposal content and parameters."""
        # Create a hash of proposal contents to detect changes
        proposal_data = []
        for proposal in proposals:
            proposal_content = {
                "id": proposal.id,
                "title": proposal.title,
                "description": proposal.description,
                "state": proposal.state.value,
                "votes_for": proposal.votes_for,
                "votes_against": proposal.votes_against,
                "votes_abstain": proposal.votes_abstain,
            }
            proposal_data.append(proposal_content)

        # Include analysis parameters in the key
        cache_input = {
            "proposals": proposal_data,
            "include_risk_assessment": include_risk_assessment,
            "include_recommendations": include_recommendations,
        }

        # Create hash of the input
        cache_input_str = json.dumps(cache_input, sort_keys=True)
        content_hash = hashlib.sha256(cache_input_str.encode()).hexdigest()[:16]

        return f"ai_summary:{len(proposals)}:{content_hash}"

    async def _generate_summary(
        self,
        proposal: Proposal,
        include_risk_assessment: bool,
        include_recommendations: bool,
    ) -> Dict[str, Any]:
        """Generate AI summary for a proposal."""
        prompt = self._build_analysis_prompt(
            proposal, include_risk_assessment, include_recommendations
        )

        ai_response = await self._call_ai_model(prompt)
        return self._parse_ai_response(ai_response)

    def _build_analysis_prompt(
        self,
        proposal: Proposal,
        include_risk_assessment: bool,
        include_recommendations: bool,
    ) -> str:
        """Build the complete analysis prompt."""
        base_prompt = self._build_base_prompt(proposal)

        if include_risk_assessment:
            base_prompt = self._add_risk_assessment_instructions(base_prompt)

        if include_recommendations:
            base_prompt = self._add_recommendation_instructions(base_prompt)

        base_prompt += self._add_response_format_instructions()

        return base_prompt

    def _build_base_prompt(self, proposal: Proposal) -> str:
        """Build the base prompt with proposal information."""
        return f"""
        Please analyze the following DAO proposal:

        **Proposal Title:** {proposal.title}

        **DAO:** {proposal.dao_name}

        **Current Status:** {proposal.state.value}

        **Voting Results:**
        - Votes For: {proposal.votes_for}
        - Votes Against: {proposal.votes_against}
        - Abstain: {proposal.votes_abstain}

        **Proposal Description:**
        {proposal.description}

        **Analysis Requirements:**
        """

    def _add_risk_assessment_instructions(self, prompt: str) -> str:
        """Add risk assessment instructions to the prompt."""
        return (
            prompt
            + """

        **Risk Assessment:** Evaluate the potential risks of this proposal and classify as:
        - LOW: Minimal risk, standard operational changes
        - MEDIUM: Some risk, requires attention but manageable
        - HIGH: Significant risk, major changes or high impact
        """
        )

    def _add_recommendation_instructions(self, prompt: str) -> str:
        """Add recommendation instructions to the prompt."""
        return (
            prompt
            + """

        **Recommendation:** Provide a clear recommendation (APPROVE, REJECT, or conditional approval)
        with brief reasoning based on your analysis.
        """
        )

    def _add_response_format_instructions(self) -> str:
        """Add response format instructions."""
        return """

        Please respond in the following JSON format:
        {
            "summary": "A concise 2-3 sentence summary in plain English",
            "key_points": ["List of 3-5 key points voters should know"],
            "risk_level": "LOW/MEDIUM/HIGH or NOT_ASSESSED if not requested",
            "recommendation": "Your recommendation or NOT_PROVIDED if not requested",
            "confidence_score": 0.85 (float between 0.0 and 1.0 indicating confidence in analysis)
        }
        """

    async def _call_ai_model(self, prompt: str) -> Dict[str, Any]:
        """Call the AI model with the given prompt."""
        try:
            logfire.info(
                "Calling AI model",
                model_type=str(type(self.model)),
                prompt_length=len(prompt),
                agent_type=str(type(self.agent)),
            )

            result = await self.agent.run(prompt)

            logfire.info(
                "AI model response received",
                result_type=str(type(result)),
                has_data_attr=hasattr(result, "data"),
                result_str_preview=str(result)[:200] if result else "None",
            )

            # PydanticAI returns a RunResult, extract the data
            if hasattr(result, "output"):
                logfire.info(
                    "Extracting data from result.output",
                    data_type=str(type(result.output)),
                )
                # If output is a string, try to parse it as JSON
                if isinstance(result.output, str):
                    import json

                    try:
                        return json.loads(result.output)
                    except json.JSONDecodeError:
                        # If JSON parsing fails, return structured fallback
                        return {
                            "summary": result.output,
                            "key_points": [],
                            "risk_level": "NOT_ASSESSED",
                            "recommendation": "NOT_PROVIDED",
                            "confidence_score": 0.5,
                        }
                return result.output
            else:
                # Fallback if response format is different
                logfire.warning(
                    "Using fallback response format",
                    result_value=str(result),
                    result_type=str(type(result)),
                )
                return {
                    "summary": str(result),
                    "key_points": [],
                    "risk_level": "NOT_ASSESSED",
                    "recommendation": "NOT_PROVIDED",
                    "confidence_score": 0.5,
                }

        except Exception as e:
            logfire.error(
                "AI model call failed",
                error=str(e),
                error_type=type(e).__name__,
                model_type=str(type(self.model)),
                agent_type=str(type(self.agent)),
                prompt_preview=prompt[:200] if prompt else "None",
            )
            raise

    def _parse_ai_response(self, ai_response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate AI response."""
        parsed = {
            "summary": ai_response.get("summary", "Summary not available"),
            "key_points": ai_response.get("key_points", []),
            "risk_level": ai_response.get("risk_level", "NOT_ASSESSED"),
            "recommendation": ai_response.get("recommendation", "NOT_PROVIDED"),
            "confidence_score": ai_response.get("confidence_score", 0.5),
        }

        # Validate and clamp confidence score
        parsed["confidence_score"] = max(
            0.0, min(1.0, float(parsed["confidence_score"]))
        )

        # Ensure key_points is a list
        if not isinstance(parsed["key_points"], list):
            parsed["key_points"] = [str(parsed["key_points"])]

        # Validate risk level
        valid_risk_levels = ["LOW", "MEDIUM", "HIGH", "NOT_ASSESSED"]
        if parsed["risk_level"] not in valid_risk_levels:
            parsed["risk_level"] = "NOT_ASSESSED"

        return parsed
