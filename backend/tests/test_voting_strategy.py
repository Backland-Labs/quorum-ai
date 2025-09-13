"""Tests for VotingStrategy enum."""

import pytest
from enum import Enum

from models import VotingStrategy


class TestVotingStrategy:
    """Test cases for VotingStrategy enum."""

    def test_voting_strategy_exists(self):
        """Test that VotingStrategy enum exists."""
        assert issubclass(VotingStrategy, Enum)

    def test_voting_strategy_has_conservative(self):
        """Test that VotingStrategy has CONSERVATIVE option."""
        assert hasattr(VotingStrategy, "CONSERVATIVE")
        assert VotingStrategy.CONSERVATIVE.value == "conservative"

    def test_voting_strategy_has_balanced(self):
        """Test that VotingStrategy has BALANCED option."""
        assert hasattr(VotingStrategy, "BALANCED")
        assert VotingStrategy.BALANCED.value == "balanced"

    def test_voting_strategy_has_aggressive(self):
        """Test that VotingStrategy has AGGRESSIVE option."""
        assert hasattr(VotingStrategy, "AGGRESSIVE")
        assert VotingStrategy.AGGRESSIVE.value == "aggressive"

    def test_voting_strategy_values_are_lowercase(self):
        """Test that all VotingStrategy values are lowercase strings."""
        for strategy in VotingStrategy:
            assert isinstance(strategy.value, str)
            assert strategy.value.islower()

    def test_voting_strategy_can_be_created_from_string(self):
        """Test that VotingStrategy can be created from string values."""
        assert VotingStrategy("conservative") == VotingStrategy.CONSERVATIVE
        assert VotingStrategy("balanced") == VotingStrategy.BALANCED
        assert VotingStrategy("aggressive") == VotingStrategy.AGGRESSIVE

    def test_voting_strategy_invalid_value_raises_error(self):
        """Test that invalid strategy value raises ValueError."""
        with pytest.raises(ValueError):
            VotingStrategy("invalid_strategy")
