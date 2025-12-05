"""Tests for PerformanceTracker service."""

import json
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Mock the problematic imports before importing PerformanceTracker
sys.modules['services.safe_service'] = MagicMock()
sys.modules['services.agent_run_service'] = MagicMock()
sys.modules['services.voting_service'] = MagicMock()
sys.modules['services.ai_service'] = MagicMock()
sys.modules['services.snapshot_service'] = MagicMock()
sys.modules['services.activity_service'] = MagicMock()

from services.performance_tracker import (
    PerformanceTracker,
    PerformanceMetric,
    AgentPerformance,
)


class TestPerformanceTrackerInitialization:
    """Test PerformanceTracker initialization."""

    def test_initialize_file_creates_directory(self, tmp_path):
        """Test that initializing creates parent directory if needed."""
        file_path = tmp_path / "subdir" / "agent_performance.json"
        tracker = PerformanceTracker(str(file_path))

        assert file_path.parent.exists()
        assert file_path.exists()

    def test_initialize_file_creates_valid_json(self, tmp_path):
        """Test that initialized file contains valid JSON structure."""
        file_path = tmp_path / "agent_performance.json"
        tracker = PerformanceTracker(str(file_path))

        with open(file_path, "r") as f:
            data = json.load(f)

        assert "timestamp" in data
        assert "metrics" in data
        assert "agent_behavior" in data
        assert data["timestamp"] is None
        assert data["metrics"] == []
        assert data["agent_behavior"] is None

    def test_existing_file_not_overwritten(self, tmp_path):
        """Test that existing performance file is not overwritten on init."""
        file_path = tmp_path / "agent_performance.json"

        # Create existing file with data
        existing_data = {
            "timestamp": 1234567890,
            "metrics": [{"name": "Test", "is_primary": True, "value": "42"}],
            "agent_behavior": "Existing behavior",
        }
        with open(file_path, "w") as f:
            json.dump(existing_data, f)

        # Initialize tracker
        tracker = PerformanceTracker(str(file_path))

        # Verify data was preserved
        data = tracker.read()
        assert data.timestamp == 1234567890
        assert len(data.metrics) == 1
        assert data.metrics[0].name == "Test"


class TestPerformanceTrackerRead:
    """Test PerformanceTracker read functionality."""

    def test_read_valid_file(self, tmp_path):
        """Test reading a valid performance file."""
        file_path = tmp_path / "agent_performance.json"
        tracker = PerformanceTracker(str(file_path))

        data = tracker.read()
        assert isinstance(data, AgentPerformance)
        assert data.timestamp is None
        assert data.metrics == []

    def test_read_missing_file_returns_empty(self, tmp_path):
        """Test reading returns empty data when file doesn't exist."""
        file_path = tmp_path / "agent_performance.json"
        tracker = PerformanceTracker(str(file_path))

        # Delete the file
        file_path.unlink()

        data = tracker.read()
        assert isinstance(data, AgentPerformance)
        assert data.metrics == []

    def test_read_corrupted_file_returns_empty(self, tmp_path):
        """Test reading returns empty data when file is corrupted."""
        file_path = tmp_path / "agent_performance.json"
        tracker = PerformanceTracker(str(file_path))

        # Corrupt the file
        with open(file_path, "w") as f:
            f.write("not valid json {{{")

        data = tracker.read()
        assert isinstance(data, AgentPerformance)
        assert data.metrics == []


class TestPerformanceTrackerUpdate:
    """Test PerformanceTracker update functionality."""

    def test_update_metrics(self, tmp_path):
        """Test updating metrics."""
        file_path = tmp_path / "agent_performance.json"
        tracker = PerformanceTracker(str(file_path))

        metrics = [
            PerformanceMetric(
                name="Total Attestations",
                is_primary=True,
                value="42",
            )
        ]

        tracker.update(metrics=metrics, agent_behavior="Active")

        data = tracker.read()
        assert data.timestamp is not None
        assert data.timestamp > 0
        assert len(data.metrics) == 1
        assert data.metrics[0].name == "Total Attestations"
        assert data.metrics[0].value == "42"
        assert data.metrics[0].is_primary is True
        assert data.agent_behavior == "Active"

    def test_update_creates_timestamp(self, tmp_path):
        """Test that update creates a timestamp."""
        file_path = tmp_path / "agent_performance.json"
        tracker = PerformanceTracker(str(file_path))

        initial = tracker.read()
        assert initial.timestamp is None

        tracker.update(metrics=[], agent_behavior="Test")

        updated = tracker.read()
        assert updated.timestamp is not None
        assert updated.timestamp > 0

    def test_update_truncates_extra_metrics(self, tmp_path):
        """Test that update truncates metrics to max 2."""
        file_path = tmp_path / "agent_performance.json"
        tracker = PerformanceTracker(str(file_path))

        metrics = [
            PerformanceMetric(name="Metric1", is_primary=True, value="1"),
            PerformanceMetric(name="Metric2", is_primary=False, value="2"),
            PerformanceMetric(name="Metric3", is_primary=False, value="3"),
        ]

        tracker.update(metrics=metrics)

        data = tracker.read()
        assert len(data.metrics) == 2
        assert data.metrics[0].name == "Metric1"
        assert data.metrics[1].name == "Metric2"

    def test_update_fixes_missing_primary(self, tmp_path):
        """Test that update auto-fixes when no primary metric is set."""
        file_path = tmp_path / "agent_performance.json"
        tracker = PerformanceTracker(str(file_path))

        metrics = [
            PerformanceMetric(name="Metric1", is_primary=False, value="1"),
            PerformanceMetric(name="Metric2", is_primary=False, value="2"),
        ]

        tracker.update(metrics=metrics)

        data = tracker.read()
        assert data.metrics[0].is_primary is True
        assert data.metrics[1].is_primary is False

    def test_update_fixes_multiple_primaries(self, tmp_path):
        """Test that update auto-fixes when multiple primary metrics are set."""
        file_path = tmp_path / "agent_performance.json"
        tracker = PerformanceTracker(str(file_path))

        metrics = [
            PerformanceMetric(name="Metric1", is_primary=True, value="1"),
            PerformanceMetric(name="Metric2", is_primary=True, value="2"),
        ]

        tracker.update(metrics=metrics)

        data = tracker.read()
        # First metric should be primary, second should not
        assert data.metrics[0].is_primary is True
        assert data.metrics[1].is_primary is False

    def test_update_preserves_partial_data(self, tmp_path):
        """Test that updating one field preserves other fields."""
        file_path = tmp_path / "agent_performance.json"
        tracker = PerformanceTracker(str(file_path))

        # Set initial data
        metrics = [PerformanceMetric(name="Test", is_primary=True, value="42")]
        tracker.update(metrics=metrics, agent_behavior="Initial")

        # Update only behavior
        tracker.update(agent_behavior="Updated")

        data = tracker.read()
        assert len(data.metrics) == 1
        assert data.metrics[0].name == "Test"
        assert data.agent_behavior == "Updated"


class TestComputeMetrics:
    """Test metrics computation."""

    def test_compute_with_attestation_count(self, tmp_path):
        """Test computing metrics with attestation count."""
        file_path = tmp_path / "agent_performance.json"
        tracker = PerformanceTracker(str(file_path))

        metrics, behavior = tracker.compute_current_metrics(
            attestation_count=42,
            monitored_daos=["test.eth"],
        )

        assert len(metrics) == 1
        assert metrics[0].name == "Total Attestations"
        assert metrics[0].value == "42"
        assert metrics[0].is_primary is True
        assert "Monitoring 1 DAO" in behavior

    def test_compute_with_both_metrics(self, tmp_path):
        """Test computing metrics with both attestations and proposals."""
        file_path = tmp_path / "agent_performance.json"
        tracker = PerformanceTracker(str(file_path))

        metrics, behavior = tracker.compute_current_metrics(
            attestation_count=42,
            proposals_analyzed=100,
            monitored_daos=["dao1.eth", "dao2.eth"],
        )

        assert len(metrics) == 2
        assert metrics[0].name == "Total Attestations"
        assert metrics[0].is_primary is True
        assert metrics[1].name == "Proposals Analyzed"
        assert metrics[1].is_primary is False
        assert "Monitoring 2 DAOs" in behavior

    def test_compute_with_no_daos(self, tmp_path):
        """Test computing metrics with no DAOs configured."""
        file_path = tmp_path / "agent_performance.json"
        tracker = PerformanceTracker(str(file_path))

        metrics, behavior = tracker.compute_current_metrics(
            attestation_count=0,
            monitored_daos=[],
        )

        assert behavior == "Idle - no DAOs configured"

    def test_compute_proposals_only_becomes_primary(self, tmp_path):
        """Test that proposals metric becomes primary when no attestations."""
        file_path = tmp_path / "agent_performance.json"
        tracker = PerformanceTracker(str(file_path))

        metrics, behavior = tracker.compute_current_metrics(
            proposals_analyzed=50,
            monitored_daos=["test.eth"],
        )

        assert len(metrics) == 1
        assert metrics[0].name == "Proposals Analyzed"
        assert metrics[0].is_primary is True


class TestUpdateFromRunData:
    """Test convenience update method."""

    def test_update_from_run_data(self, tmp_path):
        """Test the combined compute and update method."""
        file_path = tmp_path / "agent_performance.json"
        tracker = PerformanceTracker(str(file_path))

        tracker.update_from_run_data(
            attestation_count=10,
            proposals_analyzed=25,
            monitored_daos=["compound.eth", "nouns.eth", "arbitrum.eth"],
        )

        data = tracker.read()
        assert data.timestamp is not None
        assert len(data.metrics) == 2
        assert data.metrics[0].value == "10"
        assert data.metrics[1].value == "25"
        assert "Monitoring 3 DAOs" in data.agent_behavior


class TestAtomicWrite:
    """Test atomic write behavior."""

    def test_atomic_write_creates_temp_file(self, tmp_path):
        """Test that atomic write uses temp file."""
        file_path = tmp_path / "agent_performance.json"
        tracker = PerformanceTracker(str(file_path))

        # Update should not leave temp file
        tracker.update(agent_behavior="Test")

        temp_path = file_path.with_suffix(".tmp")
        assert not temp_path.exists()
        assert file_path.exists()

    def test_file_integrity_on_concurrent_read(self, tmp_path):
        """Test that file remains valid JSON after update."""
        file_path = tmp_path / "agent_performance.json"
        tracker = PerformanceTracker(str(file_path))

        # Perform multiple updates
        for i in range(10):
            tracker.update(agent_behavior=f"Update {i}")

        # File should still be valid
        data = tracker.read()
        assert data.agent_behavior == "Update 9"
