"""
Agent Run Logger Service

Provides Pearl-compliant structured logging for agent run operations with focus on debugging
and audit trail capabilities for autonomous AI agents on Pearl platform.
"""

import time
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging
from models import (
    AgentRunRequest,
    AgentRunResponse,
    Proposal,
    UserPreferences,
    VoteDecision,
)


class AgentRunLogger:
    """Pearl-compliant logger for agent run operations focused on debugging and audit trails."""

    # Security-sensitive keys to filter from logs
    SENSITIVE_KEYS = {"private_key", "api_key", "token", "secret", "password"}

    def __init__(
        self, log_file_path: Optional[str] = None, store_path: Optional[str] = None
    ):
        """Initialize the Pearl-compliant agent run logger."""
        self.start_time: Optional[float] = None
        self.run_id: Optional[str] = None

        # Import logging_config to avoid circular imports
        from logging_config import setup_pearl_logger

        # Initialize Pearl-compliant logger
        self.logger = setup_pearl_logger(
            name="agent_run_logger",
            level=logging.INFO,
            log_file_path=log_file_path,
            store_path=store_path,
        )

    def _format_structured_message(self, operation: str, params: Dict[str, Any]) -> str:
        """
        Format a structured log message with consistent parameter formatting.

        Args:
            operation: The operation being logged
            params: Dictionary of parameters to include in the log

        Returns:
            Formatted log message string
        """
        # Always include run_id if available
        if self.run_id:
            params = {"run_id": self.run_id, **params}

        # Format parameters as key=value pairs
        formatted_params = []
        for key, value in params.items():
            if value is not None:
                formatted_params.append(f"{key}={value}")

        if formatted_params:
            return f"{operation} ({', '.join(formatted_params)})"
        else:
            return operation

    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove sensitive information from log details.

        Args:
            details: Dictionary that may contain sensitive data

        Returns:
            Sanitized dictionary with sensitive keys removed
        """
        return {
            k: v
            for k, v in details.items()
            if not any(sensitive in k.lower() for sensitive in self.SENSITIVE_KEYS)
        }

    def log_agent_start(
        self, request: AgentRunRequest, preferences: UserPreferences
    ) -> None:
        """Log agent run initiation with key parameters."""
        self.start_time = time.time()
        self.run_id = f"{request.space_id}_{int(self.start_time)}"

        params = {
            "space_id": request.space_id,
            "dry_run": request.dry_run,
            "strategy": preferences.voting_strategy.value,
            "confidence_threshold": preferences.confidence_threshold,
            "max_proposals": preferences.max_proposals_per_run,
        }

        message = self._format_structured_message("Agent run started", params)
        self.logger.info(message)

    def log_proposals_fetched(
        self, proposals: List[Proposal], filtered_count: int
    ) -> None:
        """Log proposal fetching and filtering results."""
        proposal_ids = ",".join([p.id for p in proposals])

        params = {
            "total_proposals": len(proposals),
            "filtered_proposals": filtered_count,
            "proposal_ids": proposal_ids,
        }

        message = self._format_structured_message(
            "Proposals fetched and filtered", params
        )
        self.logger.info(message)

    def log_proposal_analysis(self, proposal: Proposal, decision: VoteDecision) -> None:
        """Log individual proposal analysis and decision."""
        truncated_title = proposal.title[:100]  # Truncate for readability
        risk_level = (
            decision.risk_assessment.value if decision.risk_assessment else None
        )

        params = {
            "proposal_id": proposal.id,
            "proposal_title": truncated_title,
            "vote_choice": decision.vote,
            "confidence": decision.confidence,
            "risk_level": risk_level,
        }

        message = self._format_structured_message("Proposal analyzed", params)
        self.logger.info(message)

    def log_vote_execution(
        self, decision: VoteDecision, success: bool, error: Optional[str] = None
    ) -> None:
        """Log vote execution result with audit trail."""
        params = {
            "proposal_id": decision.proposal_id,
            "vote_choice": decision.vote,
            "confidence": decision.confidence,
        }

        if success:
            message = self._format_structured_message(
                "Vote executed successfully", params
            )
            self.logger.info(message)
        else:
            params["error"] = error
            message = self._format_structured_message("Vote execution failed", params)
            self.logger.error(message)

    def log_agent_completion(self, response: AgentRunResponse) -> None:
        """Log agent run completion with summary metrics."""
        execution_time = time.time() - self.start_time if self.start_time else 0

        params = {
            "space_id": response.space_id,
            "proposals_analyzed": response.proposals_analyzed,
            "votes_cast": len(response.votes_cast),
            "successful_votes": len(
                response.votes_cast
            ),  # All votes in votes_cast are successful
            "failed_votes": 0,  # Failed votes are not included in votes_cast
            "execution_time": f"{execution_time:.3f}",
            "errors": response.errors,
        }

        message = self._format_structured_message("Agent run completed", params)
        self.logger.info(message)

    def log_error(self, operation: str, error: Exception, **context) -> None:
        """Log errors with context for debugging."""
        params = {
            "operation": operation,
            "error": str(error),
            "error_type": type(error).__name__,
            **context,  # Add context parameters
        }

        message = self._format_structured_message(
            f"Agent run {operation} failed", params
        )
        self.logger.error(message)

    def log_security_event(self, event: str, details: dict) -> None:
        """Log security-related events (never log private keys)."""
        safe_details = self._sanitize_details(details)

        params = {
            "event": event,
            "timestamp": datetime.utcnow().isoformat(),
            **safe_details,
        }

        message = self._format_structured_message(f"Security event: {event}", params)
        self.logger.warning(message)
