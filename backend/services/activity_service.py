"""Activity tracking service for OLAS compliance monitoring."""

import os
import json
import time
from datetime import date, datetime
from typing import Dict, Optional, Any

from config import settings
from logging_config import setup_pearl_logger, log_span

# Constants for repeated strings
ACTIVITY_TRACKER_FILENAME = "activity_tracker.json"
DAILY_ACTIVITY_REQUIRED_MSG = "Activity required for 24-hour checkpoint window"
DAILY_ACTIVITY_COMPLETED_MSG = "Activity completed for current checkpoint window"
SAFE_TRANSACTION_ACTION = "safe_transaction"
CHECKPOINT_INTERVAL_SECONDS = 24 * 3600  # 24 hours in seconds


class ActivityService:
    """Service for tracking daily activity requirements for OLAS staking compliance."""

    def __init__(self):
        """Initialize activity service with persistent state."""
        # Initialize Pearl-compliant logger
        self.logger = setup_pearl_logger(__name__, store_path=settings.store_path)

        self.last_activity_timestamp: Optional[int] = None  # Unix timestamp
        self.last_activity_date: Optional[date] = None  # For backward compatibility
        self.last_tx_hash: Optional[str] = None
        self.checkpoint_start_timestamp: Optional[int] = None  # When current window started
        self.persistent_file = self._get_persistent_file_path()

        self.load_state()

        # Set checkpoint start to container launch time if not already set
        if self.checkpoint_start_timestamp is None:
            self.checkpoint_start_timestamp = int(time.time())
            self.save_state()
            self.logger.info(
                "Checkpoint window initialized at container start (checkpoint_start_timestamp=%s)",
                self.checkpoint_start_timestamp,
            )

        self._log_initialization()

    def _get_persistent_file_path(self) -> str:
        """Get the path for the persistent activity tracker file.

        Returns:
            Path to the activity tracker JSON file
        """
        return os.path.join(settings.store_path, ACTIVITY_TRACKER_FILENAME)

    def _log_initialization(self) -> None:
        """Log service initialization details."""
        self.logger.info(
            "ActivityService initialized (persistent_file=%s, last_activity_date=%s, daily_activity_needed=%s)",
            self.persistent_file,
            self._format_date(self.last_activity_date),
            self.is_daily_activity_needed(),
        )

    def _format_date(self, date_obj: Optional[date]) -> Optional[str]:
        """Format a date object to ISO string.

        Args:
            date_obj: Date to format, or None

        Returns:
            ISO formatted date string, or None if date_obj is None
        """
        return date_obj.isoformat() if date_obj else None

    def load_state(self) -> None:
        """Load activity state from persistent storage."""
        try:
            if os.path.exists(self.persistent_file):
                with open(self.persistent_file, "r") as f:
                    data = json.load(f)

                    # Load timestamp (new format)
                    if data.get("last_activity_timestamp"):
                        self.last_activity_timestamp = data["last_activity_timestamp"]
                    # Fallback to date for backward compatibility
                    elif data.get("last_activity_date"):
                        self.last_activity_date = date.fromisoformat(
                            data["last_activity_date"]
                        )
                        # Convert date to timestamp (start of day)
                        dt = datetime.combine(self.last_activity_date, datetime.min.time())
                        self.last_activity_timestamp = int(dt.timestamp())

                    self.checkpoint_start_timestamp = data.get("checkpoint_start_timestamp")
                    self.last_tx_hash = data.get("last_tx_hash")

                self.logger.info(
                    "Activity state loaded from file (last_activity_timestamp=%s, last_tx_hash=%s, checkpoint_start=%s)",
                    self.last_activity_timestamp,
                    self.last_tx_hash,
                    self.checkpoint_start_timestamp,
                )
        except Exception as e:
            self.logger.warning("Could not load activity state: %s", str(e))
            # Reset to defaults on any error
            self.last_activity_timestamp = None
            self.last_activity_date = None
            self.checkpoint_start_timestamp = None
            self.last_tx_hash = None

    def save_state(self) -> None:
        """Save activity state to persistent storage."""
        try:
            self._ensure_directory_exists()
            state_data = self._prepare_state_data()
            self._write_state_file(state_data)
            self._log_state_saved()
        except Exception as e:
            self.logger.warning("Could not save activity state: %s", str(e))

    def _ensure_directory_exists(self) -> None:
        """Ensure the directory for the persistent file exists."""
        directory_path = os.path.dirname(self.persistent_file)
        os.makedirs(directory_path, exist_ok=True)

    def _prepare_state_data(self) -> Dict[str, Any]:
        """Prepare state data for persistence.

        Returns:
            Dictionary with serializable state data
        """
        return {
            "last_activity_timestamp": self.last_activity_timestamp,
            "last_activity_date": self._format_date(self.last_activity_date) if self.last_activity_date else None,  # Backward compat
            "checkpoint_start_timestamp": self.checkpoint_start_timestamp,
            "last_tx_hash": self.last_tx_hash,
        }

    def _write_state_file(self, data: Dict[str, Any]) -> None:
        """Write state data to file.

        Args:
            data: State data to write
        """
        with open(self.persistent_file, "w") as f:
            json.dump(data, f)

    def _log_state_saved(self) -> None:
        """Log that state has been saved."""
        self.logger.info(
            "Activity state saved to file (last_activity_timestamp=%s, last_tx_hash=%s, checkpoint_start=%s)",
            self.last_activity_timestamp,
            self.last_tx_hash,
            self.checkpoint_start_timestamp,
        )

    def is_daily_activity_needed(self) -> bool:
        """Check if we need to create activity for the current 24-hour checkpoint window.

        Uses a 24-hour checkpoint window aligned with OLAS staking requirements.
        Activity is needed if more than 24 hours have passed since last activity,
        or if we're in a new checkpoint window.

        Returns:
            True if activity is required for current checkpoint window, False if already completed
        """
        current_time = int(time.time())

        # No previous activity - activity is needed
        if self.last_activity_timestamp is None:
            return True

        # Calculate time elapsed since last activity
        time_since_activity = current_time - self.last_activity_timestamp

        # Activity needed if more than 24 hours have elapsed
        if time_since_activity >= CHECKPOINT_INTERVAL_SECONDS:
            return True

        # If we have a checkpoint start time, check if we've crossed into a new window
        if self.checkpoint_start_timestamp is not None:
            # Calculate the current checkpoint number
            time_since_checkpoint_start = current_time - self.checkpoint_start_timestamp
            current_checkpoint_window = time_since_checkpoint_start // CHECKPOINT_INTERVAL_SECONDS

            # Calculate which window the last activity was in
            activity_time_since_start = self.last_activity_timestamp - self.checkpoint_start_timestamp
            last_activity_window = activity_time_since_start // CHECKPOINT_INTERVAL_SECONDS

            # If we're in a different window, activity is needed
            if current_checkpoint_window > last_activity_window:
                return True

        return False

    def mark_activity_completed(self, tx_hash: str) -> None:
        """Mark activity as completed for current 24-hour checkpoint window.

        Args:
            tx_hash: Transaction hash of the completed activity transaction
        """
        # Runtime assertions
        assert tx_hash, "Transaction hash must not be empty"
        assert isinstance(tx_hash, str), "Transaction hash must be a string"

        current_time = int(time.time())
        self.last_activity_timestamp = current_time
        self.last_activity_date = date.today()  # Keep for backward compatibility
        self.last_tx_hash = tx_hash

        self.save_state()

        self.logger.info(
            "Activity marked as completed (tx_hash=%s, timestamp=%s, date=%s)",
            tx_hash,
            current_time,
            date.today().isoformat(),
        )

    def get_activity_status(self) -> Dict[str, Any]:
        """Get current activity status for monitoring.

        Returns:
            Dict containing activity status information
        """
        days_since = self._calculate_days_since_activity()
        hours_since = self._calculate_hours_since_activity()

        return {
            "daily_activity_needed": self.is_daily_activity_needed(),
            "last_activity_timestamp": self.last_activity_timestamp,
            "last_activity_date": self._format_date(self.last_activity_date),
            "last_tx_hash": self.last_tx_hash,
            "checkpoint_start_timestamp": self.checkpoint_start_timestamp,
            "hours_since_activity": hours_since,
            "days_since_activity": days_since,  # Kept for backward compatibility
        }

    def _calculate_hours_since_activity(self) -> Optional[float]:
        """Calculate hours since last activity.

        Returns:
            Number of hours since last activity, or None if no activity recorded
        """
        if self.last_activity_timestamp is None:
            return None

        current_time = int(time.time())
        seconds_elapsed = current_time - self.last_activity_timestamp
        hours_elapsed = seconds_elapsed / 3600
        return round(hours_elapsed, 2)

    def _calculate_days_since_activity(self) -> Optional[int]:
        """Calculate days since last activity (backward compatibility).

        Returns:
            Number of days since last activity, or None if no activity recorded
        """
        if self.last_activity_timestamp is None:
            return None

        hours = self._calculate_hours_since_activity()
        if hours is None:
            return None

        days_elapsed = int(hours // 24)
        return days_elapsed

    def check_olas_compliance(self) -> Dict[str, Any]:
        """Check OLAS staking compliance requirements.

        Returns:
            Dict containing compliance status and required actions
        """
        last_activity = self._format_date(self.last_activity_date)

        if self.is_daily_activity_needed():
            return self._build_non_compliant_status(last_activity)
        return self._build_compliant_status(last_activity)

    def _build_non_compliant_status(
        self, last_activity: Optional[str]
    ) -> Dict[str, Any]:
        """Build non-compliant status response.

        Args:
            last_activity: Formatted last activity date

        Returns:
            Non-compliant status dictionary
        """
        return {
            "compliant": False,
            "reason": DAILY_ACTIVITY_REQUIRED_MSG,
            "action_required": SAFE_TRANSACTION_ACTION,
            "last_activity": last_activity,
        }

    def _build_compliant_status(self, last_activity: Optional[str]) -> Dict[str, Any]:
        """Build compliant status response.

        Args:
            last_activity: Formatted last activity date

        Returns:
            Compliant status dictionary
        """
        return {
            "compliant": True,
            "reason": DAILY_ACTIVITY_COMPLETED_MSG,
            "action_required": None,
            "last_activity": last_activity,
        }

    def get_compliance_summary(self) -> Dict[str, Any]:
        """Get comprehensive compliance summary for reporting.

        Returns:
            Dict containing complete activity and compliance information
        """
        return {
            "activity_status": self.get_activity_status(),
            "olas_compliance": self.check_olas_compliance(),
        }

    async def ensure_daily_compliance(self, safe_service) -> Dict[str, Any]:
        """Ensure daily OLAS compliance by triggering Safe transaction if needed.

        Args:
            safe_service: SafeService instance for creating transactions

        Returns:
            Dict containing compliance action results
        """
        # Runtime assertions
        assert safe_service is not None, "SafeService instance is required"

        with log_span(
            self.logger, "activity_service.ensure_daily_compliance"
        ) as span_data:
            compliance_status = self.check_olas_compliance()

            if not compliance_status["compliant"]:
                return await self._handle_non_compliant_state(
                    safe_service, compliance_status
                )

            return self._handle_compliant_state(compliance_status)

    async def _handle_non_compliant_state(
        self, safe_service, compliance_status: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle non-compliant state by requesting Safe transaction.

        Args:
            safe_service: SafeService instance for creating transactions
            compliance_status: Current compliance status

        Returns:
            Action result dictionary
        """
        self.logger.info("Daily OLAS activity needed - requesting Safe transaction")
        transaction_result = await safe_service.perform_activity_transaction()

        if transaction_result["success"]:
            self.mark_activity_completed(transaction_result["tx_hash"])
            return self._build_success_response(transaction_result)

        return self._build_failure_response(transaction_result, compliance_status)

    def _handle_compliant_state(
        self, compliance_status: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle already compliant state.

        Args:
            compliance_status: Current compliance status

        Returns:
            Action result dictionary
        """
        self.logger.info("Daily OLAS activity already completed")
        return {
            "action_taken": "none",
            "success": True,
            "message": DAILY_ACTIVITY_COMPLETED_MSG,
            "compliance_status": compliance_status,
        }

    def _build_success_response(
        self, transaction_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build successful transaction response.

        Args:
            transaction_result: Result from Safe transaction

        Returns:
            Success response dictionary
        """
        return {
            "action_taken": SAFE_TRANSACTION_ACTION,
            "success": True,
            "transaction_result": transaction_result,
            "compliance_status": self.check_olas_compliance(),  # Updated status
        }

    def _build_failure_response(
        self, transaction_result: Dict[str, Any], compliance_status: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build failed transaction response.

        Args:
            transaction_result: Result from Safe transaction
            compliance_status: Current compliance status

        Returns:
            Failure response dictionary
        """
        return {
            "action_taken": SAFE_TRANSACTION_ACTION,
            "success": False,
            "error": transaction_result.get("error"),
            "compliance_status": compliance_status,
        }
