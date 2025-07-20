"""
Signal Handler Service for graceful shutdown.

This service manages system signals (SIGTERM, SIGINT) and coordinates
graceful shutdown across all application services. Critical for Pearl
deployment where containers need to handle lifecycle events properly.

Key features:
- Handles SIGTERM/SIGINT signals for graceful shutdown
- Coordinates shutdown across multiple services
- Saves state before exit for recovery
- Prevents new operations during shutdown
- Supports recovery from SIGKILL
"""

import asyncio
import signal
import json
import os
from datetime import datetime
from typing import Dict, List, Callable, Any, Optional, TypeVar, Protocol
from pathlib import Path
import logging
from logging_config import setup_pearl_logger, log_span

# Type definitions
T = TypeVar('T')
ShutdownCallback = Callable[[], Any]


class ShutdownManagedService(Protocol):
    """Protocol for services that can be managed during shutdown."""
    
    async def save_service_state(self) -> None:
        """Save service state before shutdown."""
        ...
    
    async def stop(self) -> None:
        """Stop the service gracefully."""
        ...


class VotingServiceProtocol(ShutdownManagedService, Protocol):
    """Protocol for voting service with additional methods."""
    
    async def get_active_votes(self) -> List[Dict[str, Any]]:
        """Get list of active votes."""
        ...
    
    async def complete_vote(self, vote_id: str) -> None:
        """Complete a vote."""
        ...
    
    async def cancel_vote(self, vote_id: str) -> None:
        """Cancel a vote."""
        ...


class GracefulShutdownError(Exception):
    """Raised when operations are attempted during shutdown."""
    pass


class SignalHandler:
    """Handles system signals and initiates graceful shutdown."""
    
    def __init__(self, shutdown_timeout: float = 30.0):
        """
        Initialize signal handler.
        
        Args:
            shutdown_timeout: Maximum time to wait for graceful shutdown
        """
        self.logger = setup_pearl_logger()
        self.shutdown_timeout = shutdown_timeout
        self._shutting_down = False
        self._shutdown_callbacks: List[Callable] = []
        self._shutdown_event = asyncio.Event()
        self._original_handlers = {}
    
    async def register_handlers(self) -> None:
        """Register signal handlers for SIGTERM and SIGINT."""
        # Store original handlers for restoration if needed
        self._original_handlers[signal.SIGTERM] = signal.signal(
            signal.SIGTERM, self._handle_sigterm
        )
        self._original_handlers[signal.SIGINT] = signal.signal(
            signal.SIGINT, self._handle_sigint
        )
        
        self.logger.info("Signal handlers registered for SIGTERM and SIGINT")
    
    def _handle_sigterm(self, signum: int, frame: Any) -> None:
        """Handle SIGTERM signal."""
        self._schedule_async_handler(signal.SIGTERM)
    
    def _handle_sigint(self, signum: int, frame: Any) -> None:
        """Handle SIGINT signal."""
        self._schedule_async_handler(signal.SIGINT)
    
    def _schedule_async_handler(self, signum: int) -> None:
        """Schedule async signal handler in the event loop."""
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(self._async_handle_signal(signum))
        except RuntimeError:
            # No running loop, create one
            asyncio.run(self._async_handle_signal(signum))
    
    async def _async_handle_signal(self, signum: int) -> None:
        """Async handler for signals."""
        signal_name = signal.Signals(signum).name
        
        if self._shutting_down:
            self.logger.warning("Shutdown already in progress, ignoring signal")
            return
        
        self._shutting_down = True
        self._shutdown_event.set()
        
        self.logger.info(f"Received {signal_name}, initiating graceful shutdown")
        
        # Execute shutdown callbacks
        for callback in self._shutdown_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                self.logger.error(f"Error in shutdown callback: {e}")
    
    
    def register_shutdown_callback(self, callback: Callable) -> None:
        """Register a callback to be called during shutdown."""
        self._shutdown_callbacks.append(callback)
    
    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress."""
        return self._shutting_down
    
    async def shutdown(self) -> None:
        """Execute graceful shutdown with timeout."""
        try:
            await asyncio.wait_for(
                self._execute_shutdown(),
                timeout=self.shutdown_timeout
            )
        except asyncio.TimeoutError:
            self.logger.error("Shutdown timeout exceeded, forcing exit")
            raise
    
    async def _execute_shutdown(self) -> None:
        """Execute the actual shutdown sequence."""
        # Shutdown logic is handled by callbacks
        await self._shutdown_event.wait()


class ShutdownCoordinator:
    """Coordinates shutdown across multiple services."""
    
    def __init__(self, state_file: str = "shutdown_state.json"):
        """
        Initialize shutdown coordinator.
        
        Args:
            state_file: Path to save shutdown state
        """
        self.logger = setup_pearl_logger()
        self.state_file = state_file
        self._services: Dict[str, Any] = {}
        self._shutting_down = False
        self._shutdown_lock = asyncio.Lock()
    
    def register_service(self, name: str, service: Any) -> None:
        """Register a service for coordinated shutdown."""
        self._services[name] = service
        self.logger.info(f"Registered service '{name}' for shutdown coordination")
    
    async def shutdown(self) -> None:
        """Coordinate shutdown across all registered services."""
        async with self._shutdown_lock:
            if self._shutting_down:
                return
            self._shutting_down = True
        
        with log_span(self.logger, "coordinated_shutdown"):
            self.logger.info("Starting coordinated shutdown")
            
            # Stop agent service first to prevent new operations
            await self._stop_agent_service()
            
            # Handle active votes
            await self._handle_active_votes()
            
            # Save state for all services
            await self._save_all_service_states()
    
    async def _stop_agent_service(self) -> None:
        """Stop the agent service if registered."""
        if 'agent' not in self._services:
            return
            
        agent = self._services['agent']
        if not hasattr(agent, 'stop'):
            return
            
        try:
            with log_span(self.logger, "agent_service_stop"):
                await agent.stop()
                self.logger.info("Agent service stopped")
        except Exception as e:
            self.logger.error(f"Error stopping agent service: {e}")
    
    async def _handle_active_votes(self) -> None:
        """Handle any active votes during shutdown."""
        if 'voting' not in self._services:
            return
            
        voting = self._services['voting']
        if not hasattr(voting, 'get_active_votes'):
            return
            
        try:
            with log_span(self.logger, "handle_active_votes"):
                active_votes = await voting.get_active_votes()
                for vote in active_votes:
                    if vote.get('can_complete'):
                        await voting.complete_vote(vote['id'])
                        self.logger.info(f"Completed vote {vote['id']}")
                    else:
                        await voting.cancel_vote(vote['id'])
                        self.logger.info(f"Cancelled vote {vote['id']}")
        except Exception as e:
            self.logger.error(f"Error handling active votes: {e}")
    
    async def _save_all_service_states(self) -> None:
        """Save state for all registered services."""
        state_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'reason': 'graceful_shutdown',
            'services': {}
        }
        
        with log_span(self.logger, "save_service_states"):
            for name, service in self._services.items():
                if hasattr(service, 'save_service_state'):
                    try:
                        await service.save_service_state()
                        self.logger.info(f"Saved state for service '{name}'")
                    except Exception as e:
                        self.logger.error(f"Error saving state for service '{name}': {e}")
            
            # Save coordinator state
            await self.save_state(state_data)
    
    async def save_state(self, state: Dict[str, Any]) -> None:
        """Save shutdown state to file."""
        try:
            # Atomic write using temporary file
            temp_file = f"{self.state_file}.tmp"
            with open(temp_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            # Atomic rename
            os.replace(temp_file, self.state_file)
            self.logger.info(f"Saved shutdown state to {self.state_file}")
        except Exception as e:
            self.logger.error(f"Failed to save shutdown state: {e}")
            raise
    
    async def check_recovery_needed(self) -> bool:
        """Check if recovery is needed from previous run."""
        if not os.path.exists(self.state_file):
            return False
        
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            # Check if this was an unexpected shutdown
            if state.get('reason') == 'SIGKILL':
                self.logger.warning("Detected previous SIGKILL, recovery needed")
                return True
            
            # Check timestamp to see if state is recent
            timestamp = datetime.fromisoformat(state['timestamp'])
            age = datetime.utcnow() - timestamp
            if age.total_seconds() < 300:  # Less than 5 minutes old
                self.logger.info("Found recent shutdown state, checking for recovery")
                return True
                
        except Exception as e:
            self.logger.error(f"Error checking recovery state: {e}")
        
        return False
    
    async def recover_state(self) -> Dict[str, Any]:
        """Recover state from previous run."""
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            self.logger.info(f"Recovering state from {state['timestamp']}")
            return state
        except Exception as e:
            self.logger.error(f"Failed to recover state: {e}")
            raise
    
    def begin_shutdown(self) -> None:
        """Mark the beginning of shutdown."""
        self._shutting_down = True
    
    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress."""
        return self._shutting_down
    
    async def check_can_start_operation(self) -> None:
        """Check if new operations can be started."""
        if self._shutting_down:
            raise GracefulShutdownError("Cannot start new operations during shutdown")
    
    async def handle_signal(self, signum: int) -> None:
        """Handle a signal by initiating shutdown."""
        async with self._shutdown_lock:
            if self._shutting_down:
                return
            self._shutting_down = True
        
        await self.shutdown()


# Global instance for application-wide signal handling
_signal_handler: Optional[SignalHandler] = None
_shutdown_coordinator: Optional[ShutdownCoordinator] = None


def get_signal_handler() -> SignalHandler:
    """Get or create the global signal handler."""
    global _signal_handler
    if _signal_handler is None:
        _signal_handler = SignalHandler()
    return _signal_handler


def get_shutdown_coordinator() -> ShutdownCoordinator:
    """Get or create the global shutdown coordinator."""
    global _shutdown_coordinator
    if _shutdown_coordinator is None:
        _shutdown_coordinator = ShutdownCoordinator()
    return _shutdown_coordinator


async def setup_signal_handling(
    voting_service: Any = None,
    agent_service: Any = None
) -> None:
    """
    Set up signal handling for the application.
    
    Args:
        voting_service: The voting service instance
        agent_service: The agent service instance
    """
    handler = get_signal_handler()
    coordinator = get_shutdown_coordinator()
    
    # Register services
    if voting_service:
        coordinator.register_service('voting', voting_service)
    if agent_service:
        coordinator.register_service('agent', agent_service)
    
    # Set up shutdown callback
    handler.register_shutdown_callback(coordinator.shutdown)
    
    # Register signal handlers
    await handler.register_handlers()
    
    # Check for recovery
    if await coordinator.check_recovery_needed():
        try:
            state = await coordinator.recover_state()
            logger = setup_pearl_logger()
            logger.info(f"Recovered state from previous run: {state['timestamp']}")
            # Recovery logic would be implemented by services
        except Exception as e:
            logger = setup_pearl_logger()
            logger.error(f"Failed to recover state: {e}")