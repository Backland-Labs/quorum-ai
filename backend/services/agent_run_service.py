"""Agent Run Service for executing autonomous voting decisions."""

import glob
import json
import os
import re
import time
from pathlib import Path
from typing import List, Optional, Tuple

from datetime import datetime
from logging_config import setup_pearl_logger, log_span
from config import settings
import config

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
from services.activity_service import ActivityService
from services.user_preferences_service import UserPreferencesService
from services.proposal_filter import ProposalFilter
from services.agent_run_logger import AgentRunLogger
from services.state_transition_tracker import StateTransitionTracker, AgentState


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

    def __init__(self, state_manager=None, ai_service=None) -> None:
        """Initialize AgentRunService with required dependencies.

        Args:
            state_manager: Optional StateManager instance for state persistence
            ai_service: Optional AIService instance for shared configuration
        """
        self.snapshot_service = SnapshotService()
        self.ai_service = ai_service or AIService()
        self.voting_service = VotingService()
        self.safe_service = SafeService()
        self.activity_service = ActivityService()
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

        print(f"\n{'='*80}")
        print(f"🚀 AGENT RUN STARTING - DRY_RUN={request.dry_run}, SPACE={request.space_id}")
        print(f"{'='*80}\n")
        self.pearl_logger.info(
            f"🚀 AGENT RUN STARTING (dry_run={request.dry_run}, space_id={request.space_id}, run_id={run_id})"
        )

        with log_span(
            self.pearl_logger,
            "agent_run_execution",
            space_id=request.space_id,
            dry_run=request.dry_run,
        ):
            try:
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

                # Track activity based on proposals available
                if not filtered_proposals:
                    # No proposals available to vote on
                    print("⚠️ WARNING: filtered_proposals is EMPTY!")
                else:
                    print(f"✅ filtered_proposals={len(filtered_proposals)}")

                print(f"\n💎 ABOUT TO CALL _process_voting_decisions\n")
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
                print(f"\n✨ _process_voting_decisions RETURNED - vote_decisions={len(vote_decisions)}, final_decisions={len(final_decisions)}\n")
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
                import traceback
                print(f"\n{'='*80}")
                print(f"🔥 EXCEPTION CAUGHT IN execute_agent_run!")
                print(f"Error type: {type(e).__name__}")
                print(f"Error message: {str(e)}")
                print(f"Traceback:\n{traceback.format_exc()}")
                print(f"{'='*80}\n")

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

        print(f"\n{'='*80}")
        print(f"📥 FETCHING PROPOSALS")
        print(f"   Space ID: {space_id}")
        print(f"   Max proposals: {user_preferences.max_proposals_per_run}")
        print(f"{'='*80}\n")

        # Fetch active proposals
        try:
            print(f"🔍 Calling _fetch_active_proposals...")
            proposals = await self._fetch_active_proposals(
                space_id, user_preferences.max_proposals_per_run
            )
            print(f"✅ Fetched {len(proposals)} active proposals\n")

            if proposals:
                import time
                current_time = int(time.time())
                print(f"📋 PROPOSAL DETAILS:")
                for i, p in enumerate(proposals):
                    time_until_end = p.end - current_time
                    hours_until_end = time_until_end / 3600
                    days_until_end = hours_until_end / 24

                    time_str = f"{days_until_end:.1f}d" if days_until_end > 1 else f"{hours_until_end:.1f}h"
                    if time_until_end < 0:
                        time_str = "EXPIRED"

                    print(f"   {i+1}. [{p.state}] {p.id[:16]}...")
                    print(f"      Title: {p.title[:60]}...")
                    print(f"      Author: {p.author}")
                    print(f"      Ends in: {time_str} ({time_until_end}s)")
                    print(f"      Scores: {p.scores_total}, Votes: {p.votes}")
                print()

                self.pearl_logger.info(
                    f"Fetched {len(proposals)} proposals from {space_id}. "
                    f"States: {[p.state for p in proposals]}"
                )
            else:
                print(f"⚠️  NO PROPOSALS FOUND for space {space_id}\n")
                self.pearl_logger.warning(f"No proposals found for space {space_id}")

        except Exception as e:
            error_msg = f"Failed to fetch active proposals: {str(e)}"
            errors.append(error_msg)
            self.logger.log_error("fetch_proposals", e, space_id=space_id)
            print(f"❌ Failed to fetch proposals: {error_msg}\n")
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
                print(f"❌ Failed to filter and rank: {error_msg}\n")
                # Fall back to original proposals if filtering fails
                filtered_proposals = proposals
        else:
            print(f"⚠️  Skipping filtering - no proposals to filter\n")

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

        print(f"\n{'='*80}")
        print(f"🎬 _process_voting_decisions CALLED")
        print(f"   proposals={len(proposals)}")
        print(f"   dry_run={dry_run} (TYPE: {type(dry_run)})")
        print(f"   space_id={space_id}")
        print(f"   run_id={run_id}")
        print(f"{'='*80}\n")

        self.pearl_logger.info(
            f"🎬 Processing voting decisions (proposals={len(proposals)}, "
            f"dry_run={dry_run}, space_id={space_id}, run_id={run_id})"
        )

        # Make voting decisions
        if proposals:
            print(f"✅ Proposals exist ({len(proposals)}) - calling _make_voting_decisions")
            self.pearl_logger.info(f"Making voting decisions for {len(proposals)} proposals")
            try:
                vote_decisions = await self._make_voting_decisions(
                    proposals, user_preferences, space_id
                )
                print(f"📊 _make_voting_decisions returned {len(vote_decisions)} decisions")
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
            print(f"\n🗳️  ABOUT TO EXECUTE {len(vote_decisions)} VOTES (dry_run={dry_run})")
            self.pearl_logger.info(
                f"Executing {len(vote_decisions)} votes (dry_run={dry_run}, space_id={space_id})"
            )
            try:
                final_decisions = await self._execute_votes(
                    vote_decisions, space_id, dry_run, run_id
                )
                print(f"✅ _execute_votes returned {len(final_decisions)} executed decisions")
                self.pearl_logger.info(
                    f"Vote execution completed ({len(final_decisions)}/{len(vote_decisions)} successful)"
                )
            except Exception as e:
                error_msg = f"Failed to execute votes: {str(e)}"
                errors.append(error_msg)
                self.logger.log_error("execute_votes", e)
                print(f"❌ _execute_votes FAILED: {error_msg}")
        else:
            print(f"\n⚠️  NO VOTE DECISIONS TO EXECUTE (vote_decisions is empty)")
            self.pearl_logger.warning("No vote decisions to execute - vote_decisions list is empty")

        print(f"\n📋 RETURNING FROM _process_voting_decisions:")
        print(f"   vote_decisions={len(vote_decisions)}")
        print(f"   final_decisions={len(final_decisions)}")
        print(f"   errors={len(errors)}\n")

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
        ):
            try:
                self.pearl_logger.info(
                    f"Fetching active proposals (space_id={space_id}, limit={limit})"
                )

                # Fetch proposals from Snapshot service
                proposals = await self.snapshot_service.get_proposals(
                    space_ids=[space_id], state="active", first=limit
                )

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

    def _validate_filter_params(
        self, proposals: List[Proposal], preferences: UserPreferences
    ) -> None:
        """Validate filter and rank parameters.

        Args:
            proposals: List of Proposal objects to validate
            preferences: UserPreferences to validate
        """
        assert isinstance(
            proposals, list
        ), f"Proposals must be a list, got {type(proposals)}"
        assert isinstance(
            preferences, UserPreferences
        ), f"Preferences must be UserPreferences, got {type(preferences)}"
        assert all(
            isinstance(p, Proposal) for p in proposals
        ), "All proposals must be Proposal objects"

    def _apply_proposal_limit(
        self, ranked_proposals: List[Proposal], preferences: UserPreferences
    ) -> List[Proposal]:
        """Apply max_proposals_per_run limit to ranked proposals.

        Args:
            ranked_proposals: List of ranked proposals
            preferences: User preferences containing max_proposals_per_run

        Returns:
            Limited list of proposals
        """
        if preferences.max_proposals_per_run > 0:
            final_proposals = ranked_proposals[: preferences.max_proposals_per_run]
            self.pearl_logger.info(
                f"Proposals limited to max per run (original_ranked_count={len(ranked_proposals)}, "
                f"final_count={len(final_proposals)}, "
                f"max_proposals_per_run={preferences.max_proposals_per_run})"
            )
            return final_proposals
        return ranked_proposals

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
        self._validate_filter_params(proposals, preferences)

        if not proposals:
            return []

        with log_span(
            self.pearl_logger,
            "filter_and_rank_proposals",
            proposal_count=len(proposals),
        ):
            try:
                print(f"\n{'='*80}")
                print(f"🔍 FILTERING AND RANKING PROPOSALS")
                print(f"   Input proposals: {len(proposals)}")
                print(f"   Blacklisted proposers: {len(preferences.blacklisted_proposers)}")
                print(f"   Whitelisted proposers: {len(preferences.whitelisted_proposers)}")
                print(f"   Max proposals per run: {preferences.max_proposals_per_run}")
                print(f"   Confidence threshold: {preferences.confidence_threshold}")
                print(f"{'='*80}\n")

                self.pearl_logger.info(
                    f"🔍 Starting proposal filtering and ranking (proposal_count={len(proposals)}, "
                    f"blacklisted_count={len(preferences.blacklisted_proposers)}, "
                    f"whitelisted_count={len(preferences.whitelisted_proposers)}, "
                    f"max_proposals_per_run={preferences.max_proposals_per_run})"
                )

                # Log details about each input proposal
                for i, proposal in enumerate(proposals):
                    print(f"   Input Proposal {i+1}: {proposal.id[:16]}... by {proposal.author} - '{proposal.title[:50]}...'")

                # Initialize proposal filter with user preferences
                proposal_filter = ProposalFilter(preferences)

                # Step 1: Filter proposals based on user preferences
                print(f"\n📋 Step 1: Filtering proposals...")
                filtered_proposals = proposal_filter.filter_proposals(proposals)
                print(f"   Filtered: {len(proposals)} → {len(filtered_proposals)} proposals")

                if len(filtered_proposals) < len(proposals):
                    removed_count = len(proposals) - len(filtered_proposals)
                    print(f"   ⚠️  {removed_count} proposals REMOVED by filtering")

                self.pearl_logger.info(
                    f"Proposals filtered (original_count={len(proposals)}, "
                    f"filtered_count={len(filtered_proposals)}, removed={len(proposals) - len(filtered_proposals)})"
                )

                # Step 2: Rank filtered proposals by importance and urgency
                print(f"\n📊 Step 2: Ranking proposals...")
                ranked_proposals = proposal_filter.rank_proposals(filtered_proposals)
                print(f"   Ranked: {len(ranked_proposals)} proposals")

                self.pearl_logger.info(
                    f"Proposals ranked (ranked_count={len(ranked_proposals)})"
                )

                # Step 3: Limit to max_proposals_per_run if specified
                print(f"\n✂️  Step 3: Applying max proposals limit ({preferences.max_proposals_per_run})...")
                final_proposals = self._apply_proposal_limit(
                    ranked_proposals, preferences
                )
                print(f"   Final: {len(ranked_proposals)} → {len(final_proposals)} proposals")

                # Get filtering metrics for logging
                filtering_metrics = proposal_filter.get_filtering_metrics(
                    proposals, filtered_proposals
                )

                print(f"\n📈 FILTERING METRICS:")
                print(f"   Original count: {filtering_metrics['original_count']}")
                print(f"   Filtered count: {filtering_metrics['filtered_count']}")
                print(f"   Blacklisted: {filtering_metrics['blacklisted_count']}")
                print(f"   Whitelist filtered: {filtering_metrics['whitelist_filtered_count']}")
                print(f"   Final count: {len(final_proposals)}")
                print(f"   Filter efficiency: {filtering_metrics['filter_efficiency']:.1%}\n")

                if len(final_proposals) == 0 and len(proposals) > 0:
                    print(f"⚠️  WARNING: ALL PROPOSALS WERE FILTERED OUT!")
                    print(f"   Started with {len(proposals)} proposals")
                    print(f"   Ended with 0 proposals")
                    print(f"   Check: blacklist, whitelist, urgency, and max_proposals settings\n")
                    self.pearl_logger.warning(
                        f"ALL PROPOSALS FILTERED OUT: Started with {len(proposals)}, ended with 0. "
                        f"Blacklisted: {filtering_metrics['blacklisted_count']}, "
                        f"Whitelist filtered: {filtering_metrics['whitelist_filtered_count']}"
                    )

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

        print(f"\n{'='*80}")
        print(f"🔍 _make_voting_decisions CALLED - proposals={len(proposals)}")
        print(f"{'='*80}\n")

        if not proposals:
            print("⚠️ NO PROPOSALS - returning empty list")
            return []

        with log_span(
            self.pearl_logger, "make_voting_decisions", proposal_count=len(proposals)
        ):
            try:
                print(f"🎯 ABOUT TO MAKE DECISIONS - threshold={preferences.confidence_threshold}")
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
                    print(f"📊 Decision confidence={decision.confidence}, threshold={preferences.confidence_threshold}")
                    if decision.confidence >= preferences.confidence_threshold:
                        vote_decisions.append(decision)
                        print(f"✅ Decision ACCEPTED - added to list (total={len(vote_decisions)})")
                        self.pearl_logger.info(
                            f"Vote decision accepted (proposal_id={proposal.id}, "
                            f"vote={decision.vote.value}, confidence={decision.confidence})"
                        )
                    else:
                        # Proposal was evaluated but not voted on due to low confidence
                        print(f"❌ Decision REJECTED - confidence too low")
                        self.pearl_logger.info(
                            f"Vote decision rejected due to low confidence "
                            f"(proposal_id={proposal.id}, confidence={decision.confidence}, "
                            f"threshold={preferences.confidence_threshold})"
                        )

                print(f"\n🎉 Voting decisions COMPLETED - accepted={len(vote_decisions)} of {len(proposals)}\n")
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

    async def _create_immediate_attestation(
        self,
        decision: VoteDecision,
        space_id: str,
        run_id: str,
        vote_id: Optional[str],
        vote_succeeded: bool,
        vote_choice: int,
    ) -> None:
        """Create immediate EAS attestation for a vote decision.

        Args:
            decision: The vote decision to attest
            space_id: The space ID where vote was cast
            run_id: The agent run ID
            vote_id: The Snapshot vote ID (if vote succeeded)
            vote_succeeded: Whether the vote submission succeeded
            vote_choice: The numeric vote choice (from VOTE_CHOICE_MAPPING)
        """
        try:
            self.pearl_logger.info(
                f"Creating immediate EAS attestation (proposal={decision.proposal_id}, "
                f"vote_succeeded={vote_succeeded}, vote_id={vote_id or 'None'}, "
                f"agent={self.voting_service.account.address}, space={space_id})"
            )

            # Build EAS attestation data
            eas_data = EASAttestationData(
                agent=self.voting_service.account.address,
                space_id=space_id,
                proposal_id=decision.proposal_id,
                vote_choice=vote_choice,
                snapshot_sig=vote_id if vote_id else "0x" + "0" * 64,
                timestamp=int(time.time()),
                run_id=run_id,
                confidence=int(decision.confidence * 100),
            )

            # Submit attestation through Safe service
            attestation_result = await self.safe_service.create_eas_attestation(
                eas_data
            )

            if attestation_result.get("success"):
                safe_tx_hash = attestation_result.get("safe_tx_hash")
                self.pearl_logger.info(
                    f"Successfully created EAS attestation (proposal={decision.proposal_id}, "
                    f"safe_tx_hash={safe_tx_hash}, schema_uid={config.settings.eas_schema_uid})"
                )

                # Mark daily activity as completed for OLAS staking compliance
                if safe_tx_hash:
                    self.activity_service.mark_activity_completed(safe_tx_hash)
                    self.pearl_logger.info(
                        f"Marked daily activity as completed (tx_hash={safe_tx_hash}, "
                        f"proposal={decision.proposal_id})"
                    )
            else:
                self._log_attestation_error(
                    attestation_result.get("error", "Unknown error"),
                    decision.proposal_id,
                    space_id,
                )

        except Exception as e:
            self.pearl_logger.exception(
                f"Unexpected exception during immediate attestation. "
                f"proposal={decision.proposal_id}, space={space_id}, "
                f"vote_id={vote_id or 'None'}, agent={self.voting_service.account.address}, "
                f"eas_contract={config.settings.eas_contract_address or 'NOT_SET'}, "
                f"schema_uid={config.settings.eas_schema_uid or 'NOT_SET'}, "
                f"safe_address={config.settings.safe_contract_addresses.get('base') if config.settings.safe_contract_addresses else 'NOT_SET'}. "
                f"Exception: {str(e)}"
            )

    def _get_safe_address(self) -> str:
        """Get Safe address for error messages."""
        return (
            config.settings.safe_contract_addresses.get("base")
            if config.settings.safe_contract_addresses
            else "UNKNOWN"
        )

    def _get_error_category(self, error_msg: str) -> str:
        """Categorize attestation error message.

        Args:
            error_msg: The error message to categorize

        Returns:
            Error category: 'contract_address', 'schema', 'safe_address',
            'timeout', 'funds', 'nonce', or 'generic'
        """
        error_lower = error_msg.lower()
        if "EAS_CONTRACT_ADDRESS" in error_msg or "contract address" in error_lower:
            return "contract_address"
        if "EAS_SCHEMA_UID" in error_msg or "schema" in error_lower:
            return "schema"
        if "SAFE_CONTRACT_ADDRESSES" in error_msg or "safe address" in error_lower:
            return "safe_address"
        if "timeout" in error_lower:
            return "timeout"
        if "insufficient funds" in error_lower:
            return "funds"
        if "nonce" in error_lower:
            return "nonce"
        return "generic"

    def _log_attestation_error(
        self, error_msg: str, proposal_id: str, space_id: str
    ) -> None:
        """Log categorized attestation errors with actionable guidance.

        Args:
            error_msg: The error message from attestation failure
            proposal_id: The proposal ID
            space_id: The space ID
        """
        category = self._get_error_category(error_msg)

        error_messages = {
            "contract_address": (
                f"Cannot create EAS attestation: EAS_CONTRACT_ADDRESS not configured. "
                f"Set EAS_CONTRACT_ADDRESS environment variable to the EAS contract address "
                f"on Base network (0x4200000000000000000000000000000000000021). "
                f"proposal={proposal_id}, space={space_id}"
            ),
            "schema": (
                f"Cannot create EAS attestation: EAS_SCHEMA_UID not configured. "
                f"Set EAS_SCHEMA_UID environment variable to your registered schema UID. "
                f"Register schema at https://base.easscan.org/schema/create. "
                f"proposal={proposal_id}, space={space_id}"
            ),
            "safe_address": (
                f"Cannot create EAS attestation: SAFE_CONTRACT_ADDRESSES not configured. "
                f"Set SAFE_CONTRACT_ADDRESSES environment variable with Safe address JSON. "
                f'Example: SAFE_CONTRACT_ADDRESSES=\'{{"base":"0xYourSafeAddress"}}\'. '
                f"proposal={proposal_id}, space={space_id}"
            ),
            "timeout": (
                f"EAS attestation failed due to RPC timeout. "
                f"Check RPC_URL is responsive: {config.settings.rpc_url}. "
                f"Try increasing timeout or switching RPC provider. "
                f"proposal={proposal_id}, error={error_msg}"
            ),
            "funds": (
                f"EAS attestation failed: Safe has insufficient ETH for gas. "
                f"Fund Safe address with ETH: {self._get_safe_address()}. "
                f"Check balance at https://basescan.org/address/{self._get_safe_address()}. "
                f"proposal={proposal_id}, error={error_msg}"
            ),
            "nonce": (
                f"EAS attestation failed due to nonce mismatch. "
                f"This may indicate a pending transaction or concurrent execution. "
                f"Check Safe Transaction Service for pending txs: "
                f"https://safe-transaction-base.safe.global/api/v1/safes/{self._get_safe_address()}/multisig-transactions/. "
                f"proposal={proposal_id}, error={error_msg}"
            ),
            "generic": (
                f"Failed to create EAS attestation (proposal={proposal_id}, "
                f"space={space_id}, agent={self.voting_service.account.address}, "
                f"eas_contract={config.settings.eas_contract_address or 'NOT_SET'}, "
                f"schema_uid={config.settings.eas_schema_uid or 'NOT_SET'}, "
                f"rpc_url={config.settings.rpc_url}, error={error_msg}). "
                f"Check configuration and network connectivity."
            ),
        }

        self.pearl_logger.error(error_messages[category])

    async def _execute_single_vote(
        self,
        decision: VoteDecision,
        space_id: str,
        run_id: str,
    ) -> bool:
        """Execute a single vote and create attestation.

        Args:
            decision: The vote decision to execute
            space_id: The space ID where vote will be cast
            run_id: The agent run ID

        Returns:
            True if vote was successfully executed
        """
        print(f"\n{'='*80}")
        print(f"🗳️  EXECUTING SINGLE VOTE")
        print(f"   Proposal: {decision.proposal_id}")
        print(f"   Vote: {decision.vote.value}")
        print(f"   Confidence: {decision.confidence}")
        print(f"   Space: {space_id}")
        print(f"   Run ID: {run_id}")
        print(f"{'='*80}\n")

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
        print(f"📊 Vote choice mapping: {decision.vote} → {vote_choice}")

        self.pearl_logger.info(
            f"🗳️  Attempting vote submission (space={space_id}, proposal={decision.proposal_id}, "
            f"choice={vote_choice}, vote_type={decision.vote}, confidence={decision.confidence})"
        )

        # Execute vote through voting service
        print(f"📤 Calling voting_service.vote_on_proposal...")
        vote_result = await self.voting_service.vote_on_proposal(
            space=space_id,
            proposal=decision.proposal_id,
            choice=vote_choice,
        )

        print(f"\n📥 Vote service returned:")
        print(f"   Result keys: {list(vote_result.keys())}")
        print(f"   Success: {vote_result.get('success', False)}")
        if 'error' in vote_result:
            print(f"   Error: {vote_result.get('error')}")
        if 'submission_result' in vote_result:
            print(f"   Submission result: {vote_result.get('submission_result')}")
        print()

        self.pearl_logger.info(
            f"Vote service returned (proposal={decision.proposal_id}, "
            f"success={vote_result.get('success')}, result_keys={list(vote_result.keys())})"
        )

        # Extract vote ID from the Snapshot response
        vote_id = None
        vote_succeeded = vote_result.get("success", False)
        submission_result = vote_result.get("submission_result", {})

        if vote_succeeded:
            self.logger.log_vote_execution(decision, True)
            if submission_result.get("success"):
                response = submission_result.get("response", {})
                vote_id = response.get("id")
                self.pearl_logger.info(
                    f"Vote submitted successfully (proposal={decision.proposal_id}, "
                    f"vote_id={vote_id}, choice={vote_choice})"
                )
            else:
                self.pearl_logger.warning(
                    f"Vote succeeded but submission_result failed (proposal={decision.proposal_id}, "
                    f"submission_result={submission_result})"
                )
        else:
            error_msg = vote_result.get("error", "Unknown error")
            self.logger.log_vote_execution(decision, False, error_msg)
            self.pearl_logger.error(
                f"Vote submission FAILED (proposal={decision.proposal_id}, "
                f"error={error_msg}, choice={vote_choice}, full_result={vote_result})"
            )

        # Always attempt immediate attestation regardless of vote success/failure
        await self._create_immediate_attestation(
            decision, space_id, run_id, vote_id, vote_succeeded, vote_choice
        )

        return vote_succeeded

    def _validate_execute_votes_params(
        self, decisions: List[VoteDecision], space_id: str, dry_run: bool
    ) -> None:
        """Validate parameters for execute_votes.

        Args:
            decisions: List of VoteDecision objects to validate
            space_id: The space ID to validate
            dry_run: The dry_run flag to validate
        """
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

    async def _process_vote_decisions(
        self, decisions: List[VoteDecision], space_id: str, run_id: str
    ) -> List[VoteDecision]:
        """Process and execute all vote decisions.

        Args:
            decisions: List of VoteDecision objects to execute
            space_id: The space ID where votes will be cast
            run_id: The agent run ID

        Returns:
            List of successfully executed VoteDecision objects
        """
        executed_decisions = []
        for i, decision in enumerate(decisions):
            try:
                self.pearl_logger.info(
                    f"Processing vote {i+1}/{len(decisions)} (proposal_id={decision.proposal_id}, "
                    f"vote={decision.vote}, confidence={decision.confidence})"
                )
                vote_succeeded = await self._execute_single_vote(
                    decision, space_id, run_id
                )
                if vote_succeeded:
                    executed_decisions.append(decision)
                    self.pearl_logger.info(
                        f"Vote {i+1}/{len(decisions)} executed successfully (proposal_id={decision.proposal_id})"
                    )
                else:
                    self.pearl_logger.warning(
                        f"Vote {i+1}/{len(decisions)} failed to execute (proposal_id={decision.proposal_id})"
                    )
            except Exception as e:
                import traceback
                self.pearl_logger.error(
                    f"Exception during vote {i+1}/{len(decisions)} execution "
                    f"(proposal_id={decision.proposal_id}, error={str(e)})"
                )
                self.pearl_logger.error(f"Traceback: {traceback.format_exc()}")
                self.logger.log_vote_execution(decision, False, str(e))
                continue

        self.pearl_logger.info(
            f"Vote processing complete (total={len(decisions)}, successful={len(executed_decisions)})"
        )
        return executed_decisions

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
        self._validate_execute_votes_params(decisions, space_id, dry_run)

        if not decisions:
            return []

        with log_span(
            self.pearl_logger,
            "execute_votes",
            space_id=space_id,
            decision_count=len(decisions),
            dry_run=dry_run,
        ):
            try:
                print(f"\n{'='*80}")
                print(f"🗳️  _execute_votes CALLED")
                print(f"   decisions={len(decisions)}")
                print(f"   space_id={space_id}")
                print(f"   dry_run={dry_run} (TYPE: {type(dry_run)})")
                print(f"   run_id={run_id}")
                print(f"{'='*80}\n")

                self.pearl_logger.info(
                    f"🗳️  Executing votes (space_id={space_id}, decision_count={len(decisions)}, "
                    f"dry_run={dry_run}, dry_run_type={type(dry_run).__name__})"
                )

                if dry_run:
                    print(f"\n🚫 DRY RUN MODE ACTIVE - SKIPPING VOTE EXECUTION")
                    print(f"   Returning {len(decisions)} decisions without executing")
                    print(f"   No votes will be submitted to Snapshot")
                    print(f"   No attestations will be created\n")
                    self.pearl_logger.info(
                        "🚫 DRY RUN MODE - Simulating vote execution without actual submission. "
                        f"Skipping {len(decisions)} vote submissions and attestations."
                    )
                    return decisions

                print(f"\n✅ NORMAL MODE - EXECUTING {len(decisions)} VOTES")
                self.pearl_logger.info(f"Normal mode - executing {len(decisions)} votes")

                executed_decisions = await self._process_vote_decisions(
                    decisions, space_id, run_id
                )
                print(f"✅ _process_vote_decisions completed - {len(executed_decisions)} succeeded")

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

    def _get_empty_statistics(self) -> dict:
        """Return empty statistics dict when no data available."""
        return {
            "total_runs": 0,
            "total_proposals_evaluated": 0,
            "total_votes_cast": 0,
            "average_confidence_score": 0.0,
            "success_rate": 0.0,
            "average_runtime_seconds": 0.0,
        }

    async def _aggregate_checkpoint_data(self, checkpoint_file: str) -> dict:
        """Aggregate data from a single checkpoint file.

        Args:
            checkpoint_file: The checkpoint filename to process

        Returns:
            Dictionary with aggregated counters for this checkpoint
        """
        checkpoint_key = checkpoint_file.replace(".json", "")
        checkpoint_data = await self.state_manager.load_state(
            checkpoint_key, allow_recovery=True
        )

        if not checkpoint_data:
            return {}

        # Count proposals evaluated
        proposals_analyzed = checkpoint_data.get("proposals_analyzed", 0)

        # Count votes cast and aggregate confidence scores
        votes_cast = checkpoint_data.get("votes_cast", [])
        votes_count = len(votes_cast) if isinstance(votes_cast, list) else 0

        confidence_sum = 0.0
        if isinstance(votes_cast, list):
            for vote in votes_cast:
                if isinstance(vote, dict):
                    confidence_sum += vote.get("confidence", 0.0)

        # Check if run was successful (no errors)
        errors = checkpoint_data.get("errors", [])
        is_successful = not errors

        # Get runtime
        runtime = checkpoint_data.get("runtime_seconds", 0.0)

        return {
            "proposals_evaluated": proposals_analyzed,
            "votes_cast": votes_count,
            "confidence_sum": confidence_sum,
            "is_successful": is_successful,
            "runtime_seconds": runtime,
        }

    async def _collect_checkpoint_totals(self, checkpoint_files: List[str]) -> dict:
        """Collect totals from all checkpoint files.

        Args:
            checkpoint_files: List of checkpoint filenames to process

        Returns:
            Dictionary with aggregated totals
        """
        totals = {
            "runs": 0,
            "proposals_evaluated": 0,
            "votes_cast": 0,
            "confidence_sum": 0.0,
            "successful_runs": 0,
            "runtime_seconds": 0.0,
        }

        for checkpoint_file in checkpoint_files:
            try:
                aggregated = await self._aggregate_checkpoint_data(checkpoint_file)
                if not aggregated:
                    continue

                totals["runs"] += 1
                totals["proposals_evaluated"] += aggregated["proposals_evaluated"]
                totals["votes_cast"] += aggregated["votes_cast"]
                totals["confidence_sum"] += aggregated["confidence_sum"]
                if aggregated["is_successful"]:
                    totals["successful_runs"] += 1
                totals["runtime_seconds"] += aggregated["runtime_seconds"]

            except Exception as e:
                self.pearl_logger.warning(
                    f"Error loading checkpoint {checkpoint_file}: {e}"
                )
                continue

        return totals

    def _calculate_statistics_from_totals(self, totals: dict) -> dict:
        """Calculate final statistics from totals.

        Args:
            totals: Dictionary with aggregated totals

        Returns:
            Dictionary with calculated statistics
        """
        average_confidence_score = (
            totals["confidence_sum"] / totals["votes_cast"]
            if totals["votes_cast"] > 0
            else 0.0
        )
        success_rate = (
            totals["successful_runs"] / totals["runs"] if totals["runs"] > 0 else 0.0
        )
        average_runtime_seconds = (
            totals["runtime_seconds"] / totals["runs"] if totals["runs"] > 0 else 0.0
        )

        return {
            "total_runs": totals["runs"],
            "total_proposals_evaluated": totals["proposals_evaluated"],
            "total_votes_cast": totals["votes_cast"],
            "average_confidence_score": round(average_confidence_score, 3),
            "success_rate": round(success_rate, 3),
            "average_runtime_seconds": round(average_runtime_seconds, 2),
        }

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
        if not self.state_manager or not hasattr(self.state_manager, "list_files"):
            if not self.state_manager:
                return self._get_empty_statistics()
            self.pearl_logger.warning(
                "StateManager missing list_files method, returning empty statistics"
            )
            return self._get_empty_statistics()

        try:
            # List all checkpoint files
            checkpoint_files = await self.state_manager.list_files()
            checkpoint_pattern = re.compile(r"^agent_checkpoint_.*\.json$")
            checkpoint_files = [
                f for f in checkpoint_files if checkpoint_pattern.match(f)
            ]

            # Collect totals from all checkpoints
            totals = await self._collect_checkpoint_totals(checkpoint_files)

            # Calculate and return statistics
            return self._calculate_statistics_from_totals(totals)

        except Exception as e:
            self.pearl_logger.error(f"Error calculating agent statistics: {e}")
            return self._get_empty_statistics()
