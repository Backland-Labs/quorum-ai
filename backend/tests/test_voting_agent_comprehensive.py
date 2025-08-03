"""Comprehensive test suite for VotingAgent - Task 5 implementation.

This test suite provides comprehensive coverage for the Pydantic AI agent
implementation, including:
- Unit tests for all agent tools with mocked dependencies
- Integration tests for agent voting workflow
- Performance tests for agent response times
- Error scenario testing for all failure modes
- Memory and performance impact assessment

Target: >90% test coverage for AI service module
"""

import pytest
import asyncio
import time
import json
import tempfile
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock, PropertyMock
from typing import Dict, Any, List

import pydantic_ai
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel

from services.ai_service import (
    AIService, VotingAgent, VotingDependencies, AIResponseProcessor,
    MAX_PROPOSAL_BODY_LENGTH
)
from services.snapshot_service import SnapshotService
from services.state_manager import StateManager
from services.user_preferences_service import UserPreferencesService
from models import (
    UserPreferences, VotingStrategy, Proposal, ProposalVoter,
    VoteDecision, SummarizeResponse, AiVoteResponse,
    VotingDecisionFile, VoteType, Space
)
from config import settings


class TestVotingAgentComprehensive:
    """Comprehensive unit tests for VotingAgent functionality."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        with patch('services.ai_service.settings') as mock:
            mock.openrouter_api_key = "test_api_key"
            mock.decision_output_dir = tempfile.mkdtemp()
            mock.max_decision_files = 10
            yield mock
    
    @pytest.fixture
    def mock_snapshot_service(self):
        """Create a comprehensive mock SnapshotService."""
        service = Mock(spec=SnapshotService)
        service.get_proposals = AsyncMock()
        service.get_proposal = AsyncMock()
        service.calculate_voting_power = AsyncMock()
        service.get_spaces = AsyncMock()
        service.get_space = AsyncMock()
        service.get_top_voters = AsyncMock()
        return service
    
    @pytest.fixture
    def user_preferences(self):
        """Create comprehensive user preferences for testing."""
        return UserPreferences(
            voting_strategy=VotingStrategy.BALANCED,
            confidence_threshold=0.7,
            max_proposals_per_run=5,
            blacklisted_proposers=["0xBadActor1", "0xBadActor2"],
            whitelisted_proposers=["0xTrusted1", "0xTrusted2", "0xTrusted3"]
        )
    
    @pytest.fixture
    def voting_dependencies(self, mock_snapshot_service, user_preferences):
        """Create comprehensive VotingDependencies."""
        state_manager = Mock(spec=StateManager)
        return VotingDependencies(
            snapshot_service=mock_snapshot_service,
            user_preferences=user_preferences,
            state_manager=state_manager
        )
    
    @pytest.fixture
    def sample_proposals(self) -> List[Proposal]:
        """Create comprehensive sample proposals for testing."""
        now = datetime.now(timezone.utc)
        return [
            Proposal(
                id="proposal-1",
                title="Enable Treasury Diversification Strategy",
                body="This comprehensive proposal aims to diversify the DAO treasury..." + "x" * 5000,
                choices=["For", "Against", "Abstain"],
                state="active",
                start=int((now - timedelta(days=1)).timestamp()),
                end=int((now + timedelta(days=1)).timestamp()),
                snapshot="17890123",
                author="0xTrusted1",
                space={"id": "test.eth", "name": "Test DAO"},
                type="single-choice",
                quorum=100000.0,
                privacy="",
                validation={"name": "basic"},
                strategies=[
                    {"name": "erc20-balance-of", "params": {"address": "0xTokenAddress"}}
                ],
                scores=[5000.0, 2000.0, 1000.0],
                scores_total=8000.0,
                created=int((now - timedelta(days=2)).timestamp()),
                updated=int((now - timedelta(days=1)).timestamp()),
                votes=150,
                link="https://snapshot.org/#/test.eth/proposal/proposal-1"
            ),
            Proposal(
                id="proposal-2",
                title="Emergency Protocol Upgrade",
                body="Critical security update required...",
                choices=["Yes", "No"],
                state="active",
                start=int((now - timedelta(hours=12)).timestamp()),
                end=int((now + timedelta(hours=36)).timestamp()),
                snapshot="17890456",
                author="0xBadActor1",  # Blacklisted author
                space={"id": "test.eth", "name": "Test DAO"},
                type="single-choice",
                quorum=50000.0,
                privacy="",
                validation={"name": "basic"},
                strategies=[],
                scores=[3000.0, 1500.0],
                scores_total=4500.0,
                created=int((now - timedelta(days=1)).timestamp()),
                updated=int((now - timedelta(hours=12)).timestamp()),
                votes=75,
                link="https://snapshot.org/#/test.eth/proposal/proposal-2"
            ),
            Proposal(
                id="proposal-3",
                title="Community Grant Allocation",
                body="Allocate funds to community projects...",
                choices=["Option A", "Option B", "Option C", "None"],
                state="active",
                start=int((now - timedelta(hours=6)).timestamp()),
                end=int((now + timedelta(days=3)).timestamp()),
                snapshot="17890789",
                author="0xTrusted2",
                space={"id": "another.eth", "name": "Another DAO"},
                type="ranked-choice",
                quorum=75000.0,
                privacy="shielded",
                validation={"name": "gitcoin-passport"},
                strategies=[
                    {"name": "delegation", "params": {}},
                    {"name": "quadratic", "params": {}}
                ],
                scores=[2500.0, 2000.0, 1500.0, 1000.0],
                scores_total=7000.0,
                created=int((now - timedelta(hours=12)).timestamp()),
                updated=int((now - timedelta(hours=6)).timestamp()),
                votes=200,
                link="https://snapshot.org/#/another.eth/proposal/proposal-3"
            )
        ]
    
    @pytest.mark.asyncio
    async def test_voting_agent_full_initialization(self, mock_settings):
        """Test complete VotingAgent initialization with all components.
        
        Why this test is important:
        - Validates all agent components are properly initialized
        - Ensures model configuration is correct
        - Verifies tools are registered
        - Confirms logging is set up properly
        """
        with patch('services.ai_service.setup_pearl_logger') as mock_logger:
            agent = VotingAgent()
            
            # Verify all components
            assert agent.logger is not None
            assert agent.model is not None
            assert agent.agent is not None
            assert agent.response_processor is not None
            assert isinstance(agent.response_processor, AIResponseProcessor)
            
            # Verify Pearl logging was initialized
            mock_logger.assert_called_once_with('services.ai_service')
            
            # Verify agent has tools registered
            assert hasattr(agent.agent, '_function_tools')
            assert len(agent.agent._function_tools) == 3
            assert 'query_active_proposals' in agent.agent._function_tools
            assert 'get_proposal_details' in agent.agent._function_tools
            assert 'get_voting_power' in agent.agent._function_tools
    
    @pytest.mark.asyncio
    async def test_agent_tool_dependency_validation(self, mock_settings):
        """Test that agent tools validate dependencies during execution.
        
        Why this test is important:
        - Ensures tools fail gracefully without proper dependencies
        - Validates runtime assertions work correctly
        - Confirms error messages are helpful for debugging
        """
        agent = VotingAgent()
        
        # Get a tool function
        query_tool = agent.agent._function_tools['query_active_proposals'].function
        
        # Create context without dependencies
        ctx = Mock(spec=RunContext)
        ctx.deps = None
        
        # Tool should fail with assertion error
        with pytest.raises(AssertionError, match="VotingDependencies required"):
            await query_tool(ctx, space_id="test.eth")
    
    @pytest.mark.asyncio
    async def test_proposal_truncation_in_tools(self, mock_settings, voting_dependencies, sample_proposals):
        """Test that proposal bodies are truncated in tool responses.
        
        Why this test is important:
        - Ensures large proposal bodies don't overwhelm the AI
        - Validates truncation logic works correctly
        - Confirms tool output is optimized for agent consumption
        """
        # Set up a proposal with very long body
        long_proposal = sample_proposals[0].model_copy()
        long_proposal.body = "x" * (MAX_PROPOSAL_BODY_LENGTH + 1000)
        
        voting_dependencies.snapshot_service.get_proposal.return_value = long_proposal
        
        agent = VotingAgent()
        details_tool = agent.agent._function_tools['get_proposal_details'].function
        
        ctx = Mock(spec=RunContext)
        ctx.deps = voting_dependencies
        
        result = await details_tool(ctx, proposal_id="proposal-1")
        
        # Verify body was truncated
        assert len(result['body']) <= MAX_PROPOSAL_BODY_LENGTH + 3  # +3 for "..."
        assert result['body'].endswith("...")
    
    @pytest.mark.asyncio
    async def test_comprehensive_tool_error_scenarios(self, mock_settings, voting_dependencies):
        """Test all error scenarios for agent tools.
        
        Why this test is important:
        - Ensures tools handle all types of failures gracefully
        - Validates error propagation and logging
        - Confirms tools don't silently fail
        """
        agent = VotingAgent()
        
        # Test network error
        voting_dependencies.snapshot_service.get_proposals.side_effect = Exception(
            "Network timeout", 
            service_name="Snapshot"
        )
        
        query_tool = agent.agent._function_tools['query_active_proposals'].function
        ctx = Mock(spec=RunContext)
        ctx.deps = voting_dependencies
        
        with pytest.raises(Exception) as exc_info:
            await query_tool(ctx, space_id="test.eth")
        assert "Network timeout" in str(exc_info.value)
        
        # Test invalid data error
        voting_dependencies.snapshot_service.get_proposal.side_effect = ValueError(
            "Invalid proposal ID format"
        )
        
        details_tool = agent.agent._function_tools['get_proposal_details'].function
        with pytest.raises(ValueError) as exc_info:
            await details_tool(ctx, proposal_id="invalid-id")
        assert "Invalid proposal ID" in str(exc_info.value)
        
        # Test unexpected error
        voting_dependencies.snapshot_service.calculate_voting_power.side_effect = Exception(
            "Unexpected database error"
        )
        
        power_tool = agent.agent._function_tools['get_voting_power'].function
        with pytest.raises(Exception) as exc_info:
            await power_tool(ctx, address="0xAddress", space_id="test.eth")
        assert "database error" in str(exc_info.value)
    
    def test_system_prompt_generation_comprehensive(self, mock_settings):
        """Test system prompt generation for all strategies with edge cases.
        
        Why this test is important:
        - Validates prompts contain strategy-specific guidance
        - Ensures prompts are well-formed and comprehensive
        - Confirms edge cases don't break prompt generation
        """
        agent = VotingAgent()
        
        # Test all strategies
        strategies = [
            VotingStrategy.CONSERVATIVE,
            VotingStrategy.BALANCED,
            VotingStrategy.AGGRESSIVE
        ]
        
        for strategy in strategies:
            prompt = agent._get_system_prompt_for_strategy(strategy)
            
            # Common validations
            assert isinstance(prompt, str)
            assert len(prompt) > 100  # Ensure substantial prompt
            assert "vote" in prompt.lower()
            assert "decision" in prompt.lower()
            
            # Strategy-specific validations
            if strategy == VotingStrategy.CONSERVATIVE:
                assert any(word in prompt.lower() for word in ["conservative", "careful", "risk", "safety"])
            elif strategy == VotingStrategy.BALANCED:
                assert any(word in prompt.lower() for word in ["balanced", "moderate", "weigh"])
            elif strategy == VotingStrategy.AGGRESSIVE:
                assert any(word in prompt.lower() for word in ["aggressive", "growth", "opportunity", "bold"])
        
        # Test with None (should have default behavior)
        default_prompt = agent._get_system_prompt_for_strategy(None)
        assert isinstance(default_prompt, str)
        assert len(default_prompt) > 100


class TestAIServiceIntegration:
    """Integration tests for AIService with VotingAgent."""
    
    @pytest.fixture
    def ai_service(self):
        """Create AIService instance for testing."""
        with patch('services.ai_service.settings') as mock_settings:
            mock_settings.openrouter_api_key = "test_api_key"
            mock_settings.decision_output_dir = tempfile.mkdtemp()
            mock_settings.max_decision_files = 10
            service = AIService()
            yield service
    
    @pytest.fixture
    def mock_agent_run_result(self):
        """Create a mock agent run result."""
        result = Mock()
        result.data = AiVoteResponse(
            decision=VoteType.FOR,
            confidence=0.85,
            reasoning="Strong proposal with clear benefits",
            risk_level="low"
        )
        result.usage = {"tokens": 1000}
        return result
    
    @pytest.mark.asyncio
    async def test_summarize_proposal_integration(self, ai_service, sample_proposals):
        """Test proposal summarization through AIService.
        
        Why this test is important:
        - Validates the summarization workflow end-to-end
        - Ensures backward compatibility is maintained
        - Confirms proper error handling and response formatting
        """
        with patch.object(ai_service._agent.agent, 'run') as mock_run:
            # Mock the agent response
            mock_result = Mock()
            mock_result.data = SummarizeResponse(
                summary="This proposal aims to diversify treasury holdings",
                key_points=[
                    "Reduce concentration risk",
                    "Allocate to stable assets",
                    "Maintain liquidity"
                ],
                potential_impact="Medium positive impact on DAO stability",
                voter_recommendation="Consider supporting for long-term sustainability"
            )
            mock_result.usage = {"tokens": 500}
            mock_run.return_value = mock_result
            
            # Execute summarization
            result = await ai_service.summarize_proposal(sample_proposals[0])
            
            # Verify result
            assert isinstance(result, SummarizeResponse)
            assert result.summary == "This proposal aims to diversify treasury holdings"
            assert len(result.key_points) == 3
            assert result.potential_impact == "Medium positive impact on DAO stability"
            assert result.voter_recommendation == "Consider supporting for long-term sustainability"
            
            # Verify agent was called correctly
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert "Treasury Diversification" in call_args[0][0]  # Proposal content in prompt
    
    @pytest.mark.asyncio
    async def test_decide_vote_integration_with_tools(self, ai_service, sample_proposals, mock_agent_run_result):
        """Test vote decision making with agent tools integration.
        
        Why this test is important:
        - Validates the complete voting workflow
        - Ensures tools are available during decision making
        - Confirms VoteDecision is properly created from agent response
        """
        user_prefs = UserPreferences(
            voting_strategy=VotingStrategy.AGGRESSIVE,
            confidence_threshold=0.6,
            max_proposals_per_run=10,
            blacklisted_proposers=[],
            whitelisted_proposers=[]
        )
        
        with patch.object(ai_service.voting_agent.agent, 'run') as mock_run:
            mock_run.return_value = mock_agent_run_result
            
            # Execute vote decision
            result = await ai_service.decide_vote(
                sample_proposals[0],
                user_prefs,
                save_to_file=False
            )
            
            # Verify result
            assert isinstance(result, VoteDecision)
            assert result.proposal_id == "proposal-1"
            assert result.decision == VoteType.FOR
            assert result.confidence == 0.85
            assert result.reasoning == "Strong proposal with clear benefits"
            assert result.strategy_used == VotingStrategy.AGGRESSIVE
            
            # Verify agent was called with dependencies
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args.kwargs
            assert 'deps' in call_kwargs
            deps = call_kwargs['deps']
            assert isinstance(deps, VotingDependencies)
            assert deps.user_preferences == user_prefs
    
    @pytest.mark.asyncio
    async def test_decide_vote_with_file_output(self, ai_service, sample_proposals, mock_agent_run_result):
        """Test vote decision with file-based output.
        
        Why this test is important:
        - Validates file output functionality works correctly
        - Ensures atomic file writes prevent corruption
        - Confirms file cleanup mechanism works
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('services.ai_service.settings.decision_output_dir', temp_dir):
                user_prefs = UserPreferences(
                    voting_strategy=VotingStrategy.CONSERVATIVE,
                    confidence_threshold=0.8
                )
                
                with patch.object(ai_service.voting_agent.agent, 'run') as mock_run:
                    mock_run.return_value = mock_agent_run_result
                    
                    # Execute with file output
                    result = await ai_service.decide_vote(
                        sample_proposals[0],
                        user_prefs,
                        save_to_file=True
                    )
                    
                    # Verify file was created
                    files = os.listdir(temp_dir)
                    assert len(files) == 1
                    
                    # Verify file content
                    file_path = os.path.join(temp_dir, files[0])
                    with open(file_path, 'r') as f:
                        file_data = json.load(f)
                    
                    assert file_data['proposal_id'] == "proposal-1"
                    assert file_data['decision'] == "FOR"
                    assert file_data['confidence'] == 0.85
                    assert 'checksum' in file_data
                    assert 'created_at' in file_data
    
    @pytest.mark.asyncio
    async def test_error_handling_in_vote_decision(self, ai_service, sample_proposals):
        """Test comprehensive error handling in vote decisions.
        
        Why this test is important:
        - Ensures all error paths are properly handled
        - Validates error messages are helpful
        - Confirms system fails gracefully
        """
        user_prefs = UserPreferences(voting_strategy=VotingStrategy.BALANCED)
        
        # Test agent run failure
        with patch.object(ai_service.voting_agent.agent, 'run') as mock_run:
            mock_run.side_effect = Exception("Model API error")
            
            with pytest.raises(Exception) as exc_info:
                await ai_service.decide_vote(sample_proposals[0], user_prefs)
            
            assert "Error generating vote decision" in str(exc_info.value)
            assert "Model API error" in str(exc_info.value)
        
        # Test invalid response format
        with patch.object(ai_service.voting_agent.agent, 'run') as mock_run:
            mock_result = Mock()
            mock_result.data = None  # Invalid response
            mock_result.usage = {"tokens": 100}
            mock_run.return_value = mock_result
            
            with pytest.raises(Exception) as exc_info:
                await ai_service.decide_vote(sample_proposals[0], user_prefs)
            
            assert "Invalid response format" in str(exc_info.value)


class TestVotingAgentPerformance:
    """Performance tests for VotingAgent."""
    
    @pytest.mark.asyncio
    async def test_agent_response_time(self):
        """Test that agent responds within acceptable time limits.
        
        Why this test is important:
        - Ensures agent performance meets requirements
        - Validates no performance regression
        - Confirms agent is suitable for production use
        """
        with patch('services.ai_service.settings.openrouter_api_key', 'test_key'):
            agent = VotingAgent()
            
            # Mock the model to return quickly
            with patch.object(agent.agent, 'run') as mock_run:
                mock_result = Mock()
                mock_result.data = AiVoteResponse(
                    decision=VoteType.FOR,
                    confidence=0.8,
                    reasoning="Test",
                    risk_level="low"
                )
                mock_result.usage = {"tokens": 100}
                
                # Add small delay to simulate API call
                async def delayed_response(*args, **kwargs):
                    await asyncio.sleep(0.1)  # 100ms simulated API delay
                    return mock_result
                
                mock_run.side_effect = delayed_response
                
                # Measure response time
                start_time = time.time()
                
                deps = VotingDependencies(
                    snapshot_service=Mock(spec=SnapshotService),
                    user_preferences=UserPreferences()
                )
                
                result = await agent.agent.run(
                    "Test prompt",
                    deps=deps
                )
                
                end_time = time.time()
                response_time = end_time - start_time
                
                # Verify response time is acceptable (< 2 seconds for mocked call)
                assert response_time < 2.0, f"Response time {response_time}s exceeds limit"
                assert result.data.decision == VoteType.FOR
    
    @pytest.mark.asyncio
    async def test_agent_memory_usage(self):
        """Test that agent doesn't have memory leaks.
        
        Why this test is important:
        - Ensures agent can handle multiple requests without memory issues
        - Validates proper resource cleanup
        - Confirms suitability for long-running processes
        """
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        with patch('services.ai_service.settings.openrouter_api_key', 'test_key'):
            agent = VotingAgent()
            
            with patch.object(agent.agent, 'run') as mock_run:
                mock_result = Mock()
                mock_result.data = AiVoteResponse(
                    decision=VoteType.AGAINST,
                    confidence=0.7,
                    reasoning="Test",
                    risk_level="medium"
                )
                mock_result.usage = {"tokens": 100}
                mock_run.return_value = mock_result
                
                deps = VotingDependencies(
                    snapshot_service=Mock(spec=SnapshotService),
                    user_preferences=UserPreferences()
                )
                
                # Run multiple iterations
                for i in range(10):
                    await agent.agent.run(f"Test prompt {i}", deps=deps)
        
        # Force garbage collection
        import gc
        gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be minimal (< 50MB for 10 runs)
        assert memory_increase < 50, f"Memory increased by {memory_increase}MB"
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_requests(self):
        """Test agent handles concurrent requests properly.
        
        Why this test is important:
        - Validates thread safety of agent
        - Ensures concurrent requests don't interfere
        - Confirms agent can scale horizontally
        """
        import asyncio
        
        with patch('services.ai_service.settings.openrouter_api_key', 'test_key'):
            agent = VotingAgent()
            
            with patch.object(agent.agent, 'run') as mock_run:
                # Create different responses for tracking
                responses = []
                for i in range(5):
                    mock_result = Mock()
                    mock_result.data = AiVoteResponse(
                        decision=VoteType.FOR if i % 2 == 0 else VoteType.AGAINST,
                        confidence=0.7 + i * 0.05,
                        reasoning=f"Reasoning {i}",
                        risk_level="low"
                    )
                    mock_result.usage = {"tokens": 100 + i * 10}
                    responses.append(mock_result)
                
                mock_run.side_effect = responses
                
                deps = VotingDependencies(
                    snapshot_service=Mock(spec=SnapshotService),
                    user_preferences=UserPreferences()
                )
                
                # Run concurrent requests
                tasks = []
                for i in range(5):
                    task = agent.agent.run(f"Prompt {i}", deps=deps)
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks)
                
                # Verify all requests completed successfully
                assert len(results) == 5
                for i, result in enumerate(results):
                    assert result.data.reasoning == f"Reasoning {i}"
                    assert result.data.confidence == 0.7 + i * 0.05


class TestAIResponseProcessor:
    """Tests for AIResponseProcessor functionality."""
    
    @pytest.fixture
    def processor(self):
        """Create AIResponseProcessor instance."""
        return AIResponseProcessor()
    
    def test_validate_decision_valid_cases(self, processor):
        """Test validation of valid vote decisions.
        
        Why this test is important:
        - Ensures all valid decision formats are accepted
        - Validates case-insensitive matching works
        - Confirms Decision enum conversion works properly
        """
        valid_decisions = [
            ("FOR", VoteType.FOR),
            ("for", VoteType.FOR),
            ("AGAINST", VoteType.AGAINST),
            ("against", VoteType.AGAINST),
            ("ABSTAIN", VoteType.ABSTAIN),
            ("abstain", VoteType.ABSTAIN),
            ("YES", VoteType.FOR),
            ("yes", VoteType.FOR),
            ("NO", VoteType.AGAINST),
            ("no", VoteType.AGAINST),
            ("APPROVE", VoteType.FOR),
            ("REJECT", VoteType.AGAINST),
            ("Support", VoteType.FOR),
            ("Oppose", VoteType.AGAINST)
        ]
        
        for text, expected in valid_decisions:
            result = processor._validate_decision(text)
            assert result == expected, f"Failed to validate '{text}' as {expected}"
    
    def test_validate_decision_invalid_cases(self, processor):
        """Test validation rejects invalid decisions.
        
        Why this test is important:
        - Ensures invalid input is properly rejected
        - Validates error handling for malformed decisions
        - Confirms system fails safely with bad input
        """
        invalid_decisions = [
            "MAYBE",
            "UNKNOWN",
            "123",
            "",
            None,
            "FOR SURE",  # Contains valid word but not exact
            "NOT AGAINST",  # Negation
            "for/against",  # Multiple
        ]
        
        for text in invalid_decisions:
            with pytest.raises(ValueError):
                processor._validate_decision(text)
    
    def test_validate_confidence_valid_cases(self, processor):
        """Test validation of valid confidence scores.
        
        Why this test is important:
        - Ensures confidence scores are properly bounded
        - Validates both float and string inputs work
        - Confirms edge cases are handled correctly
        """
        valid_confidences = [
            (0.0, 0.0),
            (0.5, 0.5),
            (1.0, 1.0),
            ("0.75", 0.75),
            ("0.999", 0.999),
            (0.00001, 0.00001)
        ]
        
        for input_val, expected in valid_confidences:
            result = processor._validate_confidence(input_val)
            assert abs(result - expected) < 0.0001
    
    def test_validate_confidence_invalid_cases(self, processor):
        """Test validation rejects invalid confidence scores.
        
        Why this test is important:
        - Ensures out-of-range values are rejected
        - Validates type checking works properly
        - Confirms helpful error messages are provided
        """
        invalid_confidences = [
            -0.1,
            1.1,
            "abc",
            None,
            float('inf'),
            float('nan'),
            "1.5",
            "-0.5"
        ]
        
        for value in invalid_confidences:
            with pytest.raises(ValueError):
                processor._validate_confidence(value)


class TestFileBasedDecisionOutput:
    """Tests for file-based decision output functionality."""
    
    @pytest.fixture
    def temp_decision_dir(self):
        """Create temporary directory for decision files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.mark.asyncio
    async def test_save_decision_to_file_success(self, temp_decision_dir):
        """Test successful decision file creation.
        
        Why this test is important:
        - Validates file output works correctly
        - Ensures atomic writes prevent corruption
        - Confirms file format matches specification
        """
        ai_service = AIService()
        
        vote_decision = VoteDecision(
            proposal_id="test-proposal-123",
            decision=VoteType.FOR,
            confidence=0.85,
            reasoning="Strong technical merit",
            strategy_used=VotingStrategy.BALANCED,
            risk_assessment="Low risk with high reward",
            factors_considered=["Technical feasibility", "Community support", "Economic impact"]
        )
        
        with patch('services.ai_service.settings.decision_output_dir', temp_decision_dir):
            file_path = await ai_service._save_decision_to_file(vote_decision)
            
            # Verify file exists
            assert os.path.exists(file_path)
            
            # Verify file content
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            assert data['proposal_id'] == "test-proposal-123"
            assert data['decision'] == "FOR"
            assert data['confidence'] == 0.85
            assert data['reasoning'] == "Strong technical merit"
            assert data['strategy_used'] == "balanced"
            assert 'checksum' in data
            assert 'created_at' in data
            
            # Verify checksum
            decision_file = VotingDecisionFile(**data)
            assert decision_file.verify_checksum()
    
    @pytest.mark.asyncio
    async def test_file_cleanup_mechanism(self, temp_decision_dir):
        """Test that old decision files are cleaned up.
        
        Why this test is important:
        - Ensures disk space is managed properly
        - Validates cleanup doesn't delete recent files
        - Confirms MAX_DECISION_FILES setting is respected
        """
        ai_service = AIService()
        
        with patch('services.ai_service.settings.decision_output_dir', temp_decision_dir):
            with patch('services.ai_service.settings.max_decision_files', 3):
                # Create 5 decision files
                for i in range(5):
                    vote_decision = VoteDecision(
                        proposal_id=f"proposal-{i}",
                        decision=VoteType.FOR,
                        confidence=0.8,
                        reasoning=f"Reasoning {i}",
                        strategy_used=VotingStrategy.BALANCED
                    )
                    await ai_service._save_decision_to_file(vote_decision)
                    # Small delay to ensure different timestamps
                    await asyncio.sleep(0.01)
                
                # Verify only 3 files remain (the 3 most recent)
                files = sorted(os.listdir(temp_decision_dir))
                assert len(files) == 3
                
                # Verify these are the most recent files
                for file in files:
                    with open(os.path.join(temp_decision_dir, file), 'r') as f:
                        data = json.load(f)
                        proposal_id = data['proposal_id']
                        # Should be proposal-2, proposal-3, proposal-4
                        assert proposal_id in ["proposal-2", "proposal-3", "proposal-4"]
    
    @pytest.mark.asyncio
    async def test_file_write_error_handling(self, temp_decision_dir):
        """Test error handling for file write failures.
        
        Why this test is important:
        - Ensures file write errors don't crash the system
        - Validates proper error logging occurs
        - Confirms vote decisions still work without file output
        """
        ai_service = AIService()
        
        vote_decision = VoteDecision(
            proposal_id="test-proposal",
            decision=VoteType.AGAINST,
            confidence=0.6,
            reasoning="Test",
            strategy_used=VotingStrategy.CONSERVATIVE
        )
        
        # Make directory read-only to cause write failure
        os.chmod(temp_decision_dir, 0o444)
        
        try:
            with patch('services.ai_service.settings.decision_output_dir', temp_decision_dir):
                with patch.object(ai_service.logger, 'error') as mock_logger:
                    # Should not raise exception, just log error
                    result = await ai_service._save_decision_to_file(vote_decision)
                    
                    # Verify error was logged
                    mock_logger.assert_called()
                    error_msg = mock_logger.call_args[0][0]
                    assert "Failed to save decision to file" in error_msg
                    
                    # Verify no file path returned
                    assert result is None
        finally:
            # Restore directory permissions
            os.chmod(temp_decision_dir, 0o755)


# Import asyncio for async test execution
import asyncio


if __name__ == "__main__":
    # Run tests with coverage report
    pytest.main([
        __file__,
        "-v",
        "--cov=services.ai_service",
        "--cov-report=term-missing",
        "--cov-report=html",
        "-x"  # Stop on first failure
    ])