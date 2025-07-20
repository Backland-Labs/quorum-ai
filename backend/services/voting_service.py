"""Voting service for handling Snapshot DAO voting operations."""

import time
import logging
from typing import Dict, Optional, Any, List
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_typed_data
import httpx
from logging_config import setup_pearl_logger, log_span


# Constants for vote choices and API configuration
VOTE_CHOICE_FOR = 1
VOTE_CHOICE_AGAINST = 2
VOTE_CHOICE_ABSTAIN = 3
VALID_VOTE_CHOICES = [VOTE_CHOICE_FOR, VOTE_CHOICE_AGAINST, VOTE_CHOICE_ABSTAIN]

SNAPSHOT_HUB_URL = "https://seq.snapshot.org/"
VOTE_CHOICE_DESCRIPTIONS = {
    VOTE_CHOICE_FOR: "For",
    VOTE_CHOICE_AGAINST: "Against",
    VOTE_CHOICE_ABSTAIN: "Abstain",
}

# Snapshot vote message configuration
SNAPSHOT_DOMAIN_NAME = "snapshot"
SNAPSHOT_DOMAIN_VERSION = "0.1.4"


class VotingService:
    """Service for handling Snapshot DAO voting operations."""

    def __init__(self, key_manager=None):
        """Initialize voting service with account from private key.
        
        Args:
            key_manager: Optional KeyManager instance. If not provided, creates a new one.
        """
        # Initialize KeyManager
        from services.key_manager import KeyManager
        self.key_manager = key_manager or KeyManager()
        
        # Initialize account lazily
        self._account = None

        # Initialize Pearl-compliant logger
        self.logger = setup_pearl_logger(name="voting_service", level=logging.INFO)
        
        self.logger.info("VotingService initialized")
    
    @property
    def account(self):
        """Get the account, loading it lazily from KeyManager."""
        if self._account is None:
            private_key = self.key_manager.get_private_key()
            self._account = Account.from_key(private_key)
            self.logger.info(f"Account loaded from KeyManager (eoa_address={self._account.address})")
        return self._account

    def create_snapshot_vote_message(
        self, space: str, proposal: str, choice: int, timestamp: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a Snapshot vote message payload.

        Args:
            space: The Snapshot space ID (e.g., "aave.eth")
            proposal: The proposal ID (IPFS hash or bytes32)
            choice: Vote choice (1 = For, 2 = Against, 3 = Abstain)
            timestamp: Unix timestamp in seconds (defaults to current time)

        Returns:
            Dictionary containing the vote message structure
        """
        # Runtime assertions
        assert space, "Space ID must not be empty"
        assert proposal, "Proposal ID must not be empty"
        assert choice in VALID_VOTE_CHOICES, f"Invalid choice: {choice}"
        
        # Constants
        BYTES32_LENGTH = 66  # 0x prefix + 64 hex chars
        
        if timestamp is None:
            timestamp = int(time.time())

        from_address = Web3.to_checksum_address(self.account.address)
        proposal_is_bytes32 = proposal.startswith("0x") and len(proposal) == BYTES32_LENGTH

        snapshot_message = self._build_snapshot_message_structure(
            from_address, space, timestamp, proposal, choice, proposal_is_bytes32
        )

        self.logger.info(
            f"Snapshot vote message created (space={space}, proposal={proposal}, "
            f"choice={choice}, timestamp={timestamp}, from_address={from_address})"
        )

        return snapshot_message

    def _build_snapshot_message_structure(
        self,
        from_address: str,
        space: str,
        timestamp: int,
        proposal: str,
        choice: int,
        proposal_is_bytes32: bool,
    ) -> Dict[str, Any]:
        """Build the complete Snapshot message structure."""
        # Constants for empty values
        EMPTY_REASON = ""
        EMPTY_APP = ""
        EMPTY_METADATA = "{}"
        
        # Build type definition for proposal field
        proposal_type = "bytes32" if proposal_is_bytes32 else "string"
        
        return {
            "domain": {
                "name": SNAPSHOT_DOMAIN_NAME,
                "version": SNAPSHOT_DOMAIN_VERSION,
            },
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                ],
                "Vote": [
                    {"name": "from", "type": "string"},
                    {"name": "space", "type": "string"},
                    {"name": "timestamp", "type": "uint64"},
                    {
                        "name": "proposal",
                        "type": proposal_type,
                    },
                    {"name": "choice", "type": "uint32"},
                    {"name": "reason", "type": "string"},
                    {"name": "app", "type": "string"},
                    {"name": "metadata", "type": "string"},
                ],
            },
            "primaryType": "Vote",
            "message": {
                "from": from_address,
                "space": space,
                "timestamp": timestamp,
                "proposal": proposal,
                "choice": choice,
                "reason": EMPTY_REASON,
                "app": EMPTY_APP,
                "metadata": EMPTY_METADATA,
            },
        }

    def sign_snapshot_message(self, snapshot_message: Dict[str, Any]) -> str:
        """Sign a Snapshot vote message with the EOA private key.

        Args:
            snapshot_message: The vote message dictionary from create_snapshot_vote_message

        Returns:
            Hex string of the signature
        """
        # Runtime assertions
        assert snapshot_message, "Snapshot message must not be empty"
        assert "message" in snapshot_message, "Snapshot message must contain 'message' field"
        
        # Constants
        HEX_PREFIX = "0x"
        PREVIEW_LENGTH = 10
        
        signable_message = encode_typed_data(full_message=snapshot_message)
        signed = self.account.sign_message(signable_message)
        signature = HEX_PREFIX + signed.signature.hex()
        
        # Create signature preview for logging
        signature_preview = f"{signature[:PREVIEW_LENGTH]}...{signature[-PREVIEW_LENGTH:]}"

        self.logger.info(
            f"Snapshot message signed (signature_length={len(signature)}, "
            f"signature_preview={signature_preview})"
        )

        return signature

    async def submit_vote_to_snapshot(
        self, snapshot_message: Dict[str, Any], signature: str
    ) -> Dict[str, Any]:
        """Send a signed vote to Snapshot Hub API.

        Args:
            snapshot_message: The vote message dictionary
            signature: The hex signature string

        Returns:
            API response dictionary with success status
        """
        # Runtime assertions
        assert snapshot_message, "Snapshot message must not be empty"
        assert signature, "Signature must not be empty"
        
        # Constants
        HEX_PREFIX = "0x"
        
        with log_span(self.logger, "voting_service.submit_vote_to_snapshot"):
            self.logger.info("Submitting Snapshot vote")

            # Snapshot Hub API endpoint
            url = SNAPSHOT_HUB_URL

            # Prepare Snapshot vote request
            from_address = Web3.to_checksum_address(self.account.address)
            clean_signature = (
                signature if signature.startswith(HEX_PREFIX) else f"{HEX_PREFIX}{signature}"
            )

            request_body = {
                "address": from_address,
                "sig": clean_signature,
                "data": {
                    "domain": snapshot_message["domain"],
                    "types": snapshot_message["types"],
                    "message": snapshot_message["message"],
                },
            }

            # Submit Snapshot vote
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url,
                        json=request_body,
                        headers={"Content-Type": "application/json"},
                    )

                # Constants for HTTP status
                HTTP_OK = 200
                
                if response.status_code == HTTP_OK:
                    result_data = response.json()
                    self.logger.info(
                        f"Snapshot vote submitted successfully (response_data={result_data})"
                    )
                    return {"success": True, "response": result_data}
                
                # Handle error response
                error_text = response.text
                self.logger.error(
                    f"Snapshot vote submission failed (status_code={response.status_code}, "
                    f"response_text={error_text})"
                )
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "response_text": error_text,
                }

            except Exception as e:
                self.logger.error(f"Snapshot vote submission error: {e}")
                return {"success": False, "error": str(e)}

    async def vote_on_proposal(
        self, space: str, proposal: str, choice: int, timestamp: Optional[int] = None
    ) -> Dict[str, Any]:
        """Complete workflow to vote on a Snapshot proposal.

        Args:
            space: The Snapshot space ID
            proposal: The proposal ID
            choice: Vote choice (1 = For, 2 = Against, 3 = Abstain)
            timestamp: Optional custom timestamp

        Returns:
            Dict containing complete voting workflow results
        """
        # Runtime assertions
        assert space, "Space ID must not be empty"
        assert proposal, "Proposal ID must not be empty"
        assert self.validate_vote_choice(choice), f"Invalid vote choice: {choice}"
        
        with log_span(
            self.logger,
            "voting_service.vote_on_proposal",
            space=space,
            proposal=proposal,
            choice=choice,
        ):
            self.logger.info(f"Starting vote on proposal {proposal} in space {space}")

            # Create vote message
            vote_message = self.create_snapshot_vote_message(
                space, proposal, choice, timestamp
            )

            # Sign message
            signature = self.sign_snapshot_message(vote_message)

            # Submit to Snapshot
            submission_result = await self.submit_vote_to_snapshot(
                vote_message, signature
            )

            # Compile complete result
            result = {
                "success": submission_result["success"],
                "vote_message": vote_message,
                "signature": signature,
                "submission_result": submission_result,
            }

            # Log result status
            if submission_result["success"]:
                self.logger.info("Vote workflow completed successfully")
            else:
                error_message = submission_result.get('error', 'Unknown error')
                self.logger.error(
                    f"Vote workflow failed (error={error_message})"
                )

            return result

    def validate_vote_choice(self, choice: int) -> bool:
        """Validate that vote choice is within acceptable range.

        Args:
            choice: Vote choice integer

        Returns:
            True if choice is valid (1, 2, or 3)
        """
        return choice in VALID_VOTE_CHOICES

    def get_vote_choice_description(self, choice: int) -> str:
        """Get human-readable description of vote choice.

        Args:
            choice: Vote choice integer

        Returns:
            String description of the choice
        """
        return VOTE_CHOICE_DESCRIPTIONS.get(choice, "Unknown")

    async def test_snapshot_voting(
        self,
        space: str = "spectradao.eth",
        proposal: str = "0xfbfc4f16d1f44d4298f4a7c958e3ad158ec0c8fc582d1151f766c26dbe50b237",
        choice: int = 1,
    ) -> Dict[str, Any]:
        """Test function for Snapshot voting workflow.

        Args:
            space: Test space (defaults to spectradao.eth)
            proposal: Test proposal ID
            choice: Test vote choice

        Returns:
            Dict containing test results
        """
        # Constants for test defaults
        DEFAULT_TEST_SPACE = "spectradao.eth"
        DEFAULT_TEST_PROPOSAL = "0xfbfc4f16d1f44d4298f4a7c958e3ad158ec0c8fc582d1151f766c26dbe50b237"
        DEFAULT_TEST_CHOICE = 1
        
        # Use provided values or defaults
        test_space = space or DEFAULT_TEST_SPACE
        test_proposal = proposal or DEFAULT_TEST_PROPOSAL
        test_choice = choice or DEFAULT_TEST_CHOICE
        
        with log_span(self.logger, "voting_service.test_snapshot_voting"):
            choice_description = self.get_vote_choice_description(test_choice)
            self.logger.info(
                f"Testing Snapshot voting workflow (space={test_space}, proposal={test_proposal}, "
                f"choice={test_choice}, choice_description={choice_description})"
            )

            if not self.validate_vote_choice(test_choice):
                error_message = f"Invalid vote choice: {test_choice}. Must be 1, 2, or 3."
                return {
                    "success": False,
                    "error": error_message,
                }

            # Execute complete voting workflow
            result = await self.vote_on_proposal(test_space, test_proposal, test_choice)

            # Extract error for logging
            submission_error = result.get('submission_result', {}).get('error')
            self.logger.info(
                f"Test voting workflow completed (success={result['success']}, "
                f"error={submission_error})"
            )

            return result
    
    async def shutdown(self) -> None:
        """Implement shutdown method required by ShutdownService protocol."""
        self.logger.info("Voting service shutdown initiated")
        
        # Check for any active votes
        if self._active_votes:
            self.logger.warning(f"Shutdown with {len(self._active_votes)} active votes")
            # Clear active votes as they would have completed or failed by now
            self._active_votes.clear()
        
        self.logger.info("Voting service shutdown completed")
    
    async def save_service_state(self) -> None:
        """Save current service state for recovery."""
        # Voting service doesn't maintain persistent state
        # Votes are atomic operations that complete or fail
        pass
    
    async def stop(self) -> None:
        """Stop the service gracefully."""
        # Clear any tracking of active votes
        self._active_votes.clear()
    
    async def get_active_votes(self) -> List[Dict[str, Any]]:
        """Get list of active votes for shutdown coordination."""
        return self._active_votes.copy()
    
