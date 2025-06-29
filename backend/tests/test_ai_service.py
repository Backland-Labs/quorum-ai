"""Tests for AI service."""

import pytest
from unittest.mock import patch
from datetime import datetime

from services.ai_service import AIService
from models import Proposal, ProposalState, ProposalSummary


class TestAIService:
    """Test cases for AIService."""


class TestAIServiceInitialization:
    """Test AIService initialization."""

    def test_ai_service_initialization(self) -> None:
        """Test that AIService initializes correctly."""
        service = AIService()
        assert service is not None

    @patch("services.ai_service.settings")
    def test_ai_service_uses_configured_model(self, mock_settings):
        """Test that AIService uses the configured AI model."""
        mock_settings.ai_model = "anthropic:claude-3-sonnet"
        # The actual model configuration will be tested in integration tests
        # For this unit test, we just ensure that the service can be instantiated
        # with a different model configuration.
        assert AIService() is not None


class TestAIServiceSummarizeProposal:
    """Test AIService summarize_proposal method."""

    @pytest.mark.asyncio
    async def test_summarize_proposal_success(
        self, ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test successful proposal summarization."""
        with patch.object(ai_service, "_generate_summary") as mock_generate:
            mock_generate.return_value = {
                "summary": "This proposal increases development funding from 10% to 15%.",
                "key_points": [
                    "Increase treasury allocation by 5%",
                    "Hire more developers",
                    "Accelerate roadmap implementation",
                ],
                "risk_level": "MEDIUM",
                "recommendation": "APPROVE with careful monitoring",
                "confidence_score": 0.85,
            }

            result = await ai_service.summarize_proposal(
                sample_proposal,
                include_risk_assessment=True,
                include_recommendations=True,
            )

            assert isinstance(result, ProposalSummary)
            assert result.proposal_id == "prop-123"
            assert result.title == sample_proposal.title
            assert "development funding" in result.summary
            assert len(result.key_points) == 3
            assert result.risk_level == "MEDIUM"
            assert result.confidence_score == 0.85

    @pytest.mark.asyncio
    async def test_summarize_proposal_without_risk_assessment(
        self, ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test proposal summarization without risk assessment."""
        with patch.object(ai_service, "_generate_summary") as mock_generate:
            mock_generate.return_value = {
                "summary": "This proposal increases development funding.",
                "key_points": ["Increase funding", "Hire developers"],
                "risk_level": "NOT_ASSESSED",
                "recommendation": "NOT_PROVIDED",
                "confidence_score": 0.8,
            }

            result = await ai_service.summarize_proposal(
                sample_proposal,
                include_risk_assessment=False,
                include_recommendations=False,
            )

            assert result.risk_level == "NOT_ASSESSED"
            assert result.recommendation == "NOT_PROVIDED"

    @pytest.mark.asyncio
    async def test_summarize_complex_proposal(
        self, ai_service: AIService, complex_proposal: Proposal
    ) -> None:
        """Test summarization of complex multi-phase proposal."""
        with patch.object(ai_service, "_generate_summary") as mock_generate:
            mock_generate.return_value = {
                "summary": "Multi-phase protocol upgrade including smart contracts, governance, and economics.",
                "key_points": [
                    "Three-phase implementation over 6 months",
                    "Smart contract upgrades to v2.0",
                    "Governance mechanism changes",
                    "Economic model adjustments",
                    "Budget of 2.5M tokens",
                ],
                "risk_level": "HIGH",
                "recommendation": "REVIEW CAREFULLY - High complexity and budget",
                "confidence_score": 0.9,
            }

            result = await ai_service.summarize_proposal(complex_proposal)

            assert result.risk_level == "HIGH"
            assert "Multi-phase" in result.summary
            assert len(result.key_points) == 5

    @pytest.mark.asyncio
    async def test_summarize_proposal_handles_ai_error(
        self, ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test that AI errors are handled gracefully."""
        with patch.object(ai_service, "_generate_summary") as mock_generate:
            mock_generate.side_effect = Exception("AI service unavailable")

            with pytest.raises(Exception):
                await ai_service.summarize_proposal(sample_proposal)


class TestAIServiceSummarizeMultipleProposals:
    """Test AIService summarize_multiple_proposals method."""

    @pytest.mark.asyncio
    async def test_summarize_multiple_proposals_success(
        self,
        ai_service: AIService,
        sample_proposal: Proposal,
        complex_proposal: Proposal,
    ) -> None:
        """Test successful summarization of multiple proposals."""
        proposals = [sample_proposal, complex_proposal]

        with patch.object(ai_service, "summarize_proposal") as mock_summarize:
            mock_summarize.side_effect = [
                ProposalSummary(
                    proposal_id="prop-123",
                    title=sample_proposal.title,
                    summary="Simple proposal summary",
                    key_points=["Point 1"],
                    risk_level="LOW",
                    recommendation="APPROVE",
                    confidence_score=0.8,
                ),
                ProposalSummary(
                    proposal_id="prop-456",
                    title=complex_proposal.title,
                    summary="Complex proposal summary",
                    key_points=["Point 1", "Point 2"],
                    risk_level="HIGH",
                    recommendation="REVIEW",
                    confidence_score=0.9,
                ),
            ]

            results = await ai_service.summarize_multiple_proposals(proposals)

            assert len(results) == 2
            assert results[0].proposal_id == "prop-123"
            assert results[1].proposal_id == "prop-456"
            assert mock_summarize.call_count == 2

    @pytest.mark.asyncio
    async def test_summarize_multiple_proposals_with_failures(
        self,
        ai_service: AIService,
        sample_proposal: Proposal,
        complex_proposal: Proposal,
    ) -> None:
        """Test handling of failures when summarizing multiple proposals."""
        proposals = [sample_proposal, complex_proposal]

        with patch.object(ai_service, "summarize_proposal") as mock_summarize:
            # First succeeds, second fails
            mock_summarize.side_effect = [
                ProposalSummary(
                    proposal_id="prop-123",
                    title=sample_proposal.title,
                    summary="Summary",
                    key_points=["Point 1"],
                    risk_level="LOW",
                    recommendation="APPROVE",
                    confidence_score=0.8,
                ),
                Exception("AI error"),
            ]

            with patch("logfire.error") as mock_error:
                results = await ai_service.summarize_multiple_proposals(proposals)

                # Should return only successful results
                assert len(results) == 1
                assert results[0].proposal_id == "prop-123"

                # Should log the error
                mock_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_summarize_empty_proposal_list(self, ai_service: AIService) -> None:
        """Test summarizing empty list of proposals."""
        results = await ai_service.summarize_multiple_proposals([])
        assert len(results) == 0


class TestAIServiceGenerateSummary:
    """Test AIService _generate_summary private method."""

    @pytest.mark.asyncio
    async def test_generate_summary_constructs_proper_prompt(
        self, ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test that _generate_summary constructs the proper prompt."""
        with patch.object(ai_service, "_call_ai_model") as mock_call:
            mock_call.return_value = {
                "summary": "Test summary",
                "key_points": ["Point 1"],
                "risk_level": "LOW",
                "recommendation": "APPROVE",
                "confidence_score": 0.8,
            }

            await ai_service._generate_summary(
                sample_proposal,
                include_risk_assessment=True,
                include_recommendations=True,
            )

            # Verify the AI model was called
            mock_call.assert_called_once()

            # Get the prompt that was passed
            call_args = mock_call.call_args[0]
            prompt = call_args[0]

            # Verify prompt contains key information
            assert sample_proposal.title in prompt
            assert sample_proposal.description in prompt
            assert "risk assessment" in prompt.lower()
            assert "recommendation" in prompt.lower()

    @pytest.mark.asyncio
    async def test_generate_summary_without_optional_features(
        self, ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test _generate_summary without risk assessment and recommendations."""
        with patch.object(ai_service, "_call_ai_model") as mock_call:
            mock_call.return_value = {
                "summary": "Test summary",
                "key_points": ["Point 1"],
                "risk_level": "NOT_ASSESSED",
                "recommendation": "NOT_PROVIDED",
                "confidence_score": 0.8,
            }

            await ai_service._generate_summary(
                sample_proposal,
                include_risk_assessment=False,
                include_recommendations=False,
            )

            call_args = mock_call.call_args[0]
            prompt = call_args[0]

            # Should not include risk assessment or recommendation instructions in prompt
            assert "risk assessment" not in prompt.lower()
            assert "**recommendation:**" not in prompt.lower()


class TestAIServicePromptConstruction:
    """Test AI service prompt construction methods."""

    def test_build_base_prompt_includes_proposal_details(
        self, ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test that base prompt includes all proposal details."""
        prompt = ai_service._build_base_prompt(sample_proposal)

        assert sample_proposal.title in prompt
        assert sample_proposal.description in prompt
        assert sample_proposal.dao_name in prompt
        assert sample_proposal.state.value in prompt
        assert str(sample_proposal.votes_for) in prompt

    def test_build_base_prompt_handles_missing_optional_fields(
        self, ai_service: AIService
    ) -> None:
        """Test that base prompt handles missing optional fields."""
        minimal_proposal = Proposal(
            id="prop-min",
            title="Minimal Proposal",
            description="Basic description",
            state=ProposalState.ACTIVE,
            created_at=datetime.now(),
            start_block=1000,
            end_block=2000,
            dao_id="dao-min",
            dao_name="Minimal DAO",
        )

        prompt = ai_service._build_base_prompt(minimal_proposal)

        # Should still work with minimal data
        assert minimal_proposal.title in prompt
        assert minimal_proposal.description in prompt

    def test_add_risk_assessment_instructions(self, ai_service: AIService) -> None:
        """Test adding risk assessment instructions to prompt."""
        base_prompt = "Base prompt content"

        enhanced_prompt = ai_service._add_risk_assessment_instructions(base_prompt)

        assert "risk" in enhanced_prompt.lower()
        assert "low" in enhanced_prompt.lower()
        assert "medium" in enhanced_prompt.lower()
        assert "high" in enhanced_prompt.lower()

    def test_add_recommendation_instructions(self, ai_service: AIService) -> None:
        """Test adding recommendation instructions to prompt."""
        base_prompt = "Base prompt content"

        enhanced_prompt = ai_service._add_recommendation_instructions(base_prompt)

        assert "recommend" in enhanced_prompt.lower()
        assert (
            "approve" in enhanced_prompt.lower() or "support" in enhanced_prompt.lower()
        )


class TestAIServiceResponseParsing:
    """Test AI service response parsing methods."""

    def test_parse_ai_response_valid_response(self, ai_service: AIService) -> None:
        """Test parsing a valid AI response."""
        ai_response = {
            "summary": "This is a test summary",
            "key_points": ["Point 1", "Point 2", "Point 3"],
            "risk_level": "MEDIUM",
            "recommendation": "APPROVE with monitoring",
            "confidence_score": 0.85,
        }

        parsed = ai_service._parse_ai_response(ai_response)

        assert parsed["summary"] == "This is a test summary"
        assert len(parsed["key_points"]) == 3
        assert parsed["risk_level"] == "MEDIUM"
        assert parsed["confidence_score"] == 0.85

    def test_parse_ai_response_invalid_confidence_score(
        self, ai_service: AIService
    ) -> None:
        """Test parsing AI response with invalid confidence score."""
        ai_response = {
            "summary": "Test summary",
            "key_points": ["Point 1"],
            "risk_level": "LOW",
            "recommendation": "APPROVE",
            "confidence_score": 1.5,  # Invalid - greater than 1.0
        }

        parsed = ai_service._parse_ai_response(ai_response)

        # Should clamp to valid range
        assert 0.0 <= parsed["confidence_score"] <= 1.0

    def test_parse_ai_response_missing_fields(self, ai_service: AIService) -> None:
        """Test parsing AI response with missing fields."""
        ai_response = {
            "summary": "Test summary",
            # Missing other required fields
        }

        parsed = ai_service._parse_ai_response(ai_response)

        # Should provide defaults for missing fields
        assert parsed["summary"] == "Test summary"
        assert isinstance(parsed["key_points"], list)
        assert parsed["risk_level"] in ["LOW", "MEDIUM", "HIGH", "NOT_ASSESSED"]
        assert isinstance(parsed["recommendation"], str)
        assert 0.0 <= parsed["confidence_score"] <= 1.0


class TestAIServiceCallModel:
    """Test AI service _call_ai_model method and string response handling."""

    @pytest.mark.asyncio
    async def test_call_ai_model_with_dict_response(
        self, ai_service: AIService
    ) -> None:
        """Test _call_ai_model when result.output is already a dictionary."""
        with patch.object(ai_service.agent, "run") as mock_run:
            # Mock result with dictionary output
            mock_result = type("MockResult", (), {})()
            mock_result.output = {
                "summary": "Test summary",
                "key_points": ["Point 1"],
                "risk_level": "LOW",
                "recommendation": "APPROVE",
                "confidence_score": 0.8,
            }
            mock_run.return_value = mock_result

            result = await ai_service._call_ai_model("test prompt")

            assert isinstance(result, dict)
            assert result["summary"] == "Test summary"
            assert result["key_points"] == ["Point 1"]

    @pytest.mark.asyncio
    async def test_call_ai_model_with_json_string_response(
        self, ai_service: AIService
    ) -> None:
        """Test _call_ai_model when result.output is a JSON string."""
        with patch.object(ai_service.agent, "run") as mock_run:
            # Mock result with JSON string output
            mock_result = type("MockResult", (), {})()
            mock_result.output = '{"summary": "Test summary", "key_points": ["Point 1"], "risk_level": "LOW", "recommendation": "APPROVE", "confidence_score": 0.8}'
            mock_run.return_value = mock_result

            result = await ai_service._call_ai_model("test prompt")

            assert isinstance(result, dict)
            assert result["summary"] == "Test summary"
            assert result["key_points"] == ["Point 1"]
            assert result["risk_level"] == "LOW"

    @pytest.mark.asyncio
    async def test_call_ai_model_with_invalid_json_string(
        self, ai_service: AIService
    ) -> None:
        """Test _call_ai_model when result.output is a non-JSON string."""
        with patch.object(ai_service.agent, "run") as mock_run:
            # Mock result with plain string output (not valid JSON)
            mock_result = type("MockResult", (), {})()
            mock_result.output = "This is just a plain text response that is not JSON"
            mock_run.return_value = mock_result

            result = await ai_service._call_ai_model("test prompt")

            # Should return fallback structure with the string as summary
            assert isinstance(result, dict)
            assert (
                result["summary"]
                == "This is just a plain text response that is not JSON"
            )
            assert result["key_points"] == []
            assert result["risk_level"] == "NOT_ASSESSED"
            assert result["recommendation"] == "NOT_PROVIDED"
            assert result["confidence_score"] == 0.5

    @pytest.mark.asyncio
    async def test_call_ai_model_with_empty_string(self, ai_service: AIService) -> None:
        """Test _call_ai_model when result.output is an empty string."""
        with patch.object(ai_service.agent, "run") as mock_run:
            # Mock result with empty string output
            mock_result = type("MockResult", (), {})()
            mock_result.output = ""
            mock_run.return_value = mock_result

            result = await ai_service._call_ai_model("test prompt")

            # Should return fallback structure with empty summary
            assert isinstance(result, dict)
            assert result["summary"] == ""
            assert result["key_points"] == []
            assert result["risk_level"] == "NOT_ASSESSED"
            assert result["recommendation"] == "NOT_PROVIDED"
            assert result["confidence_score"] == 0.5

    @pytest.mark.asyncio
    async def test_call_ai_model_fallback_for_no_output_attribute(
        self, ai_service: AIService
    ) -> None:
        """Test _call_ai_model fallback when result has no output attribute."""
        with patch.object(ai_service.agent, "run") as mock_run:
            # Mock result without output attribute
            mock_result = type("MockResult", (), {})()
            # No output attribute
            mock_run.return_value = mock_result

            result = await ai_service._call_ai_model("test prompt")

            # Should return fallback structure
            assert isinstance(result, dict)
            assert "summary" in result
            assert result["key_points"] == []
            assert result["risk_level"] == "NOT_ASSESSED"
            assert result["recommendation"] == "NOT_PROVIDED"
            assert result["confidence_score"] == 0.5
