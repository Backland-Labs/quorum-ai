"""
Test suite for file-based voting decision output functionality.

This test suite validates the ability to save voting decisions to structured JSON files
for integration with external systems and audit trails. Tests cover:
- Model validation for VotingDecisionFile
- Atomic file write operations
- Error handling for file I/O failures
- Integration with AIService decide_vote method
- File cleanup and rotation mechanisms
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import ValidationError

from config import settings
from models import (
    AiVoteResponse,
    Proposal,
    RiskLevel,
    Space,
    UserPreferences,
    VoteDecision,
    VotingDecisionFile,
    VotingStrategy,
)
from services.ai_service import AIService, DecisionFileError


class TestVotingDecisionFileModel:
    """Test cases for VotingDecisionFile model validation and serialization."""

    def test_voting_decision_file_creation_with_required_fields(self):
        """Test that VotingDecisionFile can be created with all required fields."""
        decision_file = VotingDecisionFile(
            proposal_id="0x123456789abcdef",
            proposal_title="Increase Treasury Allocation",
            space_id="compound.eth",
            vote="FOR",
            confidence=0.85,
            risk_level=RiskLevel.MEDIUM,
            reasoning=["Proposal aligns with DAO goals"],
            voting_strategy=VotingStrategy.BALANCED,
        )

        assert decision_file.proposal_id == "0x123456789abcdef"
        assert decision_file.vote == "FOR"
        assert decision_file.confidence == 0.85
        assert decision_file.risk_level == RiskLevel.MEDIUM
        assert len(decision_file.reasoning) == 1
        assert decision_file.version == "1.0.0"
        assert decision_file.timestamp is not None

    def test_voting_decision_file_validation_constraints(self):
        """Test that VotingDecisionFile enforces validation constraints."""
        with pytest.raises(ValidationError) as exc_info:
            VotingDecisionFile(
                proposal_id="ab",  # Too short (less than 3 chars)
                proposal_title="Test",
                space_id="test.eth",
                vote="INVALID",  # Invalid vote option
                confidence=1.5,  # Out of range
                risk_level="INVALID",  # Invalid risk level
                reasoning=[],  # Empty reasoning
                voting_strategy="invalid",  # Invalid strategy
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("proposal_id",) for e in errors)
        assert any(e["loc"] == ("vote",) for e in errors)
        assert any(e["loc"] == ("confidence",) for e in errors)
        assert any(e["loc"] == ("reasoning",) for e in errors)

    def test_voting_decision_file_serialization(self):
        """Test that VotingDecisionFile serializes correctly to JSON."""
        decision_file = VotingDecisionFile(
            proposal_id="0x123456789abcdef",
            proposal_title="Test Proposal",
            space_id="test.eth",
            vote="AGAINST",
            confidence=0.75,
            risk_level=RiskLevel.HIGH,
            reasoning=["Risk too high", "Insufficient community support"],
            key_factors=["Treasury risk", "Community consensus"],
            voting_strategy=VotingStrategy.CONSERVATIVE,
            run_id="run_20250801_143000",
            dry_run=True,
        )

        json_data = decision_file.model_dump()
        assert json_data["vote"] == "AGAINST"
        assert json_data["confidence"] == 0.75
        assert json_data["risk_level"] == "HIGH"
        assert len(json_data["reasoning"]) == 2
        assert json_data["dry_run"] is True
        assert json_data["executed"] is False
        assert json_data["checksum"] is None


class TestFileOutputConfiguration:
    """Test cases for file output configuration settings."""

    def test_file_output_configuration_defaults(self):
        """Test that file output configuration has sensible defaults."""
        assert hasattr(settings, "decision_output_dir")
        assert settings.decision_output_dir == "decisions"
        assert hasattr(settings, "decision_file_format")
        assert settings.decision_file_format == "json"
        assert hasattr(settings, "max_decision_files")
        assert 1 <= settings.max_decision_files <= 1000

    def test_file_output_configuration_from_environment(self, monkeypatch):
        """Test that file output configuration can be set from environment variables."""
        monkeypatch.setenv("DECISION_OUTPUT_DIR", "custom_decisions")
        monkeypatch.setenv("DECISION_FILE_FORMAT", "json")
        monkeypatch.setenv("MAX_DECISION_FILES", "50")

        # Reload settings to pick up environment variables
        from config import Settings

        test_settings = Settings()
        assert test_settings.decision_output_dir == "custom_decisions"
        assert test_settings.max_decision_files == 50


class TestDecisionFileSaving:
    """Test cases for saving voting decisions to files."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def ai_service(self):
        """Create AIService instance for testing."""
        service = AIService()
        return service

    @pytest.fixture
    def sample_decision_file(self):
        """Create a sample VotingDecisionFile for testing."""
        return VotingDecisionFile(
            proposal_id="0x123456789abcdef0123456789abcdef",
            proposal_title="Test Proposal",
            space_id="test.eth",
            vote="FOR",
            confidence=0.85,
            risk_level=RiskLevel.MEDIUM,
            reasoning=["Good proposal", "Benefits the DAO"],
            voting_strategy=VotingStrategy.BALANCED,
            run_id="test_run_123",
        )

    async def test_save_decision_file_creates_file_with_correct_content(
        self, ai_service, sample_decision_file, temp_dir
    ):
        """Test that save_decision_file creates a file with correct JSON content."""
        file_path = await ai_service.save_decision_file(
            sample_decision_file, base_path=temp_dir
        )

        assert file_path.exists()
        assert file_path.suffix == ".json"
        assert "decision_" in file_path.name
        assert sample_decision_file.proposal_id[:8] in file_path.name

        # Verify file content
        with open(file_path, "r") as f:
            saved_data = json.load(f)

        assert saved_data["proposal_id"] == sample_decision_file.proposal_id
        assert saved_data["vote"] == "FOR"
        assert saved_data["confidence"] == 0.85
        assert saved_data["checksum"] is not None
        assert len(saved_data["checksum"]) == 64  # SHA256 hex length

    async def test_save_decision_file_creates_directory_if_not_exists(
        self, ai_service, sample_decision_file, temp_dir
    ):
        """Test that save_decision_file creates the output directory if it doesn't exist."""
        output_path = temp_dir / "new_dir" / "decisions"
        assert not output_path.exists()

        file_path = await ai_service.save_decision_file(
            sample_decision_file, base_path=output_path
        )

        assert output_path.exists()
        assert file_path.parent == output_path

    async def test_save_decision_file_handles_permission_error(
        self, ai_service, sample_decision_file, temp_dir
    ):
        """Test that save_decision_file handles permission errors gracefully."""
        # Create a directory with no write permissions
        restricted_dir = temp_dir / "restricted"
        restricted_dir.mkdir()
        restricted_dir.chmod(0o555)  # Read and execute only

        with pytest.raises(DecisionFileError) as exc_info:
            await ai_service.save_decision_file(
                sample_decision_file, base_path=restricted_dir
            )

        assert "Permission denied" in str(exc_info.value)
        assert exc_info.value.file_path is not None

    async def test_save_decision_file_atomic_write_prevents_corruption(
        self, ai_service, sample_decision_file, temp_dir
    ):
        """Test that atomic write prevents file corruption on failure."""
        # Mock os.fdopen to raise an exception during write
        with patch("os.fdopen") as mock_fdopen:
            mock_fdopen.side_effect = IOError("Disk full")

            with pytest.raises(DecisionFileError):
                await ai_service.save_decision_file(
                    sample_decision_file, base_path=temp_dir
                )

        # Verify no partial files were left behind
        decision_files = list(temp_dir.glob("decision_*.json"))
        temp_files = list(temp_dir.glob("*.tmp"))
        assert len(decision_files) == 0
        assert len(temp_files) == 0

    async def test_save_decision_file_calculates_checksum_correctly(
        self, ai_service, sample_decision_file, temp_dir
    ):
        """Test that file checksum is calculated correctly for integrity verification."""
        file_path = await ai_service.save_decision_file(
            sample_decision_file, base_path=temp_dir
        )

        with open(file_path, "r") as f:
            saved_data = json.load(f)

        # Recalculate checksum
        checksum_data = saved_data.copy()
        del checksum_data["checksum"]
        expected_checksum = ai_service._calculate_checksum(checksum_data)

        assert saved_data["checksum"] == expected_checksum


class TestDecisionFileIntegration:
    """Test cases for integration with AIService decide_vote method."""

    @pytest.fixture
    def mock_voting_agent(self):
        """Create a mock voting agent for testing."""
        agent = Mock()
        agent.run = AsyncMock()
        return agent

    @pytest.fixture
    def ai_service_with_agent(self, mock_voting_agent):
        """Create AIService with mocked voting agent."""
        service = AIService()
        service.voting_agent = Mock()
        service.voting_agent.agent = mock_voting_agent
        return service

    @pytest.fixture
    def sample_proposal(self):
        """Create a sample proposal for testing."""
        return Proposal(
            id="0x123456789abcdef0123456789abcdef",
            title="Test Proposal",
            body="This is a test proposal",
            state="active",
            start=int(datetime.now(timezone.utc).timestamp()),
            end=int(datetime.now(timezone.utc).timestamp()) + 86400,
            author="0x1234567890abcdef1234567890abcdef12345678",
            created=int(datetime.now(timezone.utc).timestamp()),
            space_id="test.eth",
        )

    @pytest.fixture
    def user_preferences(self):
        """Create sample user preferences for testing."""
        return UserPreferences(
            voting_strategy=VotingStrategy.BALANCED,
            confidence_threshold=0.7,
            max_proposals_per_run=5,
        )

    async def test_decide_vote_saves_decision_file_by_default(
        self,
        ai_service_with_agent,
        sample_proposal,
        user_preferences,
        mock_voting_agent,
        tmp_path,
        monkeypatch,
    ):
        """Test that decide_vote saves a decision file by default."""
        # Configure file output directory
        monkeypatch.setattr(settings, "store_path", str(tmp_path))

        # Mock agent response
        mock_voting_agent.run.return_value = Mock(
            data=AiVoteResponse(
                vote="FOR",
                reasoning="Good proposal for the DAO",
                confidence=0.85,
                risk_level=RiskLevel.MEDIUM,
            )
        )

        # Execute decide_vote
        decision = await ai_service_with_agent.decide_vote(
            proposal=sample_proposal,
            user_preferences=user_preferences,
            save_to_file=True,
        )

        # Verify decision was returned
        assert decision.vote == "FOR"
        assert decision.confidence == 0.85

        # Verify file was created
        decision_dir = tmp_path / settings.decision_output_dir
        assert decision_dir.exists()
        decision_files = list(decision_dir.glob("decision_*.json"))
        assert len(decision_files) == 1

        # Verify file content
        with open(decision_files[0], "r") as f:
            saved_data = json.load(f)
        assert saved_data["proposal_id"] == sample_proposal.id
        assert saved_data["vote"] == "FOR"

    async def test_decide_vote_skips_file_save_when_disabled(
        self,
        ai_service_with_agent,
        sample_proposal,
        user_preferences,
        mock_voting_agent,
        tmp_path,
        monkeypatch,
    ):
        """Test that decide_vote skips file save when save_to_file is False."""
        monkeypatch.setattr(settings, "store_path", str(tmp_path))

        mock_voting_agent.run.return_value = Mock(
            data=AiVoteResponse(
                vote="AGAINST",
                reasoning="Risky proposal",
                confidence=0.6,
                risk_level=RiskLevel.HIGH,
            )
        )

        decision = await ai_service_with_agent.decide_vote(
            proposal=sample_proposal,
            user_preferences=user_preferences,
            save_to_file=False,
        )

        assert decision.vote == "AGAINST"

        # Verify no file was created
        decision_dir = tmp_path / settings.decision_output_dir
        if decision_dir.exists():
            decision_files = list(decision_dir.glob("decision_*.json"))
            assert len(decision_files) == 0

    async def test_decide_vote_continues_on_file_save_error(
        self,
        ai_service_with_agent,
        sample_proposal,
        user_preferences,
        mock_voting_agent,
        caplog,
    ):
        """Test that decide_vote continues execution even if file save fails."""
        mock_voting_agent.run.return_value = Mock(
            data=AiVoteResponse(
                vote="ABSTAIN",
                reasoning="Neutral position",
                confidence=0.5,
                risk_level=RiskLevel.LOW,
            )
        )

        # Mock save_decision_file to raise an error
        with patch.object(
            ai_service_with_agent,
            "save_decision_file",
            side_effect=DecisionFileError("Mock file save error"),
        ):
            decision = await ai_service_with_agent.decide_vote(
                proposal=sample_proposal,
                user_preferences=user_preferences,
                save_to_file=True,
            )

        # Verify decision was still returned
        assert decision.vote == "ABSTAIN"
        assert decision.confidence == 0.5

        # Verify error was logged
        assert "Failed to save decision file" in caplog.text


class TestFileCleanupAndRotation:
    """Test cases for decision file cleanup and rotation mechanisms."""

    @pytest.fixture
    def ai_service_with_files(self, tmp_path):
        """Create AIService with multiple decision files for testing cleanup."""
        service = AIService()
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir()

        # Create multiple decision files with different timestamps
        for i in range(10):
            timestamp = datetime.now(timezone.utc).strftime(f"%Y%m%d_%H%M{i:02d}")
            filename = f"decision_{timestamp}_test{i:04d}.json"
            file_path = decisions_dir / filename
            with open(file_path, "w") as f:
                json.dump({"test": i, "timestamp": timestamp}, f)

        return service, decisions_dir

    async def test_cleanup_old_decision_files_removes_excess_files(
        self, ai_service_with_files, monkeypatch
    ):
        """Test that cleanup removes files exceeding max_decision_files limit."""
        service, decisions_dir = ai_service_with_files
        monkeypatch.setattr(settings, "max_decision_files", 5)

        # Run cleanup
        removed_count = await service.cleanup_old_decision_files(decisions_dir)

        # Verify correct number of files removed
        assert removed_count == 5
        remaining_files = list(decisions_dir.glob("decision_*.json"))
        assert len(remaining_files) == 5

    async def test_cleanup_old_decision_files_keeps_most_recent(
        self, ai_service_with_files, monkeypatch
    ):
        """Test that cleanup keeps the most recent files based on modification time."""
        service, decisions_dir = ai_service_with_files
        monkeypatch.setattr(settings, "max_decision_files", 3)

        # Get original file names sorted by modification time
        original_files = sorted(
            decisions_dir.glob("decision_*.json"), key=lambda f: f.stat().st_mtime
        )
        newest_files = [f.name for f in original_files[-3:]]

        # Run cleanup
        await service.cleanup_old_decision_files(decisions_dir)

        # Verify the newest files were kept
        remaining_files = [f.name for f in decisions_dir.glob("decision_*.json")]
        assert set(remaining_files) == set(newest_files)

    async def test_cleanup_handles_missing_directory_gracefully(self, ai_service):
        """Test that cleanup handles missing directory without raising exceptions."""
        non_existent_dir = Path("/tmp/non_existent_directory_12345")
        removed_count = await ai_service.cleanup_old_decision_files(non_existent_dir)
        assert removed_count == 0

    async def test_cleanup_logs_operations(
        self, ai_service_with_files, monkeypatch, caplog
    ):
        """Test that cleanup operations are properly logged for audit trail."""
        service, decisions_dir = ai_service_with_files
        monkeypatch.setattr(settings, "max_decision_files", 7)

        with caplog.at_level("INFO"):
            await service.cleanup_old_decision_files(decisions_dir)

        assert "[agent] Decision file cleanup:" in caplog.text
        assert "removed 3 old files" in caplog.text
        assert "retained 7 recent files" in caplog.text