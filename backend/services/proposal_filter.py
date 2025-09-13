"""Proposal filtering and ranking service for intelligent proposal selection.

This service implements the logic for filtering and ranking proposals based on
user preferences, urgency, voting power, and other factors to help the agent
make intelligent decisions about which proposals to analyze and vote on.
"""

import math
import time
from typing import List, Dict, Any

from logging_config import setup_pearl_logger, log_span
from models import Proposal, UserPreferences

# Setup Pearl logger for this module
logger = setup_pearl_logger(__name__)


class ProposalFilterError(Exception):
    """Base exception for ProposalFilter errors."""

    pass


class ProposalFilter:
    """Service for filtering and ranking proposals based on user preferences.

    This service provides intelligent proposal selection by:
    1. Filtering proposals by user whitelist/blacklist
    2. Ranking proposals by urgency (time until deadline)
    3. Considering proposal voting power requirements
    4. Providing proposal scoring algorithm
    """

    def __init__(self, preferences: UserPreferences) -> None:
        """Initialize ProposalFilter with user preferences.

        Args:
            preferences: UserPreferences object containing filtering criteria
        """
        # Runtime assertions for critical initialization validation
        assert isinstance(preferences, UserPreferences), (
            "Preferences must be UserPreferences instance"
        )

        self.preferences = preferences

        logger.info(
            "ProposalFilter initialized",
            extra={
                "voting_strategy": preferences.voting_strategy.value,
                "confidence_threshold": preferences.confidence_threshold,
                "max_proposals_per_run": preferences.max_proposals_per_run,
                "blacklisted_count": len(preferences.blacklisted_proposers),
                "whitelisted_count": len(preferences.whitelisted_proposers),
            },
        )

    def filter_proposals(self, proposals: List[Proposal]) -> List[Proposal]:
        """Filter proposals based on user preferences.

        This method applies user-defined filtering criteria:
        1. Remove proposals from blacklisted proposers
        2. If whitelist exists, keep only whitelisted proposers
        3. Blacklist takes precedence over whitelist

        Args:
            proposals: List of Proposal objects to filter

        Returns:
            List of filtered Proposal objects
        """
        # Runtime assertions for input validation
        assert isinstance(proposals, list), "Proposals must be a list"
        assert all(isinstance(p, Proposal) for p in proposals), (
            "All proposals must be Proposal objects"
        )

        if not proposals:
            return []

        with log_span(logger, "filter_proposals", proposal_count=len(proposals)):
            logger.info(
                "Starting proposal filtering",
                extra={
                    "initial_count": len(proposals),
                    "blacklisted_count": len(self.preferences.blacklisted_proposers),
                    "whitelisted_count": len(self.preferences.whitelisted_proposers),
                },
            )

            filtered_proposals = []
            blacklisted_count = 0

            for proposal in proposals:
                # Runtime assertion: validate proposal object
                assert isinstance(proposal, Proposal), (
                    f"Invalid proposal object: {type(proposal)}"
                )

                # Check blacklist first (takes precedence)
                if proposal.author in self.preferences.blacklisted_proposers:
                    blacklisted_count += 1
                    logger.debug(
                        "Proposal filtered out due to blacklisted author",
                        extra={
                            "proposal_id": proposal.id,
                            "author": proposal.author,
                        },
                    )
                    continue

                # Check whitelist if it exists
                if self.preferences.whitelisted_proposers:
                    if proposal.author not in self.preferences.whitelisted_proposers:
                        logger.debug(
                            "Proposal filtered out due to author not in whitelist",
                            extra={
                                "proposal_id": proposal.id,
                                "author": proposal.author,
                            },
                        )
                        continue

                # Proposal passes all filters
                filtered_proposals.append(proposal)

            logger.info(
                "Proposal filtering completed",
                extra={
                    "initial_count": len(proposals),
                    "filtered_count": len(filtered_proposals),
                    "blacklisted_count": blacklisted_count,
                    "whitelist_filtered_count": len(proposals)
                    - len(filtered_proposals)
                    - blacklisted_count,
                },
            )

            # Runtime assertion: validate output
            assert isinstance(filtered_proposals, list), (
                "Filtered proposals must be a list"
            )
            assert all(isinstance(p, Proposal) for p in filtered_proposals), (
                "All filtered proposals must be Proposal objects"
            )

            return filtered_proposals

    def rank_proposals(self, proposals: List[Proposal]) -> List[Proposal]:
        """Rank proposals by importance and urgency.

        This method ranks proposals based on:
        1. Urgency (time until deadline)
        2. Voting power requirements
        3. Participation level

        Args:
            proposals: List of Proposal objects to rank

        Returns:
            List of ranked Proposal objects (most important first)
        """
        # Runtime assertions for input validation
        assert isinstance(proposals, list), "Proposals must be a list"
        assert all(isinstance(p, Proposal) for p in proposals), (
            "All proposals must be Proposal objects"
        )

        if not proposals:
            return []

        with log_span(logger, "rank_proposals", proposal_count=len(proposals)):
            logger.info(
                "Starting proposal ranking", extra={"proposal_count": len(proposals)}
            )

            # Calculate scores for all proposals
            proposal_scores = []
            for proposal in proposals:
                score = self.calculate_proposal_score(proposal)
                proposal_scores.append((proposal, score))

                logger.debug(
                    "Proposal scored",
                    extra={
                        "proposal_id": proposal.id,
                        "score": score,
                        "author": proposal.author,
                    },
                )

            # Sort by score (highest first)
            proposal_scores.sort(key=lambda x: x[1], reverse=True)

            # Extract ranked proposals
            ranked_proposals = [proposal for proposal, score in proposal_scores]

            logger.info(
                "Proposal ranking completed",
                extra={
                    "proposal_count": len(ranked_proposals),
                    "top_score": proposal_scores[0][1] if proposal_scores else 0.0,
                    "bottom_score": proposal_scores[-1][1] if proposal_scores else 0.0,
                },
            )

            # Runtime assertion: validate output
            assert isinstance(ranked_proposals, list), "Ranked proposals must be a list"
            assert all(isinstance(p, Proposal) for p in ranked_proposals), (
                "All ranked proposals must be Proposal objects"
            )
            assert len(ranked_proposals) == len(proposals), (
                "Ranking must preserve proposal count"
            )

            return ranked_proposals

    def calculate_proposal_score(self, proposal: Proposal) -> float:
        """Calculate proposal priority score.

        This method calculates a composite score based on multiple factors:
        1. Urgency factor (time until deadline)
        2. Voting power factor (total voting power)
        3. Participation factor (number of votes)

        Args:
            proposal: Proposal object to score

        Returns:
            Float score value (higher is more important)
        """
        # Runtime assertions for input validation
        assert isinstance(proposal, Proposal), "Proposal must be a Proposal object"

        with log_span(logger, "calculate_proposal_score", proposal_id=proposal.id):
            current_time = int(time.time())

            # Calculate urgency factor (higher for more urgent)
            time_until_deadline = proposal.end - current_time
            urgency_factor = self._calculate_urgency_factor(time_until_deadline)

            # Calculate voting power factor (normalized)
            voting_power_factor = self._calculate_voting_power_factor(
                proposal.scores_total
            )

            # Calculate participation factor (based on vote count)
            participation_factor = self._calculate_participation_factor(proposal.votes)

            # Combine factors with weights
            URGENCY_WEIGHT = 0.5
            VOTING_POWER_WEIGHT = 0.3
            PARTICIPATION_WEIGHT = 0.2

            composite_score = (
                urgency_factor * URGENCY_WEIGHT
                + voting_power_factor * VOTING_POWER_WEIGHT
                + participation_factor * PARTICIPATION_WEIGHT
            )

            logger.debug(
                "Proposal score calculated",
                extra={
                    "proposal_id": proposal.id,
                    "urgency_factor": urgency_factor,
                    "voting_power_factor": voting_power_factor,
                    "participation_factor": participation_factor,
                    "composite_score": composite_score,
                    "time_until_deadline": time_until_deadline,
                },
            )

            # Runtime assertion: validate output
            assert isinstance(composite_score, float), "Score must be a float"
            assert composite_score > 0.0, "Score must be positive"
            assert composite_score != float("inf"), "Score cannot be infinite"
            assert composite_score == composite_score, "Score cannot be NaN"

            return composite_score

    def _calculate_urgency_factor(self, time_until_deadline: int) -> float:
        """Calculate urgency factor based on time until deadline.

        Args:
            time_until_deadline: Seconds until proposal deadline

        Returns:
            Float urgency factor (higher for more urgent)
        """
        # Runtime assertion: validate input
        assert isinstance(time_until_deadline, int), (
            "Time until deadline must be integer"
        )

        if time_until_deadline <= 0:
            # Proposal has already ended (expired)
            return 0.0

        # Convert to hours for easier calculation
        hours_until_deadline = time_until_deadline / 3600.0

        # Urgency increases exponentially as deadline approaches
        if hours_until_deadline <= 1:
            # Very urgent (< 1 hour)
            urgency_factor = 1.0
        elif hours_until_deadline <= 6:
            # Urgent (1-6 hours)
            urgency_factor = 0.8
        elif hours_until_deadline <= 24:
            # Medium urgency (6-24 hours)
            urgency_factor = 0.6
        elif hours_until_deadline <= 72:
            # Low urgency (1-3 days)
            urgency_factor = 0.4
        else:
            # Very low urgency (> 3 days)
            urgency_factor = 0.2

        # Runtime assertion: validate output
        assert isinstance(urgency_factor, float), "Urgency factor must be float"
        assert 0.0 <= urgency_factor <= 1.0, "Urgency factor must be between 0 and 1"

        return urgency_factor

    def _calculate_voting_power_factor(self, scores_total: float) -> float:
        """Calculate voting power factor based on total voting power.

        Args:
            scores_total: Total voting power for the proposal

        Returns:
            Float voting power factor (normalized)
        """
        # Runtime assertion: validate input
        assert isinstance(scores_total, (int, float)), "Scores total must be numeric"
        assert scores_total >= 0.0, "Scores total cannot be negative"

        # Normalize voting power using logarithmic scale
        # This prevents extremely high values from dominating
        if scores_total <= 0:
            return 0.0

        # Use log10 to normalize, with a reasonable baseline
        log_score = math.log10(max(scores_total, 1.0))

        # Normalize to 0-1 range (assuming max reasonable score is 10^6)
        voting_power_factor = min(log_score / 6.0, 1.0)

        # Runtime assertion: validate output
        assert isinstance(voting_power_factor, float), (
            "Voting power factor must be float"
        )
        assert 0.0 <= voting_power_factor <= 1.0, (
            "Voting power factor must be between 0 and 1"
        )

        return voting_power_factor

    def _calculate_participation_factor(self, votes: int) -> float:
        """Calculate participation factor based on vote count.

        Args:
            votes: Number of votes cast on the proposal

        Returns:
            Float participation factor (normalized)
        """
        # Runtime assertion: validate input
        assert isinstance(votes, int), "Votes must be integer"
        assert votes >= 0, "Votes cannot be negative"

        if votes == 0:
            return 0.0

        # Normalize participation using logarithmic scale
        # This prevents extremely high values from dominating
        log_votes = math.log10(max(votes, 1.0))

        # Normalize to 0-1 range (assuming max reasonable votes is 10^3)
        participation_factor = min(log_votes / 3.0, 1.0)

        # Runtime assertion: validate output
        assert isinstance(participation_factor, float), (
            "Participation factor must be float"
        )
        assert 0.0 <= participation_factor <= 1.0, (
            "Participation factor must be between 0 and 1"
        )

        return participation_factor

    def get_filtering_metrics(
        self, original_proposals: List[Proposal], filtered_proposals: List[Proposal]
    ) -> Dict[str, Any]:
        """Get metrics about the filtering process for response inclusion.

        Args:
            original_proposals: List of proposals before filtering
            filtered_proposals: List of proposals after filtering

        Returns:
            Dictionary containing filtering metrics
        """
        # Runtime assertions for input validation
        assert isinstance(original_proposals, list), "Original proposals must be a list"
        assert isinstance(filtered_proposals, list), "Filtered proposals must be a list"

        original_count = len(original_proposals)
        filtered_count = len(filtered_proposals)

        # Calculate filtering statistics
        blacklisted_count = 0
        whitelist_filtered_count = 0

        for proposal in original_proposals:
            if proposal.author in self.preferences.blacklisted_proposers:
                blacklisted_count += 1
            elif (
                self.preferences.whitelisted_proposers
                and proposal.author not in self.preferences.whitelisted_proposers
            ):
                whitelist_filtered_count += 1

        metrics = {
            "original_count": original_count,
            "filtered_count": filtered_count,
            "blacklisted_count": blacklisted_count,
            "whitelist_filtered_count": whitelist_filtered_count,
            "filter_efficiency": filtered_count / original_count
            if original_count > 0
            else 0.0,
            "blacklisted_proposers": len(self.preferences.blacklisted_proposers),
            "whitelisted_proposers": len(self.preferences.whitelisted_proposers),
            "has_whitelist": bool(self.preferences.whitelisted_proposers),
            "has_blacklist": bool(self.preferences.blacklisted_proposers),
        }

        # Runtime assertion: validate output
        assert isinstance(metrics, dict), "Metrics must be a dictionary"
        assert all(isinstance(k, str) for k in metrics.keys()), (
            "All metric keys must be strings"
        )

        return metrics
