"""Agent Run Service for executing autonomous voting decisions."""

import glob
import json
import os
import re
import time
from pathlib import Path
from typing import List, Optional, Tuple

from datetime import datetime, timezone
from logging_config import setup_pearl_logger, log_span
from config import settings

from models import (
    AgentRunRequest,
    AgentRunResponse,
    Proposal,
    VoteDecision,
    VoteType,
    UserPreferences,
    EASAttestationData,
)
from services.snapshot_service import SnapshotService
from services.ai_service import AIService
from services.voting_service import VotingService
from services.safe_service import SafeService
from services.user_preferences_service import UserPreferencesService
from services.proposal_filter import ProposalFilter
from services.agent_run_logger import AgentRunLogger
from services.state_transition_tracker import StateTransitionTracker, AgentState


# Constants
MAX_ATTESTATION_RETRIES = 3


# Custom exceptions for better error handling
class AgentRunServiceError(Exception):
    """Base exception for AgentRunService errors."""

    pass


class ProposalFetchError(AgentRunServiceError):
    """Raised when fetching active proposals fails."""

    pass


class VotingDecisionError(AgentRunServiceError):
    """Raised when making voting decisions fails."""

    pass


class VoteExecutionError(AgentRunServiceError):
    """Raised when executing votes fails."""

    pass


# Constants for better code clarity
DEFAULT_MAX_PROPOSALS_PER_RUN = 3
VOTE_CHOICE_MAPPING = {VoteType.FOR: 1, VoteType.AGAINST: 2, VoteType.ABSTAIN: 3}


class AgentRunService:
    """Service for executing autonomous agent voting runs.

    This service orchestrates the complete agent run workflow:
    1. Fetch active proposals from Snapshot
    2. Load user preferences
    3. Make voting decisions using AI
    4. Execute votes (or simulate in dry run mode)
    """

    def __init__(self, state_manager=None) -> None:
        """Initialize AgentRunService with required dependencies.

        Args:
            state_manager: Optional StateManager instance for state persistence
        """
        self.snapshot_service = SnapshotService()
        self.ai_service = AIService()
        self.voting_service = VotingService()
        self.safe_service = SafeService()
        self.user_preferences_service = UserPreferencesService()
        self.logger = AgentRunLogger(store_path=settings.store_path)
        self.state_manager = state_manager

        # Initialize state transition tracker with StateManager for persistence
        self.state_tracker = StateTransitionTracker(
            state_manager=self.state_manager,
            enable_state_manager=True if state_manager else False,
            enable_pearl_logging=True,
        )

        # Track active operations for graceful shutdown
        self._active_run = False
        self._current_run_data = None

        # Initialize Pearl-compliant logger
        self.pearl_logger = setup_pearl_logger(name="agent_run_service")
        self.pearl_logger.info("AgentRunService initialized with all dependencies")

    async def initialize(self):
        """Initialize async components including state tracker."""
        if self.state_manager:
            await self.state_tracker.async_initialize()
            self.pearl_logger.info(
                "State tracker initialized with StateManager persistence"
            )

    async def execute_agent_run(self, request: AgentRunRequest) -> AgentRunResponse:
        """Execute a complete agent run for the given space.

        Args:
            request: AgentRunRequest containing space_id and dry_run flag

        Returns:
            AgentRunResponse with execution results and statistics
        """
        # Runtime assertions for critical method validation
        assert request is not None, "Request cannot be None"
        assert isinstance(
            request, AgentRunRequest
        ), f"Request must be AgentRunRequest, got {type(request)}"

        start_time = time.time()
        errors = []
        user_preferences_applied = False
        run_id = f"run_{request.space_id}_{int(start_time)}"

        # Track state transition from IDLE to STARTING
        self.state_tracker.transition(
            AgentState.STARTING, {"run_id": run_id, "spaces": [request.space_id]}
        )

        # Mark run as active
        self._active_run = True
        self._current_run_data = {
            "space_id": request.space_id,
            "dry_run": request.dry_run,
            "start_time": start_time,
            "run_id": run_id,
        }

        with log_span(
            self.pearl_logger,
            "agent_run_execution",
            space_id=request.space_id,
            dry_run=request.dry_run,
        ) as span_data:
            try:
                # Process any pending attestations from previous runs
                await self._process_pending_attestations(request.space_id)
                # Step 1: Load user preferences
                self.state_tracker.transition(
                    AgentState.LOADING_PREFERENCES, {"run_id": run_id}
                )
                user_preferences, preferences_error = await self._load_user_preferences(
                    request
                )
                if preferences_error:
                    errors.append(preferences_error)
                    user_preferences_applied = False
                else:
                    user_preferences_applied = True

                # Step 2: Fetch and process proposals
                self.state_tracker.transition(
                    AgentState.FETCHING_PROPOSALS,
                    {"run_id": run_id, "spaces": [request.space_id]},
                )
                (
                    proposals,
                    filtered_proposals,
                    fetch_errors,
                ) = await self._fetch_and_process_proposals(
                    request.space_id, user_preferences
                )
                errors.extend(fetch_errors)

                # Track filtering state
                self.state_tracker.transition(
                    AgentState.FILTERING_PROPOSALS,
                    {
                        "run_id": run_id,
                        "total_proposals": len(proposals),
                        "filtered_proposals": len(filtered_proposals),
                    },
                )

                # Step 3: Make and execute voting decisions
                (
                    vote_decisions,
                    final_decisions,
                    voting_errors,
                ) = await self._process_voting_decisions(
                    filtered_proposals,
                    user_preferences,
                    request.space_id,
                    request.dry_run,
                    run_id,
                )
                errors.extend(voting_errors)

                # Calculate execution time and create response
                execution_time = time.time() - start_time
                response = self._create_agent_response(
                    request.space_id,
                    filtered_proposals,
                    final_decisions,
                    user_preferences_applied,
                    execution_time,
                    errors,
                )

                # Save checkpoint state if state manager available
                if self.state_manager:
                    await self._save_checkpoint_state(response)

                # Log completion summary
                self.logger.log_agent_completion(response)

                # Track completion
                self.state_tracker.transition(
                    AgentState.COMPLETED,
                    {
                        "run_id": run_id,
                        "total_duration": execution_time,
                        "proposals_analyzed": len(filtered_proposals),
                        "votes_cast": len(final_decisions),
                    },
                )

                # Mark run as complete
                self._active_run = False
                self._current_run_data = None

                # Transition back to IDLE
                self.state_tracker.transition(AgentState.IDLE, {"run_id": run_id})

                return response

            except Exception as e:
                # Track error state
                self.state_tracker.transition(
                    AgentState.ERROR,
                    {"run_id": run_id, "error": str(e), "error_type": type(e).__name__},
                )

                # Mark run as complete even on error
                self._active_run = False
                self._current_run_data = None

                # Transition back to IDLE
                self.state_tracker.transition(AgentState.IDLE, {"run_id": run_id})

                # Catch-all for unexpected errors
                return self._handle_unexpected_error(
                    e, request.space_id, start_time, user_preferences_applied
                )

    async def _load_user_preferences(
        self, request: AgentRunRequest
    ) -> Tuple[UserPreferences, Optional[str]]:
        """Load user preferences with error handling.

        Args:
            request: AgentRunRequest containing space_id

        Returns:
            Tuple of (UserPreferences, error_message or None)
        """
        try:
            user_preferences = await self.user_preferences_service.load_preferences()
            self.logger.log_agent_start(request, user_preferences)
            return user_preferences, None
        except Exception as e:
            error_msg = f"Failed to load user preferences: {str(e)}"
            self.logger.log_error("load_preferences", e, space_id=request.space_id)
            # Use default preferences
            user_preferences = UserPreferences()
            self.logger.log_agent_start(request, user_preferences)
            return user_preferences, error_msg

    async def _fetch_and_process_proposals(
        self, space_id: str, user_preferences: UserPreferences
    ) -> Tuple[List[Proposal], List[Proposal], List[str]]:
        """Fetch and process proposals with filtering and ranking.

        Args:
            space_id: The space ID to fetch proposals for
            user_preferences: User preferences for filtering and ranking

        Returns:
            Tuple of (all_proposals, filtered_proposals, errors)
        """
        errors = []
        proposals = []
        filtered_proposals = []

        # Fetch active proposals
        try:
            proposals = await self._fetch_active_proposals(
                space_id, user_preferences.max_proposals_per_run
            )
        except Exception as e:
            error_msg = f"Failed to fetch active proposals: {str(e)}"
            errors.append(error_msg)
            self.logger.log_error("fetch_proposals", e, space_id=space_id)
            return proposals, filtered_proposals, errors

        # Filter and rank proposals if any were fetched
        if proposals:
            try:
                filtered_proposals = await self._filter_and_rank_proposals(
                    proposals, user_preferences
                )
                self.logger.log_proposals_fetched(proposals, len(filtered_proposals))
            except Exception as e:
                error_msg = f"Failed to filter and rank proposals: {str(e)}"
                errors.append(error_msg)
                self.logger.log_error("filter_proposals", e, space_id=space_id)
                # Fall back to original proposals if filtering fails
                filtered_proposals = proposals

        return proposals, filtered_proposals, errors

    async def _process_voting_decisions(
        self,
        proposals: List[Proposal],
        user_preferences: UserPreferences,
        space_id: str,
        dry_run: bool,
        run_id: str,
    ) -> Tuple[List[VoteDecision], List[VoteDecision], List[str]]:
        """Make voting decisions and execute them.

        Args:
            proposals: Proposals to vote on
            user_preferences: User preferences for voting
            space_id: The space ID for the proposals
            dry_run: Whether to actually execute votes

        Returns:
            Tuple of (vote_decisions, final_decisions, errors)
        """
        errors = []
        vote_decisions = []
        final_decisions = []

        # Make voting decisions
        if proposals:
            try:
                vote_decisions = await self._make_voting_decisions(
                    proposals, user_preferences, space_id
                )
                # Log individual proposal analysis
                for proposal, decision in zip(proposals, vote_decisions):
                    # Track analyzing state for each proposal
                    self.state_tracker.transition(
                        AgentState.ANALYZING_PROPOSAL,
                        {
                            "run_id": run_id,
                            "proposal_id": proposal.id,
                            "proposal_title": proposal.title,
                        },
                    )

                    self.logger.log_proposal_analysis(proposal, decision)

                    # Track decision state
                    self.state_tracker.transition(
                        AgentState.DECIDING_VOTE,
                        {
                            "run_id": run_id,
                            "proposal_id": proposal.id,
                            "vote_decision": decision.vote.value
                            if decision.vote
                            else "skip",
                            "confidence_score": decision.confidence,
                        },
                    )
            except Exception as e:
                error_msg = f"Failed to make voting decisions: {str(e)}"
                errors.append(error_msg)
                self.logger.log_error("make_decisions", e)
                return vote_decisions, final_decisions, errors

        # Execute votes
        if vote_decisions:
            try:
                final_decisions = await self._execute_votes(
                    vote_decisions, space_id, dry_run, run_id
                )
            except Exception as e:
                error_msg = f"Failed to execute votes: {str(e)}"
                errors.append(error_msg)
                self.logger.log_error("execute_votes", e)

        return vote_decisions, final_decisions, errors

    def _create_agent_response(
        self,
        space_id: str,
        filtered_proposals: List[Proposal],
        vote_decisions: List[VoteDecision],
        user_preferences_applied: bool,
        execution_time: float,
        errors: List[str],
    ) -> AgentRunResponse:
        """Create the agent run response.

        Args:
            space_id: The space ID
            filtered_proposals: Proposals that were analyzed
            vote_decisions: Voting decisions made
            user_preferences_applied: Whether user preferences were applied
            execution_time: Total execution time
            errors: List of errors encountered

        Returns:
            AgentRunResponse with all results
        """
        return AgentRunResponse(
            space_id=space_id,
            proposals_analyzed=len(filtered_proposals),
            votes_cast=vote_decisions,
            user_preferences_applied=user_preferences_applied,
            execution_time=execution_time,
            errors=errors,
            next_check_time=None,  # Could be implemented for scheduling
        )

    def _handle_unexpected_error(
        self,
        error: Exception,
        space_id: str,
        start_time: float,
        user_preferences_applied: bool,
    ) -> AgentRunResponse:
        """Handle unexpected errors during agent run.

        Args:
            error: The exception that occurred
            space_id: The space ID
            start_time: When the agent run started
            user_preferences_applied: Whether user preferences were applied

        Returns:
            AgentRunResponse with error information
        """
        error_msg = f"Unexpected error during agent run: {str(error)}"
        self.pearl_logger.error(f"Unexpected agent run error: {str(error)}")
        execution_time = time.time() - start_time

        return AgentRunResponse(
            space_id=space_id,
            proposals_analyzed=0,
            votes_cast=[],
            user_preferences_applied=user_preferences_applied,
            execution_time=execution_time,
            errors=[error_msg],
            next_check_time=None,
        )

    async def _fetch_active_proposals(
        self, space_id: str, limit: int
    ) -> List[Proposal]:
        """Fetch active proposals from the specified Snapshot space.

        Args:
            space_id: Snapshot space identifier
            limit: Maximum number of proposals to fetch

        Returns:
            List of active Proposal objects

        Raises:
            ProposalFetchError: When fetching proposals fails
        """
        # Runtime assertions for critical method validation
        assert isinstance(
            space_id, str
        ), f"Space ID must be string, got {type(space_id)}"
        assert space_id.strip(), "Space ID must be non-empty string"
        assert isinstance(limit, int), f"Limit must be integer, got {type(limit)}"
        assert limit > 0, "Limit must be positive integer"

        with log_span(
            self.pearl_logger, "fetch_active_proposals", space_id=space_id, limit=limit
        ) as span_data:
            try:
                self.pearl_logger.info(
                    f"Fetching active proposals (space_id={space_id}, limit={limit})"
                )

                # Fetch proposals from Snapshot service
                proposals = await self.snapshot_service.get_proposals(
                    space_ids=[space_id], state="active", first=limit
                )

                span_data["proposal_count"] = len(proposals)
                self.pearl_logger.info(
                    f"Successfully fetched active proposals (space_id={space_id}, proposal_count={len(proposals)})"
                )

                # Runtime assertion: validate output
                assert isinstance(
                    proposals, list
                ), f"Expected list of proposals, got {type(proposals)}"
                assert all(
                    isinstance(p, Proposal) for p in proposals
                ), "All items must be Proposal objects"

                return proposals

            except Exception as e:
                self.pearl_logger.error(
                    f"Failed to fetch active proposals (space_id={space_id}, limit={limit}, error={str(e)})"
                )
                raise ProposalFetchError(
                    f"Failed to fetch active proposals from {space_id}: {str(e)}"
                ) from e

    async def _filter_and_rank_proposals(
        self, proposals: List[Proposal], preferences: UserPreferences
    ) -> List[Proposal]:
        """Filter and rank proposals based on user preferences and urgency.

        Args:
            proposals: List of Proposal objects to filter and rank
            preferences: User preferences for filtering and ranking

        Returns:
            List of filtered and ranked Proposal objects

        Raises:
            AgentRunServiceError: When filtering or ranking proposals fails
        """
        # Runtime assertions for critical method validation
        assert isinstance(
            proposals, list
        ), f"Proposals must be a list, got {type(proposals)}"
        assert isinstance(
            preferences, UserPreferences
        ), f"Preferences must be UserPreferences, got {type(preferences)}"
        assert all(
            isinstance(p, Proposal) for p in proposals
        ), "All proposals must be Proposal objects"

        if not proposals:
            return []

        with log_span(
            self.pearl_logger,
            "filter_and_rank_proposals",
            proposal_count=len(proposals),
        ) as span_data:
            try:
                self.pearl_logger.info(
                    f"Starting proposal filtering and ranking (proposal_count={len(proposals)}, "
                    f"blacklisted_count={len(preferences.blacklisted_proposers)}, "
                    f"whitelisted_count={len(preferences.whitelisted_proposers)}, "
                    f"max_proposals_per_run={preferences.max_proposals_per_run})"
                )

                # Initialize proposal filter with user preferences
                proposal_filter = ProposalFilter(preferences)

                # Step 1: Filter proposals based on user preferences
                filtered_proposals = proposal_filter.filter_proposals(proposals)

                self.pearl_logger.info(
                    f"Proposals filtered (original_count={len(proposals)}, "
                    f"filtered_count={len(filtered_proposals)})"
                )

                # Step 2: Rank filtered proposals by importance and urgency
                ranked_proposals = proposal_filter.rank_proposals(filtered_proposals)

                self.pearl_logger.info(
                    f"Proposals ranked (ranked_count={len(ranked_proposals)})"
                )

                # Step 3: Limit to max_proposals_per_run if specified
                if preferences.max_proposals_per_run > 0:
                    final_proposals = ranked_proposals[
                        : preferences.max_proposals_per_run
                    ]
                    self.pearl_logger.info(
                        f"Proposals limited to max per run (original_ranked_count={len(ranked_proposals)}, "
                        f"final_count={len(final_proposals)}, "
                        f"max_proposals_per_run={preferences.max_proposals_per_run})"
                    )
                else:
                    final_proposals = ranked_proposals

                # Get filtering metrics for logging
                filtering_metrics = proposal_filter.get_filtering_metrics(
                    proposals, filtered_proposals
                )

                # Format filtering metrics as string
                metrics_str = ", ".join(
                    f"{k}={v}" for k, v in filtering_metrics.items()
                )
                self.pearl_logger.info(
                    f"Filtering and ranking completed ({metrics_str}, "
                    f"final_proposal_count={len(final_proposals)})"
                )

                # Runtime assertion: validate output
                assert isinstance(
                    final_proposals, list
                ), f"Expected list of proposals, got {type(final_proposals)}"
                assert all(
                    isinstance(p, Proposal) for p in final_proposals
                ), "All filtered proposals must be Proposal objects"
                assert len(final_proposals) <= len(
                    proposals
                ), "Filtered count cannot exceed original count"

                return final_proposals

            except Exception as e:
                self.pearl_logger.error(
                    f"Failed to filter and rank proposals (proposal_count={len(proposals)}, "
                    f"error={str(e)})"
                )
                raise AgentRunServiceError(
                    f"Failed to filter and rank proposals: {str(e)}"
                ) from e

    async def _make_voting_decisions(
        self, proposals: List[Proposal], preferences: UserPreferences, space_id: str
    ) -> List[VoteDecision]:
        """Make voting decisions for the given proposals using AI and user preferences.

        Args:
            proposals: List of Proposal objects to analyze
            preferences: User preferences for voting strategy and filters
            space_id: The space identifier for the proposals

        Returns:
            List of VoteDecision objects that meet confidence threshold

        Raises:
            VotingDecisionError: When making voting decisions fails
        """
        # Runtime assertions for critical method validation
        assert isinstance(
            proposals, list
        ), f"Proposals must be a list, got {type(proposals)}"
        assert isinstance(
            preferences, UserPreferences
        ), f"Preferences must be UserPreferences, got {type(preferences)}"
        assert all(
            isinstance(p, Proposal) for p in proposals
        ), "All proposals must be Proposal objects"

        if not proposals:
            return []

        with log_span(
            self.pearl_logger, "make_voting_decisions", proposal_count=len(proposals)
        ) as span_data:
            try:
                self.pearl_logger.info(
                    f"Making voting decisions (proposal_count={len(proposals)}, "
                    f"voting_strategy={preferences.voting_strategy.value}, "
                    f"confidence_threshold={preferences.confidence_threshold})"
                )

                vote_decisions = []

                for proposal in proposals:
                    # Make voting decision using AI
                    decision = await self.ai_service.decide_vote(
                        proposal=proposal,
                        strategy=preferences.voting_strategy,
                        space_id=space_id,
                    )

                    # Filter by confidence threshold
                    if decision.confidence >= preferences.confidence_threshold:
                        vote_decisions.append(decision)
                        self.pearl_logger.info(
                            f"Vote decision accepted (proposal_id={proposal.id}, "
                            f"vote={decision.vote.value}, confidence={decision.confidence})"
                        )
                    else:
                        self.pearl_logger.info(
                            f"Vote decision rejected due to low confidence "
                            f"(proposal_id={proposal.id}, confidence={decision.confidence}, "
                            f"threshold={preferences.confidence_threshold})"
                        )

                self.pearl_logger.info(
                    f"Voting decisions completed (total_proposals={len(proposals)}, "
                    f"accepted_decisions={len(vote_decisions)})"
                )

                # Runtime assertion: validate output
                assert isinstance(
                    vote_decisions, list
                ), f"Expected list of vote decisions, got {type(vote_decisions)}"
                assert all(
                    isinstance(d, VoteDecision) for d in vote_decisions
                ), "All decisions must be VoteDecision objects"

                return vote_decisions

            except Exception as e:
                self.pearl_logger.error(
                    f"Failed to make voting decisions (proposal_count={len(proposals)}, "
                    f"error={str(e)})"
                )
                raise VotingDecisionError(
                    f"Failed to make voting decisions: {str(e)}"
                ) from e

    async def _execute_votes(
        self, decisions: List[VoteDecision], space_id: str, dry_run: bool, run_id: str
    ) -> List[VoteDecision]:
        """Execute votes for the given decisions.

        Args:
            decisions: List of VoteDecision objects to execute
            space_id: The space ID where votes will be cast
            dry_run: If True, simulate voting without actual execution

        Returns:
            List of VoteDecision objects (same as input for now)

        Raises:
            VoteExecutionError: When executing votes fails
        """
        # Runtime assertions for critical method validation
        assert isinstance(
            decisions, list
        ), f"Decisions must be a list, got {type(decisions)}"
        assert (
            isinstance(space_id, str) and space_id.strip()
        ), f"Space ID must be non-empty string, got {space_id}"
        assert isinstance(
            dry_run, bool
        ), f"Dry run must be boolean, got {type(dry_run)}"
        assert all(
            isinstance(d, VoteDecision) for d in decisions
        ), "All decisions must be VoteDecision objects"

        if not decisions:
            return []

        with log_span(
            self.pearl_logger,
            "execute_votes",
            space_id=space_id,
            decision_count=len(decisions),
            dry_run=dry_run,
        ) as span_data:
            try:
                self.pearl_logger.info(
                    f"Executing votes (space_id={space_id}, decision_count={len(decisions)}, dry_run={dry_run})"
                )

                if dry_run:
                    self.pearl_logger.info("Dry run mode - simulating vote execution")
                    # In dry run, we skip actual submission but still return decisions
                    return decisions

                # Execute actual votes
                executed_decisions = []

                for decision in decisions:
                    try:
                        # Track vote submission state
                        self.state_tracker.transition(
                            AgentState.SUBMITTING_VOTE,
                            {
                                "run_id": run_id,
                                "proposal_id": decision.proposal_id,
                                "vote_type": decision.vote.value,
                            },
                        )

                        # Convert VoteType to Snapshot choice format
                        vote_choice = VOTE_CHOICE_MAPPING[decision.vote]

                        # Execute vote through voting service
                        vote_result = await self.voting_service.vote_on_proposal(
                            space=space_id,
                            proposal=decision.proposal_id,
                            choice=vote_choice,
                        )

                        if vote_result.get("success"):
                            executed_decisions.append(decision)
                            self.logger.log_vote_execution(decision, True)

                            # Queue attestation for successful vote
                            await self._queue_attestation(decision, space_id, run_id)
                        else:
                            self.logger.log_vote_execution(
                                decision, False, vote_result.get("error")
                            )

                    except Exception as e:
                        self.logger.log_vote_execution(decision, False, str(e))
                        # Continue with other votes
                        continue

                self.pearl_logger.info(
                    f"Vote execution completed (total_decisions={len(decisions)}, "
                    f"successful_executions={len(executed_decisions)})"
                )

                # Runtime assertion: validate output
                assert isinstance(
                    executed_decisions, list
                ), f"Expected list of executed decisions, got {type(executed_decisions)}"
                assert all(
                    isinstance(d, VoteDecision) for d in executed_decisions
                ), "All executed decisions must be VoteDecision objects"

                return executed_decisions

            except Exception as e:
                self.pearl_logger.error(
                    f"Failed to execute votes (decision_count={len(decisions)}, "
                    f"dry_run={dry_run}, error={str(e)})"
                )
                raise VoteExecutionError(f"Failed to execute votes: {str(e)}") from e

    async def close(self) -> None:
        """Close service resources."""
        if hasattr(self.snapshot_service, "close"):
            await self.snapshot_service.close()

        self.pearl_logger.info("AgentRunService resources closed")

    async def __aenter__(self) -> "AgentRunService":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit with proper resource cleanup."""
        await self.close()

    async def shutdown(self) -> None:
        """Implement shutdown method required by ShutdownService protocol.

        This method is called during graceful shutdown to clean up resources
        and save any pending state.
        """
        self.pearl_logger.info("Agent run service shutdown initiated")

        # If there's an active run, try to save its state
        if self._active_run and self._current_run_data:
            try:
                await self._save_shutdown_state()
            except Exception as e:
                self.pearl_logger.error(f"Failed to save shutdown state: {e}")

        # Close resources
        await self.close()

        self.pearl_logger.info("Agent run service shutdown completed")

    async def save_service_state(self) -> None:
        """Save current service state for recovery."""
        if not self.state_manager:
            return

        state_data = {
            "active_run": self._active_run,
            "current_run_data": self._current_run_data,
            "last_checkpoint": datetime.utcnow().isoformat(),
        }

        await self.state_manager.save_state(
            "agent_run_service", state_data, sensitive=False
        )

    async def stop(self) -> None:
        """Stop the service gracefully."""
        self._active_run = False
        await self.save_state()

    async def _process_pending_attestations(self, space_id: str) -> None:
        """Process any pending attestations from previous runs.

        Args:
            space_id: The space ID to process attestations for
        """
        if not self.state_manager:
            return

        try:
            # Load checkpoint with any pending attestations
            checkpoint = await self.state_manager.load_checkpoint(
                f"agent_checkpoint_{space_id}"
            )
            if not checkpoint or "pending_attestations" not in checkpoint:
                return

            pending_attestations = checkpoint["pending_attestations"]
            if not pending_attestations:
                return

            self.pearl_logger.info(
                f"Processing {len(pending_attestations)} pending attestations for space {space_id}"
            )

            processed_attestations = []
            remaining_attestations = []

            for attestation in pending_attestations:
                # Check retry count
                retry_count = attestation.get("retry_count", 0)
                if retry_count >= MAX_ATTESTATION_RETRIES:
                    self.pearl_logger.warning(
                        f"Attestation for proposal {attestation['proposal_id']} exceeded max retries, dropping"
                    )
                    continue

                try:
                    # Create EAS attestation data
                    eas_data = EASAttestationData(
                        proposal_id=attestation["proposal_id"],
                        space_id=space_id,
                        voter_address=attestation["voter_address"],
                        choice=attestation["vote_choice"],
                        vote_tx_hash=attestation.get("vote_tx_hash", "unknown"),
                        timestamp=datetime.fromisoformat(attestation["timestamp"])
                        if isinstance(attestation["timestamp"], str)
                        else attestation["timestamp"],
                        retry_count=attestation.get("retry_count", 0),
                    )

                    # Submit attestation
                    result = await self.safe_service.create_eas_attestation(eas_data)

                    self.pearl_logger.info(
                        f"Successfully created attestation for proposal {attestation['proposal_id']}: "
                        f"tx_hash={result.get('tx_hash')}, uid={result.get('attestation_uid')}"
                    )

                    processed_attestations.append(attestation["proposal_id"])

                except Exception as e:
                    self.pearl_logger.error(
                        f"Failed to process attestation for proposal {attestation['proposal_id']}: {str(e)}"
                    )

                    # Increment retry count and keep in queue
                    attestation["retry_count"] = retry_count + 1
                    remaining_attestations.append(attestation)

            # Update checkpoint with remaining attestations
            checkpoint["pending_attestations"] = remaining_attestations
            await self.state_manager.save_checkpoint(
                f"agent_checkpoint_{space_id}", checkpoint
            )

            if processed_attestations:
                self.pearl_logger.info(
                    f"Processed {len(processed_attestations)} attestations successfully"
                )

        except Exception as e:
            self.pearl_logger.error(
                f"Error processing pending attestations for space {space_id}: {str(e)}"
            )

    async def _queue_attestation(
        self, decision: VoteDecision, space_id: str, run_id: str
    ) -> None:
        """Queue an attestation for a successful vote.

        Args:
            decision: The vote decision that was executed
            space_id: The space ID where the vote was cast
            run_id: The current agent run ID
        """
        if not self.state_manager:
            self.pearl_logger.warning("No state manager, skipping attestation queue")
            return

        try:
            # Load current checkpoint
            checkpoint = await self.state_manager.load_checkpoint(f"run_{run_id}")
            if checkpoint is None:
                checkpoint = {}

            # Initialize pending_attestations if not present
            if "pending_attestations" not in checkpoint:
                checkpoint["pending_attestations"] = []

            # Get voter address from voting service account
            voter_address = self.voting_service.account.address

            # For now, use the same address as delegate (can be configured later)
            delegate_address = voter_address

            # Create attestation data
            attestation_data = {
                "proposal_id": decision.proposal_id,
                "vote_choice": VOTE_CHOICE_MAPPING[
                    decision.vote
                ],  # Convert VoteType to choice number
                "voter_address": voter_address,
                "delegate_address": delegate_address,
                "reasoning": decision.reasoning,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "retry_count": 0,
            }

            # Add to pending attestations
            checkpoint["pending_attestations"].append(attestation_data)

            # Save updated checkpoint
            await self.state_manager.save_checkpoint(f"run_{run_id}", checkpoint)

            self.pearl_logger.info(
                f"Queued attestation for vote on proposal {decision.proposal_id} - checkpoint key: run_{run_id}"
            )

        except Exception as e:
            self.pearl_logger.error(
                f"Failed to queue attestation for proposal {decision.proposal_id}: {str(e)}"
            )
            # Don't raise - attestation failures should not block voting

    async def _save_checkpoint_state(self, response: AgentRunResponse) -> None:
        """Save checkpoint state during agent run.

        Args:
            response: The current agent run response
        """
        if not self.state_manager:
            return

        # Serialize vote decisions with timestamps
        votes_with_timestamps = []
        for vote in response.votes_cast:
            vote_data = vote.model_dump(mode="json")
            vote_data["timestamp"] = datetime.utcnow().isoformat()
            votes_with_timestamps.append(vote_data)

        checkpoint_data = {
            "space_id": response.space_id,
            "proposals_analyzed": response.proposals_analyzed,
            "votes_cast": votes_with_timestamps,
            "execution_time": response.execution_time,
            "timestamp": datetime.utcnow().isoformat(),
            "errors": response.errors,
            "pending_attestations": [],  # Initialize empty if not loaded
        }

        await self.state_manager.save_state(
            f"agent_checkpoint_{response.space_id}", checkpoint_data, sensitive=False
        )

        self.pearl_logger.info(f"Saved checkpoint state for space {response.space_id}")

    async def _save_shutdown_state(self) -> None:
        """Save state during shutdown for recovery."""
        if not self.state_manager or not self._current_run_data:
            return

        shutdown_data = {
            **self._current_run_data,
            "shutdown_time": datetime.utcnow().isoformat(),
            "reason": "graceful_shutdown",
        }

        await self.state_manager.save_state(
            "agent_shutdown_state", shutdown_data, sensitive=False
        )

        self.pearl_logger.info("Saved shutdown state for recovery")

    def _get_checkpoint_pattern(self) -> str:
        """Get the file pattern for checkpoint files.

        Returns:
            Glob pattern for checkpoint files
        """
        return os.path.join(self.state_manager.store_path, "agent_checkpoint_*.json")

    async def get_latest_checkpoint(self) -> Optional[dict]:
        """Get the most recent checkpoint across all spaces.

        Returns:
            The most recent checkpoint data or None if no checkpoints exist
        """
        if not self.state_manager:
            return None

        latest_checkpoint = None
        latest_timestamp = None

        # Find all checkpoint files
        checkpoint_files = glob.glob(self._get_checkpoint_pattern())

        for file_path in checkpoint_files:
            checkpoint_name = os.path.basename(file_path).replace(".json", "")
            checkpoint_data = await self.state_manager.load_state(checkpoint_name)

            if checkpoint_data and "timestamp" in checkpoint_data:
                # Parse timestamp
                try:
                    timestamp = datetime.fromisoformat(
                        checkpoint_data["timestamp"].replace("Z", "+00:00")
                    )

                    if latest_timestamp is None or timestamp > latest_timestamp:
                        latest_timestamp = timestamp
                        latest_checkpoint = checkpoint_data
                except Exception as e:
                    self.pearl_logger.warning(
                        f"Failed to parse timestamp for {checkpoint_name}: {e}"
                    )

        return latest_checkpoint

    def get_current_state(self) -> str:
        """Get the current agent state from StateTransitionTracker.

        Returns:
            Current state value as string
        """
        return self.state_tracker.current_state.value

    def is_agent_active(self) -> bool:
        """Check if the agent is currently running.

        Returns:
            True if agent is active, False otherwise
        """
        return self._active_run or self.state_tracker.current_state != AgentState.IDLE

    async def get_all_checkpoint_data(self) -> List[dict]:
        """Get data from all checkpoint files.

        Returns:
            List of all checkpoint data
        """
        if not self.state_manager:
            return []

        checkpoints = []

        # Find all checkpoint files
        checkpoint_files = glob.glob(self._get_checkpoint_pattern())

        for file_path in checkpoint_files:
            checkpoint_name = os.path.basename(file_path).replace(".json", "")
            checkpoint_data = await self.state_manager.load_state(checkpoint_name)

            if checkpoint_data:
                checkpoints.append(checkpoint_data)

        return checkpoints

    async def get_recent_decisions(
        self, limit: int = 5
    ) -> List[Tuple[VoteDecision, str]]:
        """Get recent voting decisions from decision files.

        Args:
            limit: Maximum number of decisions to return

        Returns:
            List of tuples containing (VoteDecision, timestamp)
        """
        all_decisions = []

        try:
            # Get the decisions directory path
            decisions_dir = Path(settings.decision_output_dir)
            if not decisions_dir.exists():
                self.pearl_logger.warning(
                    f"Decisions directory does not exist: {decisions_dir}"
                )
                return []

            # Get all decision files and sort by modification time (most recent first)
            decision_files = list(decisions_dir.glob("decision_*.json"))
            decision_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

            # Load and parse decision files
            for decision_file in decision_files[:limit]:
                try:
                    with open(decision_file, "r") as f:
                        decision_data = json.load(f)

                    # Extract the timestamp
                    timestamp = decision_data.get("timestamp", "")

                    # Map the decision file data to VoteDecision model format
                    vote_data = {
                        "proposal_id": decision_data.get("proposal_id"),
                        "vote": decision_data.get("vote"),
                        "confidence": decision_data.get("confidence"),
                        "reasoning": " ".join(decision_data.get("reasoning", []))
                        if isinstance(decision_data.get("reasoning"), list)
                        else decision_data.get("reasoning", ""),
                        "risk_assessment": decision_data.get("risk_level", "MEDIUM"),
                        "strategy_used": decision_data.get(
                            "voting_strategy", "balanced"
                        ),
                        "space_id": decision_data.get("space_id"),
                        "attestation_status": None,  # Not in decision files
                        "estimated_gas_cost": 0.002,  # Default value
                        "run_id": decision_data.get("run_id"),
                        "proposal_title": decision_data.get("proposal_title"),
                        "dry_run": decision_data.get("dry_run", False),
                        "executed": decision_data.get("executed", False),
                        "transaction_hash": decision_data.get("transaction_hash"),
                        "key_factors": decision_data.get("key_factors", []),
                    }

                    # Create VoteDecision from the mapped data
                    vote_decision = VoteDecision(**vote_data)
                    all_decisions.append((vote_decision, timestamp))

                except Exception as e:
                    self.pearl_logger.warning(
                        f"Skipping invalid decision file {decision_file}: {e}"
                    )

            return all_decisions

        except Exception as e:
            self.pearl_logger.error(f"Error retrieving recent decisions: {e}")
            return []

    async def get_agent_run_statistics(self) -> dict:
        """Calculate aggregated statistics from all agent checkpoint files.

        Returns:
            Dictionary containing aggregated statistics:
            - total_runs: Total number of agent runs
            - total_proposals_evaluated: Total proposals evaluated across all runs
            - total_votes_cast: Total votes cast across all runs
            - average_confidence_score: Average confidence across all votes
            - success_rate: Percentage of runs without errors (0.0 to 1.0)
            - average_runtime_seconds: Average runtime per run
        """
        if not self.state_manager:
            return {
                "total_runs": 0,
                "total_proposals_evaluated": 0,
                "total_votes_cast": 0,
                "average_confidence_score": 0.0,
                "success_rate": 0.0,
                "average_runtime_seconds": 0.0,
            }

        # Initialize counters
        total_runs = 0
        total_proposals_evaluated = 0
        total_votes_cast = 0
        total_confidence_sum = 0.0
        successful_runs = 0
        total_runtime_seconds = 0.0

        try:
            # Check if list_files method exists
            if not hasattr(self.state_manager, "list_files"):
                self.pearl_logger.warning(
                    "StateManager missing list_files method, returning empty statistics"
                )
                return {
                    "total_runs": 0,
                    "total_proposals_evaluated": 0,
                    "total_votes_cast": 0,
                    "average_confidence_score": 0.0,
                    "success_rate": 0.0,
                    "average_runtime_seconds": 0.0,
                }

            # List all checkpoint files
            checkpoint_files = await self.state_manager.list_files()
            checkpoint_pattern = re.compile(r"^agent_checkpoint_.*\.json$")

            # Filter for checkpoint files
            checkpoint_files = [
                f for f in checkpoint_files if checkpoint_pattern.match(f)
            ]

            # Load and aggregate data from each checkpoint
            for checkpoint_file in checkpoint_files:
                try:
                    # Remove .json extension to get the key name
                    checkpoint_key = checkpoint_file.replace(".json", "")
                    checkpoint_data = await self.state_manager.load_state(
                        checkpoint_key, allow_recovery=True
                    )

                    if checkpoint_data:
                        total_runs += 1

                        # Count proposals evaluated
                        proposals_evaluated = checkpoint_data.get(
                            "proposals_evaluated", 0
                        )
                        total_proposals_evaluated += proposals_evaluated

                        # Count votes cast and aggregate confidence scores
                        votes_cast = checkpoint_data.get("votes_cast", [])
                        if isinstance(votes_cast, list):
                            total_votes_cast += len(votes_cast)

                            # Sum confidence scores
                            for vote in votes_cast:
                                if isinstance(vote, dict):
                                    confidence = vote.get("confidence", 0.0)
                                    total_confidence_sum += confidence

                        # Check if run was successful (no errors)
                        errors = checkpoint_data.get("errors", [])
                        if not errors:
                            successful_runs += 1

                        # Aggregate runtime
                        runtime = checkpoint_data.get("runtime_seconds", 0.0)
                        total_runtime_seconds += runtime

                except Exception as e:
                    self.pearl_logger.warning(
                        f"Error loading checkpoint {checkpoint_file}: {e}"
                    )
                    continue

            # Calculate averages
            average_confidence_score = (
                total_confidence_sum / total_votes_cast if total_votes_cast > 0 else 0.0
            )
            success_rate = successful_runs / total_runs if total_runs > 0 else 0.0
            average_runtime_seconds = (
                total_runtime_seconds / total_runs if total_runs > 0 else 0.0
            )

            return {
                "total_runs": total_runs,
                "total_proposals_evaluated": total_proposals_evaluated,
                "total_votes_cast": total_votes_cast,
                "average_confidence_score": round(average_confidence_score, 3),
                "success_rate": round(success_rate, 3),
                "average_runtime_seconds": round(average_runtime_seconds, 2),
            }

        except Exception as e:
            self.pearl_logger.error(f"Error calculating agent statistics: {e}")
            return {
                "total_runs": 0,
                "total_proposals_evaluated": 0,
                "total_votes_cast": 0,
                "average_confidence_score": 0.0,
                "success_rate": 0.0,
                "average_runtime_seconds": 0.0,
            }
