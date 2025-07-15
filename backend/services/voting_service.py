"""Voting service for handling Snapshot DAO voting operations."""

import time
from typing import Dict, Optional, Any
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_typed_data
import httpx
import logfire


# Constants for vote choices and API configuration
VOTE_CHOICE_FOR = 1
VOTE_CHOICE_AGAINST = 2
VOTE_CHOICE_ABSTAIN = 3
VALID_VOTE_CHOICES = [VOTE_CHOICE_FOR, VOTE_CHOICE_AGAINST, VOTE_CHOICE_ABSTAIN]

SNAPSHOT_HUB_URL = "https://seq.snapshot.org/"
VOTE_CHOICE_DESCRIPTIONS = {
    VOTE_CHOICE_FOR: "For",
    VOTE_CHOICE_AGAINST: "Against", 
    VOTE_CHOICE_ABSTAIN: "Abstain"
}

# Snapshot vote message configuration
SNAPSHOT_DOMAIN_NAME = "snapshot"
SNAPSHOT_DOMAIN_VERSION = "0.1.4"


class VotingService:
    """Service for handling Snapshot DAO voting operations."""

    def __init__(self):
        """Initialize voting service with account from private key."""
        # Load private key from file (OLAS-provided)
        with open("ethereum_private_key.txt", "r") as f:
            private_key = f.read().strip()

        self.account = Account.from_key(private_key)

        logfire.info("VotingService initialized", eoa_address=self.account.address)

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
        if timestamp is None:
            timestamp = int(time.time())

        from_address = Web3.to_checksum_address(self.account.address)
        proposal_is_bytes32 = proposal.startswith("0x") and len(proposal) == 66

        snapshot_message = self._build_snapshot_message_structure(
            from_address, space, timestamp, proposal, choice, proposal_is_bytes32
        )

        logfire.info(
            "Snapshot vote message created",
            space=space,
            proposal=proposal,
            choice=choice,
            timestamp=timestamp,
            from_address=from_address,
        )

        return snapshot_message

    def _build_snapshot_message_structure(
        self, 
        from_address: str, 
        space: str, 
        timestamp: int, 
        proposal: str, 
        choice: int, 
        proposal_is_bytes32: bool
    ) -> Dict[str, Any]:
        """Build the complete Snapshot message structure."""
        return {
            "domain": {"name": SNAPSHOT_DOMAIN_NAME, "version": SNAPSHOT_DOMAIN_VERSION},
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
                        "type": "bytes32" if proposal_is_bytes32 else "string",
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
                "reason": "",
                "app": "",
                "metadata": "{}",
            },
        }

    def sign_snapshot_message(self, snapshot_message: Dict[str, Any]) -> str:
        """Sign a Snapshot vote message with the EOA private key.

        Args:
            snapshot_message: The vote message dictionary from create_snapshot_vote_message

        Returns:
            Hex string of the signature
        """
        signable_message = encode_typed_data(full_message=snapshot_message)
        signed = self.account.sign_message(signable_message)
        signature = "0x" + signed.signature.hex()

        logfire.info(
            "Snapshot message signed",
            signature_length=len(signature),
            signature_preview=f"{signature[:10]}...{signature[-10:]}",
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
        with logfire.span("voting_service.submit_vote_to_snapshot"):
            logfire.info("Submitting Snapshot vote")

            # Snapshot Hub API endpoint
            url = SNAPSHOT_HUB_URL

            # Prepare Snapshot vote request
            from_address = Web3.to_checksum_address(self.account.address)
            clean_signature = (
                signature if signature.startswith("0x") else f"0x{signature}"
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

                if response.status_code == 200:
                    result_data = response.json()
                    logfire.info(
                        "Snapshot vote submitted successfully",
                        response_data=result_data,
                    )
                    return {"success": True, "response": result_data}
                else:
                    error_text = response.text
                    logfire.error(
                        "Snapshot vote submission failed",
                        status_code=response.status_code,
                        response_text=error_text,
                    )
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                        "response_text": error_text,
                    }

            except Exception as e:
                logfire.error(f"Snapshot vote submission error: {e}")
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
        with logfire.span(
            "voting_service.vote_on_proposal",
            space=space,
            proposal=proposal,
            choice=choice,
        ):
            logfire.info(f"Starting vote on proposal {proposal} in space {space}")

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

            if submission_result["success"]:
                logfire.info("Vote workflow completed successfully")
            else:
                logfire.error(
                    "Vote workflow failed", error=submission_result.get("error")
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
        with logfire.span("voting_service.test_snapshot_voting"):
            logfire.info(
                "Testing Snapshot voting workflow",
                space=space,
                proposal=proposal,
                choice=choice,
                choice_description=self.get_vote_choice_description(choice),
            )

            if not self.validate_vote_choice(choice):
                return {
                    "success": False,
                    "error": f"Invalid vote choice: {choice}. Must be 1, 2, or 3.",
                }

            # Execute complete voting workflow
            result = await self.vote_on_proposal(space, proposal, choice)

            logfire.info(
                "Test voting workflow completed",
                success=result["success"],
                error=result.get("submission_result", {}).get("error"),
            )

            return result
