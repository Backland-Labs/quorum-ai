"""
Critical tests for Phase 4: AI Service Agent Separation End-to-End Testing.

This test module verifies that both VotingAgent and SummarizationAgent work correctly
with their respective agents, using Pearl-compliant logging for monitoring.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from models import (
    Proposal,
    ProposalSummary,
    VoteDecision,
    VoteType,
    VotingStrategy,
    RiskLevel,
    AiVoteResponse,
)
from services.ai_service import (
    AIService,
    VotingAgent,
    SummarizationAgent,
    VotingDependencies,
    SummarizationDependencies,
)
from services.snapshot_service import SnapshotService


class TestAgentSeparationInitialization:
    """Test that both agents initialize correctly with shared model."""

    @pytest.fixture
    def mock_model(self):
        """Create a mock OpenAIModel for testing."""
        model = MagicMock(spec=OpenAIModel)
        return model

    @pytest.fixture
    def mock_snapshot_service(self):
        """Create a mock SnapshotService for testing."""
        return MagicMock(spec=SnapshotService)

    def test_both_agents_initialize_with_shared_model(self, mock_model):
        """Test that both VotingAgent and SummarizationAgent can be initialized with shared model."""
        # Test VotingAgent initialization
        voting_agent = VotingAgent(mock_model)
        assert voting_agent is not None
        assert voting_agent.model == mock_model
        assert voting_agent.agent is not None

        # Test SummarizationAgent initialization
        summarization_agent = SummarizationAgent(mock_model)
        assert summarization_agent is not None
        assert summarization_agent.model == mock_model
        assert summarization_agent.agent is not None

    def test_aiservice_creates_both_agents_with_shared_model(
        self, mock_snapshot_service
    ):
        """Test that AIService creates both agents with shared model."""
        with patch("services.ai_service.settings.openrouter_api_key", "test-key"):
            with patch.object(AIService, "_create_model") as mock_create_model:
                mock_model = MagicMock(spec=OpenAIModel)
                mock_create_model.return_value = mock_model

                ai_service = AIService(snapshot_service=mock_snapshot_service)
                ai_service.swap_api_key("test-api-key")

                assert ai_service.voting_agent is not None
                assert ai_service.summarization_agent is not None
                assert ai_service.voting_agent.model == mock_model
                assert ai_service.summarization_agent.model == mock_model


class TestAgentSeparationFunctionality:
    """Test that each agent returns correct response types."""

    @pytest.fixture
    def mock_proposal(self):
        """Create a mock proposal for testing."""
        return Proposal(
            id="test-proposal-123",
            title="Test Proposal",
            body="This is a test proposal for agent separation testing.",
            state="active",
            author="0x1234567890123456789012345678901234567890",
            created=1640000000,
            start=1640000000,
            end=1640010000,
            votes=150,
            scores_total=150.0,
            choices=["For", "Against"],
            scores=[100.0, 50.0],
            snapshot=None,
            discussion=None,
            ipfs=None,
            space_id="test-space",
            is_active=True,
            time_remaining=None,
            vote_choices=[],
        )

    @pytest.mark.asyncio
    async def test_voting_agent_returns_vote_decision(self, mock_proposal):
        """Test that VotingAgent returns correct AiVoteResponse structure."""
        with patch("services.ai_service.settings.openrouter_api_key", "test-key"):
            with patch.object(AIService, "_create_model") as mock_create_model:
                mock_model = MagicMock(spec=OpenAIModel)
                mock_create_model.return_value = mock_model

                # Mock the agent.run to return AiVoteResponse structure
                mock_agent_result = MagicMock()
                mock_agent_result.output = AiVoteResponse(
                    vote="FOR",
                    reasoning="Test reasoning for voting decision",
                    confidence=0.85,
                    risk_level="MEDIUM",
                )

                ai_service = AIService()
                ai_service.swap_api_key("test-api-key")

                # Ensure agents are created
                assert ai_service.voting_agent is not None

                with patch.object(
                    ai_service.voting_agent.agent, "run", new_callable=AsyncMock
                ) as mock_run:
                    mock_run.return_value = mock_agent_result

                    # Test voting decision generation
                    decision = await ai_service.decide_vote(
                        mock_proposal,
                        strategy=VotingStrategy.BALANCED,
                        save_to_file=False,
                    )

                    assert isinstance(decision, VoteDecision)
                    assert decision.vote == VoteType.FOR
                    assert decision.confidence == 0.85
                    assert "Test reasoning" in decision.reasoning

    @pytest.mark.asyncio
    async def test_summarization_agent_returns_proposal_summary(self, mock_proposal):
        """Test that SummarizationAgent returns correct ProposalSummary structure."""
        with patch("services.ai_service.settings.openrouter_api_key", "test-key"):
            with patch.object(AIService, "_create_model") as mock_create_model:
                mock_model = MagicMock(spec=OpenAIModel)
                mock_create_model.return_value = mock_model

                # Mock the agent.run to return ProposalSummary structure
                mock_agent_result = MagicMock()
                mock_agent_result.output = ProposalSummary(
                    proposal_id="test-proposal-123",
                    title="Test Proposal",
                    summary="This is a comprehensive test summary.",
                    key_points=["Key point 1", "Key point 2"],
                    risk_assessment=RiskLevel.MEDIUM,
                    recommendation="Consider voting FOR",
                    confidence=0.90,
                )

                ai_service = AIService()
                ai_service.swap_api_key("test-api-key")

                # Ensure agents are created
                assert ai_service.summarization_agent is not None

                with patch.object(
                    ai_service.summarization_agent.agent, "run", new_callable=AsyncMock
                ) as mock_run:
                    mock_run.return_value = mock_agent_result

                    # Test summarization
                    summary = await ai_service.summarize_proposal(mock_proposal)

                    assert isinstance(summary, ProposalSummary)
                    assert summary.proposal_id == "test-proposal-123"
                    assert summary.title == "Test Proposal"
                    assert "comprehensive test summary" in summary.summary
                    assert len(summary.key_points) == 2


class TestConcurrentAgentOperations:
    """Test that both agents can operate simultaneously without conflicts."""

    @pytest.fixture
    def mock_proposal(self):
        """Create a mock proposal for testing."""
        return Proposal(
            id="concurrent-test-123",
            title="Concurrent Test Proposal",
            body="This proposal tests concurrent agent operations.",
            state="active",
            author="0x1234567890123456789012345678901234567890",
            created=1640000000,
            start=1640000000,
            end=1640010000,
            votes=300,
            scores_total=300.0,
            choices=["For", "Against"],
            scores=[200.0, 100.0],
            snapshot=None,
            discussion=None,
            ipfs=None,
            space_id="test-space",
            is_active=True,
            time_remaining=None,
            vote_choices=[],
        )

    @pytest.mark.asyncio
    async def test_concurrent_voting_and_summarization(self, mock_proposal):
        """Test that voting and summarization can run concurrently."""
        import asyncio

        with patch("services.ai_service.settings.openrouter_api_key", "test-key"):
            with patch.object(AIService, "_create_model") as mock_create_model:
                mock_model = MagicMock(spec=OpenAIModel)
                mock_create_model.return_value = mock_model

                ai_service = AIService()
                ai_service.swap_api_key("test-api-key")

                # Mock both agents
                mock_vote_result = MagicMock()
                mock_vote_result.output = AiVoteResponse(
                    vote="AGAINST",
                    reasoning="Concurrent test reasoning",
                    confidence=0.75,
                    risk_level="HIGH",
                )

                mock_summary_result = MagicMock()
                mock_summary_result.output = ProposalSummary(
                    proposal_id="concurrent-test-123",
                    title="Concurrent Test Proposal",
                    summary="Concurrent operation test summary.",
                    key_points=["Concurrent point 1"],
                    risk_assessment=RiskLevel.HIGH,
                    recommendation="Test recommendation",
                    confidence=0.80,
                )

                # Ensure both agents are created
                assert ai_service.voting_agent is not None
                assert ai_service.summarization_agent is not None

                with patch.object(
                    ai_service.voting_agent.agent, "run", new_callable=AsyncMock
                ) as mock_vote_run:
                    with patch.object(
                        ai_service.summarization_agent.agent,
                        "run",
                        new_callable=AsyncMock,
                    ) as mock_summary_run:
                        mock_vote_run.return_value = mock_vote_result
                        mock_summary_run.return_value = mock_summary_result

                        # Run both operations concurrently
                        decision_task = ai_service.decide_vote(
                            mock_proposal,
                            strategy=VotingStrategy.CONSERVATIVE,
                            save_to_file=False,
                        )
                        summary_task = ai_service.summarize_proposal(mock_proposal)

                        decision, summary = await asyncio.gather(
                            decision_task, summary_task
                        )

                        # Verify both operations completed successfully
                        assert isinstance(decision, VoteDecision)
                        assert decision.vote == VoteType.AGAINST
                        assert isinstance(summary, ProposalSummary)
                        assert summary.proposal_id == "concurrent-test-123"

                        # Verify both agents were called
                        mock_vote_run.assert_called_once()
                        mock_summary_run.assert_called_once()
