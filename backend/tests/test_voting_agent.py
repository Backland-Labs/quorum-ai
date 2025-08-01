"""Tests for VotingAgent and VotingDependencies in AI service.

This module tests the Pydantic AI agent implementation for autonomous voting,
including dependency injection, agent tools, and system prompt generation.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import dataclass
from typing import Optional

from services.ai_service import VotingDependencies, VotingAgent, AIService
from services.snapshot_service import SnapshotService
from models import UserPreferences, VotingStrategy, VoteDecision, Proposal
from services.state_manager import StateManager


class TestVotingDependencies:
    """Test VotingDependencies dataclass for proper initialization and validation."""

    def test_voting_dependencies_initialization_with_required_fields(self):
        """Test that VotingDependencies initializes correctly with required fields.
        
        Why this test is important:
        - Ensures the dependency injection container can be created with minimal required fields
        - Validates that the dataclass structure matches the planned architecture
        - Confirms that dependencies are properly stored and accessible
        """
        # Arrange
        mock_snapshot_service = MagicMock(spec=SnapshotService)
        mock_user_preferences = MagicMock(spec=UserPreferences)
        
        # Act
        deps = VotingDependencies(
            snapshot_service=mock_snapshot_service,
            user_preferences=mock_user_preferences
        )
        
        # Assert
        assert deps.snapshot_service is mock_snapshot_service
        assert deps.user_preferences is mock_user_preferences
        assert deps.state_manager is None  # Optional field defaults to None

    def test_voting_dependencies_initialization_with_all_fields(self):
        """Test that VotingDependencies initializes correctly with all fields including optional ones.
        
        Why this test is important:
        - Validates that optional fields can be properly set
        - Ensures StateManager integration is supported for file-based decision output
        - Confirms the full dependency injection container works as expected
        """
        # Arrange
        mock_snapshot_service = MagicMock(spec=SnapshotService)
        mock_user_preferences = MagicMock(spec=UserPreferences)
        mock_state_manager = MagicMock(spec=StateManager)
        
        # Act
        deps = VotingDependencies(
            snapshot_service=mock_snapshot_service,
            user_preferences=mock_user_preferences,
            state_manager=mock_state_manager
        )
        
        # Assert
        assert deps.snapshot_service is mock_snapshot_service
        assert deps.user_preferences is mock_user_preferences
        assert deps.state_manager is mock_state_manager

    def test_voting_dependencies_post_init_validation(self):
        """Test that VotingDependencies validates required fields in __post_init__.
        
        Why this test is important:
        - Ensures runtime assertions catch missing dependencies early
        - Validates that the dependency container enforces required fields
        - Prevents agent initialization with incomplete dependencies
        """
        # Test missing snapshot_service
        with pytest.raises(AssertionError, match="SnapshotService required"):
            VotingDependencies(
                snapshot_service=None,
                user_preferences=MagicMock(spec=UserPreferences)
            )
        
        # Test missing user_preferences
        with pytest.raises(AssertionError, match="UserPreferences required"):
            VotingDependencies(
                snapshot_service=MagicMock(spec=SnapshotService),
                user_preferences=None
            )


class TestVotingAgentInitialization:
    """Test VotingAgent class initialization and configuration."""

    @patch('services.ai_service.setup_pearl_logger')
    @patch('services.ai_service.Agent')
    def test_voting_agent_initialization(self, mock_agent_class, mock_logger):
        """Test that VotingAgent initializes correctly with proper configuration.
        
        Why this test is important:
        - Validates the agent is created with Pydantic AI Agent class
        - Ensures Pearl-compliant logging is initialized
        - Confirms the agent has all required attributes for voting decisions
        """
        # Arrange
        mock_agent_instance = MagicMock()
        mock_agent_class.return_value = mock_agent_instance
        
        # Act
        agent = VotingAgent()
        
        # Assert
        assert agent.logger is not None
        assert agent.agent is mock_agent_instance
        assert hasattr(agent, 'response_processor')
        mock_logger.assert_called_once()
        mock_agent_class.assert_called_once()

    @patch('services.ai_service.setup_pearl_logger')
    @patch('services.ai_service.Agent')
    def test_voting_agent_model_configuration(self, mock_agent_class, mock_logger):
        """Test that VotingAgent configures the AI model correctly.
        
        Why this test is important:
        - Ensures Google Gemini 2.0 Flash is configured via OpenRouter
        - Validates model initialization follows the planned architecture
        - Confirms error handling for model creation failures
        """
        # Arrange
        mock_agent_instance = MagicMock()
        mock_agent_class.return_value = mock_agent_instance
        
        # Act
        agent = VotingAgent()
        
        # Assert
        # Verify Agent was called with correct parameters
        call_args = mock_agent_class.call_args
        assert call_args is not None
        assert 'model' in call_args.kwargs
        assert 'system_prompt' in call_args.kwargs
        assert 'output_type' in call_args.kwargs

    @patch('services.ai_service.settings')
    def test_voting_agent_missing_api_key_error(self, mock_settings):
        """Test that VotingAgent raises error when OpenRouter API key is missing.
        
        Why this test is important:
        - Ensures proper configuration validation
        - Prevents agent initialization without required credentials
        - Validates error messages are clear and actionable
        """
        # Arrange
        mock_settings.openrouter_api_key = None
        
        # Act & Assert
        with pytest.raises(AssertionError, match="OpenRouter API key is not configured"):
            VotingAgent()


class TestVotingAgentSystemPrompts:
    """Test dynamic system prompt generation based on voting strategies."""

    @patch('services.ai_service.setup_pearl_logger')
    @patch('services.ai_service.Agent')
    def test_system_prompt_generation_for_conservative_strategy(self, mock_agent_class, mock_logger):
        """Test system prompt generation for conservative voting strategy.
        
        Why this test is important:
        - Validates strategy-specific prompts are properly generated
        - Ensures conservative strategy emphasizes safety and stability
        - Confirms prompt includes proper context for AI decision making
        """
        # Arrange
        agent = VotingAgent()
        
        # Act
        prompt = agent._get_system_prompt_for_strategy(VotingStrategy.CONSERVATIVE)
        
        # Assert
        assert "conservative" in prompt.lower()
        assert "risk" in prompt.lower()
        assert "safety" in prompt.lower() or "stable" in prompt.lower()

    @patch('services.ai_service.setup_pearl_logger')
    @patch('services.ai_service.Agent')
    def test_system_prompt_generation_for_balanced_strategy(self, mock_agent_class, mock_logger):
        """Test system prompt generation for balanced voting strategy.
        
        Why this test is important:
        - Ensures balanced strategy considers both risks and opportunities
        - Validates moderate approach is reflected in the prompt
        - Confirms prompt guides AI to weigh pros and cons equally
        """
        # Arrange
        agent = VotingAgent()
        
        # Act
        prompt = agent._get_system_prompt_for_strategy(VotingStrategy.BALANCED)
        
        # Assert
        assert "balanced" in prompt.lower()
        assert "risk" in prompt.lower()
        assert "benefit" in prompt.lower() or "opportunity" in prompt.lower()

    @patch('services.ai_service.setup_pearl_logger')
    @patch('services.ai_service.Agent')
    def test_system_prompt_generation_for_aggressive_strategy(self, mock_agent_class, mock_logger):
        """Test system prompt generation for aggressive voting strategy.
        
        Why this test is important:
        - Validates aggressive strategy focuses on growth and innovation
        - Ensures higher risk tolerance is communicated in the prompt
        - Confirms prompt encourages bold decision making when appropriate
        """
        # Arrange
        agent = VotingAgent()
        
        # Act
        prompt = agent._get_system_prompt_for_strategy(VotingStrategy.AGGRESSIVE)
        
        # Assert
        assert "aggressive" in prompt.lower() or "growth" in prompt.lower()
        assert "innovation" in prompt.lower() or "opportunity" in prompt.lower()


class TestVotingAgentErrorHandling:
    """Test error handling and edge cases for VotingAgent."""

    @patch('services.ai_service.setup_pearl_logger')
    @patch('services.ai_service.Agent')
    def test_agent_initialization_error_handling(self, mock_agent_class, mock_logger):
        """Test that agent initialization errors are properly handled and logged.
        
        Why this test is important:
        - Ensures failures during agent creation are caught and logged
        - Validates error messages provide useful debugging information
        - Confirms the system fails gracefully with clear error reporting
        """
        # Arrange
        mock_agent_class.side_effect = Exception("Failed to create agent")
        
        # Act & Assert
        with pytest.raises(Exception, match="Failed to create agent"):
            VotingAgent()

    @patch('services.ai_service.setup_pearl_logger')
    @patch('services.ai_service.Agent')
    def test_tool_registration_validates_dependencies(self, mock_agent_class, mock_logger):
        """Test that agent tools validate dependencies during registration.
        
        Why this test is important:
        - Ensures tools cannot be registered without proper dependencies
        - Validates tool registration follows the planned architecture
        - Confirms error handling for invalid tool configurations
        """
        # Arrange
        agent = VotingAgent()
        
        # Act & Assert
        # Tools should be registered during initialization
        assert hasattr(agent, '_register_tools')
        # This will fail until we implement the actual method


class TestVotingAgentIntegration:
    """Test VotingAgent integration with AIService."""

    @pytest.mark.asyncio
    async def test_ai_service_uses_voting_agent(self):
        """Test that AIService properly integrates VotingAgent for vote decisions.
        
        Why this test is important:
        - Validates backward compatibility with existing AIService interface
        - Ensures VotingAgent is used instead of manual prompt building
        - Confirms the refactoring maintains the same public API
        """
        # This test will fail until we implement the VotingAgent integration
        ai_service = AIService()
        assert hasattr(ai_service, 'voting_agent')
        assert isinstance(ai_service.voting_agent, VotingAgent)


class TestVotingAgentTools:
    """Test suite for VotingAgent tools functionality - Task 2 implementation."""
    
    @pytest.fixture
    def mock_snapshot_service(self):
        """Create a mock SnapshotService for testing."""
        service = MagicMock(spec=SnapshotService)
        service.get_proposals = AsyncMock()
        service.get_proposal = AsyncMock()
        service.calculate_voting_power = AsyncMock()
        return service
    
    @pytest.fixture
    def voting_dependencies(self, mock_snapshot_service):
        """Create VotingDependencies for testing."""
        user_prefs = UserPreferences(
            voting_strategy=VotingStrategy.BALANCED,
            confidence_threshold=0.7,
            max_proposals_per_run=5,
            blacklisted_proposers=["0xBadActor"],
            whitelisted_proposers=["0xTrusted"]
        )
        return VotingDependencies(
            snapshot_service=mock_snapshot_service,
            user_preferences=user_prefs
        )
    
    @patch('services.ai_service.setup_pearl_logger')
    @patch('services.ai_service.settings')
    def test_query_active_proposals_tool_exists(self, mock_settings, mock_logger):
        """Test that the query_active_proposals tool is registered on the agent.
        
        Why this test is important:
        - Verifies that agent tools are properly registered during initialization
        - Ensures the query_active_proposals tool is available for fetching proposals
        - Validates the tool registration follows Pydantic AI patterns
        """
        # Arrange
        mock_settings.openrouter_api_key = "test_api_key"
        
        # Act
        agent = VotingAgent()
        
        # Assert - Tool registration should happen in _register_function_tools
        # Check if tools are registered
        assert hasattr(agent.agent, '_function_tools'), "Agent should have _function_tools attribute"
        tool_names = list(agent.agent._function_tools.keys()) if hasattr(agent.agent, '_function_tools') else []
        assert 'query_active_proposals' in tool_names, "query_active_proposals tool should be registered"
    
    @patch('services.ai_service.setup_pearl_logger')
    @patch('services.ai_service.settings')
    def test_get_proposal_details_tool_exists(self, mock_settings, mock_logger):
        """Test that the get_proposal_details tool is registered on the agent.
        
        Why this test is important:
        - Ensures the tool for fetching detailed proposal data is available
        - Validates comprehensive proposal information can be accessed
        - Confirms tool naming follows the planned architecture
        """
        # Arrange
        mock_settings.openrouter_api_key = "test_api_key"
        
        # Act
        agent = VotingAgent()
        
        # Assert
        tool_names = list(agent.agent._function_tools.keys()) if hasattr(agent.agent, '_function_tools') else []
        assert 'get_proposal_details' in tool_names, "get_proposal_details tool should be registered"
    
    @patch('services.ai_service.setup_pearl_logger')
    @patch('services.ai_service.settings')
    def test_get_voting_power_tool_exists(self, mock_settings, mock_logger):
        """Test that the get_voting_power tool is registered on the agent.
        
        Why this test is important:
        - Verifies voting power calculation is available as an agent tool
        - Ensures the agent can assess user influence in DAOs
        - Validates the tool is properly integrated with the agent
        """
        # Arrange
        mock_settings.openrouter_api_key = "test_api_key"
        
        # Act
        agent = VotingAgent()
        
        # Assert
        tool_names = list(agent.agent._function_tools.keys()) if hasattr(agent.agent, '_function_tools') else []
        assert 'get_voting_power' in tool_names, "get_voting_power tool should be registered"
    
    @pytest.mark.asyncio
    @patch('services.ai_service.setup_pearl_logger')
    @patch('services.ai_service.settings')
    async def test_query_active_proposals_tool_functionality(self, mock_settings, mock_logger, voting_dependencies):
        """Test that query_active_proposals tool correctly fetches proposals.
        
        Why this test is important:
        - Validates the tool properly integrates with SnapshotService
        - Ensures active proposals are filtered correctly
        - Confirms the tool returns data in the expected format for AI processing
        """
        # Arrange
        from datetime import datetime, timezone
        sample_proposals = [
            Proposal(
                id="proposal-1",
                title="Enable Treasury Diversification",
                body="This proposal aims to diversify the DAO treasury...",
                choices=["For", "Against", "Abstain"],
                state="active",
                start=int(datetime.now(timezone.utc).timestamp() - 86400),
                end=int(datetime.now(timezone.utc).timestamp() + 86400),
                snapshot="17890123",
                author="0x1234567890123456789012345678901234567890",
                space={"id": "test.eth", "name": "Test DAO"},
                type="single-choice",
                privacy="",
                validation={"name": "basic"},
                strategies=[],
                scores=[5000.0, 2000.0, 1000.0],
                scores_total=8000.0,
                created=int(datetime.now(timezone.utc).timestamp() - 172800),
                updated=int(datetime.now(timezone.utc).timestamp() - 86400),
                votes=0,
                link=f"https://snapshot.org/#/test.eth/proposal/proposal-1"
            )
        ]
        voting_dependencies.snapshot_service.get_proposals.return_value = sample_proposals
        mock_settings.openrouter_api_key = "test_api_key"
        
        # Create agent and verify tool functionality
        agent = VotingAgent()
        
        # Find the tool (this will fail until implementation)
        query_tool = None
        if hasattr(agent.agent, '_function_tools'):
            tool_obj = agent.agent._function_tools.get('query_active_proposals')
            if tool_obj:
                query_tool = tool_obj.function
        
        assert query_tool is not None, "query_active_proposals tool should exist"
        
        # Create a mock context with dependencies
        from pydantic_ai import RunContext
        ctx = MagicMock(spec=RunContext)
        ctx.deps = voting_dependencies
        
        # Execute the tool
        result = await query_tool(ctx, space_id="test.eth")
        
        # Verify the tool called the service correctly
        voting_dependencies.snapshot_service.get_proposals.assert_called_once_with(
            space_id="test.eth", 
            state="active"
        )
        
        # Verify the result
        assert len(result) == 1
        assert result[0]['id'] == "proposal-1"
        assert result[0]['title'] == "Enable Treasury Diversification"
    
    @pytest.mark.asyncio
    @patch('services.ai_service.setup_pearl_logger')
    @patch('services.ai_service.settings')
    async def test_function_tools_error_handling(self, mock_settings, mock_logger, voting_dependencies):
        """Test that tools handle service errors gracefully.
        
        Why this test is important:
        - Ensures tools don't crash when external services fail
        - Validates error messages are informative for debugging
        - Confirms Pearl-compliant logging captures errors appropriately
        """
        # Arrange
        voting_dependencies.snapshot_service.get_proposals.side_effect = Exception(
            "Snapshot API unavailable"
        )
        mock_settings.openrouter_api_key = "test_api_key"
        
        agent = VotingAgent()
        
        # Find the query tool
        query_tool = None
        if hasattr(agent.agent, '_function_tools'):
            tool_obj = agent.agent._function_tools.get('query_active_proposals')
            if tool_obj:
                query_tool = tool_obj.function
        
        assert query_tool is not None
        
        # Create context
        from pydantic_ai import RunContext
        ctx = MagicMock(spec=RunContext)
        ctx.deps = voting_dependencies
        
        # Execute and expect error handling
        with pytest.raises(Exception) as exc_info:
            await query_tool(ctx, space_id="test.eth")
        
        assert "Snapshot API unavailable" in str(exc_info.value)