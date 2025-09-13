"""
Tests for EAS (Ethereum Attestation Service) attestation functionality.

This test module validates the vote attestation feature which creates on-chain
attestations for Snapshot votes using EAS on Base network. The tests ensure
proper model validation, service integration, and state management for attestations.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from models import EASAttestationData, VoteDecision, VoteType, RiskLevel, VotingStrategy


class TestEASAttestationData:
    """Test the EASAttestationData model for proper validation and functionality."""

    def test_eas_attestation_data_creation(self):
        """
        Test that EASAttestationData can be created with valid data.

        This test is important because it validates that the attestation data model
        properly accepts all required fields for creating an on-chain attestation.
        """
        attestation_data = EASAttestationData(
            proposal_id="0x123abc",
            space_id="aave.eth",
            agent="0x742d35Cc6634C0532925a3b844Bc9e7595f89590",
            vote_choice=1,
            snapshot_sig="0x742d35Cc6634C0532925a3b844Bc9e7595f89590742d35Cc6634C0532925a3b8",
            timestamp=int(datetime.utcnow().timestamp()),
            run_id="test_run_123",
            confidence=80,
            retry_count=0,
        )

        assert attestation_data.proposal_id == "0x123abc"
        assert attestation_data.space_id == "aave.eth"
        assert attestation_data.agent == "0x742d35Cc6634C0532925a3b844Bc9e7595f89590"
        assert attestation_data.vote_choice == 1
        assert (
            attestation_data.snapshot_sig
            == "0x742d35Cc6634C0532925a3b844Bc9e7595f89590742d35Cc6634C0532925a3b8"
        )
        assert attestation_data.retry_count == 0
        assert isinstance(attestation_data.timestamp, int)
        assert attestation_data.run_id == "test_run_123"
        assert attestation_data.confidence == 80

    def test_eas_attestation_data_with_transaction_details(self):
        """
        Test that EASAttestationData can track attestation transaction details.

        This test validates that the model can store the on-chain transaction
        details after an attestation is submitted to the blockchain.
        """
        attestation_data = EASAttestationData(
            proposal_id="0x123abc",
            space_id="aave.eth",
            agent="0x742d35Cc6634C0532925a3b844Bc9e7595f89590",
            vote_choice=1,
            snapshot_sig="0x742d35Cc6634C0532925a3b844Bc9e7595f89590742d35Cc6634C0532925a3b8",
            timestamp=int(datetime.utcnow().timestamp()),
            run_id="test_run_123",
            confidence=80,
            retry_count=0,
            attestation_tx_hash="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            attestation_uid="0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            attestation_status="success",
        )

        assert (
            attestation_data.attestation_tx_hash
            == "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        assert (
            attestation_data.attestation_uid
            == "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        )
        assert attestation_data.attestation_status == "success"

    def test_eas_attestation_data_validation_errors(self):
        """
        Test that EASAttestationData validates required fields properly.

        This test ensures that the model enforces data integrity by rejecting
        invalid or missing required fields.
        """
        # Missing required fields
        with pytest.raises(ValidationError):
            EASAttestationData()

        # Invalid agent address format
        with pytest.raises(ValidationError):
            EASAttestationData(
                proposal_id="0x123abc",
                space_id="aave.eth",
                agent="short",  # Invalid address format
                vote_choice=1,
                snapshot_sig="0x742d35Cc6634C0532925a3b844Bc9e7595f89590742d35Cc6634C0532925a3b8",
                timestamp=int(datetime.utcnow().timestamp()),
                run_id="test_run_123",
                confidence=80,
                retry_count=0,
            )

    def test_eas_attestation_data_serialization(self):
        """
        Test that EASAttestationData can be serialized and deserialized properly.

        This test is critical for state persistence as attestation data needs to
        be saved to and loaded from the agent checkpoint JSON file.
        """
        attestation_data = EASAttestationData(
            proposal_id="0x123abc",
            space_id="aave.eth",
            agent="0x742d35Cc6634C0532925a3b844Bc9e7595f89590",
            vote_choice=1,
            snapshot_sig="0x742d35Cc6634C0532925a3b844Bc9e7595f89590742d35Cc6634C0532925a3b8",
            timestamp=int(datetime.utcnow().timestamp()),
            run_id="test_run_123",
            confidence=80,
            retry_count=0,
        )

        # Serialize to dict
        data_dict = attestation_data.model_dump()
        assert isinstance(data_dict, dict)
        assert data_dict["proposal_id"] == "0x123abc"
        assert data_dict["agent"] == "0x742d35Cc6634C0532925a3b844Bc9e7595f89590"
        assert data_dict["vote_choice"] == 1
        assert data_dict["run_id"] == "test_run_123"
        assert data_dict["confidence"] == 80

        # Deserialize from dict
        restored_data = EASAttestationData(**data_dict)
        assert restored_data.proposal_id == attestation_data.proposal_id
        assert restored_data.timestamp == attestation_data.timestamp
        assert restored_data.agent == attestation_data.agent
        assert restored_data.vote_choice == attestation_data.vote_choice
        assert restored_data.run_id == attestation_data.run_id
        assert restored_data.confidence == attestation_data.confidence


class TestVoteDecisionAttestationFields:
    """Test the VoteDecision model extensions for attestation tracking."""

    def test_vote_decision_with_attestation_fields(self):
        """
        Test that VoteDecision model includes attestation tracking fields.

        This test validates that vote decisions can track the attestation
        lifecycle from creation through success or failure.
        """
        vote_decision = VoteDecision(
            proposal_id="0x123abc",
            vote=VoteType.FOR,
            confidence=0.9,
            reasoning="Supporting improved governance",
            risk_assessment=RiskLevel.LOW,
            strategy_used=VotingStrategy.BALANCED,
            attestation_status="pending",
        )

        assert vote_decision.attestation_status == "pending"
        assert vote_decision.attestation_tx_hash is None
        assert vote_decision.attestation_uid is None
        assert vote_decision.attestation_error is None
        assert vote_decision.space_id is None  # Optional field

    def test_vote_decision_attestation_success(self):
        """
        Test updating VoteDecision with successful attestation details.

        This test ensures that vote decisions can be updated with attestation
        results after successful on-chain submission.
        """
        vote_decision = VoteDecision(
            proposal_id="0x123abc",
            vote=VoteType.FOR,
            confidence=0.9,
            reasoning="Supporting improved governance",
            risk_assessment=RiskLevel.LOW,
            strategy_used=VotingStrategy.BALANCED,
            space_id="aave.eth",
            attestation_status="success",
            attestation_tx_hash="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            attestation_uid="0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        )

        assert vote_decision.attestation_status == "success"
        assert (
            vote_decision.attestation_tx_hash
            == "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        )
        assert (
            vote_decision.attestation_uid
            == "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        )
        assert vote_decision.space_id == "aave.eth"

    def test_vote_decision_attestation_failure(self):
        """
        Test tracking attestation failures in VoteDecision.

        This test validates that the model can capture error information
        when attestations fail, enabling proper error handling and retries.
        """
        vote_decision = VoteDecision(
            proposal_id="0x123abc",
            vote=VoteType.FOR,
            confidence=0.9,
            reasoning="Supporting improved governance",
            risk_assessment=RiskLevel.LOW,
            strategy_used=VotingStrategy.BALANCED,
            attestation_status="failed",
            attestation_error="Insufficient gas for transaction",
        )

        assert vote_decision.attestation_status == "failed"
        assert vote_decision.attestation_error == "Insufficient gas for transaction"
        assert vote_decision.attestation_tx_hash is None
        assert vote_decision.attestation_uid is None
