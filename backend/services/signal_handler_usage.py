"""
Example usage of the Signal Handler Service.

This module demonstrates how to integrate the signal handler
into your application for graceful shutdown.
"""

import asyncio
import signal
from services.signal_handler import (
    setup_signal_handling,
    get_signal_handler,
    get_shutdown_coordinator
)
# Import these from your actual services
# from services.voting_service import VotingService
# from services.agent_run_service import AgentRunService


async def main():
    """Example application with signal handling."""
    # Initialize services (replace with actual service instances)
    voting_service = None  # VotingService()
    agent_service = None   # AgentRunService()
    
    # Set up signal handling
    await setup_signal_handling(
        voting_service=voting_service,
        agent_service=agent_service
    )
    
    # Your application logic here
    try:
        while True:
            # Check if shutdown is requested
            coordinator = get_shutdown_coordinator()
            if coordinator.is_shutting_down():
                print("Shutdown requested, exiting main loop")
                break
                
            # Do work
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        # Will be handled by signal handler
        pass


# For FastAPI integration
async def lifespan(app):
    """FastAPI lifespan context manager."""
    # Startup
    voting_service = None  # VotingService()
    agent_service = None   # AgentRunService()
    
    await setup_signal_handling(
        voting_service=voting_service,
        agent_service=agent_service
    )
    
    yield
    
    # Shutdown - signal handler will coordinate


# For manual shutdown trigger
async def trigger_shutdown():
    """Manually trigger graceful shutdown."""
    handler = get_signal_handler()
    await handler._async_handle_signal(signal.SIGTERM)


if __name__ == "__main__":
    asyncio.run(main())