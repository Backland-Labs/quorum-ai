#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "httpx>=0.27.0",
# ]
# ///
"""Trigger autonomous agent run via /agent-run endpoint every 24 hours."""

import os
import sys
from pathlib import Path
import httpx

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from logging_config import setup_pearl_logger

logger = setup_pearl_logger(__name__)


def main():
    """Trigger agent run for the first monitored DAO."""
    logger.info("Starting agent-run trigger")

    try:
        # Get monitored DAOs from environment
        monitored_daos_env = os.environ.get("MONITORED_DAOS", "")

        # Use defaults if not set
        default_daos = "compound.eth,nouns.eth,arbitrum.eth"
        if not monitored_daos_env.strip():
            monitored_daos_env = default_daos
            logger.info(f"Using default DAOs: {default_daos}")

        # Parse and get first DAO
        dao_list = [dao.strip() for dao in monitored_daos_env.split(",") if dao.strip()]

        if not dao_list:
            logger.error("No monitored DAOs found in MONITORED_DAOS")
            sys.exit(1)

        space_id = dao_list[0]
        logger.info(f" Automatic triggering agent-run for space: {space_id}")

        # Prepare request
        url = "http://localhost:8716/agent-run"
        payload = {
            "space_id": space_id,
            "dry_run": False
        }

        # Make POST request with timeout
        with httpx.Client(timeout=300.0) as client:
            response = client.post(url, json=payload)

            # Check response
            if response.status_code == 200:
                result = response.json()
                logger.info(
                    f"Automatic Triggering agent-run for space: {space_id} completed successfully"
                )
            else:
                logger.error(
                    f"Automatic Triggering agent-run for space: {space_id} failed"
                )
                sys.exit(1)

    except httpx.ConnectError as e:
        logger.error(f"Cannot connect to application at localhost:8716: {e}")
        sys.exit(1)
    except httpx.TimeoutException:
        logger.error("Request timed out after 300 seconds")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Agent-run trigger failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
