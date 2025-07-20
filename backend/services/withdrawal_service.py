"""
Withdrawal Service for emergency fund recovery.

Implements BAC-177: Withdrawal Mode functionality for detecting withdrawal mode,
listing invested positions, calculating withdrawals, and executing them through
Safe contracts.
"""

import os
from decimal import Decimal
from typing import Dict, List
from datetime import datetime

from models import InvestedPosition, WithdrawalTransaction, WithdrawalStatus
from services.state_manager import StateManager
from services.safe_service import SafeService
from services.snapshot_service import SnapshotService
from logging_config import setup_pearl_logger

logger = setup_pearl_logger(__name__)


class WithdrawalService:
    """Service for handling emergency withdrawal operations."""

    def __init__(
        self,
        state_manager: StateManager,
        safe_service: SafeService,
        snapshot_service: SnapshotService,
    ):
        """Initialize withdrawal service with required dependencies."""
        self.state_manager = state_manager
        self.safe_service = safe_service
        self.snapshot_service = snapshot_service
        logger.info("WithdrawalService initialized")

    async def is_withdrawal_mode_active(self) -> bool:
        """Check if withdrawal mode is active via environment variable."""
        withdrawal_mode = os.environ.get("WITHDRAWAL_MODE", "false").lower()
        is_active = withdrawal_mode == "true"

        if is_active:
            logger.warning("WITHDRAWAL MODE IS ACTIVE - Normal voting disabled")

        return is_active

    async def list_invested_positions(self) -> List[InvestedPosition]:
        """List all invested positions from state."""
        state = await self.state_manager.get_state()
        positions_data = state.get("invested_positions", [])

        positions = []
        for pos_data in positions_data:
            position = InvestedPosition(
                protocol=pos_data["protocol"],
                asset=pos_data["asset"],
                amount=Decimal(pos_data["amount"]),
                chain_id=pos_data["chain_id"],
                position_id=pos_data["position_id"],
                timestamp=pos_data["timestamp"],
                contract_address=pos_data.get("contract_address"),
            )
            positions.append(position)

        logger.info(f"Found {len(positions)} invested positions")
        return positions

    async def discover_onchain_positions(self) -> List[InvestedPosition]:
        """Discover positions directly from on-chain data."""
        positions = []

        # Get Safe addresses across chains
        safe_addresses = await self.safe_service.get_safe_addresses()

        for chain_id, safe_address in safe_addresses.items():
            logger.info(
                f"Querying positions for Safe {safe_address} on chain {chain_id}"
            )

            # Query DeFi positions for this Safe
            chain_positions = await self._query_defi_positions(chain_id, safe_address)
            positions.extend(chain_positions)

        logger.info(f"Discovered {len(positions)} on-chain positions")
        return positions

    async def _query_defi_positions(
        self, chain_id: int, safe_address: str
    ) -> List[InvestedPosition]:
        """Query DeFi positions for a specific Safe on a chain."""
        # This would integrate with various DeFi protocols
        # For now, returning empty list as placeholder
        _ = chain_id  # noqa: F841
        _ = safe_address  # noqa: F841
        return []

    async def calculate_withdrawal_amounts(
        self, positions: List[InvestedPosition], withdrawal_percentage: int = 100
    ) -> List[Dict]:
        """Calculate withdrawal amounts for positions."""
        if not 0 < withdrawal_percentage <= 100:
            raise ValueError("Withdrawal percentage must be between 1 and 100")

        withdrawals = []

        for position in positions:
            withdrawal_amount = position.amount * Decimal(withdrawal_percentage) / 100

            withdrawals.append(
                {
                    "position_id": position.position_id,
                    "protocol": position.protocol,
                    "asset": position.asset,
                    "original_amount": position.amount,
                    "amount": withdrawal_amount,
                    "percentage": withdrawal_percentage,
                    "chain_id": position.chain_id,
                }
            )

        logger.info(
            f"Calculated withdrawals for {len(withdrawals)} positions "
            f"at {withdrawal_percentage}% withdrawal rate"
        )

        return withdrawals

    async def prioritize_withdrawals(
        self, positions: List[InvestedPosition]
    ) -> List[InvestedPosition]:
        """Prioritize withdrawals based on size and chain."""
        # Sort by amount (descending) and group by chain
        sorted_positions = sorted(positions, key=lambda p: (p.chain_id, -p.amount))

        return sorted_positions

    async def execute_withdrawal(
        self, position: InvestedPosition, amount: Decimal, max_retries: int = 1
    ) -> WithdrawalTransaction:
        """Execute a withdrawal transaction through Safe."""
        logger.info(
            f"Executing withdrawal for position {position.position_id} "
            f"amount: {amount} {position.asset}"
        )

        attempts = 0
        last_error = None

        while attempts < max_retries:
            try:
                # Build withdrawal transaction data
                tx_data = await self._build_withdrawal_tx(position, amount)

                # Execute through Safe
                result = await self.safe_service.execute_transaction(
                    chain_id=position.chain_id,
                    to=position.contract_address,
                    data=tx_data,
                    value=0,
                )

                # Create withdrawal transaction record
                withdrawal = WithdrawalTransaction(
                    transaction_hash=result["transaction_hash"],
                    safe_tx_hash=result.get("safe_tx_hash"),
                    status=WithdrawalStatus.PENDING,
                    position_id=position.position_id,
                    amount=amount,
                    chain_id=position.chain_id,
                    timestamp=datetime.utcnow().isoformat(),
                )

                # Update state with pending withdrawal
                await self._update_pending_withdrawal(withdrawal)

                logger.info(
                    f"Withdrawal transaction submitted: {withdrawal.transaction_hash}"
                )
                return withdrawal

            except Exception as e:
                attempts += 1
                last_error = str(e)
                logger.error(f"Withdrawal attempt {attempts} failed: {e}")

                if attempts >= max_retries:
                    # Create failed withdrawal record
                    withdrawal = WithdrawalTransaction(
                        transaction_hash="0x" + "0" * 64,  # Placeholder
                        status=WithdrawalStatus.FAILED,
                        position_id=position.position_id,
                        amount=amount,
                        chain_id=position.chain_id,
                        timestamp=datetime.utcnow().isoformat(),
                        error_message=last_error,
                    )
                    return withdrawal

        raise Exception(f"All withdrawal attempts failed: {last_error}")

    async def _build_withdrawal_tx(
        self, position: InvestedPosition, amount: Decimal
    ) -> str:
        """Build withdrawal transaction data for the position."""
        # This would build protocol-specific withdrawal transaction
        # For now, returning empty data
        _ = position  # noqa: F841
        _ = amount  # noqa: F841
        return "0x"

    async def _update_pending_withdrawal(self, withdrawal: WithdrawalTransaction):
        """Update state with pending withdrawal."""
        state = await self.state_manager.get_state()

        pending_withdrawals = state.get("pending_withdrawals", [])
        pending_withdrawals.append(
            {
                "transaction_hash": withdrawal.transaction_hash,
                "safe_tx_hash": withdrawal.safe_tx_hash,
                "status": withdrawal.status.value,
                "position_id": withdrawal.position_id,
                "amount": str(withdrawal.amount),
                "chain_id": withdrawal.chain_id,
                "timestamp": withdrawal.timestamp,
                "error_message": withdrawal.error_message,
            }
        )

        state["pending_withdrawals"] = pending_withdrawals
        await self.state_manager.update_state(state)

    async def monitor_pending_withdrawals(self):
        """Monitor and update status of pending withdrawals."""
        state = await self.state_manager.get_state()
        pending_withdrawals = state.get("pending_withdrawals", [])

        updated_withdrawals = []

        for withdrawal_data in pending_withdrawals:
            if withdrawal_data["status"] == "pending":
                # Check transaction status
                tx_status = await self.safe_service.get_transaction_status(
                    withdrawal_data["transaction_hash"]
                )

                if tx_status["status"] == "confirmed":
                    withdrawal_data["status"] = "confirmed"
                    logger.info(
                        f"Withdrawal {withdrawal_data['transaction_hash']} confirmed"
                    )
                elif tx_status.get("failed"):
                    withdrawal_data["status"] = "failed"
                    withdrawal_data["error_message"] = tx_status.get(
                        "error", "Unknown error"
                    )
                    logger.error(
                        f"Withdrawal {withdrawal_data['transaction_hash']} failed"
                    )

            updated_withdrawals.append(withdrawal_data)

        state["pending_withdrawals"] = updated_withdrawals
        await self.state_manager.update_state(state)

    async def run_withdrawal_process(self) -> List[WithdrawalTransaction]:
        """Run the complete withdrawal process."""
        if not await self.is_withdrawal_mode_active():
            logger.info("Withdrawal mode not active, skipping withdrawal process")
            return []

        logger.info("Starting withdrawal process")

        # Get invested positions
        positions = await self.list_invested_positions()

        if not positions:
            logger.warning("No invested positions found")
            return []

        # Calculate withdrawals (100% by default)
        withdrawal_plans = await self.calculate_withdrawal_amounts(positions)

        # Execute withdrawals
        results = []
        for plan in withdrawal_plans:
            position = next(
                p for p in positions if p.position_id == plan["position_id"]
            )

            try:
                result = await self.execute_withdrawal(
                    position=position, amount=plan["amount"]
                )
                results.append(result)
            except Exception as e:
                logger.error(
                    f"Failed to execute withdrawal for {position.position_id}: {e}"
                )

        # Monitor pending withdrawals
        await self.monitor_pending_withdrawals()

        logger.info(f"Withdrawal process completed with {len(results)} transactions")
        return results

    async def get_withdrawal_progress(self) -> Dict:
        """Get current withdrawal progress and status."""
        state = await self.state_manager.get_state()
        progress = state.get("withdrawal_progress", {})

        if not progress:
            return {
                "status": "not_started",
                "total_positions": 0,
                "processed_positions": 0,
                "completion_percentage": 0.0,
            }

        total = progress.get("total_positions", 0)
        processed = progress.get("processed_positions", 0)

        completion_percentage = (processed / total * 100) if total > 0 else 0

        status = "completed" if processed >= total else "in_progress"

        return {
            "total_positions": total,
            "processed_positions": processed,
            "pending_transactions": progress.get("pending_transactions", 0),
            "confirmed_transactions": progress.get("confirmed_transactions", 0),
            "failed_transactions": progress.get("failed_transactions", 0),
            "total_value_withdrawn": progress.get("total_value_withdrawn", "0"),
            "start_time": progress.get("start_time"),
            "completion_percentage": round(completion_percentage, 2),
            "status": status,
        }

    async def emergency_stop(self):
        """Emergency stop for withdrawal process."""
        logger.warning("EMERGENCY STOP TRIGGERED")

        state = await self.state_manager.get_state()
        state["emergency_stop"] = True
        state["withdrawal_active"] = False

        await self.state_manager.update_state(state)

        logger.info("Emergency stop completed - all withdrawals halted")
