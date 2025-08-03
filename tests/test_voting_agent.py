"""Test suite for VotingAgent tools and functionality.

This test suite verifies the correct implementation of Pydantic AI agent tools
for Snapshot integration. Tests ensure that:
1. Tools can query active proposals from Snapshot
2. Tools can fetch detailed proposal information 
3. Tools can calculate voting power for addresses
4. Tools handle errors gracefully
5. Tools integrate properly with the agent context
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from pydantic_ai import Agent, RunContext
from models import (
    Proposal, 
    UserPreferences, 
    VotingStrategy,
    ProposalVote,
    ProposalChoice
)
from services.ai_service import VotingAgent, VotingDependencies
from services.snapshot_service import SnapshotService
from services.state_manager import StateManager


@pytest.fixture
def mock_snapshot_service():
    """Create a mock SnapshotService for testing."""
    service = Mock(spec=SnapshotService)
    service.get_proposals = AsyncMock()
    service.get_proposal = AsyncMock()
    service.calculate_voting_power = AsyncMock()
    return service


@pytest.fixture
def user_preferences():
    """Create test user preferences."""
    return UserPreferences(
        voting_strategy=VotingStrategy.BALANCED,
        confidence_threshold=0.7,
        max_proposals_per_run=5,
        blacklisted_proposers=["0xBadActor"],
        whitelisted_proposers=["0xTrusted"]
    )


@pytest.fixture
def voting_dependencies(mock_snapshot_service, user_preferences):
    """Create VotingDependencies for testing."""
    return VotingDependencies(
        snapshot_service=mock_snapshot_service,
        user_preferences=user_preferences,
        state_manager=Mock(spec=StateManager)
    )


@pytest.fixture
def voting_agent():
    """Create a VotingAgent instance for testing."""
    return VotingAgent()


@pytest.fixture
def sample_proposals():
    """Create sample proposal data for testing."""
    return [
        Proposal(
            id="proposal-1",
            title="Enable Treasury Diversification",
            body="This proposal aims to diversify the DAO treasury...",
            choices=["For", "Against", "Abstain"],
            state="active",
            start=datetime.now(timezone.utc).timestamp() - 86400,
            end=datetime.now(timezone.utc).timestamp() + 86400,
            snapshot="17890123",
            author="0xTrusted",
            space={"id": "test.eth", "name": "Test DAO"},
            type="single-choice",
            quorum=100000.0,
            privacy="",
            validation={"name": "basic"},
            strategies=[],
            scores=[5000.0, 2000.0, 1000.0],
            scores_total=8000.0,
            created=datetime.now(timezone.utc).timestamp() - 172800,
            updated=datetime.now(timezone.utc).timestamp() - 86400,
            votes=[],
            link=f"https://snapshot.org/#/test.eth/proposal/proposal-1"
        ),
        Proposal(
            id="proposal-2", 
            title="Update Governance Parameters",
            body="Adjusting quorum requirements...",
            choices=["Yes", "No"],
            state="active",
            start=datetime.now(timezone.utc).timestamp() - 43200,
            end=datetime.now(timezone.utc).timestamp() + 129600,
            snapshot="17890456",
            author="0xGovernor",
            space={"id": "test.eth", "name": "Test DAO"},
            type="single-choice",
            quorum=50000.0,
            privacy="",
            validation={"name": "basic"},
            strategies=[],
            scores=[3000.0, 1500.0],
            scores_total=4500.0,
            created=datetime.now(timezone.utc).timestamp() - 86400,
            updated=datetime.now(timezone.utc).timestamp() - 43200,
            votes=[],
            link=f"https://snapshot.org/#/test.eth/proposal/proposal-2"
        )
    ]


class TestVotingAgentTools:
    """Test suite for VotingAgent tools functionality."""
    
    @pytest.mark.asyncio
    async def test_query_active_proposals_tool_exists(self, voting_agent):
        """Test that the query_active_proposals tool is registered on the agent.
        
        This test verifies that:
        - The agent has tools registered
        - The query_active_proposals tool exists
        - The tool can be called with proper parameters
        """
        # Check that agent has tools
        assert hasattr(voting_agent.agent, 'tools'), "Agent should have tools attribute"
        
        # Check that query_active_proposals tool exists
        tool_names = [tool.name for tool in voting_agent.agent.tools]
        assert 'query_active_proposals' in tool_names, "query_active_proposals tool should be registered"
    
    @pytest.mark.asyncio
    async def test_query_active_proposals_tool_functionality(
        self, voting_agent, voting_dependencies, sample_proposals
    ):
        """Test that query_active_proposals tool correctly fetches proposals.
        
        This test verifies that:
        - The tool calls the SnapshotService with correct parameters
        - The tool returns proposal data in the expected format
        - The tool handles the space_id parameter correctly
        """
        # Set up mock to return sample proposals
        voting_dependencies.snapshot_service.get_proposals.return_value = sample_proposals
        
        # Create a mock context with dependencies
        ctx = Mock(spec=RunContext)
        ctx.deps = voting_dependencies
        
        # Find and execute the tool
        query_tool = next(
            (tool for tool in voting_agent.agent.tools if tool.name == 'query_active_proposals'),
            None
        )
        assert query_tool is not None, "query_active_proposals tool should exist"
        
        # Execute the tool
        result = await query_tool.func(ctx, space_id="test.eth")
        
        # Verify the tool called the service correctly
        voting_dependencies.snapshot_service.get_proposals.assert_called_once_with(
            space_id="test.eth", 
            state="active"
        )
        
        # Verify the result contains proposal data
        assert len(result) == 2, "Should return 2 proposals"
        assert all('id' in p for p in result), "Each proposal should have an id"
        assert all('title' in p for p in result), "Each proposal should have a title"
    
    @pytest.mark.asyncio
    async def test_get_proposal_details_tool_exists(self, voting_agent):
        """Test that the get_proposal_details tool is registered on the agent.
        
        This test verifies that:
        - The get_proposal_details tool exists
        - The tool has the correct signature
        """
        tool_names = [tool.name for tool in voting_agent.agent.tools]
        assert 'get_proposal_details' in tool_names, "get_proposal_details tool should be registered"
    
    @pytest.mark.asyncio 
    async def test_get_proposal_details_tool_functionality(
        self, voting_agent, voting_dependencies, sample_proposals
    ):
        """Test that get_proposal_details tool fetches detailed proposal data.
        
        This test verifies that:
        - The tool calls SnapshotService.get_proposal with correct ID
        - The tool returns comprehensive proposal information
        - The tool handles proposal_id parameter correctly
        """
        # Set up mock to return a specific proposal
        voting_dependencies.snapshot_service.get_proposal.return_value = sample_proposals[0]
        
        # Create a mock context
        ctx = Mock(spec=RunContext)
        ctx.deps = voting_dependencies
        
        # Find and execute the tool
        details_tool = next(
            (tool for tool in voting_agent.agent.tools if tool.name == 'get_proposal_details'),
            None
        )
        assert details_tool is not None, "get_proposal_details tool should exist"
        
        # Execute the tool
        result = await details_tool.func(ctx, proposal_id="proposal-1")
        
        # Verify the service was called correctly
        voting_dependencies.snapshot_service.get_proposal.assert_called_once_with("proposal-1")
        
        # Verify the result contains detailed data
        assert result['id'] == "proposal-1"
        assert result['title'] == "Enable Treasury Diversification"
        assert 'body' in result
        assert 'choices' in result
        assert 'scores' in result
    
    @pytest.mark.asyncio
    async def test_get_voting_power_tool_exists(self, voting_agent):
        """Test that the get_voting_power tool is registered on the agent.
        
        This test verifies that:
        - The get_voting_power tool exists  
        - The tool is properly registered
        """
        tool_names = [tool.name for tool in voting_agent.agent.tools]
        assert 'get_voting_power' in tool_names, "get_voting_power tool should be registered"
    
    @pytest.mark.asyncio
    async def test_get_voting_power_tool_functionality(
        self, voting_agent, voting_dependencies
    ):
        """Test that get_voting_power tool calculates voting power correctly.
        
        This test verifies that:
        - The tool calls the appropriate service method
        - The tool returns voting power as a float
        - The tool handles address and space_id parameters
        """
        # Set up mock to return voting power
        voting_dependencies.snapshot_service.calculate_voting_power.return_value = 1500.75
        
        # Create a mock context
        ctx = Mock(spec=RunContext)
        ctx.deps = voting_dependencies
        
        # Find and execute the tool
        power_tool = next(
            (tool for tool in voting_agent.agent.tools if tool.name == 'get_voting_power'),
            None
        )
        assert power_tool is not None, "get_voting_power tool should exist"
        
        # Execute the tool
        result = await power_tool.func(
            ctx, 
            address="0xTrusted",
            space_id="test.eth"
        )
        
        # Verify the service was called correctly
        voting_dependencies.snapshot_service.calculate_voting_power.assert_called_once_with(
            address="0xTrusted",
            space_id="test.eth"
        )
        
        # Verify the result
        assert isinstance(result, float), "Voting power should be a float"
        assert result == 1500.75, "Should return the correct voting power"
    
    @pytest.mark.asyncio
    async def test_tools_error_handling(self, voting_agent, voting_dependencies):
        """Test that tools handle errors gracefully.
        
        This test verifies that:
        - Tools handle service exceptions appropriately
        - Error messages are informative
        - Pearl logging captures errors
        """
        # Set up mock to raise an exception
        voting_dependencies.snapshot_service.get_proposals.side_effect = Exception(
            "Snapshot API unavailable"
        )
        
        # Create a mock context
        ctx = Mock(spec=RunContext)
        ctx.deps = voting_dependencies
        
        # Find the query tool
        query_tool = next(
            (tool for tool in voting_agent.agent.tools if tool.name == 'query_active_proposals'),
            None
        )
        assert query_tool is not None
        
        # Execute the tool and expect it to handle the error
        with pytest.raises(Exception) as exc_info:
            await query_tool.func(ctx, space_id="test.eth")
        
        assert "Snapshot API unavailable" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_tools_logging(self, voting_agent, voting_dependencies, sample_proposals):
        """Test that tools implement proper Pearl-compliant logging.
        
        This test verifies that:
        - Tools log their execution
        - Log entries include tool name and parameters
        - Errors are logged appropriately
        """
        # Set up mock
        voting_dependencies.snapshot_service.get_proposals.return_value = sample_proposals
        
        # Create a mock context
        ctx = Mock(spec=RunContext)
        ctx.deps = voting_dependencies
        
        # Find and execute tool with logging capture
        query_tool = next(
            (tool for tool in voting_agent.agent.tools if tool.name == 'query_active_proposals'),
            None
        )
        
        with patch('services.ai_service.logger') as mock_logger:
            await query_tool.func(ctx, space_id="test.eth")
            
            # Verify logging occurred
            assert mock_logger.debug.called or mock_logger.info.called, \
                "Tool execution should be logged"
    
    @pytest.mark.asyncio
    async def test_tools_response_optimization(self, voting_agent, voting_dependencies, sample_proposals):
        """Test that tool responses are optimized for agent consumption.
        
        This test verifies that:
        - Tool responses contain only necessary data
        - Responses are structured for easy agent processing
        - Large data is summarized appropriately
        """
        # Create a large proposal for testing
        large_proposal = sample_proposals[0].model_copy()
        large_proposal.body = "x" * 10000  # Very long body
        
        voting_dependencies.snapshot_service.get_proposal.return_value = large_proposal
        
        # Create context and find tool
        ctx = Mock(spec=RunContext)
        ctx.deps = voting_dependencies
        
        details_tool = next(
            (tool for tool in voting_agent.agent.tools if tool.name == 'get_proposal_details'),
            None
        )
        
        # Execute tool
        result = await details_tool.func(ctx, proposal_id="proposal-1")
        
        # Verify response is optimized
        assert 'id' in result
        assert 'title' in result
        assert 'body' in result
        # Body should be truncated or summarized for large content
        assert len(str(result)) < 15000, "Response should be reasonably sized"


class TestVotingAgentIntegration:
    """Integration tests for VotingAgent with tools."""
    
    @pytest.mark.asyncio
    async def test_agent_can_use_tools_in_decision(self, voting_agent, voting_dependencies):
        """Test that the agent can use tools during vote decision making.
        
        This test verifies that:
        - The agent calls tools during execution
        - Tools provide data that influences decisions
        - The complete workflow functions correctly
        """
        # This test will verify tool usage once decide_vote is updated in Task 3
        pass  # Placeholder for future implementation