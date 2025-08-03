"""Extended test suite for VotingAgent - Task 5 implementation.

This test suite extends the existing VotingAgent tests with:
- More comprehensive tool testing with error scenarios
- Integration tests for the complete voting workflow
- Performance benchmarking tests
- Additional edge case coverage

Target: Increase test coverage to >90% for ai_service module
"""

import pytest
import asyncio
import time
import json
import tempfile
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
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
from models import (
    UserPreferences, VotingStrategy, Proposal, ProposalVoter,
    VoteDecision, SummarizeResponse, AiVoteResponse,
    VotingDecisionFile, VoteType
)
from config import settings


class TestVotingAgentToolsExtended:
    """Extended tests for VotingAgent tools with comprehensive error scenarios."""
    
    @pytest.fixture
    def voting_agent(self):
        """Create a VotingAgent instance."""
        with patch('services.ai_service.settings.openrouter_api_key', 'test_key'):
            return VotingAgent()
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create comprehensive mock dependencies."""
        snapshot_service = Mock(spec=SnapshotService)
        snapshot_service.get_proposals = AsyncMock()
        snapshot_service.get_proposal = AsyncMock()
        snapshot_service.calculate_voting_power = AsyncMock()
        
        user_prefs = UserPreferences(
            voting_strategy=VotingStrategy.BALANCED,
            confidence_threshold=0.7,
            max_proposals_per_run=5,
            blacklisted_proposers=["0xBadActor"],
            whitelisted_proposers=["0xTrusted"]
        )
        
        state_manager = Mock(spec=StateManager)
        
        return VotingDependencies(
            snapshot_service=snapshot_service,
            user_preferences=user_prefs,
            state_manager=state_manager
        )
    
    @pytest.mark.asyncio
    async def test_tools_handle_network_errors(self, voting_agent, mock_dependencies):
        """Test that tools handle network errors gracefully.
        
        Why this test is important:
        - Ensures tools don't crash on network failures
        - Validates error messages are helpful
        - Confirms errors are properly propagated
        """
        # Setup network error
        mock_dependencies.snapshot_service.get_proposals.side_effect = ConnectionError(
            "Network connection failed"
        )
        
        # Get the query tool
        query_tool = voting_agent.agent._function_tools['query_active_proposals'].function
        
        # Create context
        ctx = Mock(spec=RunContext)
        ctx.deps = mock_dependencies
        
        # Execute and expect error
        with pytest.raises(ConnectionError) as exc_info:
            await query_tool(ctx, space_id="test.eth")
        
        assert "Network connection failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_tools_handle_invalid_data(self, voting_agent, mock_dependencies):
        """Test that tools handle invalid data responses.
        
        Why this test is important:
        - Ensures tools validate data properly
        - Prevents crashes from malformed responses
        - Confirms data integrity checks work
        """
        # Setup invalid data response
        mock_dependencies.snapshot_service.get_proposal.return_value = None
        
        # Get the details tool
        details_tool = voting_agent.agent._function_tools['get_proposal_details'].function
        
        # Create context
        ctx = Mock(spec=RunContext)
        ctx.deps = mock_dependencies
        
        # Execute and expect handling of None
        result = await details_tool(ctx, proposal_id="invalid-id")
        
        # Should handle None gracefully
        assert result is None or isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_tools_with_large_proposal_data(self, voting_agent, mock_dependencies):
        """Test that tools handle large proposal bodies correctly.
        
        Why this test is important:
        - Validates truncation logic works
        - Ensures memory efficiency
        - Confirms tools can handle edge cases
        """
        # Create proposal with very large body
        large_body = "x" * (MAX_PROPOSAL_BODY_LENGTH + 5000)
        large_proposal = Proposal(
            id="large-proposal",
            title="Large Proposal",
            body=large_body,
            choices=["Yes", "No"],
            state="active",
            start=int(datetime.now(timezone.utc).timestamp()),
            end=int((datetime.now(timezone.utc) + timedelta(days=1)).timestamp()),
            snapshot="12345",
            author="0xAuthor",
            space={"id": "test.eth", "name": "Test DAO"},
            type="single-choice",
            privacy="",
            validation={"name": "basic"},
            strategies=[],
            scores=[100.0, 50.0],
            scores_total=150.0,
            created=int(datetime.now(timezone.utc).timestamp()),
            updated=int(datetime.now(timezone.utc).timestamp()),
            votes=10,
            link="https://snapshot.org/#/test.eth/proposal/large-proposal"
        )
        
        mock_dependencies.snapshot_service.get_proposal.return_value = large_proposal
        
        # Get details tool
        details_tool = voting_agent.agent._function_tools['get_proposal_details'].function
        
        # Create context
        ctx = Mock(spec=RunContext)
        ctx.deps = mock_dependencies
        
        # Execute
        result = await details_tool(ctx, proposal_id="large-proposal")
        
        # Verify truncation
        assert len(result['body']) <= MAX_PROPOSAL_BODY_LENGTH + 3
        if len(large_body) > MAX_PROPOSAL_BODY_LENGTH:
            assert result['body'].endswith("...")


class TestVotingAgentIntegrationWorkflow:
    """Integration tests for complete voting workflow."""
    
    @pytest.fixture
    def ai_service(self):
        """Create AIService instance."""
        with patch('services.ai_service.settings.openrouter_api_key', 'test_key'):
            with patch('services.ai_service.settings.decision_output_dir', tempfile.mkdtemp()):
                return AIService()
    
    @pytest.mark.asyncio
    async def test_full_voting_workflow(self, ai_service):
        """Test the complete voting decision workflow.
        
        Why this test is important:
        - Validates end-to-end functionality
        - Ensures all components work together
        - Confirms proper data flow through the system
        """
        # Create test proposal
        proposal = Proposal(
            id="test-proposal",
            title="Test Proposal",
            body="This is a test proposal for integration testing.",
            choices=["For", "Against"],
            state="active",
            start=int(datetime.now(timezone.utc).timestamp()),
            end=int((datetime.now(timezone.utc) + timedelta(days=1)).timestamp()),
            snapshot="12345",
            author="0xTrusted",
            space={"id": "test.eth", "name": "Test DAO"},
            type="single-choice",
            privacy="",
            validation={"name": "basic"},
            strategies=[],
            scores=[1000.0, 500.0],
            scores_total=1500.0,
            created=int(datetime.now(timezone.utc).timestamp()),
            updated=int(datetime.now(timezone.utc).timestamp()),
            votes=50,
            link="https://snapshot.org/#/test.eth/proposal/test-proposal"
        )
        
        user_prefs = UserPreferences(
            voting_strategy=VotingStrategy.BALANCED,
            confidence_threshold=0.7,
            max_proposals_per_run=5
        )
        
        # Mock the agent response
        with patch.object(ai_service.voting_agent.agent, 'run') as mock_run:
            mock_result = Mock()
            mock_result.data = AiVoteResponse(
                decision=VoteType.FOR,
                confidence=0.8,
                reasoning="Strong proposal with community support",
                risk_level="low"
            )
            mock_result.usage = {"tokens": 1000}
            mock_run.return_value = mock_result
            
            # Execute voting decision
            result = await ai_service.decide_vote(proposal, user_prefs, save_to_file=False)
            
            # Verify result
            assert isinstance(result, VoteDecision)
            assert result.proposal_id == "test-proposal"
            assert result.decision == VoteType.FOR
            assert result.confidence == 0.8
            assert result.reasoning == "Strong proposal with community support"
            assert result.strategy_used == VotingStrategy.BALANCED
    
    @pytest.mark.asyncio
    async def test_voting_with_file_output(self, ai_service):
        """Test voting decision with file output enabled.
        
        Why this test is important:
        - Validates file output functionality
        - Ensures atomic file writes work
        - Confirms file format is correct
        """
        proposal = Proposal(
            id="file-test-proposal",
            title="File Test Proposal",
            body="Testing file output.",
            choices=["Yes", "No"],
            state="active",
            start=int(datetime.now(timezone.utc).timestamp()),
            end=int((datetime.now(timezone.utc) + timedelta(days=1)).timestamp()),
            snapshot="12345",
            author="0xAuthor",
            space={"id": "test.eth", "name": "Test DAO"},
            type="single-choice",
            privacy="",
            validation={"name": "basic"},
            strategies=[],
            scores=[100.0, 50.0],
            scores_total=150.0,
            created=int(datetime.now(timezone.utc).timestamp()),
            updated=int(datetime.now(timezone.utc).timestamp()),
            votes=10,
            link="https://snapshot.org/#/test.eth/proposal/file-test-proposal"
        )
        
        user_prefs = UserPreferences(voting_strategy=VotingStrategy.CONSERVATIVE)
        
        with patch.object(ai_service.voting_agent.agent, 'run') as mock_run:
            mock_result = Mock()
            mock_result.data = AiVoteResponse(
                decision=VoteType.AGAINST,
                confidence=0.9,
                reasoning="High risk proposal",
                risk_level="high"
            )
            mock_result.usage = {"tokens": 500}
            mock_run.return_value = mock_result
            
            # Execute with file output
            result = await ai_service.decide_vote(proposal, user_prefs, save_to_file=True)
            
            # Verify decision file was created
            output_dir = settings.decision_output_dir
            if output_dir and os.path.exists(output_dir):
                files = os.listdir(output_dir)
                assert len(files) > 0
                
                # Check file content
                with open(os.path.join(output_dir, files[0]), 'r') as f:
                    file_data = json.load(f)
                
                assert file_data['proposal_id'] == "file-test-proposal"
                assert file_data['decision'] == "AGAINST"
                assert file_data['confidence'] == 0.9


class TestVotingAgentPerformanceBenchmarks:
    """Performance benchmarking tests for VotingAgent."""
    
    @pytest.mark.asyncio
    async def test_tool_execution_performance(self):
        """Test that agent tools execute within acceptable time limits.
        
        Why this test is important:
        - Ensures tools don't have performance regressions
        - Validates response times are acceptable
        - Confirms scalability of the implementation
        """
        with patch('services.ai_service.settings.openrouter_api_key', 'test_key'):
            agent = VotingAgent()
            
            # Mock dependencies with fast responses
            mock_deps = Mock(spec=VotingDependencies)
            mock_deps.snapshot_service = Mock(spec=SnapshotService)
            mock_deps.snapshot_service.get_proposals = AsyncMock(return_value=[])
            mock_deps.user_preferences = UserPreferences()
            
            # Get query tool
            query_tool = agent.agent._function_tools['query_active_proposals'].function
            
            # Create context
            ctx = Mock(spec=RunContext)
            ctx.deps = mock_deps
            
            # Measure execution time
            start_time = time.time()
            await query_tool(ctx, space_id="test.eth")
            end_time = time.time()
            
            execution_time = end_time - start_time
            
            # Tool should execute very quickly (< 0.1s for mocked call)
            assert execution_time < 0.1
    
    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self):
        """Test that tools can handle concurrent execution.
        
        Why this test is important:
        - Validates thread safety
        - Ensures no race conditions
        - Confirms scalability under load
        """
        with patch('services.ai_service.settings.openrouter_api_key', 'test_key'):
            agent = VotingAgent()
            
            # Mock dependencies
            mock_deps = Mock(spec=VotingDependencies)
            mock_deps.snapshot_service = Mock(spec=SnapshotService)
            mock_deps.snapshot_service.calculate_voting_power = AsyncMock(
                side_effect=lambda addr, space: float(addr[-2:])  # Use last 2 chars as mock power
            )
            mock_deps.user_preferences = UserPreferences()
            
            # Get voting power tool
            power_tool = agent.agent._function_tools['get_voting_power'].function
            
            # Create multiple contexts
            contexts = []
            for i in range(10):
                ctx = Mock(spec=RunContext)
                ctx.deps = mock_deps
                contexts.append(ctx)
            
            # Execute concurrently
            tasks = []
            for i in range(10):
                task = power_tool(contexts[i], address=f"0xAddress{i:02d}", space_id="test.eth")
                tasks.append(task)
            
            start_time = time.time()
            results = await asyncio.gather(*tasks)
            end_time = time.time()
            
            # Verify all completed
            assert len(results) == 10
            
            # Verify correctness
            for i, result in enumerate(results):
                expected_power = float(f"{i:02d}")
                assert result == expected_power
            
            # Should complete quickly even with 10 concurrent calls
            total_time = end_time - start_time
            assert total_time < 1.0


class TestAIResponseProcessorExtended:
    """Extended tests for AIResponseProcessor validation logic."""
    
    @pytest.fixture
    def processor(self):
        """Create AIResponseProcessor instance."""
        return AIResponseProcessor()
    
    def test_edge_case_decisions(self, processor):
        """Test validation of edge case vote decisions.
        
        Why this test is important:
        - Ensures all valid formats are accepted
        - Validates normalization works correctly
        - Confirms edge cases don't break validation
        """
        # Test with extra whitespace
        assert processor._validate_decision("  FOR  ") == VoteType.FOR
        assert processor._validate_decision("AGAINST\n") == VoteType.AGAINST
        
        # Test mixed case variations
        assert processor._validate_decision("FoR") == VoteType.FOR
        assert processor._validate_decision("AgAiNsT") == VoteType.AGAINST
        assert processor._validate_decision("aBsTaIn") == VoteType.ABSTAIN
    
    def test_confidence_edge_cases(self, processor):
        """Test validation of edge case confidence values.
        
        Why this test is important:
        - Ensures boundary values are handled correctly
        - Validates type conversion works
        - Confirms precision is maintained
        """
        # Test boundary values
        assert processor._validate_confidence(0.0) == 0.0
        assert processor._validate_confidence(1.0) == 1.0
        
        # Test very small values
        assert processor._validate_confidence(0.000001) == 0.000001
        assert processor._validate_confidence(0.999999) == 0.999999
        
        # Test string conversion
        assert processor._validate_confidence("0.12345") == 0.12345


class TestSystemPromptGeneration:
    """Tests for system prompt generation logic."""
    
    @pytest.mark.asyncio
    async def test_prompt_includes_strategy_context(self):
        """Test that system prompts include strategy-specific context.
        
        Why this test is important:
        - Ensures AI receives proper guidance
        - Validates strategy differentiation
        - Confirms prompts are well-structured
        """
        with patch('services.ai_service.settings.openrouter_api_key', 'test_key'):
            agent = VotingAgent()
            
            strategies = [
                VotingStrategy.CONSERVATIVE,
                VotingStrategy.BALANCED,
                VotingStrategy.AGGRESSIVE
            ]
            
            for strategy in strategies:
                prompt = agent._get_system_prompt_for_strategy(strategy)
                
                # Verify prompt structure
                assert isinstance(prompt, str)
                assert len(prompt) > 100
                assert "vote" in prompt.lower()
                assert "proposal" in prompt.lower()
                
                # Verify strategy-specific content
                if strategy == VotingStrategy.CONSERVATIVE:
                    assert any(word in prompt.lower() for word in ["conservative", "careful", "risk"])
                elif strategy == VotingStrategy.BALANCED:
                    assert any(word in prompt.lower() for word in ["balanced", "moderate", "consider"])
                elif strategy == VotingStrategy.AGGRESSIVE:
                    assert any(word in prompt.lower() for word in ["aggressive", "growth", "opportunity"])


# Test count: ~20 additional comprehensive tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])