"""AI service for proposal summarization using Pydantic AI."""

import asyncio
from typing import Dict, List, Any

import logfire
from pydantic_ai import Agent
from pydantic_ai.models import KnownModelName

from config import settings
from models import Proposal, ProposalSummary


class AIService:
    """Service for AI-powered proposal analysis and summarization."""

    def __init__(self) -> None:
        """Initialize the AI service with configured model."""
        self.model_name = self._parse_model_name(settings.ai_model)
        self.agent = self._create_agent()

    def _parse_model_name(self, model_string: str) -> KnownModelName:
        """Parse model string into PydanticAI model name."""
        # Handle different model formats: "openai:gpt-4o-mini", "anthropic:claude-3-sonnet", etc.
        if ":" in model_string:
            provider, model = model_string.split(":", 1)
            if provider == "openai":
                return f"openai:{model}"
            elif provider == "anthropic":
                return f"anthropic:{model}"

        # Default to OpenAI GPT-4o-mini if parsing fails
        return "openai:gpt-4o-mini"

    def _create_agent(self) -> Agent:
        """Create and configure the Pydantic AI agent."""
        return Agent(
            model=self.model_name,
            system_prompt=self._get_system_prompt(),
        )

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
                summary_data = await self._generate_summary(
                    proposal, include_risk_assessment, include_recommendations
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
                "Failed to summarize proposal", proposal_id=proposal.id, error=str(e)
            )
            raise

    async def summarize_multiple_proposals(
        self,
        proposals: List[Proposal],
        include_risk_assessment: bool = True,
        include_recommendations: bool = True,
    ) -> List[ProposalSummary]:
        """Summarize multiple proposals concurrently."""
        if not proposals:
            return []

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
            result = await self.agent.run(prompt)

            # PydanticAI returns a RunResult, extract the data
            if hasattr(result, "data"):
                return result.data
            else:
                # Fallback if response format is different
                return {
                    "summary": str(result),
                    "key_points": [],
                    "risk_level": "NOT_ASSESSED",
                    "recommendation": "NOT_PROVIDED",
                    "confidence_score": 0.5,
                }

        except Exception as e:
            logfire.error("AI model call failed", error=str(e))
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
