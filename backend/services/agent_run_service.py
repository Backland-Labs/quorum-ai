"""Agent Run Service for executing autonomous voting decisions."""

import glob
import os
import re
import time
from typing import List, Optional, Tuple, Dict, Any

from datetime import datetime, timezone
from logging_config import setup_pearl_logger, log_span

from models import (
    AgentRunRequest,
    AgentRunResponse,
    Proposal,
    VoteDecision,
    VoteType,
    UserPreferences,
    EASAttestationData,
    VotingStrategy,
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
        self.logger = AgentRunLogger()
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
                    # Save voting decisions to history
                    if final_decisions:
                        await self.save_voting_decisions(final_decisions)

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
                    proposals, user_preferences
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

    async def _fetch_active_proposals(
        self, space_id: str, max_proposals: int
    ) -> List[Proposal]:
        """Fetch active proposals from Snapshot service.

        Args:
            space_id: The Snapshot space ID
            max_proposals: Maximum number of proposals to process

        Returns:
            List of active proposals

        Raises:
            ProposalFetchError: If fetching proposals fails
        """
        try:
            self.pearl_logger.info(f"Fetching active proposals for space {space_id}")
            proposals = await self.snapshot_service.get_proposals(
                space_id, state="active", limit=max_proposals * 2
            )

            if not proposals:
                self.pearl_logger.warning(f"No active proposals found for {space_id}")
                return []

            self.pearl_logger.info(
                f"Fetched {len(proposals)} active proposals for {space_id}"
            )
            return proposals

        except Exception as e:
            self.pearl_logger.error(f"Error fetching proposals: {e}")
            raise ProposalFetchError(f"Failed to fetch proposals: {str(e)}")

    async def _filter_and_rank_proposals(
        self, proposals: List[Proposal], user_preferences: UserPreferences
    ) -> List[Proposal]:
        """Filter and rank proposals based on user preferences.

        Args:
            proposals: List of proposals to filter
            user_preferences: User preferences for filtering

        Returns:
            Filtered and ranked list of proposals
        """
        proposal_filter = ProposalFilter(user_preferences)
        filtered_proposals = proposal_filter.filter_proposals(proposals)

        # Limit to max proposals per run
        if (
            user_preferences.max_proposals_per_run
            and len(filtered_proposals) > user_preferences.max_proposals_per_run
        ):
            filtered_proposals = filtered_proposals[
                : user_preferences.max_proposals_per_run
            ]

        self.pearl_logger.info(
            f"Filtered {len(proposals)} proposals to {len(filtered_proposals)}"
        )
        return filtered_proposals

    async def _make_voting_decisions(
        self, proposals: List[Proposal], user_preferences: UserPreferences
    ) -> List[VoteDecision]:
        """Make voting decisions using AI service.

        Args:
            proposals: Proposals to analyze
            user_preferences: User preferences for decision making

        Returns:
            List of voting decisions

        Raises:
            VotingDecisionError: If making decisions fails
        """
        try:
            self.pearl_logger.info(f"Making voting decisions for {len(proposals)} proposals")
            decisions = await self.ai_service.decide_votes(proposals, user_preferences)

            # Validate decisions match proposals
            if len(decisions) != len(proposals):
                raise VotingDecisionError(
                    f"Decision count mismatch: {len(decisions)} decisions for {len(proposals)} proposals"
                )

            self.pearl_logger.info(f"Made {len(decisions)} voting decisions")
            return decisions

        except Exception as e:
            self.pearl_logger.error(f"Error making voting decisions: {e}")
            raise VotingDecisionError(f"Failed to make voting decisions: {str(e)}")

    async def _execute_votes(
        self,
        vote_decisions: List[VoteDecision],
        space_id: str,
        dry_run: bool,
        run_id: str,
    ) -> List[VoteDecision]:
        """Execute voting decisions.

        Args:
            vote_decisions: Decisions to execute
            space_id: The space ID for the votes
            dry_run: Whether to simulate or actually vote
            run_id: The current run ID

        Returns:
            List of executed decisions

        Raises:
            VoteExecutionError: If vote execution fails
        """
        executed_decisions = []

        for decision in vote_decisions:
            try:
                # Track voting state
                self.state_tracker.transition(
                    AgentState.VOTING,
                    {
                        "run_id": run_id,
                        "proposal_id": decision.proposal_id,
                        "vote": decision.vote.value,
                        "dry_run": dry_run,
                    },
                )

                if dry_run:
                    self.logger.log_dry_run_vote(decision)
                    executed_decisions.append(decision)
                else:
                    # Execute actual vote
                    success = await self._execute_single_vote(decision, space_id)
                    if success:
                        self.logger.log_vote_execution(decision, space_id, success)
                        executed_decisions.append(decision)
                        # Add space_id to decision for attestation tracking
                        decision.space_id = space_id
                    else:
                        self.logger.log_vote_execution(decision, space_id, success)

            except Exception as e:
                self.pearl_logger.error(
                    f"Error executing vote for proposal {decision.proposal_id}: {e}"
                )
                # Continue with other votes

        return executed_decisions

    async def _execute_single_vote(
        self, decision: VoteDecision, space_id: str
    ) -> bool:
        """Execute a single vote.

        Args:
            decision: The voting decision
            space_id: The space ID

        Returns:
            True if vote was successful, False otherwise
        """
        try:
            # Map vote type to choice index
            choice = VOTE_CHOICE_MAPPING.get(decision.vote, 1)
            
            # Get Safe address for this space
            safe_addresses = self.safe_service.get_safe_addresses()
            if not safe_addresses:
                self.pearl_logger.error("No Safe addresses configured")
                return False
                
            safe_address = safe_addresses[0]  # Use first Safe for now
            
            result = await self.voting_service.cast_vote(
                safe_address=safe_address,
                space=space_id,
                proposal=decision.proposal_id,
                choice=choice,
            )
            
            return result is not None
            
        except Exception as e:
            self.pearl_logger.error(f"Failed to execute vote: {e}")
            return False

    def _create_agent_response(
        self,
        space_id: str,
        proposals: List[Proposal],
        decisions: List[VoteDecision],
        preferences_applied: bool,
        execution_time: float,
        errors: List[str],
    ) -> AgentRunResponse:
        """Create agent run response object.

        Args:
            space_id: The space ID
            proposals: Proposals that were analyzed
            decisions: Voting decisions that were made
            preferences_applied: Whether user preferences were applied
            execution_time: Total execution time
            errors: Any errors that occurred

        Returns:
            AgentRunResponse object
        """
        return AgentRunResponse(
            space_id=space_id,
            proposals_analyzed=len(proposals),
            votes_cast=decisions,
            user_preferences_applied=preferences_applied,
            execution_time=execution_time,
            errors=errors,
        )

    def _handle_unexpected_error(
        self,
        error: Exception,
        space_id: str,
        start_time: float,
        preferences_applied: bool,
    ) -> AgentRunResponse:
        """Handle unexpected errors gracefully.

        Args:
            error: The exception that occurred
            space_id: The space ID
            start_time: Run start time
            preferences_applied: Whether preferences were applied

        Returns:
            AgentRunResponse with error information
        """
        self.pearl_logger.error(f"Unexpected error in agent run: {error}", exc_info=True)
        
        return AgentRunResponse(
            space_id=space_id,
            proposals_analyzed=0,
            votes_cast=[],
            user_preferences_applied=preferences_applied,
            execution_time=time.time() - start_time,
            errors=[f"Unexpected error: {str(error)}"],
        )

    async def cleanup(self):
        """Cleanup resources and save shutdown state."""
        try:
            self.pearl_logger.info("Starting AgentRunService cleanup")

            # Save any active run state for recovery
            if self._active_run:
                await self._save_shutdown_state()

            # Finalize state tracker
            if hasattr(self, "state_tracker"):
                await self.state_tracker.finalize()

            self.pearl_logger.info("AgentRunService cleanup completed")

        except Exception as e:
            self.pearl_logger.error(f"Error during cleanup: {e}")

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

    async def _process_pending_attestations(self, space_id: str) -> None:
        """Process any pending attestations from previous runs."""
        if not self.state_manager:
            return

        try:
            # Load checkpoint to get pending attestations
            checkpoint = await self.state_manager.load_state(
                f"agent_checkpoint_{space_id}"
            )
            if not checkpoint or "pending_attestations" not in checkpoint:
                return

            pending_attestations = checkpoint.get("pending_attestations", [])
            if not pending_attestations:
                return

            self.pearl_logger.info(
                f"Processing {len(pending_attestations)} pending attestations"
            )

            remaining_attestations = []
            for attestation_data in pending_attestations:
                try:
                    # Reconstruct VoteDecision and attestation data
                    vote_decision = VoteDecision(**attestation_data["vote_decision"])
                    eas_data = EASAttestationData(**attestation_data["eas_data"])

                    # Retry attestation
                    success = await self._retry_attestation(
                        vote_decision, eas_data, attestation_data.get("retry_count", 0)
                    )

                    if not success:
                        # Keep for next run if still failing
                        attestation_data["retry_count"] = (
                            attestation_data.get("retry_count", 0) + 1
                        )
                        remaining_attestations.append(attestation_data)

                except Exception as e:
                    self.pearl_logger.error(
                        f"Error processing pending attestation: {e}"
                    )
                    # Keep for next run
                    remaining_attestations.append(attestation_data)

            # Update checkpoint with remaining attestations
            checkpoint["pending_attestations"] = remaining_attestations
            await self.state_manager.save_checkpoint(
                f"agent_checkpoint_{space_id}", checkpoint
            )

            self.pearl_logger.info(
                f"Processed pending attestations, {len(remaining_attestations)} remaining"
            )

        except Exception as e:
            self.pearl_logger.error(f"Error processing pending attestations: {e}")

    async def _retry_attestation(
        self, vote_decision: VoteDecision, eas_data: EASAttestationData, retry_count: int
    ) -> bool:
        """Retry a failed attestation."""
        if retry_count >= MAX_ATTESTATION_RETRIES:
            self.pearl_logger.warning(
                f"Attestation for {vote_decision.proposal_id} exceeded max retries"
            )
            return True  # Remove from pending

        try:
            # Get Safe address
            safe_addresses = self.safe_service.get_safe_addresses()
            if not safe_addresses:
                return False

            safe_address = safe_addresses[0]

            # Create attestation with EAS data
            tx_hash = await self.safe_service.create_attestation_with_eas(
                vote_decision, safe_address, eas_data
            )

            if tx_hash:
                self.pearl_logger.info(
                    f"Successfully created attestation on retry: {tx_hash}"
                )
                return True

            return False

        except Exception as e:
            self.pearl_logger.error(f"Error retrying attestation: {e}")
            return False

    async def track_attestation_checkpoint(
        self, run_id: str, vote_decision: VoteDecision, eas_data: EASAttestationData
    ) -> None:
        """Track failed attestation for retry in next run."""
        if not self.state_manager:
            return

        try:
            # Load current checkpoint
            checkpoint = await self.state_manager.load_state(f"run_{run_id}")
            if not checkpoint:
                checkpoint = {}

            # Add to pending attestations
            pending = checkpoint.get("pending_attestations", [])
            pending.append(
                {
                    "vote_decision": vote_decision.model_dump(mode="json"),
                    "eas_data": eas_data.model_dump(mode="json"),
                    "retry_count": 0,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

            checkpoint["pending_attestations"] = pending

            # Save updated checkpoint
            await self.state_manager.save_checkpoint(f"run_{run_id}", checkpoint)

            self.pearl_logger.info(
                f"Tracked failed attestation for {vote_decision.proposal_id}"
            )

        except Exception as e:
            self.pearl_logger.error(f"Error tracking attestation checkpoint: {e}")
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
        """Get recent voting decisions from all checkpoint files.

        Args:
            limit: Maximum number of decisions to return

        Returns:
            List of tuples containing (VoteDecision, timestamp)
        """
        if not self.state_manager:
            return []

        all_decisions = []

        try:
            # List all checkpoint files
            checkpoint_files = await self.state_manager.list_files()
            checkpoint_pattern = re.compile(r"^agent_checkpoint_.*\.json$")

            # Filter for checkpoint files
            checkpoint_files = [
                f for f in checkpoint_files if checkpoint_pattern.match(f)
            ]

            # Load and aggregate decisions from each checkpoint
            for checkpoint_file in checkpoint_files:
                try:
                    # Remove .json extension to get the key name
                    checkpoint_key = checkpoint_file.replace(".json", "")
                    checkpoint_data = await self.state_manager.load_state(
                        checkpoint_key, allow_recovery=True
                    )

                    if checkpoint_data and "votes_cast" in checkpoint_data:
                        votes = checkpoint_data["votes_cast"]

                        # Handle both old format (count) and new format (list of decisions)
                        if isinstance(votes, list):
                            for vote_data in votes:
                                try:
                                    # Create a copy to avoid modifying the original
                                    vote_data_copy = vote_data.copy()

                                    # Extract timestamp before creating VoteDecision
                                    timestamp = vote_data_copy.pop(
                                        "timestamp",
                                        checkpoint_data.get("timestamp", ""),
                                    )

                                    # Create VoteDecision from the data
                                    vote_decision = VoteDecision(**vote_data_copy)
                                    all_decisions.append((vote_decision, timestamp))
                                except Exception as e:
                                    self.pearl_logger.warning(
                                        f"Skipping invalid vote decision: {e}"
                                    )

                except Exception as e:
                    self.pearl_logger.warning(
                        f"Error loading checkpoint {checkpoint_file}: {e}"
                    )
                    continue

            # Sort by timestamp (most recent first)
            all_decisions.sort(key=lambda x: x[1], reverse=True)

            # Apply limit
            return all_decisions[:limit]

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
                "average_confidence_score": average_confidence_score,
                "success_rate": success_rate,
                "average_runtime_seconds": average_runtime_seconds,
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

    async def get_voting_history(self, limit: int = 10) -> List[VoteDecision]:
        """Get recent voting history from state manager (max 10).
        
        Args:
            limit: Maximum number of decisions to return (default and max: 10)
            
        Returns:
            List of VoteDecision objects representing recent votes
        """
        if not self.state_manager:
            return []
            
        # Enforce maximum limit of 10
        limit = min(limit, 10)
        
        try:
            # Load voting history from state
            state = await self.state_manager.load_state("voting_history")
            
            if not state or "voting_history" not in state:
                return []
                
            history_data = state["voting_history"]
            
            # Convert to VoteDecision objects, filtering invalid entries
            decisions = []
            for item in history_data:
                try:
                    # Ensure all required fields are present
                    if not isinstance(item, dict):
                        continue
                        
                    # Set defaults for missing optional fields
                    if "confidence" not in item:
                        item["confidence"] = 0.0
                    if "strategy_used" not in item:
                        item["strategy_used"] = VotingStrategy.BALANCED.value
                    if "reasoning" not in item or len(item.get("reasoning", "")) < 10:
                        item["reasoning"] = "Decision made based on available information"
                        
                    decision = VoteDecision(**item)
                    decisions.append(decision)
                except Exception as e:
                    self.pearl_logger.warning(f"Skipping invalid vote decision: {e}")
                    continue
                    
            # Return only the most recent N decisions
            return decisions[-limit:]
            
        except Exception as e:
            self.pearl_logger.error(f"Error loading voting history: {e}")
            return []

    async def save_voting_decisions(self, decisions: List[VoteDecision]) -> None:
        """Save new voting decisions and maintain 10-item history.
        
        Args:
            decisions: List of new VoteDecision objects to save
        """
        if not self.state_manager:
            return
            
        try:
            # Load existing history
            state = await self.state_manager.load_state("voting_history")
            existing_history = []
            
            if state and "voting_history" in state:
                existing_history = state["voting_history"]
            
            # Convert new decisions to dict format
            new_history_items = []
            for decision in decisions:
                decision_dict = decision.model_dump(mode="json")
                new_history_items.append(decision_dict)
            
            # Combine and prune to keep only 10 most recent
            combined_history = existing_history + new_history_items
            pruned_history = combined_history[-10:]  # Keep only last 10
            
            # Save updated history
            await self.state_manager.save_state(
                "voting_history",
                {"voting_history": pruned_history},
                sensitive=False
            )
            
            self.pearl_logger.info(
                f"Saved {len(decisions)} new decisions, "
                f"maintaining history of {len(pruned_history)} items"
            )
            
        except Exception as e:
            self.pearl_logger.error(f"Error saving voting decisions: {e}")
            # Don't raise - voting history failures should not block voting

    async def get_voting_patterns(self) -> Dict[str, Any]:
        """Analyze voting patterns from history.
        
        Returns:
            Dictionary containing:
            - vote_distribution: Count of each vote type
            - average_confidence: Average confidence score
            - total_votes: Total number of votes in history
        """
        try:
            history = await self.get_voting_history()
            
            if not history:
                return {
                    "vote_distribution": {"FOR": 0, "AGAINST": 0, "ABSTAIN": 0},
                    "average_confidence": 0.0,
                    "total_votes": 0
                }
            
            # Calculate vote distribution
            vote_distribution = {"FOR": 0, "AGAINST": 0, "ABSTAIN": 0}
            confidence_sum = 0.0
            
            for decision in history:
                vote_distribution[decision.vote.value] += 1
                confidence_sum += decision.confidence
            
            average_confidence = confidence_sum / len(history) if history else 0.0
            
            return {
                "vote_distribution": vote_distribution,
                "average_confidence": average_confidence,
                "total_votes": len(history)
            }
            
        except Exception as e:
            self.pearl_logger.error(f"Error analyzing voting patterns: {e}")
            return {
                "vote_distribution": {"FOR": 0, "AGAINST": 0, "ABSTAIN": 0},
                "average_confidence": 0.0,
                "total_votes": 0
            }