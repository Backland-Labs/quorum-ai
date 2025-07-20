#!/usr/bin/env python3
"""Test script to verify signal handling integration."""

import asyncio
import signal
import os
import sys
import time

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.signal_handler import SignalHandler, ShutdownCoordinator
from services.state_manager import StateManager
from logging_config import setup_pearl_logger


async def test_signal_handling():
    """Test the signal handling integration."""
    logger = setup_pearl_logger(__name__)
    
    # Initialize components
    state_manager = StateManager()
    signal_handler = SignalHandler()
    shutdown_coordinator = ShutdownCoordinator()
    
    # Mock service that tracks state
    class MockService:
        def __init__(self, name):
            self.name = name
            self.running = True
            
        async def save_state(self):
            logger.info(f"{self.name}: Saving state")
            await asyncio.sleep(0.1)  # Simulate save operation
            
        async def stop(self):
            logger.info(f"{self.name}: Stopping")
            self.running = False
    
    # Create mock services
    mock_agent = MockService("MockAgent")
    mock_voting = MockService("MockVoting")
    
    # Register services
    shutdown_coordinator.register_service('agent', mock_agent)
    shutdown_coordinator.register_service('voting', mock_voting)
    shutdown_coordinator.register_service('state_manager', state_manager)
    
    # Set up shutdown callback
    signal_handler.register_shutdown_callback(shutdown_coordinator.shutdown)
    
    # Register signal handlers
    await signal_handler.register_handlers()
    
    logger.info("Test application started. Send SIGTERM or SIGINT to test graceful shutdown.")
    logger.info(f"Process ID: {os.getpid()}")
    
    # Keep running until shutdown
    try:
        while not signal_handler.is_shutting_down():
            await asyncio.sleep(1)
            logger.info("Application running...")
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received")
    
    logger.info("Test completed - graceful shutdown executed")


if __name__ == "__main__":
    asyncio.run(test_signal_handling())