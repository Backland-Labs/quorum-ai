"""
Service for tracking agent performance metrics for Pearl v1 compliance.

This module manages the agent_performance.json file that provides observability
data to the Pearl platform. The file contains performance metrics and current
agent behavior descriptions.

File Schema:
{
  "timestamp": 1733400000,  # UTC seconds
  "metrics": [
    {
      "name": "Total Attestations",
      "is_primary": true,
      "description": "EAS attestations created on <b>Base</b> network",
      "value": "42"
    },
    {
      "name": "Proposals Analyzed",
      "is_primary": false,
      "description": "DAO proposals analyzed since deployment",
      "value": "100"
    }
  ],
  "agent_behavior": "Monitoring 3 DAOs: compound.eth, nouns.eth, arbitrum.eth"
}

Constraints:
- Max 2 metrics
- Exactly 1 primary metric (is_primary: true)
- Timestamp in UTC seconds
- HTML allowed in descriptions
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PerformanceMetric(BaseModel):
    """Individual performance metric for Pearl v1 compliance."""

    name: str = Field(..., description="Metric name")
    is_primary: bool = Field(default=False, description="Whether this is the primary metric")
    description: Optional[str] = Field(None, description="Tooltip text (HTML allowed)")
    value: str = Field(..., description="Metric value as string")


class AgentPerformance(BaseModel):
    """Agent performance data structure for Pearl v1 compliance."""

    timestamp: Optional[int] = Field(None, description="Last update time (UTC seconds)")
    metrics: List[PerformanceMetric] = Field(
        default_factory=list, description="Performance metrics (max 2)"
    )
    agent_behavior: Optional[str] = Field(
        None, description="Current agent behavior description"
    )


class PerformanceTracker:
    """Manages agent_performance.json file for Pearl v1 compliance.

    This service handles atomic writes and reads of the performance file,
    ensuring data integrity and providing metrics computation utilities.
    """

    # Maximum number of metrics allowed by Pearl v1 spec
    MAX_METRICS = 2

    def __init__(self, file_path: str):
        """Initialize performance tracker.

        Args:
            file_path: Full path to agent_performance.json
        """
        self.file_path = Path(file_path)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Ensure parent directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize file if it doesn't exist
        if not self.file_path.exists():
            self._initialize_file()

    def _initialize_file(self) -> None:
        """Create empty performance file with default structure."""
        initial_data = AgentPerformance(
            timestamp=None,
            metrics=[],
            agent_behavior=None,
        )

        self._write_file(initial_data)
        self.logger.info(f"Initialized performance file at {self.file_path}")

    def _write_file(self, data: AgentPerformance) -> None:
        """Atomic write to performance file.

        Uses temp file and rename for atomicity to prevent
        corrupted reads during concurrent access.

        Args:
            data: AgentPerformance data to write
        """
        json_data = data.model_dump(mode="json")

        # Write to temp file first
        temp_path = self.file_path.with_suffix(".tmp")
        with open(temp_path, "w") as f:
            json.dump(json_data, f, indent=2)

        # Atomic rename
        temp_path.replace(self.file_path)

    def read(self) -> AgentPerformance:
        """Read current performance data.

        Returns:
            AgentPerformance data, or empty instance on error
        """
        try:
            with open(self.file_path, "r") as f:
                data = json.load(f)
            return AgentPerformance.model_validate(data)
        except FileNotFoundError:
            self.logger.warning(f"Performance file not found at {self.file_path}")
            return AgentPerformance()
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse performance file: {e}")
            return AgentPerformance()
        except Exception as e:
            self.logger.error(f"Failed to read performance file: {e}")
            return AgentPerformance()

    def update(
        self,
        metrics: Optional[List[PerformanceMetric]] = None,
        agent_behavior: Optional[str] = None,
    ) -> None:
        """Update performance file.

        Args:
            metrics: List of metrics (max 2, exactly 1 primary required)
            agent_behavior: Current behavior description
        """
        # Read current data
        current = self.read()

        # Update timestamp
        current.timestamp = int(datetime.now(timezone.utc).timestamp())

        # Update metrics if provided
        if metrics is not None:
            if len(metrics) > self.MAX_METRICS:
                self.logger.warning(
                    f"Too many metrics ({len(metrics)}), truncating to {self.MAX_METRICS}"
                )
                metrics = metrics[: self.MAX_METRICS]

            # Validate exactly 1 primary metric
            primary_count = sum(1 for m in metrics if m.is_primary)
            if metrics and primary_count != 1:
                self.logger.warning(
                    f"Expected 1 primary metric, found {primary_count}. "
                    "Setting first metric as primary."
                )
                # Auto-fix: ensure exactly one primary
                for i, m in enumerate(metrics):
                    m.is_primary = i == 0

            current.metrics = metrics

        # Update behavior if provided
        if agent_behavior is not None:
            current.agent_behavior = agent_behavior

        # Write to file
        self._write_file(current)
        self.logger.info(f"Updated performance file: {len(current.metrics)} metrics")

    def compute_current_metrics(
        self,
        attestation_count: Optional[int] = None,
        proposals_analyzed: Optional[int] = None,
        monitored_daos: Optional[List[str]] = None,
    ) -> Tuple[List[PerformanceMetric], str]:
        """Compute current performance metrics from available data.

        Args:
            attestation_count: Total attestations created on-chain
            proposals_analyzed: Total proposals processed since deployment
            monitored_daos: List of DAO space IDs being monitored

        Returns:
            Tuple of (metrics_list, agent_behavior_string)
        """
        metrics = []

        # Primary metric: Total Attestations
        if attestation_count is not None:
            metrics.append(
                PerformanceMetric(
                    name="Total Attestations",
                    is_primary=True,
                    description="EAS attestations created on <b>Base</b> network",
                    value=str(attestation_count),
                )
            )

        # Secondary metric: Proposals Analyzed
        if proposals_analyzed is not None:
            metrics.append(
                PerformanceMetric(
                    name="Proposals Analyzed",
                    is_primary=False,
                    description="DAO proposals analyzed since deployment",
                    value=str(proposals_analyzed),
                )
            )

        # If we have proposals but no attestations, make proposals primary
        if metrics and not any(m.is_primary for m in metrics):
            metrics[0].is_primary = True

        # Ensure only first metric is primary if we have both
        if len(metrics) > 1:
            metrics[0].is_primary = True
            metrics[1].is_primary = False

        # Agent behavior description
        if monitored_daos:
            dao_list = ", ".join(monitored_daos)
            count = len(monitored_daos)
            behavior = f"Monitoring {count} DAO{'s' if count != 1 else ''}: {dao_list}"
        else:
            behavior = "Idle - no DAOs configured"

        return metrics, behavior

    def update_from_run_data(
        self,
        attestation_count: Optional[int] = None,
        proposals_analyzed: Optional[int] = None,
        monitored_daos: Optional[List[str]] = None,
    ) -> None:
        """Convenience method to compute metrics and update file in one call.

        Args:
            attestation_count: Total attestations created on-chain
            proposals_analyzed: Total proposals processed since deployment
            monitored_daos: List of DAO space IDs being monitored
        """
        metrics, behavior = self.compute_current_metrics(
            attestation_count=attestation_count,
            proposals_analyzed=proposals_analyzed,
            monitored_daos=monitored_daos,
        )

        self.update(metrics=metrics, agent_behavior=behavior)
