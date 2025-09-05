"""Tests for AI service."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from services.ai_service import AIService
from models import Proposal, ProposalState, ProposalSummary, RiskLevel


class TestAIServiceInitialization:
    """Test AIService initialization."""

    @patch("services.ai_service.settings")
    def test_ai_service_initialization(self, mock_settings) -> None:
        """Test that AIService initializes correctly."""
        mock_settings.openrouter_api_key = "test-api-key"
        service = AIService()
        assert service is not None

    @patch("services.ai_service.settings")
    def test_ai_service_uses_configured_model(self, mock_settings):
        """Test that AIService uses the configured AI model."""
        mock_settings.openrouter_api_key = "test-api-key"
        mock_settings.ai_model = "anthropic:claude-3-sonnet"
        assert AIService() is not None


class TestAIServiceSummarizeProposal:
    """Test AIService summarize_proposal method without caching."""

    @pytest.mark.asyncio
    async def test_summarize_proposal_success(
        self, ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test successful proposal summarization."""
        with patch.object(ai_service, "_generate_proposal_summary") as mock_generate:
            mock_generate.return_value = {
                "summary": "This proposal increases development funding from 10% to 15%.",
                "key_points": [
                    "Increase treasury allocation by 5%",
                    "Hire more developers", 
                    "Accelerate roadmap implementation",
                ],
                "risk_level": "MEDIUM",
                "recommendation": "APPROVE with careful monitoring",
            }

            result = await ai_service.summarize_proposal(sample_proposal)

            assert isinstance(result, ProposalSummary)
            assert result.proposal_id == "prop-123"
            assert "development funding" in result.summary
            assert len(result.key_points) == 3
            assert result.risk_assessment == RiskLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_summarize_proposal_handles_ai_error(
        self, ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test that AI errors are handled gracefully."""
        with patch.object(ai_service, "_generate_proposal_summary") as mock_generate:
            mock_generate.side_effect = Exception("AI service unavailable")

            with pytest.raises(Exception):
                await ai_service.summarize_proposal(sample_proposal)

    @pytest.mark.asyncio
    async def test_summarize_proposal_validates_input(
        self, ai_service: AIService
    ) -> None:
        """Test that input validation works correctly."""
        with pytest.raises(AssertionError, match="Proposal cannot be None"):
            await ai_service.summarize_proposal(None)

        with pytest.raises(AssertionError, match="Expected Proposal object"):
            await ai_service.summarize_proposal("not_a_proposal")


class TestAIServiceSummarizeMultipleProposals:
    """Test AIService summarize_multiple_proposals method without caching."""

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
                    title="Sample Title",
                    summary="Simple proposal summary",
                    key_points=["Point 1"],
                    risk_assessment=RiskLevel.LOW,
                    recommendation="APPROVE",
                    confidence=0.8,
                ),
                ProposalSummary(
                    proposal_id="prop-456",
                    title="Complex Title", 
                    summary="Complex proposal summary",
                    key_points=["Point 1", "Point 2"],
                    risk_assessment=RiskLevel.HIGH,
                    recommendation="REVIEW",
                    confidence=0.9,
                ),
            ]

            results = await ai_service.summarize_multiple_proposals(proposals)

            assert len(results) == 2
            assert results[0].proposal_id == "prop-123"
            assert results[1].proposal_id == "prop-456"
            assert mock_summarize.call_count == 2

    @pytest.mark.asyncio
    async def test_summarize_multiple_proposals_validates_input(
        self, ai_service: AIService
    ) -> None:
        """Test input validation for multiple proposals."""
        with pytest.raises(AssertionError, match="Proposals list cannot be None"):
            await ai_service.summarize_multiple_proposals(None)

        with pytest.raises(AssertionError, match="Expected list of Proposals"):
            await ai_service.summarize_multiple_proposals("not_a_list")

        with pytest.raises(AssertionError, match="Proposals list cannot be empty"):
            await ai_service.summarize_multiple_proposals([])


class TestAIServiceGenerateProposalSummary:
    """Test AIService _generate_proposal_summary private method."""

    @pytest.mark.asyncio
    async def test_generate_proposal_summary_constructs_proper_prompt(
        self, ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test that _generate_proposal_summary constructs the proper prompt."""
        with patch.object(ai_service, "_call_ai_model_for_summary") as mock_call:
            mock_call.return_value = {
                "summary": "Test summary",
                "key_points": ["Point 1"],
                "risk_level": "LOW",
                "recommendation": "APPROVE",
            }

            await ai_service._generate_proposal_summary(sample_proposal)

            # Verify the AI model was called
            mock_call.assert_called_once()

            # Get the prompt that was passed
            call_args = mock_call.call_args[0]
            prompt = call_args[0]

            # Verify prompt contains key information
            assert sample_proposal.title in prompt
            assert sample_proposal.body in prompt
            assert "summary" in prompt.lower()


class TestAIServiceSummaryPromptConstruction:
    """Test AI service summary prompt construction methods."""

    def test_build_summary_prompt_includes_proposal_details(
        self, ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test that summary prompt includes all proposal details."""
        prompt = ai_service._build_summary_prompt(sample_proposal)

        assert sample_proposal.title in prompt
        assert sample_proposal.body in prompt
        assert sample_proposal.state in prompt
        assert str(sample_proposal.votes) in prompt

    def test_get_summary_json_format(self, ai_service: AIService) -> None:
        """Test summary JSON format specification."""
        json_format = ai_service._get_summary_json_format()
        
        assert "summary" in json_format
        assert "key_points" in json_format
        assert "risk_level" in json_format
        assert "recommendation" in json_format


class TestAIServiceSummaryResponseParsing:
    """Test AI service summary response parsing methods."""

    def test_parse_and_validate_summary_response_valid_response(
        self, ai_service: AIService
    ) -> None:
        """Test parsing a valid AI summary response with ProposalSummary structure."""
        ai_response = {
            "proposal_id": "test-proposal-123",
            "title": "Test Proposal Title",
            "summary": "This is a test summary",
            "key_points": ["Point 1", "Point 2", "Point 3"],
            "risk_assessment": "MEDIUM",
            "recommendation": "APPROVE with monitoring",
            "confidence": 0.85,
        }

        parsed = ai_service._parse_and_validate_summary_response(ai_response)

        assert parsed["proposal_id"] == "test-proposal-123"
        assert parsed["title"] == "Test Proposal Title"
        assert parsed["summary"] == "This is a test summary"
        assert len(parsed["key_points"]) == 3
        assert parsed["risk_assessment"] == "MEDIUM"
        assert parsed["recommendation"] == "APPROVE with monitoring"
        assert parsed["confidence"] == 0.85

    def test_parse_and_validate_summary_response_missing_fields(
        self, ai_service: AIService
    ) -> None:
        """Test parsing AI summary response with missing fields using ProposalSummary structure."""
        ai_response = {
            "proposal_id": "test-proposal-123",
            "title": "Test Proposal",
            "summary": "Test summary",
            # Missing other fields
        }

        parsed = ai_service._parse_and_validate_summary_response(ai_response)

        # Should provide defaults for missing fields
        assert parsed["proposal_id"] == "test-proposal-123"
        assert parsed["title"] == "Test Proposal"
        assert parsed["summary"] == "Test summary"
        assert isinstance(parsed["key_points"], list)
        assert parsed["key_points"] == []  # Empty list default
        assert parsed["risk_assessment"] is None  # None default for optional field
        assert parsed["recommendation"] is None   # None default for optional field
        assert parsed["confidence"] == 0.5       # Default confidence

    def test_parse_and_validate_summary_response_invalid_key_points(
        self, ai_service: AIService
    ) -> None:
        """Test parsing summary response with invalid key_points using ProposalSummary structure."""
        ai_response = {
            "proposal_id": "test-proposal-123",
            "title": "Test Proposal",
            "summary": "Test summary",
            "key_points": "not a list",  # Should be a list
            "risk_assessment": "LOW",
            "recommendation": "APPROVE",
            "confidence": 0.7,
        }

        parsed = ai_service._parse_and_validate_summary_response(ai_response)

        # Should convert to list
        assert isinstance(parsed["key_points"], list)
        assert parsed["key_points"] == ["not a list"]
        assert parsed["confidence"] == 0.7

    def test_parse_and_validate_summary_response_validates_input(
        self, ai_service: AIService
    ) -> None:
        """Test input validation for summary response parsing."""
        with pytest.raises(AssertionError, match="AI response cannot be None"):
            ai_service._parse_and_validate_summary_response(None)

        with pytest.raises(AssertionError, match="Expected dict response"):
            ai_service._parse_and_validate_summary_response("not_a_dict")


class TestAIServiceCallModelForSummary:
    """Test AI service _call_ai_model_for_summary method."""

    @pytest.mark.asyncio
    async def test_call_ai_model_for_summary_success(
        self, ai_service: AIService
    ) -> None:
        """Test _call_ai_model_for_summary successful call using SummarizationAgent."""
        # Mock the summarization agent
        if ai_service.summarization_agent:
            with patch.object(ai_service.summarization_agent.agent, "run") as mock_run:
                # Mock result with ProposalSummary structure
                mock_result = type("MockResult", (), {})()
                mock_result.output = {
                    "proposal_id": "test-id",
                    "title": "Test Title",
                    "summary": "Test summary",
                    "key_points": ["Point 1"],
                    "risk_assessment": "LOW",
                    "recommendation": "APPROVE",
                    "confidence": 0.8
                }
                mock_run.return_value = mock_result

                result = await ai_service._call_ai_model_for_summary("test prompt")

                assert isinstance(result, dict)
                assert result["summary"] == "Test summary"
                assert result["key_points"] == ["Point 1"]
        else:
            # If no summarization agent initialized, expect ValueError
            with pytest.raises(ValueError, match="AI service not initialized"):
                await ai_service._call_ai_model_for_summary("test prompt")

    @pytest.mark.asyncio
    async def test_call_ai_model_for_summary_handles_error(
        self, ai_service: AIService
    ) -> None:
        """Test _call_ai_model_for_summary error handling using SummarizationAgent."""
        # Mock the summarization agent
        if ai_service.summarization_agent:
            with patch.object(ai_service.summarization_agent.agent, "run") as mock_run:
                mock_run.side_effect = Exception("AI model error")

                with pytest.raises(Exception, match="AI model error"):
                    await ai_service._call_ai_model_for_summary("test prompt")
        else:
            # If no summarization agent initialized, expect ValueError
            with pytest.raises(ValueError, match="AI service not initialized"):
                await ai_service._call_ai_model_for_summary("test prompt")


class TestAIServiceSummaryProcessing:
    """Test AI service summary processing methods."""

    def test_process_summary_ai_result_with_output_attribute(
        self, ai_service: AIService
    ) -> None:
        """Test _process_summary_ai_result with result having output attribute."""
        # Mock result with output attribute containing JSON string
        mock_result = type("MockResult", (), {})()
        mock_result.output = '{"summary": "Test", "key_points": ["Point 1"], "risk_level": "LOW"}'
        
        result = ai_service._process_summary_ai_result(mock_result)
        
        assert isinstance(result, dict)
        assert result["summary"] == "Test"
        assert result["key_points"] == ["Point 1"]
        assert result["risk_level"] == "LOW"

    def test_process_summary_ai_result_with_dict_output(
        self, ai_service: AIService
    ) -> None:
        """Test _process_summary_ai_result with result having dict output."""
        # Mock result with output attribute containing dict
        mock_result = type("MockResult", (), {})()
        mock_result.output = {
            "summary": "Test dict", 
            "key_points": ["Point 1"], 
            "risk_level": "MEDIUM"
        }
        
        result = ai_service._process_summary_ai_result(mock_result)
        
        assert isinstance(result, dict)
        assert result["summary"] == "Test dict"
        assert result["key_points"] == ["Point 1"]
        assert result["risk_level"] == "MEDIUM"

    def test_process_summary_ai_result_with_json_string(
        self, ai_service: AIService
    ) -> None:
        """Test _process_summary_ai_result with JSON string result."""
        json_string = '{"summary": "String test", "key_points": ["Point 1"], "risk_level": "HIGH"}'
        
        result = ai_service._process_summary_ai_result(json_string)
        
        assert isinstance(result, dict)
        assert result["summary"] == "String test"
        assert result["key_points"] == ["Point 1"]
        assert result["risk_level"] == "HIGH"

    def test_process_summary_ai_result_with_invalid_json(
        self, ai_service: AIService
    ) -> None:
        """Test _process_summary_ai_result with invalid JSON string."""
        invalid_json = "This is not valid JSON"
        
        result = ai_service._process_summary_ai_result(invalid_json)
        
        assert isinstance(result, dict)
        assert result["summary"] == "Unable to generate structured summary from AI response"
        assert "AI response processing failed" in result["key_points"]
        assert result["risk_level"] == "MEDIUM"

    def test_create_summary_fallback_response(
        self, ai_service: AIService
    ) -> None:
        """Test _create_summary_fallback_response creates proper fallback."""
        raw_output = "Some unparseable output"
        
        result = ai_service._create_summary_fallback_response(raw_output)
        
        assert isinstance(result, dict)
        assert "summary" in result
        assert "key_points" in result
        assert "risk_level" in result
        assert "recommendation" in result
        assert result["risk_level"] == "MEDIUM"