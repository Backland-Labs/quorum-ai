"""Health Check Service for Olas Pearl compliance.

This service provides comprehensive health status information required for
Olas Pearl integration, including transaction manager health, agent health,
and consensus rounds information.
"""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from logging_config import setup_pearl_logger, log_span


class HealthCheckService:
    """Service for providing Pearl-compliant health check information."""

    def __init__(
        self,
        activity_service=None,
        safe_service=None,
        state_transition_tracker=None,
        cache_ttl_seconds: int = 10,
    ):
        """Initialize health check service.
        
        Args:
            activity_service: ActivityService instance for staking KPI checks
            safe_service: SafeService instance for balance checks
            state_transition_tracker: StateTransitionTracker for TM health
            cache_ttl_seconds: Cache time-to-live in seconds (default: 10)
        """
        self.logger = setup_pearl_logger(__name__)
        self.activity_service = activity_service
        self.safe_service = safe_service
        self.state_transition_tracker = state_transition_tracker
        self.cache_ttl_seconds = cache_ttl_seconds
        
        # Cache for performance
        self._cache: Dict[str, Any] = {}
        self._cache_timestamp: Optional[float] = None
        
        self.logger.info(
            f"HealthCheckService initialized cache_ttl={cache_ttl_seconds}s"
        )

    def get_complete_health_status(self) -> Dict[str, Any]:
        """Get complete health status with caching for performance.
        
        Returns:
            Dict containing all Pearl-required health fields
        """
        with log_span(self.logger, "health_check_service.get_complete_health_status"):
            # Check cache first
            if self._is_cache_valid():
                self.logger.debug("Returning cached health status")
                return self._cache.copy()
            
            # Generate fresh health status
            health_status = self._generate_health_status()
            
            # Update cache
            self._cache = health_status.copy()
            self._cache_timestamp = time.time()
            
            self.logger.debug("Generated fresh health status")
            return health_status

    def _is_cache_valid(self) -> bool:
        """Check if cached data is still valid.
        
        Returns:
            True if cache is valid, False otherwise
        """
        if self._cache_timestamp is None:
            return False
        
        cache_age = time.time() - self._cache_timestamp
        return cache_age < self.cache_ttl_seconds

    def _generate_health_status(self) -> Dict[str, Any]:
        """Generate complete health status information.
        
        Returns:
            Dict with all required Pearl health fields
        """
        try:
            # Get basic state transition info (existing fields)
            basic_status = self._get_basic_status()
            
            # Get new required fields
            tm_health = self._get_tm_health()
            agent_health = self._get_agent_health()
            rounds_info = self._get_rounds_info()
            
            # Combine all status information
            complete_status = {
                **basic_status,
                "is_tm_healthy": tm_health,
                "agent_health": agent_health,
                "rounds": rounds_info["rounds"],
                "rounds_info": rounds_info["rounds_info"],
            }
            
            return complete_status
            
        except Exception as e:
            self.logger.error(f"Error generating health status: {e}")
            return self._get_safe_defaults()

    def _get_basic_status(self) -> Dict[str, Any]:
        """Get basic status fields (existing functionality).
        
        Returns:
            Dict with seconds_since_last_transition, is_transitioning_fast, etc.
        """
        try:
            if not self.state_transition_tracker:
                return self._get_basic_defaults()
            
            # Get state transition information
            if hasattr(self.state_transition_tracker.seconds_since_last_transition, "__call__"):
                # It's mocked as a method
                seconds_since_last_transition = self.state_transition_tracker.seconds_since_last_transition()
            else:
                # It's a property
                seconds_since_last_transition = self.state_transition_tracker.seconds_since_last_transition

            is_transitioning_fast = self.state_transition_tracker.is_transitioning_fast()

            # Handle case where no transitions have occurred (infinity)
            if seconds_since_last_transition == float("inf"):
                seconds_since_last_transition = -1  # Use -1 to indicate no transitions

            # Build response with required fields
            response = {
                "seconds_since_last_transition": seconds_since_last_transition,
                "is_transitioning_fast": is_transitioning_fast,
            }

            # Add optional fields based on configuration
            if hasattr(self.state_transition_tracker, "fast_transition_window"):
                response["period"] = self.state_transition_tracker.fast_transition_window
            else:
                response["period"] = 5  # Default value

            if hasattr(self.state_transition_tracker, "fast_transition_threshold"):
                response["reset_pause_duration"] = self.state_transition_tracker.fast_transition_threshold
            else:
                response["reset_pause_duration"] = 0.5  # Default value

            return response
            
        except Exception as e:
            self.logger.error(f"Error getting basic status: {e}")
            return self._get_basic_defaults()

    def _get_basic_defaults(self) -> Dict[str, Any]:
        """Get safe defaults for basic status fields.
        
        Returns:
            Dict with safe default values
        """
        return {
            "seconds_since_last_transition": -1,
            "is_transitioning_fast": False,
            "period": 5,
            "reset_pause_duration": 0.5,
        }

    def _get_tm_health(self) -> bool:
        """Get transaction manager health status.
        
        Returns:
            True if transaction manager is healthy, False otherwise
        """
        try:
            if not self.state_transition_tracker:
                return False
            
            # Consider TM healthy if we have recent transitions and not in error state
            seconds_since = self.state_transition_tracker.seconds_since_last_transition
            if hasattr(seconds_since, "__call__"):
                seconds_since = seconds_since()
            
            # TM is healthy if:
            # 1. We have recorded transitions (not infinity)
            # 2. Last transition was within reasonable time (5 minutes)
            # 3. Not transitioning too fast (indicates stability)
            if seconds_since == float("inf"):
                return False
            
            is_recent = seconds_since < 300  # 5 minutes
            is_stable = not self.state_transition_tracker.is_transitioning_fast()
            
            return is_recent and is_stable
            
        except Exception as e:
            self.logger.error(f"Error checking TM health: {e}")
            return False

    def _get_agent_health(self) -> Dict[str, bool]:
        """Get agent health object with required fields.
        
        Returns:
            Dict with is_making_on_chain_transactions, is_staking_kpi_met, has_required_funds
        """
        try:
            # Check if making on-chain transactions
            is_making_transactions = self._check_on_chain_transactions()
            
            # Check if staking KPI is met
            is_staking_kpi_met = self._check_staking_kpi()
            
            # Check if has required funds
            has_required_funds = self._check_required_funds()
            
            return {
                "is_making_on_chain_transactions": is_making_transactions,
                "is_staking_kpi_met": is_staking_kpi_met,
                "has_required_funds": has_required_funds,
            }
            
        except Exception as e:
            self.logger.error(f"Error getting agent health: {e}")
            return {
                "is_making_on_chain_transactions": False,
                "is_staking_kpi_met": False,
                "has_required_funds": False,
            }

    def _check_on_chain_transactions(self) -> bool:
        """Check if agent is making on-chain transactions.
        
        Returns:
            True if agent has made recent transactions, False otherwise
        """
        try:
            if not self.activity_service:
                return False
            
            # Check if we have recent activity (within last 24 hours)
            activity_status = self.activity_service.get_activity_status()
            
            # If we have activity today or yesterday, consider it active
            if activity_status.get("last_activity_date"):
                return not activity_status.get("daily_activity_needed", True)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking on-chain transactions: {e}")
            return False

    def _check_staking_kpi(self) -> bool:
        """Check if staking KPI requirements are met.
        
        Returns:
            True if staking KPIs are met, False otherwise
        """
        try:
            if not self.activity_service:
                return False
            
            # Use ActivityService to check if daily activity is needed
            # If daily activity is NOT needed, then KPI is met
            return not self.activity_service.is_daily_activity_needed()
            
        except Exception as e:
            self.logger.error(f"Error checking staking KPI: {e}")
            return False

    def _check_required_funds(self) -> bool:
        """Check if agent has sufficient funds.
        
        Returns:
            True if agent has sufficient funds, False otherwise
        """
        try:
            if not self.safe_service:
                return False
            
            # Use SafeService to check minimum balances
            # This will be implemented in Feature 2
            if hasattr(self.safe_service, 'has_sufficient_funds'):
                return self.safe_service.has_sufficient_funds()
            
            # Fallback: assume we have funds if we can't check
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking required funds: {e}")
            return False

    def _get_rounds_info(self) -> Dict[str, Any]:
        """Get consensus rounds information.
        
        Returns:
            Dict with rounds array and rounds_info object
        """
        try:
            if not self.state_transition_tracker:
                return {"rounds": [], "rounds_info": {}}
            
            # Get recent transitions as "rounds"
            rounds = self._build_rounds_from_transitions()
            
            # Build rounds metadata
            rounds_info = self._build_rounds_metadata(rounds)
            
            return {
                "rounds": rounds,
                "rounds_info": rounds_info,
            }
            
        except Exception as e:
            self.logger.error(f"Error getting rounds info: {e}")
            return {"rounds": [], "rounds_info": {}}

    def _build_rounds_from_transitions(self) -> List[Dict[str, Any]]:
        """Build rounds array from recent state transitions.
        
        Returns:
            List of round objects based on state transitions
        """
        try:
            if not hasattr(self.state_transition_tracker, 'transition_history'):
                return []
            
            # Get recent transitions (last 10)
            recent_transitions = self.state_transition_tracker.transition_history[-10:]
            
            rounds = []
            for i, transition in enumerate(recent_transitions):
                round_data = {
                    "round_id": i + 1,
                    "from_state": transition.from_state.value,
                    "to_state": transition.to_state.value,
                    "timestamp": transition.timestamp.isoformat(),
                    "metadata": transition.metadata,
                }
                rounds.append(round_data)
            
            return rounds
            
        except Exception as e:
            self.logger.error(f"Error building rounds from transitions: {e}")
            return []

    def _build_rounds_metadata(self, rounds: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build rounds metadata object.
        
        Args:
            rounds: List of round objects
            
        Returns:
            Dict with rounds metadata
        """
        try:
            if not rounds:
                return {
                    "total_rounds": 0,
                    "latest_round": None,
                    "average_round_duration": 0,
                }
            
            # Calculate metadata
            total_rounds = len(rounds)
            latest_round = rounds[-1] if rounds else None
            
            # Calculate average duration between rounds
            average_duration = 0
            if len(rounds) > 1:
                durations = []
                for i in range(1, len(rounds)):
                    prev_time = datetime.fromisoformat(rounds[i-1]["timestamp"])
                    curr_time = datetime.fromisoformat(rounds[i]["timestamp"])
                    duration = (curr_time - prev_time).total_seconds()
                    durations.append(duration)
                
                if durations:
                    average_duration = sum(durations) / len(durations)
            
            return {
                "total_rounds": total_rounds,
                "latest_round": latest_round,
                "average_round_duration": average_duration,
            }
            
        except Exception as e:
            self.logger.error(f"Error building rounds metadata: {e}")
            return {
                "total_rounds": 0,
                "latest_round": None,
                "average_round_duration": 0,
            }

    def _get_safe_defaults(self) -> Dict[str, Any]:
        """Get safe default values for all health fields.
        
        Returns:
            Dict with safe default values for error cases
        """
        return {
            "seconds_since_last_transition": -1,
            "is_transitioning_fast": False,
            "period": 5,
            "reset_pause_duration": 0.5,
            "is_tm_healthy": False,
            "agent_health": {
                "is_making_on_chain_transactions": False,
                "is_staking_kpi_met": False,
                "has_required_funds": False,
            },
            "rounds": [],
            "rounds_info": {
                "total_rounds": 0,
                "latest_round": None,
                "average_round_duration": 0,
            },
        }