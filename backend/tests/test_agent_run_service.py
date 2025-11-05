"""Tests for AgentRunService immediate attestation functionality."""

import logging
import pytest
from unittest.mock import AsyncMock, Mock, patch
from models import VoteDecision, VoteType, VotingStrategy, EASAttestationData
from services.agent_run_service import AgentRunService


# Valid 66-character transaction hash for testing
VALID_TX_HASH = "0x" + "a" * 64


@pytest.fixture
def agent_run_service():
    """Create an AgentRunService instance with mocked dependencies."""
    with patch("services.agent_run_service.SnapshotService"), \
         patch("services.agent_run_service.AIService"), \
         patch("services.agent_run_service.VotingService"), \
         patch("services.agent_run_service.SafeService"), \
         patch("services.agent_run_service.ActivityService"), \
         patch("services.agent_run_service.UserPreferencesService"):
        
        service = AgentRunService()
        
        # Set up default mocks
        service.voting_service.account = Mock()
        service.voting_service.account.address = "0xTestAgent"
        service.voting_service.vote_on_proposal = AsyncMock()
        service.safe_service.create_eas_attestation = AsyncMock()
        service.activity_service.mark_activity_completed = Mock()
        
        yield service


class TestImmediateAttestation:
    """Test immediate attestation after vote submission."""

    @pytest.mark.asyncio
    async def test_immediate_attestation_after_successful_vote(self, agent_run_service):
        """Test that attestation is created immediately after successful vote.

        Importance: Verifies the core immediate attestation flow works correctly
        when votes succeed, ensuring on-chain audit trail is created promptly.
        This is the happy path that should occur for most votes.
        """
        # Mock vote success with valid 66-character transaction hash
        agent_run_service.voting_service.vote_on_proposal = AsyncMock(
            return_value={
                "success": True,
                "submission_result": {"success": True, "response": {"id": VALID_TX_HASH}},
            }
        )

        # Mock successful attestation
        agent_run_service.safe_service.create_eas_attestation = AsyncMock(
            return_value={"success": True, "safe_tx_hash": "0x" + "b" * 64}
        )

        # Mock activity marking
        agent_run_service.activity_service.mark_activity_completed = Mock()

        # Execute votes
        decision = VoteDecision(
            proposal_id="test-proposal",
            vote=VoteType.FOR,
            confidence=0.85,
            reasoning="This is a valid test reasoning that meets minimum length",
            strategy_used=VotingStrategy.BALANCED,
        )

        await agent_run_service._execute_votes(
            decisions=[decision],
            space_id="test.eth",
            dry_run=False,
            run_id="test_run_123",
        )

        # Verify attestation was called with correct data
        assert agent_run_service.safe_service.create_eas_attestation.called
        call_args = agent_run_service.safe_service.create_eas_attestation.call_args[0][0]
        assert isinstance(call_args, EASAttestationData)
        assert call_args.proposal_id == "test-proposal"
        assert call_args.vote_choice == 1  # FOR = 1
        assert call_args.snapshot_sig == VALID_TX_HASH
        assert call_args.confidence == 85  # 0.85 * 100
        assert call_args.agent == "0xTestAgent"
        assert call_args.space_id == "test.eth"
        assert call_args.run_id == "test_run_123"

        # Verify activity was marked
        agent_run_service.activity_service.mark_activity_completed.assert_called_once_with(
            "0x" + "b" * 64
        )

    @pytest.mark.asyncio
    async def test_immediate_attestation_after_failed_vote(self, agent_run_service):
        """Test that attestation still attempted after vote failure with placeholder sig.

        Importance: Ensures failed votes are also attested for complete audit trail,
        using placeholder signature when no vote_id available. This is critical for
        understanding why certain votes failed and maintaining comprehensive records.
        """
        # Mock vote failure
        agent_run_service.voting_service.vote_on_proposal = AsyncMock(
            return_value={"success": False, "error": "Snapshot API error"}
        )

        # Mock successful attestation
        agent_run_service.safe_service.create_eas_attestation = AsyncMock(
            return_value={"success": True, "safe_tx_hash": VALID_TX_HASH}
        )

        decision = VoteDecision(
            proposal_id="test-proposal",
            vote=VoteType.FOR,
            confidence=0.85,
            reasoning="Valid reasoning for test with minimum required characters",
            strategy_used=VotingStrategy.BALANCED,
        )

        await agent_run_service._execute_votes(
            decisions=[decision],
            space_id="test.eth",
            dry_run=False,
            run_id="test_run_123",
        )

        # Verify attestation was called with placeholder signature
        assert agent_run_service.safe_service.create_eas_attestation.called
        call_args = agent_run_service.safe_service.create_eas_attestation.call_args[0][0]
        assert call_args.snapshot_sig == "0x" + "0" * 64  # Placeholder for failed vote

    @pytest.mark.asyncio
    async def test_attestation_failure_does_not_block_subsequent_votes(self, agent_run_service):
        """Test that attestation failure does not prevent subsequent votes.

        Importance: Critical for resilience - attestation issues should not
        stop the agent from processing remaining proposals. This ensures that
        configuration issues or temporary failures don't completely halt voting.
        """
        # Mock vote success with valid transaction hash
        agent_run_service.voting_service.vote_on_proposal = AsyncMock(
            return_value={
                "success": True,
                "submission_result": {"success": True, "response": {"id": VALID_TX_HASH}},
            }
        )

        # Mock attestation failure
        agent_run_service.safe_service.create_eas_attestation = AsyncMock(
            return_value={"success": False, "error": "EAS contract not configured"}
        )

        # Create two decisions with valid reasoning
        decisions = [
            VoteDecision(
                proposal_id="proposal-1",
                vote=VoteType.FOR,
                confidence=0.85,
                reasoning="This proposal has sufficient detail for evaluation",
                strategy_used=VotingStrategy.BALANCED,
            ),
            VoteDecision(
                proposal_id="proposal-2",
                vote=VoteType.AGAINST,
                confidence=0.75,
                reasoning="This proposal does not meet criteria for approval",
                strategy_used=VotingStrategy.BALANCED,
            ),
        ]

        # Execute votes - should not raise exception
        result = await agent_run_service._execute_votes(
            decisions=decisions,
            space_id="test.eth",
            dry_run=False,
            run_id="test_run_123",
        )

        # Verify both votes were attempted
        assert agent_run_service.voting_service.vote_on_proposal.call_count == 2

        # Verify both attestations were attempted despite first failure
        assert agent_run_service.safe_service.create_eas_attestation.call_count == 2

        # Verify execution completed with both decisions
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_dry_run_skips_attestation(self, agent_run_service):
        """Test that dry run mode skips both voting and attestation.

        Importance: Ensures test mode doesn't create any on-chain transactions,
        allowing operators to safely test the system without creating real votes
        or attestations. This is essential for testing and development workflows.
        """
        decision = VoteDecision(
            proposal_id="test-proposal",
            vote=VoteType.FOR,
            confidence=0.85,
            reasoning="Valid test reasoning with sufficient length for validation",
            strategy_used=VotingStrategy.BALANCED,
        )

        # Execute in dry run mode
        result = await agent_run_service._execute_votes(
            decisions=[decision],
            space_id="test.eth",
            dry_run=True,
            run_id="test_run_123",
        )

        # Verify no vote was attempted
        agent_run_service.voting_service.vote_on_proposal.assert_not_called()

        # Verify no attestation was attempted
        agent_run_service.safe_service.create_eas_attestation.assert_not_called()

        # Verify decisions returned unchanged
        assert result == [decision]

    @pytest.mark.asyncio
    async def test_attestation_exception_handling(self, agent_run_service):
        """Test that exceptions during attestation are caught and logged.

        Importance: Ensures unexpected errors don't crash the agent run.
        Proper exception handling allows the system to continue operating
        even when attestation encounters unexpected issues like network failures.
        """
        # Mock vote success with valid transaction hash
        agent_run_service.voting_service.vote_on_proposal = AsyncMock(
            return_value={
                "success": True,
                "submission_result": {"success": True, "response": {"id": VALID_TX_HASH}},
            }
        )

        # Mock attestation raising exception
        agent_run_service.safe_service.create_eas_attestation = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        decision = VoteDecision(
            proposal_id="test-proposal",
            vote=VoteType.FOR,
            confidence=0.85,
            reasoning="Test reasoning with enough characters to pass validation",
            strategy_used=VotingStrategy.BALANCED,
        )

        # Execute votes - should not raise exception
        result = await agent_run_service._execute_votes(
            decisions=[decision],
            space_id="test.eth",
            dry_run=False,
            run_id="test_run_123",
        )

        # Verify vote was attempted
        assert agent_run_service.voting_service.vote_on_proposal.called

        # Verify execution completed despite exception
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_error_messages_are_actionable_config_missing(
        self, agent_run_service, caplog
    ):
        """Test that configuration error messages include actionable guidance.

        Importance: Verifies error messages help users resolve configuration issues
        without requiring code inspection or external documentation. Clear error
        messages reduce support burden and enable faster problem resolution.
        """
        # Mock vote success with valid transaction hash
        agent_run_service.voting_service.vote_on_proposal = AsyncMock(
            return_value={
                "success": True,
                "submission_result": {"success": True, "response": {"id": VALID_TX_HASH}},
            }
        )

        # Mock attestation failure with config error
        agent_run_service.safe_service.create_eas_attestation = AsyncMock(
            return_value={
                "success": False,
                "error": "EAS_CONTRACT_ADDRESS not configured"
            }
        )

        decision = VoteDecision(
            proposal_id="test-proposal",
            vote=VoteType.FOR,
            confidence=0.85,
            reasoning="This test validates error messages for config issues",
            strategy_used=VotingStrategy.BALANCED,
        )

        with caplog.at_level(logging.ERROR):
            await agent_run_service._execute_votes(
                decisions=[decision],
                space_id="test.eth",
                dry_run=False,
                run_id="test_run_123",
            )

        # Verify error message contains actionable information
        error_logs = [record.message for record in caplog.records if record.levelname == "ERROR"]
        assert len(error_logs) > 0

        error_msg = error_logs[0]
        # Must contain the environment variable name
        assert "EAS_CONTRACT_ADDRESS" in error_msg
        # Must contain instruction on how to set it
        assert "Set EAS_CONTRACT_ADDRESS" in error_msg
        # Must contain proposal context
        assert "proposal=test-proposal" in error_msg

    @pytest.mark.asyncio
    async def test_error_messages_include_debugging_context(
        self, agent_run_service, caplog
    ):
        """Test that error messages include debugging context for investigation.

        Importance: Ensures operators have sufficient information to debug issues
        from log files without needing to reproduce the error. Complete context
        in error messages enables faster root cause analysis.
        """
        # Mock vote success with valid transaction hash
        agent_run_service.voting_service.vote_on_proposal = AsyncMock(
            return_value={
                "success": True,
                "submission_result": {"success": True, "response": {"id": VALID_TX_HASH}},
            }
        )

        # Mock generic attestation failure
        agent_run_service.safe_service.create_eas_attestation = AsyncMock(
            return_value={
                "success": False,
                "error": "Network timeout"
            }
        )

        decision = VoteDecision(
            proposal_id="test-proposal",
            vote=VoteType.FOR,
            confidence=0.85,
            reasoning="This test validates error message debugging context",
            strategy_used=VotingStrategy.BALANCED,
        )

        with caplog.at_level(logging.ERROR):
            await agent_run_service._execute_votes(
                decisions=[decision],
                space_id="test.eth",
                dry_run=False,
                run_id="test_run_123",
            )

        error_logs = [record.message for record in caplog.records if record.levelname == "ERROR"]
        assert len(error_logs) > 0

        error_msg = error_logs[0]
        # Must contain proposal ID for tracing
        assert "proposal=" in error_msg and "test-proposal" in error_msg
        # Timeout errors have different format, but should still include proposal context
        # The error message should provide enough debugging context even if format varies
        assert "timeout" in error_msg.lower() or "RPC" in error_msg

    @pytest.mark.asyncio
    async def test_error_messages_distinguish_failure_types(
        self, agent_run_service, caplog
    ):
        """Test that different failure types produce distinct error messages.

        Importance: Users should be able to quickly identify the type of problem
        from the error message without analyzing generic stack traces. Specific
        error categorization enables targeted troubleshooting.
        """
        # Test different error types
        error_scenarios = [
            ("EAS_SCHEMA_UID not set", ["schema", "EAS_SCHEMA_UID"]),
            ("insufficient funds for gas", ["insufficient", "fund", "ETH"]),
            ("nonce too low", ["nonce", "pending", "Safe Transaction Service"]),
            ("timeout", ["timeout", "RPC_URL"])
        ]

        for error_message, expected_keywords in error_scenarios:
            caplog.clear()

            # Mock vote success with valid transaction hash
            agent_run_service.voting_service.vote_on_proposal = AsyncMock(
                return_value={
                    "success": True,
                    "submission_result": {"success": True, "response": {"id": VALID_TX_HASH}},
                }
            )

            agent_run_service.safe_service.create_eas_attestation = AsyncMock(
                return_value={"success": False, "error": error_message}
            )

            decision = VoteDecision(
                proposal_id="test-proposal",
                vote=VoteType.FOR,
                confidence=0.85,
                reasoning="Test decision for error message validation scenarios",
                strategy_used=VotingStrategy.BALANCED,
            )

            with caplog.at_level(logging.ERROR):
                await agent_run_service._execute_votes(
                    decisions=[decision],
                    space_id="test.eth",
                    dry_run=False,
                    run_id="test_run_123",
                )

            error_logs = [record.message for record in caplog.records if record.levelname == "ERROR"]
            assert len(error_logs) > 0

            error_msg = error_logs[0].lower()
            # Verify error message contains expected keywords for this error type
            keywords_found = [kw for kw in expected_keywords if kw.lower() in error_msg]
            assert len(keywords_found) > 0, \
                f"Error message for '{error_message}' should contain at least one of {expected_keywords}"


class TestCheckpointStateSimplification:
    """Test that checkpoint state no longer includes pending attestations."""

    @pytest.mark.asyncio
    async def test_checkpoint_excludes_pending_attestations(self, tmp_path, monkeypatch):
        """Test that saved checkpoint does not contain pending_attestations field.

        Importance: Verifies queue infrastructure fully removed from state persistence.
        This ensures the simplified architecture is properly reflected in saved state,
        preventing confusion from legacy fields appearing in checkpoints.
        """
        from models import AgentRunResponse
        from services.state_manager import StateManager
        
        # Use tmp_path for test state storage
        test_store_path = tmp_path / "state"
        test_store_path.mkdir(parents=True, exist_ok=True)
        
        # Set environment variable for StateManager to use test directory
        monkeypatch.setenv("STORE_PATH", str(test_store_path))
        
        # Create a state manager (will read from STORE_PATH env var)
        state_manager = StateManager()
        
        # Create an AgentRunService with the state manager
        with patch("services.agent_run_service.SnapshotService"), \
             patch("services.agent_run_service.AIService"), \
             patch("services.agent_run_service.VotingService"), \
             patch("services.agent_run_service.SafeService"), \
             patch("services.agent_run_service.ActivityService"), \
             patch("services.agent_run_service.UserPreferencesService"):
            
            service = AgentRunService(state_manager=state_manager)
            
            response = AgentRunResponse(
                space_id="test.eth",
                proposals_analyzed=2,
                votes_cast=[],
                user_preferences_applied=True,
                execution_time=1.5,
                errors=[],
            )

            # Save checkpoint
            await service._save_checkpoint_state(response)

            # Load checkpoint using load_state (saved as "agent_checkpoint_{space_id}")
            checkpoint = await state_manager.load_state("agent_checkpoint_test.eth")

            assert checkpoint is not None
            assert "pending_attestations" not in checkpoint
            assert "space_id" in checkpoint
            assert "votes_cast" in checkpoint
