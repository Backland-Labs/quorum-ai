"""Tests for Agent Run Pydantic models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from models import (
    VotingStrategy,
    VoteDecision,
    VoteType,
    RiskLevel,
)


class TestAgentRunRequest:
    """Test cases for AgentRunRequest model."""

    def test_agent_run_request_creation_with_required_fields(self) -> None:
        """Test AgentRunRequest creation with only required fields."""
        from models import AgentRunRequest
        
        request = AgentRunRequest(space_id="test-space-123")
        
        assert request.space_id == "test-space-123"
        assert request.dry_run is False  # default value

    def test_agent_run_request_creation_with_all_fields(self) -> None:
        """Test AgentRunRequest creation with all fields."""
        from models import AgentRunRequest
        
        request = AgentRunRequest(
            space_id="test-space-456",
            dry_run=True
        )
        
        assert request.space_id == "test-space-456"
        assert request.dry_run is True

    def test_agent_run_request_space_id_validation(self) -> None:
        """Test AgentRunRequest space_id validation."""
        from models import AgentRunRequest
        
        # Test empty space_id
        with pytest.raises(ValidationError):
            AgentRunRequest(space_id="")
        
        # Test whitespace-only space_id
        with pytest.raises(ValidationError):
            AgentRunRequest(space_id="   ")
        
        # Test None space_id
        with pytest.raises(ValidationError):
            AgentRunRequest(space_id=None)  # type: ignore

    def test_agent_run_request_dry_run_validation(self) -> None:
        """Test AgentRunRequest dry_run validation."""
        from models import AgentRunRequest
        
        # Test valid boolean values
        request_true = AgentRunRequest(space_id="test-space", dry_run=True)
        assert request_true.dry_run is True
        
        request_false = AgentRunRequest(space_id="test-space", dry_run=False)
        assert request_false.dry_run is False
        
        # Test invalid non-boolean values
        with pytest.raises(ValidationError):
            AgentRunRequest(space_id="test-space", dry_run="true")  # type: ignore
        
        with pytest.raises(ValidationError):
            AgentRunRequest(space_id="test-space", dry_run=1)  # type: ignore

    def test_agent_run_request_creation_fails_with_missing_required_fields(self) -> None:
        """Test that AgentRunRequest creation fails when required fields are missing."""
        from models import AgentRunRequest
        
        with pytest.raises(ValidationError):
            AgentRunRequest()  # type: ignore


class TestAgentRunResponse:
    """Test cases for AgentRunResponse model."""

    def _create_valid_vote_decision(self) -> VoteDecision:
        """Create a valid VoteDecision for testing."""
        return VoteDecision(
            proposal_id="prop-123",
            vote=VoteType.FOR,
            confidence=0.85,
            reasoning="Test reasoning for the vote decision",
            strategy_used=VotingStrategy.BALANCED,
            risk_assessment=RiskLevel.MEDIUM,
            estimated_gas_cost=0.005
        )

    def test_agent_run_response_creation_with_required_fields(self) -> None:
        """Test AgentRunResponse creation with required fields."""
        from models import AgentRunResponse
        
        response = AgentRunResponse(
            space_id="test-space-123",
            proposals_analyzed=3,
            votes_cast=[],
            user_preferences_applied=True,
            execution_time=2.5
        )
        
        assert response.space_id == "test-space-123"
        assert response.proposals_analyzed == 3
        assert response.votes_cast == []
        assert response.user_preferences_applied is True
        assert response.execution_time == 2.5
        assert response.errors == []  # default value
        assert response.next_check_time is None  # default value

    def test_agent_run_response_creation_with_all_fields(self) -> None:
        """Test AgentRunResponse creation with all fields."""
        from models import AgentRunResponse
        
        vote_decision = self._create_valid_vote_decision()
        next_check = datetime.now()
        
        response = AgentRunResponse(
            space_id="test-space-456",
            proposals_analyzed=5,
            votes_cast=[vote_decision],
            user_preferences_applied=False,
            execution_time=4.2,
            errors=["Error 1", "Error 2"],
            next_check_time=next_check
        )
        
        assert response.space_id == "test-space-456"
        assert response.proposals_analyzed == 5
        assert len(response.votes_cast) == 1
        assert response.votes_cast[0] == vote_decision
        assert response.user_preferences_applied is False
        assert response.execution_time == 4.2
        assert response.errors == ["Error 1", "Error 2"]
        assert response.next_check_time == next_check

    def test_agent_run_response_proposals_analyzed_validation(self) -> None:
        """Test AgentRunResponse proposals_analyzed validation."""
        from models import AgentRunResponse
        
        # Test negative proposals_analyzed
        with pytest.raises(ValidationError):
            AgentRunResponse(
                space_id="test-space",
                proposals_analyzed=-1,
                votes_cast=[],
                user_preferences_applied=True,
                execution_time=1.0
            )
        
        # Test zero proposals_analyzed (should be valid)
        response = AgentRunResponse(
            space_id="test-space",
            proposals_analyzed=0,
            votes_cast=[],
            user_preferences_applied=True,
            execution_time=1.0
        )
        assert response.proposals_analyzed == 0

    def test_agent_run_response_execution_time_validation(self) -> None:
        """Test AgentRunResponse execution_time validation."""
        from models import AgentRunResponse
        
        # Test negative execution_time
        with pytest.raises(ValidationError):
            AgentRunResponse(
                space_id="test-space",
                proposals_analyzed=1,
                votes_cast=[],
                user_preferences_applied=True,
                execution_time=-1.0
            )
        
        # Test zero execution_time (should be valid)
        response = AgentRunResponse(
            space_id="test-space",
            proposals_analyzed=1,
            votes_cast=[],
            user_preferences_applied=True,
            execution_time=0.0
        )
        assert response.execution_time == 0.0

    def test_agent_run_response_with_vote_decisions(self) -> None:
        """Test AgentRunResponse with multiple vote decisions."""
        from models import AgentRunResponse
        
        vote_decision_1 = self._create_valid_vote_decision()
        vote_decision_2 = VoteDecision(
            proposal_id="prop-456",
            vote=VoteType.AGAINST,
            confidence=0.72,
            reasoning="Test reasoning for against vote",
            strategy_used=VotingStrategy.CONSERVATIVE,
            risk_assessment=RiskLevel.HIGH,
            estimated_gas_cost=0.008
        )
        
        response = AgentRunResponse(
            space_id="test-space",
            proposals_analyzed=2,
            votes_cast=[vote_decision_1, vote_decision_2],
            user_preferences_applied=True,
            execution_time=3.1
        )
        
        assert len(response.votes_cast) == 2
        assert response.votes_cast[0].proposal_id == "prop-123"
        assert response.votes_cast[1].proposal_id == "prop-456"

    def test_agent_run_response_creation_fails_with_missing_required_fields(self) -> None:
        """Test that AgentRunResponse creation fails when required fields are missing."""
        from models import AgentRunResponse
        
        with pytest.raises(ValidationError):
            AgentRunResponse(space_id="test-space")  # type: ignore


class TestUserPreferences:
    """Test cases for UserPreferences model."""

    def test_user_preferences_creation_with_defaults(self) -> None:
        """Test UserPreferences creation with default values."""
        from models import UserPreferences
        
        preferences = UserPreferences()
        
        assert preferences.voting_strategy == VotingStrategy.BALANCED
        assert preferences.confidence_threshold == 0.7
        assert preferences.max_proposals_per_run == 3
        assert preferences.blacklisted_proposers == []
        assert preferences.whitelisted_proposers == []

    def test_user_preferences_creation_with_all_fields(self) -> None:
        """Test UserPreferences creation with all fields."""
        from models import UserPreferences
        
        preferences = UserPreferences(
            voting_strategy=VotingStrategy.CONSERVATIVE,
            confidence_threshold=0.85,
            max_proposals_per_run=5,
            blacklisted_proposers=["0x123", "0x456"],
            whitelisted_proposers=["0x789", "0xabc"]
        )
        
        assert preferences.voting_strategy == VotingStrategy.CONSERVATIVE
        assert preferences.confidence_threshold == 0.85
        assert preferences.max_proposals_per_run == 5
        assert preferences.blacklisted_proposers == ["0x123", "0x456"]
        assert preferences.whitelisted_proposers == ["0x789", "0xabc"]

    def test_user_preferences_confidence_threshold_validation(self) -> None:
        """Test UserPreferences confidence_threshold validation."""
        from models import UserPreferences
        
        # Test confidence_threshold below 0
        with pytest.raises(ValidationError):
            UserPreferences(confidence_threshold=-0.1)
        
        # Test confidence_threshold above 1
        with pytest.raises(ValidationError):
            UserPreferences(confidence_threshold=1.1)
        
        # Test valid boundary values
        preferences_min = UserPreferences(confidence_threshold=0.0)
        assert preferences_min.confidence_threshold == 0.0
        
        preferences_max = UserPreferences(confidence_threshold=1.0)
        assert preferences_max.confidence_threshold == 1.0

    def test_user_preferences_max_proposals_per_run_validation(self) -> None:
        """Test UserPreferences max_proposals_per_run validation."""
        from models import UserPreferences
        
        # Test max_proposals_per_run below 1
        with pytest.raises(ValidationError):
            UserPreferences(max_proposals_per_run=0)
        
        # Test max_proposals_per_run above 10
        with pytest.raises(ValidationError):
            UserPreferences(max_proposals_per_run=11)
        
        # Test valid boundary values
        preferences_min = UserPreferences(max_proposals_per_run=1)
        assert preferences_min.max_proposals_per_run == 1
        
        preferences_max = UserPreferences(max_proposals_per_run=10)
        assert preferences_max.max_proposals_per_run == 10

    def test_user_preferences_voting_strategy_validation(self) -> None:
        """Test UserPreferences voting_strategy validation."""
        from models import UserPreferences
        
        # Test all valid voting strategies
        for strategy in [VotingStrategy.CONSERVATIVE, VotingStrategy.BALANCED, VotingStrategy.AGGRESSIVE]:
            preferences = UserPreferences(voting_strategy=strategy)
            assert preferences.voting_strategy == strategy
        
        # Test invalid voting strategy
        with pytest.raises(ValidationError):
            UserPreferences(voting_strategy="invalid_strategy")  # type: ignore

    def test_user_preferences_blacklisted_proposers_validation(self) -> None:
        """Test UserPreferences blacklisted_proposers validation."""
        from models import UserPreferences
        
        # Test empty list (should be valid)
        preferences = UserPreferences(blacklisted_proposers=[])
        assert preferences.blacklisted_proposers == []
        
        # Test list with valid addresses
        addresses = ["0x742d35cc6835c0532021efc598c51ddc1d8b4b21", "0x123abc456def789012345678901234567890abcd"]
        preferences = UserPreferences(blacklisted_proposers=addresses)
        assert preferences.blacklisted_proposers == addresses
        
        # Test list with empty strings (should be invalid)
        with pytest.raises(ValidationError):
            UserPreferences(blacklisted_proposers=[""])

    def test_user_preferences_whitelisted_proposers_validation(self) -> None:
        """Test UserPreferences whitelisted_proposers validation."""
        from models import UserPreferences
        
        # Test empty list (should be valid)
        preferences = UserPreferences(whitelisted_proposers=[])
        assert preferences.whitelisted_proposers == []
        
        # Test list with valid addresses
        addresses = ["0x742d35cc6835c0532021efc598c51ddc1d8b4b21", "0x123abc456def789012345678901234567890abcd"]
        preferences = UserPreferences(whitelisted_proposers=addresses)
        assert preferences.whitelisted_proposers == addresses
        
        # Test list with empty strings (should be invalid)
        with pytest.raises(ValidationError):
            UserPreferences(whitelisted_proposers=[""])

    def test_user_preferences_serialization_deserialization(self) -> None:
        """Test UserPreferences can be serialized and deserialized."""
        from models import UserPreferences
        
        preferences = UserPreferences(
            voting_strategy=VotingStrategy.AGGRESSIVE,
            confidence_threshold=0.9,
            max_proposals_per_run=7,
            blacklisted_proposers=["0x123"],
            whitelisted_proposers=["0x456"]
        )
        
        # Test serialization
        serialized = preferences.model_dump()
        assert serialized["voting_strategy"] == "aggressive"
        assert serialized["confidence_threshold"] == 0.9
        assert serialized["max_proposals_per_run"] == 7
        assert serialized["blacklisted_proposers"] == ["0x123"]
        assert serialized["whitelisted_proposers"] == ["0x456"]
        
        # Test deserialization
        deserialized = UserPreferences(**serialized)
        assert deserialized.voting_strategy == VotingStrategy.AGGRESSIVE
        assert deserialized.confidence_threshold == 0.9
        assert deserialized.max_proposals_per_run == 7
        assert deserialized.blacklisted_proposers == ["0x123"]
        assert deserialized.whitelisted_proposers == ["0x456"]

    def test_user_preferences_with_mixed_case_strategy(self) -> None:
        """Test UserPreferences with mixed case strategy strings."""
        from models import UserPreferences
        
        # Test that string values are case-sensitive
        with pytest.raises(ValidationError):
            UserPreferences(voting_strategy="Conservative")  # type: ignore
        
        with pytest.raises(ValidationError):
            UserPreferences(voting_strategy="BALANCED")  # type: ignore