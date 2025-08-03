"""Tests for AI Service Pearl logging migration.

This test suite ensures that the AI service correctly uses Pearl-compliant logging
instead of Logfire, maintaining all existing functionality while adhering to Pearl
logging standards.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call, ANY
from datetime import datetime
import json

from services.ai_service import AIService, AIResponseProcessor
from models import (
    Proposal,
    ProposalState,
    ProposalSummary,
    VoteDecision,
    VoteType,
    VotingStrategy,
    RiskLevel,
)


class TestAIServicePearlLogging:
    """Test that AI Service uses Pearl-compliant logging instead of Logfire."""

    def test_ai_service_imports_pearl_logging(self):
        """Test that AI service imports Pearl logging utilities instead of logfire.
        
        This test verifies that the AI service module has been migrated to use
        Pearl-compliant logging infrastructure and no longer imports logfire.
        """
        import services.ai_service
        
        # Should not have logfire in module
        assert not hasattr(services.ai_service, 'logfire'), "AI service should not import logfire"
        
        # Should have Pearl logging imports
        assert hasattr(services.ai_service, 'setup_pearl_logger'), "AI service should import setup_pearl_logger"
        assert hasattr(services.ai_service, 'log_span'), "AI service should import log_span"

    @patch("services.ai_service.settings")
    def test_model_creation_uses_pearl_logging(self, mock_settings):
        """Test that model creation uses Pearl logger instead of logfire.
        
        This test ensures that all logging during AI model creation follows
        Pearl standards with proper formatting and structured data.
        """
        mock_settings.openrouter_api_key = "test-api-key"
        
        with patch("services.ai_service.logger") as mock_logger:
            service = AIService()
            
            # Verify Pearl logging calls during model creation
            mock_logger.info.assert_any_call(
                "Creating AI model"
            )
            mock_logger.info.assert_any_call(
                "Using OpenRouter"
            )
            # Check for structured logging with key-value pairs
            assert any(
                "model_type=" in str(call) 
                for call in mock_logger.info.call_args_list
            ), "Should log model type with Pearl format"

    @patch("services.ai_service.settings")
    def test_agent_creation_uses_pearl_logging(self, mock_settings):
        """Test that agent creation uses Pearl logger instead of logfire.
        
        Verifies that Pydantic AI agent creation logs are Pearl-compliant
        with appropriate context and error handling.
        """
        mock_settings.openrouter_api_key = "test-api-key"
        
        with patch("services.ai_service.logger") as mock_logger:
            service = AIService()
            
            # Verify Pearl logging calls during agent creation
            assert any(
                "Creating Pydantic AI agent" in str(call)
                for call in mock_logger.info.call_args_list
            ), "Should log agent creation with Pearl logger"
            
            # Verify structured logging format
            assert any(
                "agent_type=" in str(call) or "model_type=" in str(call)
                for call in mock_logger.info.call_args_list
            ), "Should include structured data in Pearl format"

    @pytest.mark.asyncio
    @patch("services.ai_service.settings")
    async def test_vote_decision_uses_log_span(self, mock_settings):
        """Test that vote decision uses log_span context manager instead of logfire.span.
        
        This test verifies that the AI vote decision process uses Pearl's log_span
        for operation tracking, maintaining the same functionality as logfire spans.
        """
        mock_settings.openrouter_api_key = "test-api-key"
        service = AIService()
        
        proposal = Proposal(
            id="test-proposal",
            title="Test Proposal",
            space={"id": "test.eth", "name": "Test Space"},
            author="0x123",
            body="Test body",
            choices=["For", "Against", "Abstain"],
            created=1234567890,
            start=1234567890,
            end=1234567900,
            snapshot="12345",
            state=ProposalState.ACTIVE,
            scores=[100.0, 50.0, 10.0],
            scores_total=160.0,
            quorum=100.0,
            link="https://test.com",
            network="1",
            symbol="TEST",
            type="single-choice",
            votes=10,
        )
        
        with patch("services.ai_service.log_span") as mock_log_span:
            with patch.object(service, "_generate_vote_decision") as mock_generate:
                mock_generate.return_value = {
                    "vote": "FOR",
                    "confidence": 0.8,
                    "reasoning": "Test reasoning",
                    "risk_level": "LOW",
                }
                
                mock_log_span.return_value.__enter__ = MagicMock()
                mock_log_span.return_value.__exit__ = MagicMock()
                
                await service.decide_vote(proposal, VotingStrategy.BALANCED)
                
                # Verify log_span was called with correct parameters
                mock_log_span.assert_called_once_with(
                    ANY,  # logger instance
                    "ai_vote_decision",
                    proposal_id="test-proposal",
                    strategy="balanced"
                )

    @pytest.mark.asyncio
    @patch("services.ai_service.settings")
    async def test_proposal_summary_uses_log_span(self, mock_settings):
        """Test that proposal summarization uses log_span instead of logfire.span.
        
        Ensures the summarization process tracks operations using Pearl's
        log_span context manager with appropriate metadata.
        """
        mock_settings.openrouter_api_key = "test-api-key"
        service = AIService()
        
        proposal = Proposal(
            id="test-proposal",
            title="Test Proposal",
            space={"id": "test.eth", "name": "Test Space"},
            author="0x123",
            body="Test body",
            choices=["For", "Against", "Abstain"],
            created=1234567890,
            start=1234567890,
            end=1234567900,
            snapshot="12345",
            state=ProposalState.ACTIVE,
            scores=[100.0, 50.0, 10.0],
            scores_total=160.0,
            quorum=100.0,
            link="https://test.com",
            network="1",
            symbol="TEST",
            type="single-choice",
            votes=10,
        )
        
        with patch("services.ai_service.log_span") as mock_log_span:
            with patch.object(service, "_generate_proposal_summary") as mock_generate:
                mock_generate.return_value = {
                    "summary": "Test summary",
                    "key_points": ["Point 1", "Point 2"],
                    "risk_level": "MEDIUM",
                    "recommendation": "Test recommendation",
                }
                
                mock_log_span.return_value.__enter__ = MagicMock()
                mock_log_span.return_value.__exit__ = MagicMock()
                
                await service.summarize_proposal(proposal)
                
                # Verify log_span was called for proposal summary
                mock_log_span.assert_called_once_with(
                    ANY,  # logger instance
                    "ai_proposal_summary",
                    proposal_id="test-proposal"
                )

    @pytest.mark.asyncio
    @patch("services.ai_service.settings")
    async def test_multiple_proposals_uses_log_span(self, mock_settings):
        """Test that multiple proposal summarization uses log_span.
        
        Verifies that batch operations are tracked with Pearl's log_span
        including appropriate metadata about the batch size.
        """
        mock_settings.openrouter_api_key = "test-api-key"
        service = AIService()
        
        proposals = [
            Proposal(
                id=f"test-proposal-{i}",
                title=f"Test Proposal {i}",
                space={"id": "test.eth", "name": "Test Space"},
                author="0x123",
                body="Test body",
                choices=["For", "Against", "Abstain"],
                created=1234567890,
                start=1234567890,
                end=1234567900,
                snapshot="12345",
                state=ProposalState.ACTIVE,
                scores=[100.0, 50.0, 10.0],
                scores_total=160.0,
                quorum=100.0,
                link="https://test.com",
                network="1",
                symbol="TEST",
                type="single-choice",
                votes=10,
            )
            for i in range(3)
        ]
        
        with patch("services.ai_service.log_span") as mock_log_span:
            with patch.object(service, "summarize_proposal") as mock_summarize:
                mock_summarize.side_effect = [
                    ProposalSummary(
                        proposal_id=p.id,
                        title=p.title,
                        summary=f"Summary for {p.id}",
                        key_points=["Point 1"],
                        risk_level="LOW",
                        recommendation="",
                        confidence_score=0.85,
                    )
                    for p in proposals
                ]
                
                mock_log_span.return_value.__enter__ = MagicMock()
                mock_log_span.return_value.__exit__ = MagicMock()
                
                await service.summarize_multiple_proposals(proposals)
                
                # Verify log_span was called for batch operation
                mock_log_span.assert_called_once_with(
                    ANY,  # logger instance
                    "ai_multiple_proposal_summaries",
                    proposal_count=3
                )

    @patch("services.ai_service.settings")
    def test_error_logging_uses_pearl_logger(self, mock_settings):
        """Test that error logging uses Pearl logger instead of logfire.
        
        Ensures all error conditions are logged using Pearl-compliant
        formatting with proper error context and stack traces.
        """
        mock_settings.openrouter_api_key = "test-api-key"
        
        with patch("services.ai_service.logger") as mock_logger:
            with patch("services.ai_service.OpenAIModel") as mock_model_class:
                mock_model_class.side_effect = Exception("Model creation failed")
                
                with pytest.raises(Exception):
                    service = AIService()
                
                # Verify error was logged with Pearl logger
                mock_logger.error.assert_called()
                error_call = mock_logger.error.call_args
                assert "Failed to create OpenRouter model" in str(error_call)
                assert "error=" in str(error_call)
                assert "error_type=" in str(error_call)

    @pytest.mark.asyncio
    @patch("services.ai_service.settings")
    async def test_ai_model_calls_use_pearl_logging(self, mock_settings):
        """Test that AI model API calls use Pearl logging.
        
        Verifies that all external AI model interactions are logged
        with Pearl-compliant formatting for debugging and monitoring.
        """
        mock_settings.openrouter_api_key = "test-api-key"
        service = AIService()
        
        with patch("services.ai_service.logger") as mock_logger:
            with patch.object(service.agent, "run") as mock_run:
                mock_run.return_value = MagicMock(
                    output=json.dumps({
                        "vote": "FOR",
                        "confidence": 0.8,
                        "reasoning": "Test",
                        "risk_level": "LOW"
                    })
                )
                
                await service._call_ai_model_for_vote_decision("test prompt")
                
                # Verify AI model call was logged with Pearl format
                mock_logger.info.assert_any_call(
                    "Calling AI model for vote decision, prompt_length=%s",
                    11
                )

    @patch("services.ai_service.settings")
    def test_response_processor_uses_assertions(self, mock_settings):
        """Test that AIResponseProcessor maintains runtime assertions.
        
        Verifies that the response processor still includes all runtime
        assertions for data validation after Pearl migration.
        """
        processor = AIResponseProcessor()
        
        # Test None input assertion
        with pytest.raises(AssertionError, match="AI response cannot be None"):
            processor.parse_and_validate_vote_response(None)
        
        # Test type assertion
        with pytest.raises(AssertionError, match="Expected dict response"):
            processor.parse_and_validate_vote_response("not a dict")
        
        # Test valid response passes assertions
        valid_response = {
            "vote": "FOR",
            "confidence": 0.8,
            "reasoning": "Test",
            "risk_level": "LOW"
        }
        result = processor.parse_and_validate_vote_response(valid_response)
        assert result["vote"] == "FOR"

    @pytest.mark.asyncio
    @patch("services.ai_service.settings")
    async def test_no_logfire_references_remain(self, mock_settings):
        """Test that no logfire references remain in AI service.
        
        Comprehensive test to ensure complete migration from logfire
        to Pearl logging throughout the AI service module.
        """
        mock_settings.openrouter_api_key = "test-api-key"
        
        # Read the actual service file to check for logfire references
        import inspect
        import services.ai_service
        
        source = inspect.getsource(services.ai_service)
        
        # Should not contain any logfire references
        assert "import logfire" not in source, "Should not import logfire"
        assert "logfire." not in source, "Should not use logfire methods"
        assert "with logfire" not in source, "Should not use logfire context managers"
        
        # Should contain Pearl logging references
        assert "from logging_config import" in source, "Should import from logging_config"
        assert "log_span" in source, "Should use log_span context manager"
        assert "logger" in source, "Should use Pearl logger"