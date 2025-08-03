"""Tests for migrating decide_vote to use VotingAgent - TDD RED phase.

This test suite validates the migration of the decide_vote method from manual
prompt building to using the Pydantic AI Agent system with tools and structured
output. All tests should fail initially and guide the implementation.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from dataclasses import dataclass
from typing import Dict, Any
import time

from services.ai_service import AIService, VotingAgent, VotingDependencies
from models import (
    Proposal,
    ProposalState,
    VoteDecision,
    VoteType,
    VotingStrategy,
    RiskLevel,
    UserPreferences,
    AiVoteResponse,
)
from services.snapshot_service import SnapshotService
from pydantic_ai import Agent, RunContext


# Note: Using sample_proposal fixture from conftest.py

@pytest.fixture
def user_preferences():
    """Create user preferences for testing."""
    return UserPreferences(
        voting_strategy=VotingStrategy.BALANCED,
        confidence_threshold=0.7,
        max_proposals_per_run=5,
        blacklisted_proposers=[],
        whitelisted_proposers=[],
    )


@pytest.fixture
def voting_dependencies(user_preferences):
    """Create VotingDependencies for testing."""
    mock_snapshot_service = MagicMock(spec=SnapshotService)
    return VotingDependencies(
        snapshot_service=mock_snapshot_service,
        user_preferences=user_preferences,
    )


class TestDecideVoteAgentMigration:
    """Test suite for migrating decide_vote to use VotingAgent."""

    @pytest.mark.asyncio
    async def test_decide_vote_uses_voting_agent_run_method(
        self, sample_proposal: Proposal, user_preferences: UserPreferences
    ):
        """Test that decide_vote uses VotingAgent.agent.run() instead of manual prompts.
        
        Why this test is important:
        - Validates that the new implementation uses the agent architecture
        - Ensures manual prompt building is replaced with agent execution
        - Confirms proper integration with Pydantic AI Agent system
        """
        # Arrange
        with patch("services.ai_service.settings") as mock_settings:
            mock_settings.openrouter_api_key = "test-key"
            service = AIService()
            
            # Mock the VotingAgent's agent.run method
            mock_agent_run = AsyncMock()
            mock_agent_run.return_value = MagicMock(
                data=AiVoteResponse(
                    vote="FOR",
                    reasoning="Strong proposal with clear benefits",
                    confidence=0.85,
                    risk_level="MEDIUM"
                )
            )
            
            # Replace the agent's run method
            service.voting_agent.agent.run = mock_agent_run
            
            # Act
            result = await service.decide_vote(sample_proposal, VotingStrategy.BALANCED)
            
            # Assert
            # The agent.run method should be called with proper parameters
            mock_agent_run.assert_called_once()
            call_args = mock_agent_run.call_args
            
            # Verify the prompt includes proposal information
            prompt = call_args[0][0] if call_args[0] else call_args.kwargs.get('prompt', '')
            assert sample_proposal.title in prompt
            
            # Verify dependencies are passed
            assert 'deps' in call_args.kwargs
            deps = call_args.kwargs['deps']
            assert isinstance(deps, VotingDependencies)
            assert deps.snapshot_service is not None
            assert deps.user_preferences is not None
            
            # Verify result is properly converted to VoteDecision
            assert isinstance(result, VoteDecision)
            assert result.vote == VoteType.FOR
            assert result.confidence == 0.85
            assert result.risk_assessment == RiskLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_decide_vote_creates_voting_dependencies(
        self, sample_proposal: Proposal
    ):
        """Test that decide_vote creates proper VotingDependencies for agent execution.
        
        Why this test is important:
        - Ensures dependency injection is properly set up for agent tools
        - Validates that SnapshotService and UserPreferences are injected
        - Confirms the agent has access to all required services
        """
        # Arrange
        with patch("services.ai_service.settings") as mock_settings:
            mock_settings.openrouter_api_key = "test-key"
            service = AIService()
            
            # Track VotingDependencies creation
            dependencies_created = []
            
            original_run = service.voting_agent.agent.run
            async def track_dependencies(*args, **kwargs):
                if 'deps' in kwargs:
                    dependencies_created.append(kwargs['deps'])
                # Return a mock response
                return MagicMock(
                    data=AiVoteResponse(
                        vote="FOR",
                        reasoning="Test decision based on analysis",
                        confidence=0.8,
                        risk_level="LOW"
                    )
                )
            
            service.voting_agent.agent.run = track_dependencies
            
            # Act
            await service.decide_vote(sample_proposal, VotingStrategy.CONSERVATIVE)
            
            # Assert
            assert len(dependencies_created) == 1
            deps = dependencies_created[0]
            assert isinstance(deps, VotingDependencies)
            assert deps.snapshot_service == service.snapshot_service
            assert deps.user_preferences is not None
            assert deps.user_preferences.voting_strategy == VotingStrategy.CONSERVATIVE

    @pytest.mark.asyncio
    async def test_decide_vote_uses_structured_output_with_aivoteresponse(
        self, sample_proposal: Proposal
    ):
        """Test that agent is configured to return structured AiVoteResponse.
        
        Why this test is important:
        - Validates that the agent uses result_type=AiVoteResponse
        - Ensures structured output parsing instead of manual JSON parsing
        - Confirms type safety through Pydantic models
        """
        # Arrange
        with patch("services.ai_service.settings") as mock_settings:
            mock_settings.openrouter_api_key = "test-key"
            service = AIService()
            
            # The agent should return structured data
            mock_result = MagicMock()
            mock_result.data = AiVoteResponse(
                vote="AGAINST",
                reasoning="Proposal lacks clear implementation details",
                confidence=0.6,
                risk_level="HIGH"
            )
            
            service.voting_agent.agent.run = AsyncMock(return_value=mock_result)
            
            # Act
            result = await service.decide_vote(sample_proposal, VotingStrategy.CONSERVATIVE)
            
            # Assert
            # Verify the result is properly structured
            assert isinstance(result, VoteDecision)
            assert result.vote == VoteType.AGAINST
            assert result.confidence == 0.6
            assert result.risk_assessment == RiskLevel.HIGH
            assert "implementation details" in result.reasoning

    @pytest.mark.asyncio
    async def test_decide_vote_maintains_strategy_specific_prompts(
        self, sample_proposal: Proposal
    ):
        """Test that agent uses strategy-specific system prompts.
        
        Why this test is important:
        - Ensures voting strategies are preserved in agent migration
        - Validates that each strategy has unique behavior
        - Confirms backward compatibility with existing strategies
        """
        # Arrange
        strategies_and_expected = [
            (VotingStrategy.CONSERVATIVE, "prioritize safety", "AGAINST"),
            (VotingStrategy.BALANCED, "balance innovation", "FOR"),
            (VotingStrategy.AGGRESSIVE, "innovation", "FOR"),
        ]
        
        for strategy, expected_prompt_keyword, expected_vote in strategies_and_expected:
            with patch("services.ai_service.settings") as mock_settings:
                mock_settings.openrouter_api_key = "test-key"
                service = AIService()
                
                # Capture the prompt used
                used_prompts = []
                
                async def capture_prompt(*args, **kwargs):
                    prompt = args[0] if args else kwargs.get('prompt', '')
                    used_prompts.append(prompt)
                    return MagicMock(
                        data=AiVoteResponse(
                            vote=expected_vote,
                            reasoning=f"Decision based on {strategy.value} strategy",
                            confidence=0.75,
                            risk_level="MEDIUM"
                        )
                    )
                
                service.voting_agent.agent.run = capture_prompt
                
                # Act
                result = await service.decide_vote(sample_proposal, strategy)
                
                # Assert
                assert len(used_prompts) == 1
                prompt = used_prompts[0]
                
                # Verify strategy-specific keywords appear in prompt
                assert expected_prompt_keyword in prompt.lower()
                assert result.strategy_used == strategy

    @pytest.mark.asyncio
    async def test_decide_vote_integrates_with_existing_response_processor(
        self, sample_proposal: Proposal
    ):
        """Test that agent response goes through AIResponseProcessor validation.
        
        Why this test is important:
        - Ensures existing validation logic is preserved
        - Validates that response processing maintains data integrity
        - Confirms error handling for invalid responses
        """
        # Arrange
        with patch("services.ai_service.settings") as mock_settings:
            mock_settings.openrouter_api_key = "test-key"
            service = AIService()
            
            # Test with response that needs processing/normalization
            mock_result = MagicMock()
            # Return a valid AiVoteResponse (agent should return valid data)
            mock_result.data = AiVoteResponse(
                vote="FOR",
                reasoning="Test reasoning for normalization",
                confidence=0.95,
                risk_level="HIGH"
            )
            
            service.voting_agent.agent.run = AsyncMock(return_value=mock_result)
            
            # Mock the response processor to verify it's called
            original_processor = service.response_processor.parse_and_validate_vote_response
            processor_called = False
            
            def track_processor_call(response):
                nonlocal processor_called
                processor_called = True
                # Just return the response as-is to verify processor is called
                return response
            
            service.response_processor.parse_and_validate_vote_response = track_processor_call
            
            # Act
            result = await service.decide_vote(sample_proposal, VotingStrategy.BALANCED)
            
            # Assert
            assert processor_called
            assert result.vote == VoteType.FOR
            assert result.confidence == 0.95
            assert result.risk_assessment == RiskLevel.HIGH

    @pytest.mark.asyncio
    async def test_decide_vote_maintains_error_handling(
        self, sample_proposal: Proposal
    ):
        """Test that agent errors are properly handled and logged.
        
        Why this test is important:
        - Ensures robustness of the migrated implementation
        - Validates that errors don't crash the system
        - Confirms proper error propagation and logging
        """
        # Arrange
        with patch("services.ai_service.settings") as mock_settings:
            mock_settings.openrouter_api_key = "test-key"
            service = AIService()
            
            # Simulate agent execution error
            service.voting_agent.agent.run = AsyncMock(
                side_effect=Exception("Agent execution failed: API error")
            )
            
            # Act & Assert
            with pytest.raises(Exception) as exc_info:
                await service.decide_vote(sample_proposal, VotingStrategy.BALANCED)
            
            assert "Agent execution failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_decide_vote_preserves_all_vote_decision_fields(
        self, sample_proposal: Proposal
    ):
        """Test that all VoteDecision fields are properly populated.
        
        Why this test is important:
        - Ensures no data is lost in the migration
        - Validates complete backward compatibility
        - Confirms all fields are mapped correctly
        """
        # Arrange
        with patch("services.ai_service.settings") as mock_settings:
            mock_settings.openrouter_api_key = "test-key"
            service = AIService()
            
            strategy = VotingStrategy.AGGRESSIVE
            expected_response = AiVoteResponse(
                vote="FOR",
                reasoning="This proposal shows great innovation potential",
                confidence=0.92,
                risk_level="LOW"
            )
            
            mock_result = MagicMock()
            mock_result.data = expected_response
            
            service.voting_agent.agent.run = AsyncMock(return_value=mock_result)
            
            # Act
            result = await service.decide_vote(sample_proposal, strategy)
            
            # Assert - all fields should be populated
            assert result.proposal_id == sample_proposal.id
            assert result.vote == VoteType.FOR
            assert result.confidence == 0.92
            assert result.reasoning == expected_response.reasoning
            assert result.risk_assessment == RiskLevel.LOW
            assert result.strategy_used == strategy

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Tool registration will be implemented in a future iteration")
    async def test_decide_vote_agent_tools_are_available(
        self, sample_proposal: Proposal
    ):
        """Test that agent has access to required tools during execution.
        
        Why this test is important:
        - Validates that tools are properly registered with the agent
        - Ensures the agent can query proposals and voting power
        - Confirms tool integration works during vote decisions
        """
        # Arrange
        with patch("services.ai_service.settings") as mock_settings:
            mock_settings.openrouter_api_key = "test-key"
            service = AIService()
            
            # Verify agent has tools registered by checking VotingAgent has the tool methods
            voting_agent = service.voting_agent
            
            # Check that tool methods exist on the VotingAgent
            assert hasattr(voting_agent, 'query_active_proposals')
            assert hasattr(voting_agent, 'get_proposal_details')
            assert hasattr(voting_agent, 'get_voting_power')
            
            # Simulate agent using tools during execution
            tools_used = []
            
            async def track_tool_usage(*args, **kwargs):
                # Track which tools are available in context
                if 'deps' in kwargs:
                    deps = kwargs['deps']
                    if hasattr(deps, 'snapshot_service'):
                        tools_used.append('snapshot_service_available')
                
                return MagicMock(
                    data=AiVoteResponse(
                        vote="FOR",
                        reasoning="Used tools to analyze",
                        confidence=0.8,
                        risk_level="MEDIUM"
                    )
                )
            
            service.voting_agent.agent.run = track_tool_usage
            
            # Act
            await service.decide_vote(sample_proposal, VotingStrategy.BALANCED)
            
            # Assert
            assert 'snapshot_service_available' in tools_used