"""
Agent Run Logger Service

Provides structured logging for agent run operations with focus on debugging
and audit trail capabilities.
"""

import time
from datetime import datetime
from typing import List, Optional

import logfire

from models import AgentRunRequest, AgentRunResponse, Proposal, UserPreferences, VoteDecision


class AgentRunLogger:
    """Simple, effective logger for agent run operations focused on debugging."""
    
    def __init__(self):
        """Initialize the agent run logger."""
        self.start_time: Optional[float] = None
        self.run_id: Optional[str] = None
    
    def log_agent_start(self, request: AgentRunRequest, preferences: UserPreferences) -> None:
        """Log agent run initiation with key parameters."""
        self.start_time = time.time()
        self.run_id = f"{request.space_id}_{int(self.start_time)}"
        
        logfire.info(
            "Agent run started",
            run_id=self.run_id,
            space_id=request.space_id,
            dry_run=request.dry_run,
            strategy=preferences.voting_strategy.value,
            confidence_threshold=preferences.confidence_threshold,
            max_proposals=preferences.max_proposals_per_run
        )
    
    def log_proposals_fetched(self, proposals: List[Proposal], filtered_count: int) -> None:
        """Log proposal fetching and filtering results."""
        logfire.info(
            "Proposals fetched and filtered",
            run_id=self.run_id,
            total_proposals=len(proposals),
            filtered_proposals=filtered_count,
            proposal_ids=[p.id for p in proposals]
        )
    
    def log_proposal_analysis(self, proposal: Proposal, decision: VoteDecision) -> None:
        """Log individual proposal analysis and decision."""
        logfire.info(
            "Proposal analyzed",
            run_id=self.run_id,
            proposal_id=proposal.id,
            proposal_title=proposal.title[:100],  # Truncate for readability
            vote_choice=decision.vote,
            confidence=decision.confidence,
            risk_level=decision.risk_assessment.level.value if decision.risk_assessment else None
        )
    
    def log_vote_execution(self, decision: VoteDecision, success: bool, error: Optional[str] = None) -> None:
        """Log vote execution result with audit trail."""
        if success:
            logfire.info(
                "Vote executed successfully",
                run_id=self.run_id,
                proposal_id=decision.proposal_id,
                vote_choice=decision.vote,
                confidence=decision.confidence
            )
        else:
            logfire.error(
                "Vote execution failed",
                run_id=self.run_id,
                proposal_id=decision.proposal_id,
                vote_choice=decision.vote,
                error=error
            )
    
    def log_agent_completion(self, response: AgentRunResponse) -> None:
        """Log agent run completion with summary metrics."""
        execution_time = time.time() - self.start_time if self.start_time else 0
        
        logfire.info(
            "Agent run completed",
            run_id=self.run_id,
            space_id=response.space_id,
            proposals_analyzed=response.proposals_analyzed,
            votes_cast=len([v for v in response.votes_cast if v.executed]),
            successful_votes=len([v for v in response.votes_cast if v.executed and not v.error]),
            failed_votes=len([v for v in response.votes_cast if v.executed and v.error]),
            execution_time=execution_time,
            errors=response.errors
        )
    
    def log_error(self, operation: str, error: Exception, **context) -> None:
        """Log errors with context for debugging."""
        logfire.error(
            f"Agent run {operation} failed",
            run_id=self.run_id,
            operation=operation,
            error=str(error),
            error_type=type(error).__name__,
            **context
        )
    
    def log_security_event(self, event: str, details: dict) -> None:
        """Log security-related events (never log private keys)."""
        safe_details = {k: v for k, v in details.items() 
                       if k not in ['private_key', 'api_key', 'token']}
        
        logfire.warn(
            f"Security event: {event}",
            run_id=self.run_id,
            event=event,
            timestamp=datetime.utcnow().isoformat(),
            **safe_details
        )