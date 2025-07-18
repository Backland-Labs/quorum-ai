"""Agent Run Service for executing autonomous voting decisions."""

import time
from typing import List, Optional, Tuple
import logging

from logging_config import setup_pearl_logger, log_span

from models import (
    AgentRunRequest,
    AgentRunResponse,
    Proposal,
    VoteDecision,
    VoteType,
    UserPreferences,
)
from services.snapshot_service import SnapshotService
from services.ai_service import AIService
from services.voting_service import VotingService
from services.user_preferences_service import UserPreferencesService
from services.proposal_filter import ProposalFilter
from services.agent_run_logger import AgentRunLogger


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

    def __init__(self) -> None:
        """Initialize AgentRunService with required dependencies."""
        self.snapshot_service = SnapshotService()
        self.ai_service = AIService()
        self.voting_service = VotingService()
        self.user_preferences_service = UserPreferencesService()
        self.logger = AgentRunLogger()
        
        # Initialize Pearl-compliant logger
        self.pearl_logger = setup_pearl_logger(name='agent_run_service')
        self.pearl_logger.info("AgentRunService initialized with all dependencies")

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

        with log_span(
            self.pearl_logger, "agent_run_execution", space_id=request.space_id, dry_run=request.dry_run
        ) as span_data:
            try:
                # Step 1: Load user preferences
                user_preferences, preferences_error = await self._load_user_preferences(
                    request
                )
                if preferences_error:
                    errors.append(preferences_error)
                    user_preferences_applied = False
                else:
                    user_preferences_applied = True

                # Step 2: Fetch and process proposals
                proposals, filtered_proposals, fetch_errors = (
                    await self._fetch_and_process_proposals(
                        request.space_id, user_preferences
                    )
                )
                errors.extend(fetch_errors)

                # Step 3: Make and execute voting decisions
                vote_decisions, final_decisions, voting_errors = (
                    await self._process_voting_decisions(
                        filtered_proposals, user_preferences, request.space_id, request.dry_run
                    )
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

                # Log completion summary
                self.logger.log_agent_completion(response)
                return response

            except Exception as e:
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
                self.logger.log_proposals_fetched(
                    proposals, len(filtered_proposals)
                )
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
                    self.logger.log_proposal_analysis(proposal, decision)
            except Exception as e:
                error_msg = f"Failed to make voting decisions: {str(e)}"
                errors.append(error_msg)
                self.logger.log_error("make_decisions", e)
                return vote_decisions, final_decisions, errors

        # Execute votes
        if vote_decisions:
            try:
                final_decisions = await self._execute_votes(vote_decisions, space_id, dry_run)
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

        with log_span(self.pearl_logger, "fetch_active_proposals", space_id=space_id, limit=limit) as span_data:
            try:
                self.pearl_logger.info(
                    f"Fetching active proposals (space_id={space_id}, limit={limit})"
                )

                # Fetch proposals from Snapshot service
                proposals = await self.snapshot_service.get_proposals(
                    space_ids=[space_id], state="active", first=limit
                )

                span_data['proposal_count'] = len(proposals)
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

        with log_span(self.pearl_logger, "filter_and_rank_proposals", proposal_count=len(proposals)) as span_data:
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
                metrics_str = ', '.join(f"{k}={v}" for k, v in filtering_metrics.items())
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
        self, proposals: List[Proposal], preferences: UserPreferences
    ) -> List[VoteDecision]:
        """Make voting decisions for the given proposals using AI and user preferences.

        Args:
            proposals: List of Proposal objects to analyze
            preferences: User preferences for voting strategy and filters

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

        with log_span(self.pearl_logger, "make_voting_decisions", proposal_count=len(proposals)) as span_data:
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
                        proposal=proposal, strategy=preferences.voting_strategy
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
        self, decisions: List[VoteDecision], space_id: str, dry_run: bool
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
        assert isinstance(
            space_id, str
        ) and space_id.strip(), f"Space ID must be non-empty string, got {space_id}"
        assert isinstance(
            dry_run, bool
        ), f"Dry run must be boolean, got {type(dry_run)}"
        assert all(
            isinstance(d, VoteDecision) for d in decisions
        ), "All decisions must be VoteDecision objects"

        if not decisions:
            return []

        with log_span(
            self.pearl_logger, "execute_votes", space_id=space_id, decision_count=len(decisions), dry_run=dry_run
        ) as span_data:
            try:
                self.pearl_logger.info(
                    f"Executing votes (space_id={space_id}, decision_count={len(decisions)}, dry_run={dry_run})"
                )

                if dry_run:
                    self.pearl_logger.info("Dry run mode - simulating vote execution")
                    return decisions

                # Execute actual votes
                executed_decisions = []

                for decision in decisions:
                    try:
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
