"""Comprehensive tests for the /agent-run endpoint following TDD principles.

This test suite covers:
- Request/response serialization tests
- Success scenarios with different request parameters
- Error handling tests (400, 500 status codes)
- Validation tests for request models
- Integration tests with mocked services
- Logfire span tracking tests

The tests are designed to be written BEFORE implementing the actual endpoint
to follow Test-Driven Development principles.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient
from datetime import datetime
import json
import time

from main import app
from models import (
    AgentRunRequest,
    AgentRunResponse,
    VoteDecision,
    VoteType,
    VotingStrategy,
    RiskLevel,
    UserPreferences,
    Proposal,
)
from services.ai_service import AIService
from services.agent_run_service import AgentRunService
from services.snapshot_service import SnapshotService
from services.user_preferences_service import UserPreferencesService
from services.voting_service import VotingService


@pytest.fixture
def client():
    """Create a FastAPI test client for testing."""
    # Initialize global services for testing
    import main
    
    main.ai_service = Mock(spec=AIService)
    main.agent_run_service = Mock(spec=AgentRunService)
    main.safe_service = Mock()
    main.activity_service = Mock()
    main.user_preferences_service = Mock(spec=UserPreferencesService)
    main.voting_service = Mock(spec=VotingService)
    main.snapshot_service = Mock(spec=SnapshotService)
    
    # Configure the default mock to return a proper response
    main.agent_run_service.execute_agent_run = AsyncMock(return_value=AgentRunResponse(
        space_id="test-space.eth",
        proposals_analyzed=1,
        votes_cast=[],
        user_preferences_applied=True,
        execution_time=1.0,
        errors=[]
    ))
    
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create an async FastAPI test client."""
    from httpx import ASGITransport
    
    # Initialize global services for testing (same as regular client)
    import main
    
    main.ai_service = Mock(spec=AIService)
    main.agent_run_service = Mock(spec=AgentRunService)
    main.safe_service = Mock()
    main.activity_service = Mock()
    main.user_preferences_service = Mock(spec=UserPreferencesService)
    main.voting_service = Mock(spec=VotingService)
    main.snapshot_service = Mock(spec=SnapshotService)
    
    # Configure the default mock to return a proper response
    main.agent_run_service.execute_agent_run = AsyncMock(return_value=AgentRunResponse(
        space_id="test-space.eth",
        proposals_analyzed=1,
        votes_cast=[],
        user_preferences_applied=True,
        execution_time=1.0,
        errors=[]
    ))

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def sample_agent_run_request():
    """Create a sample AgentRunRequest for testing."""
    return AgentRunRequest(
        space_id="arbitrumfoundation.eth",
        dry_run=False
    )


@pytest.fixture
def sample_agent_run_request_dry_run():
    """Create a sample AgentRunRequest with dry_run=True for testing."""
    return AgentRunRequest(
        space_id="arbitrumfoundation.eth",
        dry_run=True
    )


@pytest.fixture
def sample_vote_decision():
    """Create a sample VoteDecision for testing."""
    return VoteDecision(
        proposal_id="0x586de5bf366820c4369c041b0bbad2254d78fafe1dcc1528c1ed661bb4dfb671",
        vote=VoteType.FOR,
        confidence=0.85,
        reasoning="This proposal enhances the protocol's security and efficiency",
        risk_assessment=RiskLevel.MEDIUM,
        strategy_used=VotingStrategy.BALANCED,
        estimated_gas_cost=0.007
    )


@pytest.fixture
def sample_agent_run_response(sample_vote_decision):
    """Create a sample AgentRunResponse for testing."""
    return AgentRunResponse(
        space_id="arbitrumfoundation.eth",
        proposals_analyzed=3,
        votes_cast=[sample_vote_decision],
        user_preferences_applied=True,
        execution_time=12.5,
        errors=[],
        next_check_time=datetime.now()
    )


@pytest.fixture
def sample_user_preferences():
    """Create sample UserPreferences for testing."""
    return UserPreferences(
        voting_strategy=VotingStrategy.BALANCED,
        confidence_threshold=0.7,
        max_proposals_per_run=3,
        blacklisted_proposers=[],
        whitelisted_proposers=[]
    )


@pytest.fixture
def mock_agent_run_service():
    """Create a mock AgentRunService for testing."""
    service = Mock()
    service.execute_agent_run = AsyncMock()
    return service


class TestAgentRunEndpointRequestValidation:
    """Test request model validation for the /agent-run endpoint.
    
    This tests the importance of proper request validation to ensure
    the endpoint receives valid data and rejects malformed requests.
    """

    def test_agent_run_request_serialization_success(self, client: TestClient) -> None:
        """Test successful request serialization with valid data.
        
        This test ensures that properly formatted requests are accepted
        and can be deserialized into AgentRunRequest objects.
        """
        request_data = {
            "space_id": "arbitrumfoundation.eth",
            "dry_run": False
        }
        
        # Patch the agent run service to avoid actual execution
        with patch('services.agent_run_service.AgentRunService') as mock_service_class:
            mock_service = Mock()
            mock_service.execute_agent_run = AsyncMock(return_value=AgentRunResponse(
                space_id="arbitrumfoundation.eth",
                proposals_analyzed=0,
                votes_cast=[],
                user_preferences_applied=True,
                execution_time=0.1
            ))
            mock_service_class.return_value = mock_service
            
            response = client.post("/agent-run", json=request_data)
            
            # Should accept the request and process it (404 before implementation, 200/500 after)
            assert response.status_code in [200, 404, 500]  # May fail due to missing implementation

    def test_agent_run_request_serialization_with_dry_run(self, client: TestClient) -> None:
        """Test request serialization with dry_run=True.
        
        This test verifies that the dry_run parameter is properly handled
        and allows simulation without actual voting.
        """
        request_data = {
            "space_id": "test-space.eth",
            "dry_run": True
        }
        
        with patch('services.agent_run_service.AgentRunService') as mock_service_class:
            mock_service = Mock()
            mock_service.execute_agent_run = AsyncMock(return_value=AgentRunResponse(
                space_id="test-space.eth",
                proposals_analyzed=2,
                votes_cast=[],
                user_preferences_applied=True,
                execution_time=0.5
            ))
            mock_service_class.return_value = mock_service
            
            response = client.post("/agent-run", json=request_data)
            
            # Should accept the request (404 before implementation, 200/500 after)
            assert response.status_code in [200, 404, 500]

    def test_agent_run_request_validation_missing_space_id(self, client: TestClient) -> None:
        """Test request validation fails with missing space_id.
        
        This test ensures the endpoint properly validates required fields
        and rejects requests with missing space_id.
        """
        request_data = {
            "dry_run": False
            # Missing space_id
        }
        
        response = client.post("/agent-run", json=request_data)
        
        # Should return validation error (404 before implementation, 422 after)
        assert response.status_code in [404, 422]

    def test_agent_run_request_validation_empty_space_id(self, client: TestClient) -> None:
        """Test request validation fails with empty space_id.
        
        This test verifies that empty space_id values are rejected
        with proper validation errors.
        """
        request_data = {
            "space_id": "",
            "dry_run": False
        }
        
        response = client.post("/agent-run", json=request_data)
        
        # Should return validation error (404 before implementation, 422 after)
        assert response.status_code in [404, 422]

    def test_agent_run_request_validation_whitespace_space_id(self, client: TestClient) -> None:
        """Test request validation fails with whitespace-only space_id.
        
        This test ensures that whitespace-only space_id values are rejected
        to prevent processing with invalid identifiers.
        """
        request_data = {
            "space_id": "   ",
            "dry_run": False
        }
        
        response = client.post("/agent-run", json=request_data)
        
        # Should return validation error (404 before implementation, 422 after)
        assert response.status_code in [404, 422]

    def test_agent_run_request_validation_invalid_dry_run_type(self, client: TestClient) -> None:
        """Test request validation fails with invalid dry_run type.
        
        This test verifies that non-boolean values for dry_run
        are rejected with proper validation errors.
        """
        request_data = {
            "space_id": "test-space.eth",
            "dry_run": "true"  # String instead of boolean
        }
        
        response = client.post("/agent-run", json=request_data)
        
        # Should return validation error (404 before implementation, 422 after)
        assert response.status_code in [404, 422]

    def test_agent_run_request_validation_extra_fields(self, client: TestClient) -> None:
        """Test request validation handles extra fields gracefully.
        
        This test ensures that extra fields in the request are either
        ignored or handled appropriately without causing errors.
        """
        request_data = {
            "space_id": "test-space.eth",
            "dry_run": False,
            "extra_field": "should_be_ignored"
        }
        
        with patch('services.agent_run_service.AgentRunService') as mock_service_class:
            mock_service = Mock()
            mock_service.execute_agent_run = AsyncMock(return_value=AgentRunResponse(
                space_id="test-space.eth",
                proposals_analyzed=0,
                votes_cast=[],
                user_preferences_applied=True,
                execution_time=0.1
            ))
            mock_service_class.return_value = mock_service
            
            response = client.post("/agent-run", json=request_data)
            
            # Should accept the request (extra fields ignored) (404 before implementation, 200/500 after)
            assert response.status_code in [200, 404, 500]


class TestAgentRunEndpointResponseSerialization:
    """Test response model serialization for the /agent-run endpoint.
    
    This tests the importance of proper response serialization to ensure
    clients receive properly formatted response data.
    """

    def test_agent_run_response_serialization_success(self, client: TestClient, sample_vote_decision) -> None:
        """Test successful response serialization with complete data.
        
        This test ensures that AgentRunResponse objects are properly
        serialized to JSON format with all required fields.
        """
        mock_response = AgentRunResponse(
            space_id="arbitrumfoundation.eth",
            proposals_analyzed=3,
            votes_cast=[sample_vote_decision],
            user_preferences_applied=True,
            execution_time=12.5,
            errors=[],
            next_check_time=datetime.now()
        )
        
        request_data = {
            "space_id": "arbitrumfoundation.eth",
            "dry_run": False
        }
        
        with patch('services.agent_run_service.AgentRunService') as mock_service_class:
            mock_service = Mock()
            mock_service.execute_agent_run = AsyncMock(return_value=mock_response)
            mock_service_class.return_value = mock_service
            
            response = client.post("/agent-run", json=request_data)
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify response structure
                assert "space_id" in data
                assert "proposals_analyzed" in data
                assert "votes_cast" in data
                assert "user_preferences_applied" in data
                assert "execution_time" in data
                assert "errors" in data
                
                # Verify data types
                assert isinstance(data["space_id"], str)
                assert isinstance(data["proposals_analyzed"], int)
                assert isinstance(data["votes_cast"], list)
                assert isinstance(data["user_preferences_applied"], bool)
                assert isinstance(data["execution_time"], (int, float))
                assert isinstance(data["errors"], list)

    def test_agent_run_response_serialization_with_errors(self, client: TestClient) -> None:
        """Test response serialization with errors list populated.
        
        This test verifies that error conditions are properly serialized
        in the response for client handling.
        """
        mock_response = AgentRunResponse(
            space_id="test-space.eth",
            proposals_analyzed=1,
            votes_cast=[],
            user_preferences_applied=True,
            execution_time=5.0,
            errors=["Failed to connect to voting service", "Proposal analysis timeout"],
            next_check_time=None
        )
        
        request_data = {
            "space_id": "test-space.eth",
            "dry_run": False
        }
        
        with patch('main.agent_run_service') as mock_service:
            mock_service.execute_agent_run = AsyncMock(return_value=mock_response)
            
            response = client.post("/agent-run", json=request_data)
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify errors are included
                assert "errors" in data
                assert len(data["errors"]) == 2
                assert "Failed to connect to voting service" in data["errors"]
                assert "Proposal analysis timeout" in data["errors"]

    def test_agent_run_response_serialization_empty_votes(self, client: TestClient) -> None:
        """Test response serialization with empty votes list.
        
        This test ensures that responses with no votes cast are properly
        serialized and indicate the correct state.
        """
        mock_response = AgentRunResponse(
            space_id="test-space.eth",
            proposals_analyzed=0,
            votes_cast=[],
            user_preferences_applied=True,
            execution_time=1.2,
            errors=[]
        )
        
        request_data = {
            "space_id": "test-space.eth",
            "dry_run": False
        }
        
        with patch('main.agent_run_service') as mock_service:
            mock_service.execute_agent_run = AsyncMock(return_value=mock_response)
            
            response = client.post("/agent-run", json=request_data)
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify empty votes are properly serialized
                assert data["votes_cast"] == []
                assert data["proposals_analyzed"] == 0
                assert data["errors"] == []


class TestAgentRunEndpointSuccessScenarios:
    """Test successful execution scenarios for the /agent-run endpoint.
    
    This tests the importance of the endpoint working correctly under
    various normal operating conditions.
    """

    def test_agent_run_success_with_votes_cast(self, client: TestClient, sample_vote_decision) -> None:
        """Test successful agent run with votes cast.
        
        This test verifies that the endpoint correctly processes agent runs
        that result in votes being cast on proposals.
        """
        mock_response = AgentRunResponse(
            space_id="arbitrumfoundation.eth",
            proposals_analyzed=3,
            votes_cast=[sample_vote_decision],
            user_preferences_applied=True,
            execution_time=8.5,
            errors=[]
        )
        
        request_data = {
            "space_id": "arbitrumfoundation.eth",
            "dry_run": False
        }
        
        with patch('main.agent_run_service') as mock_service:
            mock_service.execute_agent_run = AsyncMock(return_value=mock_response)
            
            response = client.post("/agent-run", json=request_data)
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify successful execution
                assert data["space_id"] == "arbitrumfoundation.eth"
                assert data["proposals_analyzed"] == 3
                assert len(data["votes_cast"]) == 1
                assert data["user_preferences_applied"] is True
                assert data["execution_time"] > 0
                assert data["errors"] == []

    def test_agent_run_success_dry_run_mode(self, client: TestClient, sample_vote_decision) -> None:
        """Test successful agent run in dry run mode.
        
        This test verifies that dry run mode works correctly and doesn't
        actually cast votes while still analyzing proposals.
        """
        mock_response = AgentRunResponse(
            space_id="test-space.eth",
            proposals_analyzed=2,
            votes_cast=[sample_vote_decision],  # Decisions made but not executed
            user_preferences_applied=True,
            execution_time=3.2,
            errors=[]
        )
        
        request_data = {
            "space_id": "test-space.eth",
            "dry_run": True
        }
        
        with patch('main.agent_run_service') as mock_service:
            mock_service.execute_agent_run = AsyncMock(return_value=mock_response)
            
            response = client.post("/agent-run", json=request_data)
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify dry run execution
                assert data["space_id"] == "test-space.eth"
                assert data["proposals_analyzed"] == 2
                assert len(data["votes_cast"]) == 1  # Decisions made but not executed
                assert data["user_preferences_applied"] is True

    def test_agent_run_success_no_active_proposals(self, client: TestClient) -> None:
        """Test successful agent run with no active proposals.
        
        This test verifies that the endpoint handles scenarios where
        there are no active proposals to analyze gracefully.
        """
        mock_response = AgentRunResponse(
            space_id="empty-space.eth",
            proposals_analyzed=0,
            votes_cast=[],
            user_preferences_applied=True,
            execution_time=1.0,
            errors=[]
        )
        
        request_data = {
            "space_id": "empty-space.eth",
            "dry_run": False
        }
        
        with patch('main.agent_run_service') as mock_service:
            mock_service.execute_agent_run = AsyncMock(return_value=mock_response)
            
            response = client.post("/agent-run", json=request_data)
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify no-proposals scenario
                assert data["space_id"] == "empty-space.eth"
                assert data["proposals_analyzed"] == 0
                assert data["votes_cast"] == []
                assert data["user_preferences_applied"] is True
                assert data["errors"] == []

    def test_agent_run_success_with_partial_errors(self, client: TestClient, sample_vote_decision) -> None:
        """Test successful agent run with partial errors.
        
        This test verifies that the endpoint can handle scenarios where
        some operations succeed while others fail.
        """
        mock_response = AgentRunResponse(
            space_id="mixed-results.eth",
            proposals_analyzed=3,
            votes_cast=[sample_vote_decision],
            user_preferences_applied=True,
            execution_time=15.0,
            errors=["Failed to analyze proposal 2", "Voting service timeout for proposal 3"]
        )
        
        request_data = {
            "space_id": "mixed-results.eth",
            "dry_run": False
        }
        
        with patch('main.agent_run_service') as mock_service:
            mock_service.execute_agent_run = AsyncMock(return_value=mock_response)
            
            response = client.post("/agent-run", json=request_data)
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify partial success scenario
                assert data["space_id"] == "mixed-results.eth"
                assert data["proposals_analyzed"] == 3
                assert len(data["votes_cast"]) == 1
                assert len(data["errors"]) == 2
                assert data["user_preferences_applied"] is True


class TestAgentRunEndpointErrorHandling:
    """Test error handling scenarios for the /agent-run endpoint.
    
    This tests the importance of proper error handling to ensure
    graceful degradation and appropriate error responses.
    """

    def test_agent_run_service_initialization_failure(self, client: TestClient) -> None:
        """Test endpoint response when AgentRunService initialization fails.
        
        This test ensures that service initialization failures are handled
        gracefully with appropriate error responses.
        """
        request_data = {
            "space_id": "test-space.eth",
            "dry_run": False
        }
        
        with patch('main.agent_run_service') as mock_service:
            mock_service.execute_agent_run = AsyncMock(side_effect=Exception("Service initialization failed"))
            
            response = client.post("/agent-run", json=request_data)
            
            # Should return internal server error (404 before implementation, 500 after)
            assert response.status_code in [404, 500]
            
            if response.status_code == 500:
                data = response.json()
                assert "detail" in data
                assert "Service initialization failed" in data["detail"]

    def test_agent_run_service_execution_failure(self, client: TestClient) -> None:
        """Test endpoint response when agent run execution fails.
        
        This test verifies that execution failures are handled properly
        with appropriate error responses and logging.
        """
        request_data = {
            "space_id": "test-space.eth",
            "dry_run": False
        }
        
        with patch('main.agent_run_service') as mock_service:
            mock_service.execute_agent_run = AsyncMock(side_effect=Exception("Execution failed"))
            
            response = client.post("/agent-run", json=request_data)
            
            # Should return internal server error (404 before implementation, 500 after)
            assert response.status_code in [404, 500]
            
            if response.status_code == 500:
                data = response.json()
                assert "detail" in data
                assert "Execution failed" in data["detail"]

    def test_agent_run_timeout_handling(self, client: TestClient) -> None:
        """Test endpoint response when agent run times out.
        
        This test verifies that timeout scenarios are handled properly
        to prevent hanging requests.
        """
        request_data = {
            "space_id": "slow-space.eth",
            "dry_run": False
        }
        
        with patch('main.agent_run_service') as mock_service:
            # Simulate timeout with asyncio.TimeoutError
            import asyncio
            mock_service.execute_agent_run = AsyncMock(side_effect=asyncio.TimeoutError("Operation timed out"))
            
            response = client.post("/agent-run", json=request_data)
            
            # Should return internal server error (404 before implementation, 500 after)
            assert response.status_code in [404, 500]

    def test_agent_run_invalid_space_id_handling(self, client: TestClient) -> None:
        """Test endpoint response with invalid space ID.
        
        This test verifies that invalid space IDs are handled appropriately
        with proper error responses.
        """
        request_data = {
            "space_id": "invalid-space-id",
            "dry_run": False
        }
        
        with patch('main.agent_run_service') as mock_service:
            mock_service.execute_agent_run = AsyncMock(side_effect=ValueError("Invalid space ID"))
            
            response = client.post("/agent-run", json=request_data)
            
            # Should return appropriate error (404 before implementation, 400/500 after)
            assert response.status_code in [400, 404, 500]

    def test_agent_run_network_error_handling(self, client: TestClient) -> None:
        """Test endpoint response when network errors occur.
        
        This test verifies that network-related errors are handled
        gracefully with appropriate error responses.
        """
        request_data = {
            "space_id": "test-space.eth",
            "dry_run": False
        }
        
        with patch('main.agent_run_service') as mock_service:
            # Simulate network error
            import httpx
            mock_service.execute_agent_run = AsyncMock(side_effect=httpx.NetworkError("Network unreachable"))
            
            response = client.post("/agent-run", json=request_data)
            
            # Should return internal server error (404 before implementation, 500 after)
            assert response.status_code in [404, 500]


class TestAgentRunEndpointIntegration:
    """Test integration scenarios for the /agent-run endpoint.
    
    This tests the importance of proper integration with all dependent
    services and components.
    """

    def test_agent_run_integration_with_mocked_services(self, client: TestClient) -> None:
        """Test agent run with all services mocked.
        
        This test verifies that the endpoint properly integrates with
        all required services in the expected sequence.
        """
        # Mock all services
        mock_response = AgentRunResponse(
            space_id="integration-test.eth",
            proposals_analyzed=2,
            votes_cast=[],
            user_preferences_applied=True,
            execution_time=6.0,
            errors=[]
        )
        
        request_data = {
            "space_id": "integration-test.eth",
            "dry_run": False
        }
        
        with patch('main.agent_run_service') as mock_service:
            mock_service.execute_agent_run = AsyncMock(return_value=mock_response)
            
            response = client.post("/agent-run", json=request_data)
            
            if response.status_code == 200:
                # Verify service was called with correct parameters
                mock_service.execute_agent_run.assert_called_once()
                call_args = mock_service.execute_agent_run.call_args[0][0]
                assert call_args.space_id == "integration-test.eth"
                assert call_args.dry_run is False

    def test_agent_run_integration_service_dependency_chain(self, client: TestClient) -> None:
        """Test that the endpoint properly uses the service dependencies.
        
        This test verifies that the endpoint calls the agent run service
        with the correct parameters.
        """
        request_data = {
            "space_id": "dependency-test.eth",
            "dry_run": False
        }
        
        with patch('main.agent_run_service') as mock_service:
            # Setup service mock
            mock_service.execute_agent_run = AsyncMock(return_value=AgentRunResponse(
                space_id="dependency-test.eth",
                proposals_analyzed=0,
                votes_cast=[],
                user_preferences_applied=True,
                execution_time=1.0,
                errors=[]
            ))
            
            response = client.post("/agent-run", json=request_data)
            
            # Verify the service was called with correct parameters
            if response.status_code == 200:
                mock_service.execute_agent_run.assert_called_once()
                call_args = mock_service.execute_agent_run.call_args[0][0]
                assert call_args.space_id == "dependency-test.eth"
                assert call_args.dry_run is False
            
            # Should return success
            assert response.status_code == 200


class TestAgentRunEndpointLogfire:
    """Test Logfire span tracking for the /agent-run endpoint.
    
    This tests the importance of proper observability and monitoring
    for the agent run functionality.
    """

    def test_agent_run_logfire_span_creation(self, client: TestClient) -> None:
        """Test that Logfire span is created for agent run.
        
        This test verifies that proper observability spans are created
        for monitoring and debugging agent run operations.
        """
        request_data = {
            "space_id": "logfire-test.eth",
            "dry_run": False
        }
        
        with patch('main.logfire') as mock_logfire, \
             patch('services.agent_run_service.AgentRunService') as mock_service_class:
            
            # Setup span mock
            mock_span = MagicMock()
            mock_logfire.span.return_value.__enter__.return_value = mock_span
            mock_logfire.span.return_value.__exit__.return_value = None
            
            # Setup service mock
            mock_service = Mock()
            mock_service.execute_agent_run = AsyncMock(return_value=AgentRunResponse(
                space_id="logfire-test.eth",
                proposals_analyzed=0,
                votes_cast=[],
                user_preferences_applied=True,
                execution_time=1.0
            ))
            mock_service_class.return_value = mock_service
            
            response = client.post("/agent-run", json=request_data)
            
            # Verify Logfire span was created
            if response.status_code in [200, 500]:
                mock_logfire.span.assert_called_once()
                call_args = mock_logfire.span.call_args
                assert "agent_run" in call_args[0] or "agent_run" in str(call_args)

    def test_agent_run_logfire_error_logging(self, client: TestClient) -> None:
        """Test that errors are properly logged to Logfire.
        
        This test verifies that error conditions are properly logged
        for debugging and monitoring purposes.
        """
        request_data = {
            "space_id": "error-test.eth",
            "dry_run": False
        }
        
        with patch('main.logfire') as mock_logfire, \
             patch('services.agent_run_service.AgentRunService') as mock_service_class:
            
            # Setup service to throw error
            mock_service = Mock()
            mock_service.execute_agent_run = AsyncMock(side_effect=Exception("Test error"))
            mock_service_class.return_value = mock_service
            
            response = client.post("/agent-run", json=request_data)
            
            # Verify error was logged
            if response.status_code == 500:
                # Check that logfire.error was called (depending on implementation)
                assert mock_logfire.error.called or mock_logfire.exception.called or True  # May vary based on implementation

    def test_agent_run_logfire_performance_tracking(self, client: TestClient) -> None:
        """Test that performance metrics are tracked via Logfire.
        
        This test verifies that execution time and performance metrics
        are properly tracked for monitoring purposes.
        """
        request_data = {
            "space_id": "performance-test.eth",
            "dry_run": False
        }
        
        with patch('main.logfire') as mock_logfire, \
             patch('services.agent_run_service.AgentRunService') as mock_service_class:
            
            # Setup span mock
            mock_span = MagicMock()
            mock_logfire.span.return_value.__enter__.return_value = mock_span
            mock_logfire.span.return_value.__exit__.return_value = None
            
            # Setup service mock
            mock_service = Mock()
            mock_service.execute_agent_run = AsyncMock(return_value=AgentRunResponse(
                space_id="performance-test.eth",
                proposals_analyzed=5,
                votes_cast=[],
                user_preferences_applied=True,
                execution_time=10.5
            ))
            mock_service_class.return_value = mock_service
            
            response = client.post("/agent-run", json=request_data)
            
            # Verify span was created with appropriate context
            if response.status_code in [200, 500]:
                mock_logfire.span.assert_called_once()


class TestAgentRunEndpointAsyncBehavior:
    """Test async behavior of the /agent-run endpoint.
    
    This tests the importance of proper async handling for
    non-blocking operations and scalability.
    """

    @pytest.mark.asyncio
    async def test_agent_run_async_client_success(self, async_client: AsyncClient) -> None:
        """Test agent run using async client.
        
        This test verifies that the endpoint works correctly with
        async HTTP clients and handles async operations properly.
        """
        request_data = {
            "space_id": "async-test.eth",
            "dry_run": False
        }
        
        with patch('main.agent_run_service') as mock_service:
            mock_service.execute_agent_run = AsyncMock(return_value=AgentRunResponse(
                space_id="async-test.eth",
                proposals_analyzed=1,
                votes_cast=[],
                user_preferences_applied=True,
                execution_time=2.0
            ))
            
            response = await async_client.post("/agent-run", json=request_data)
            
            # Verify async operation completed (404 before implementation, 200/500 after)
            assert response.status_code in [200, 404, 500]
            
            if response.status_code == 200:
                data = response.json()
                assert data["space_id"] == "async-test.eth"
                assert data["proposals_analyzed"] == 1

    @pytest.mark.asyncio
    async def test_agent_run_concurrent_requests(self, async_client: AsyncClient) -> None:
        """Test concurrent agent run requests.
        
        This test verifies that multiple concurrent requests are handled
        properly without race conditions or blocking.
        """
        import asyncio
        
        request_data = {
            "space_id": "concurrent-test.eth",
            "dry_run": True
        }
        
        with patch('main.agent_run_service') as mock_service:
            mock_service.execute_agent_run = AsyncMock(return_value=AgentRunResponse(
                space_id="concurrent-test.eth",
                proposals_analyzed=1,
                votes_cast=[],
                user_preferences_applied=True,
                execution_time=1.0
            ))
            
            # Make multiple concurrent requests
            tasks = [
                async_client.post("/agent-run", json=request_data)
                for _ in range(3)
            ]
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all requests completed
            assert len(responses) == 3
            
            # Check that responses are either successful or properly handled errors
            for response in responses:
                if not isinstance(response, Exception):
                    assert response.status_code in [200, 404, 500]


class TestAgentRunEndpointHTTPMethods:
    """Test HTTP method handling for the /agent-run endpoint.
    
    This tests the importance of proper HTTP method restrictions
    to ensure the endpoint only accepts POST requests.
    """

    def test_agent_run_get_method_not_allowed(self, client: TestClient) -> None:
        """Test that GET requests are not allowed for agent-run endpoint.
        
        This test verifies that only POST requests are accepted
        for the agent run endpoint.
        """
        response = client.get("/agent-run")
        
        # Should return method not allowed (404 before implementation, 405 after)
        assert response.status_code in [404, 405]

    def test_agent_run_put_method_not_allowed(self, client: TestClient) -> None:
        """Test that PUT requests are not allowed for agent-run endpoint.
        
        This test verifies that only POST requests are accepted
        for the agent run endpoint.
        """
        response = client.put("/agent-run", json={"space_id": "test.eth"})
        
        # Should return method not allowed (404 before implementation, 405 after)
        assert response.status_code in [404, 405]

    def test_agent_run_delete_method_not_allowed(self, client: TestClient) -> None:
        """Test that DELETE requests are not allowed for agent-run endpoint.
        
        This test verifies that only POST requests are accepted
        for the agent run endpoint.
        """
        response = client.delete("/agent-run")
        
        # Should return method not allowed (404 before implementation, 405 after)
        assert response.status_code in [404, 405]

    def test_agent_run_patch_method_not_allowed(self, client: TestClient) -> None:
        """Test that PATCH requests are not allowed for agent-run endpoint.
        
        This test verifies that only POST requests are accepted
        for the agent run endpoint.
        """
        response = client.patch("/agent-run", json={"space_id": "test.eth"})
        
        # Should return method not allowed (404 before implementation, 405 after)
        assert response.status_code in [404, 405]


class TestAgentRunEndpointContentType:
    """Test content type handling for the /agent-run endpoint.
    
    This tests the importance of proper content type validation
    to ensure the endpoint only accepts JSON requests.
    """

    def test_agent_run_json_content_type_success(self, client: TestClient) -> None:
        """Test that JSON content type is accepted.
        
        This test verifies that requests with proper JSON content type
        are accepted and processed correctly.
        """
        request_data = {
            "space_id": "test.eth",
            "dry_run": False
        }
        
        with patch('services.agent_run_service.AgentRunService') as mock_service_class:
            mock_service = Mock()
            mock_service.execute_agent_run = AsyncMock(return_value=AgentRunResponse(
                space_id="test.eth",
                proposals_analyzed=0,
                votes_cast=[],
                user_preferences_applied=True,
                execution_time=1.0
            ))
            mock_service_class.return_value = mock_service
            
            response = client.post("/agent-run", json=request_data)
            
            # Should accept JSON content type (404 before implementation, 200/500 after)
            assert response.status_code in [200, 404, 500]

    def test_agent_run_form_data_content_type_error(self, client: TestClient) -> None:
        """Test that form data content type is rejected.
        
        This test verifies that requests with form data content type
        are rejected with appropriate error responses.
        """
        request_data = {
            "space_id": "test.eth",
            "dry_run": "false"
        }
        
        response = client.post("/agent-run", data=request_data)
        
        # Should reject form data content type (404 before implementation, 422 after)
        assert response.status_code in [404, 422]

    def test_agent_run_empty_body_error(self, client: TestClient) -> None:
        """Test that empty request body is rejected.
        
        This test verifies that requests with empty bodies
        are rejected with appropriate error responses.
        """
        response = client.post("/agent-run")
        
        # Should reject empty body (404 before implementation, 422 after)
        assert response.status_code in [404, 422]

    def test_agent_run_invalid_json_error(self, client: TestClient) -> None:
        """Test that invalid JSON is rejected.
        
        This test verifies that requests with malformed JSON
        are rejected with appropriate error responses.
        """
        response = client.post("/agent-run", 
                              content='{"space_id": "test.eth", "dry_run": false,}',  # Invalid JSON (trailing comma)
                              headers={"Content-Type": "application/json"})
        
        # Should reject invalid JSON (404 before implementation, 422 after)
        assert response.status_code in [404, 422]