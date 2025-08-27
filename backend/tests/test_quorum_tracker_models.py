"""Tests for QuorumTracker-related models."""

import pytest
from models import ActivityType


class TestActivityType:
    """Test ActivityType enum for QuorumTracker integration."""

    def test_activity_type_values(self):
        """Test ActivityType enum has correct integer values."""
        assert ActivityType.VOTE_CAST == 0
        assert ActivityType.OPPORTUNITY_CONSIDERED == 1
        assert ActivityType.NO_OPPORTUNITY == 2

    def test_activity_type_count(self):
        """Test ActivityType enum has exactly 3 values."""
        activity_types = list(ActivityType)
        assert len(activity_types) == 3

    def test_activity_type_is_int_enum(self):
        """Test ActivityType values are integers."""
        assert isinstance(ActivityType.VOTE_CAST.value, int)
        assert isinstance(ActivityType.OPPORTUNITY_CONSIDERED.value, int)  
        assert isinstance(ActivityType.NO_OPPORTUNITY.value, int)