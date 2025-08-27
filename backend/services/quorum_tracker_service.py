"""Service for QuorumTracker contract interactions."""

import json
from typing import Dict, Any, Optional
from web3 import Web3

from config import settings
from services.safe_service import SafeService
from logging_config import setup_pearl_logger, log_span


class QuorumTrackerService:
    """Service for QuorumTracker contract interactions.

    This service handles registration of activity types with the QuorumTracker
    smart contract through Safe multisig transactions. It follows the existing
    service patterns and integrates with SafeService for blockchain operations.
    """

    def __init__(self, safe_service: SafeService):
        """Initialize QuorumTracker service with SafeService dependency.

        Args:
            safe_service: SafeService instance for blockchain interactions
        """
        self.logger = setup_pearl_logger(__name__)
        self.safe_service = safe_service

    async def register_activity(
        self, multisig_address: str, activity_type: int
    ) -> Dict[str, Any]:
        """Register activity with QuorumTracker contract.

        Creates a Safe transaction to register an activity type for a given
        multisig address in the QuorumTracker contract.

        Args:
            multisig_address: Address of the multisig to register activity for
            activity_type: Type of activity (0=VOTE_CAST, 1=OPPORTUNITY_CONSIDERED, 2=NO_OPPORTUNITY)

        Returns:
            Dict containing success status and transaction details or error message
        """
        # Runtime assertions for critical inputs
        assert (
            isinstance(multisig_address, str) and multisig_address
        ), "Multisig address must be a non-empty string"
        assert (
            isinstance(activity_type, int) and 0 <= activity_type <= 2
        ), "Activity type must be integer between 0 and 2"

        with log_span(
            self.logger,
            "quorum_tracker_service.register_activity",
            multisig_address=multisig_address,
            activity_type=activity_type,
        ):
            try:
                # Check if QuorumTracker is configured
                if not settings.quorum_tracker_address:
                    return {
                        "success": False,
                        "error": "QuorumTracker contract address not configured",
                    }

                # Build the transaction data for contract interaction
                tx_data = self._build_register_transaction(
                    multisig_address, activity_type
                )

                self.logger.info(
                    f"Registering activity (multisig={multisig_address}, "
                    f"activity_type={activity_type}, "
                    f"contract={settings.quorum_tracker_address})"
                )

                # Submit through Safe service
                result = await self.safe_service._submit_safe_transaction(
                    chain="base",  # Using Base network following EAS pattern
                    to=tx_data["to"],
                    value=tx_data["value"],
                    data=tx_data["data"],
                )

                if result.get("success"):
                    self.logger.info(
                        f"Successfully registered activity type {activity_type} "
                        f"for multisig {multisig_address}. Tx: {result.get('tx_hash')}"
                    )
                    return {
                        "success": True,
                        "tx_hash": result.get("tx_hash"),
                        "chain": result.get("chain"),
                        "activity_type": activity_type,
                        "multisig_address": multisig_address,
                    }
                else:
                    self.logger.error(
                        f"Failed to register activity: {result.get('error')}"
                    )
                    return {
                        "success": False,
                        "error": result.get("error", "Unknown error"),
                    }

            except Exception as e:
                self.logger.error(f"Error registering activity: {str(e)}")
                return {"success": False, "error": str(e)}

    def _build_register_transaction(
        self, multisig_address: str, activity_type: int
    ) -> Dict[str, Any]:
        """Build transaction data for QuorumTracker.register() call.

        Args:
            multisig_address: Address to register activity for
            activity_type: Activity type to register

        Returns:
            Dict containing transaction data with 'to', 'value', and 'data' fields
        """
        # Runtime assertions
        assert (
            settings.quorum_tracker_address
        ), "QuorumTracker address must be configured"

        # Load QuorumTracker ABI
        quorum_tracker_abi = self._load_quorum_tracker_abi()

        # Create Web3 instance for encoding
        w3 = Web3()

        # Create contract instance for encoding
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(settings.quorum_tracker_address),
            abi=quorum_tracker_abi,
        )

        # Build the register transaction
        tx_data = contract.functions.register(
            Web3.to_checksum_address(multisig_address), activity_type
        ).build_transaction(
            {
                "gas": 100000,  # Reasonable gas limit for simple register call
                "gasPrice": 0,  # Will be set by Safe
            }
        )

        return {
            "to": settings.quorum_tracker_address,
            "value": 0,  # No ETH transfer needed
            "data": tx_data["data"],
        }

    def _load_quorum_tracker_abi(self) -> list:
        """Load QuorumTracker contract ABI from file.

        Returns:
            List containing the QuorumTracker ABI
        """
        import os

        abi_path = os.path.join(os.path.dirname(__file__), "../abi/quorum_tracker.json")

        with open(abi_path, "r") as f:
            return json.load(f)

    def get_voting_stats(self, multisig_address: str) -> Optional[Dict[str, Any]]:
        """Get voting statistics for a multisig address from QuorumTracker contract.

        This method would query the contract's getVotingStats function.
        Implementation is simplified for now but shows the intended interface.

        Args:
            multisig_address: Address to get statistics for

        Returns:
            Dict containing voting statistics or None if not available
        """
        if not settings.quorum_tracker_address:
            self.logger.warning("QuorumTracker contract address not configured")
            return None

        try:
            # This would be implemented to call the contract's getVotingStats function
            # For now, return a placeholder structure
            return {
                "multisig_address": multisig_address,
                "votes_cast": 0,
                "opportunities_considered": 0,
                "no_opportunities": 0,
            }
        except Exception as e:
            self.logger.error(f"Error getting voting stats: {str(e)}")
            return None
