"""Agent Run Service for executing autonomous voting decisions."""

import time
from typing import List

import logfire

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

        logfire.info("AgentRunService initialized with all dependencies")

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

        with logfire.span(
            "agent_run_execution", space_id=request.space_id, dry_run=request.dry_run
        ):
            try:
                # Step 1: Load user preferences
                try:
                    user_preferences = (
                        await self.user_preferences_service.load_preferences()
                    )
                    user_preferences_applied = True

                    # Log agent run start with preferences
                    self.logger.log_agent_start(request, user_preferences)

                except Exception as e:
                    error_msg = f"Failed to load user preferences: {str(e)}"
                    errors.append(error_msg)
                    self.logger.log_error(
                        "load_preferences", e, space_id=request.space_id
                    )
                    # Use default preferences
                    user_preferences = UserPreferences()
                    user_preferences_applied = False

                    # Log agent run start with default preferences
                    self.logger.log_agent_start(request, user_preferences)

                # Step 2: Fetch active proposals
                try:
                    proposals = await self._fetch_active_proposals(
                        request.space_id, user_preferences.max_proposals_per_run
                    )
                except Exception as e:
                    error_msg = f"Failed to fetch active proposals: {str(e)}"
                    errors.append(error_msg)
                    self.logger.log_error(
                        "fetch_proposals", e, space_id=request.space_id
                    )
                    proposals = []

                # Step 3: Filter and rank proposals
                filtered_and_ranked_proposals = []
                if proposals:
                    try:
                        filtered_and_ranked_proposals = (
                            await self._filter_and_rank_proposals(
                                proposals, user_preferences
                            )
                        )
                        # Log proposals fetched and filtered
                        self.logger.log_proposals_fetched(
                            proposals, len(filtered_and_ranked_proposals)
                        )
                    except Exception as e:
                        error_msg = f"Failed to filter and rank proposals: {str(e)}"
                        errors.append(error_msg)
                        self.logger.log_error(
                            "filter_proposals", e, space_id=request.space_id
                        )
                        # Fall back to original proposals if filtering fails
                        filtered_and_ranked_proposals = proposals

                # Step 4: Make voting decisions
                vote_decisions = []
                if filtered_and_ranked_proposals:
                    try:
                        vote_decisions = await self._make_voting_decisions(
                            filtered_and_ranked_proposals, user_preferences
                        )
                        # Log individual proposal analysis
                        for proposal, decision in zip(
                            filtered_and_ranked_proposals, vote_decisions
                        ):
                            self.logger.log_proposal_analysis(proposal, decision)
                    except Exception as e:
                        error_msg = f"Failed to make voting decisions: {str(e)}"
                        errors.append(error_msg)
                        self.logger.log_error(
                            "make_decisions", e, space_id=request.space_id
                        )
                        vote_decisions = []

                # Step 5: Execute votes
                final_vote_decisions = []
                if vote_decisions:
                    try:
                        final_vote_decisions = await self._execute_votes(
                            vote_decisions, request.dry_run
                        )
                    except Exception as e:
                        error_msg = f"Failed to execute votes: {str(e)}"
                        errors.append(error_msg)
                        self.logger.log_error(
                            "execute_votes", e, space_id=request.space_id
                        )
                        final_vote_decisions = []

                # Calculate execution time
                execution_time = time.time() - start_time

                # Create response
                response = AgentRunResponse(
                    space_id=request.space_id,
                    proposals_analyzed=len(filtered_and_ranked_proposals),
                    votes_cast=final_vote_decisions,
                    user_preferences_applied=user_preferences_applied,
                    execution_time=execution_time,
                    errors=errors,
                    next_check_time=None,  # Could be implemented for scheduling
                )

                # Log completion summary
                self.logger.log_agent_completion(response)

                return response

            except Exception as e:
                # Catch-all for unexpected errors
                error_msg = f"Unexpected error during agent run: {str(e)}"
                errors.append(error_msg)
                logfire.error("Unexpected agent run error", error=str(e))

                execution_time = time.time() - start_time

                return AgentRunResponse(
                    space_id=request.space_id,
                    proposals_analyzed=0,
                    votes_cast=[],
                    user_preferences_applied=user_preferences_applied,
                    execution_time=execution_time,
                    errors=errors,
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

        with logfire.span("fetch_active_proposals", space_id=space_id, limit=limit):
            try:
                logfire.info(
                    "Fetching active proposals", space_id=space_id, limit=limit
                )

                # Fetch proposals from Snapshot service
                proposals = await self.snapshot_service.get_proposals(
                    space_ids=[space_id], state="active", first=limit
                )

                logfire.info(
                    "Successfully fetched active proposals",
                    space_id=space_id,
                    proposal_count=len(proposals),
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
                logfire.error(
                    "Failed to fetch active proposals",
                    space_id=space_id,
                    limit=limit,
                    error=str(e),
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

        with logfire.span("filter_and_rank_proposals", proposal_count=len(proposals)):
            try:
                logfire.info(
                    "Starting proposal filtering and ranking",
                    proposal_count=len(proposals),
                    blacklisted_count=len(preferences.blacklisted_proposers),
                    whitelisted_count=len(preferences.whitelisted_proposers),
                    max_proposals_per_run=preferences.max_proposals_per_run,
                )

                # Initialize proposal filter with user preferences
                proposal_filter = ProposalFilter(preferences)

                # Step 1: Filter proposals based on user preferences
                filtered_proposals = proposal_filter.filter_proposals(proposals)

                logfire.info(
                    "Proposals filtered",
                    original_count=len(proposals),
                    filtered_count=len(filtered_proposals),
                )

                # Step 2: Rank filtered proposals by importance and urgency
                ranked_proposals = proposal_filter.rank_proposals(filtered_proposals)

                logfire.info(
                    "Proposals ranked",
                    ranked_count=len(ranked_proposals),
                )

                # Step 3: Limit to max_proposals_per_run if specified
                if preferences.max_proposals_per_run > 0:
                    final_proposals = ranked_proposals[
                        : preferences.max_proposals_per_run
                    ]
                    logfire.info(
                        "Proposals limited to max per run",
                        original_ranked_count=len(ranked_proposals),
                        final_count=len(final_proposals),
                        max_proposals_per_run=preferences.max_proposals_per_run,
                    )
                else:
                    final_proposals = ranked_proposals

                # Get filtering metrics for logging
                filtering_metrics = proposal_filter.get_filtering_metrics(
                    proposals, filtered_proposals
                )

                logfire.info(
                    "Filtering and ranking completed",
                    **filtering_metrics,
                    final_proposal_count=len(final_proposals),
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
                logfire.error(
                    "Failed to filter and rank proposals",
                    proposal_count=len(proposals),
                    error=str(e),
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

        with logfire.span("make_voting_decisions", proposal_count=len(proposals)):
            try:
                logfire.info(
                    "Making voting decisions",
                    proposal_count=len(proposals),
                    voting_strategy=preferences.voting_strategy.value,
                    confidence_threshold=preferences.confidence_threshold,
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
                        logfire.info(
                            "Vote decision accepted",
                            proposal_id=proposal.id,
                            vote=decision.vote.value,
                            confidence=decision.confidence,
                        )
                    else:
                        logfire.info(
                            "Vote decision rejected due to low confidence",
                            proposal_id=proposal.id,
                            confidence=decision.confidence,
                            threshold=preferences.confidence_threshold,
                        )

                logfire.info(
                    "Voting decisions completed",
                    total_proposals=len(proposals),
                    accepted_decisions=len(vote_decisions),
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
                logfire.error(
                    "Failed to make voting decisions",
                    proposal_count=len(proposals),
                    error=str(e),
                )
                raise VotingDecisionError(
                    f"Failed to make voting decisions: {str(e)}"
                ) from e

    async def _execute_votes(
        self, decisions: List[VoteDecision], dry_run: bool
    ) -> List[VoteDecision]:
        """Execute votes for the given decisions.

        Args:
            decisions: List of VoteDecision objects to execute
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
            dry_run, bool
        ), f"Dry run must be boolean, got {type(dry_run)}"
        assert all(
            isinstance(d, VoteDecision) for d in decisions
        ), "All decisions must be VoteDecision objects"

        if not decisions:
            return []

        with logfire.span(
            "execute_votes", decision_count=len(decisions), dry_run=dry_run
        ):
            try:
                logfire.info(
                    "Executing votes", decision_count=len(decisions), dry_run=dry_run
                )

                if dry_run:
                    logfire.info("Dry run mode - simulating vote execution")
                    return decisions

                # Execute actual votes
                executed_decisions = []

                for decision in decisions:
                    try:
                        # Convert VoteType to Snapshot choice format
                        vote_choice = VOTE_CHOICE_MAPPING[decision.vote]

                        # Execute vote through voting service
                        vote_result = await self.voting_service.vote_on_proposal(
                            space="",  # Space ID would need to be passed through
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

                logfire.info(
                    "Vote execution completed",
                    total_decisions=len(decisions),
                    successful_executions=len(executed_decisions),
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
                logfire.error(
                    "Failed to execute votes",
                    decision_count=len(decisions),
                    dry_run=dry_run,
                    error=str(e),
                )
                raise VoteExecutionError(f"Failed to execute votes: {str(e)}") from e

    async def close(self) -> None:
        """Close service resources."""
        if hasattr(self.snapshot_service, "close"):
            await self.snapshot_service.close()

        logfire.info("AgentRunService resources closed")

    async def __aenter__(self) -> "AgentRunService":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit with proper resource cleanup."""
        await self.close()
