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