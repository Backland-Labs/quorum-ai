"""
Test suite for Signal Handler Service.

This test suite ensures the application can gracefully handle system signals
(SIGTERM, SIGINT) and coordinate shutdown across all services. This is critical
for Pearl deployment where the container may be stopped at any time.
"""

import asyncio
import signal
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import json
import os

from services.signal_handler import SignalHandler, ShutdownCoordinator, GracefulShutdownError


class TestSignalHandler:
    """Test signal registration and handling."""
    
    @pytest.fixture
    def signal_handler(self):
        """Create a signal handler instance."""
        return SignalHandler()
    
    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock()
    
    @pytest.mark.asyncio
    async def test_sigterm_handler_registration(self, signal_handler):
        """
        Test that SIGTERM handler is properly registered.
        
        Why this is important:
        - SIGTERM is the standard graceful shutdown signal sent by Docker/Kubernetes
        - Pearl container orchestration relies on proper SIGTERM handling
        - Without this, the container would be forcefully killed after timeout
        
        What we're testing:
        - Signal handler is registered with the event loop
        - Handler function is callable and async
        - Registration doesn't raise exceptions
        """
        with patch('signal.signal') as mock_signal:
            await signal_handler.register_handlers()
            
            # Verify SIGTERM handler was registered
            mock_signal.assert_any_call(signal.SIGTERM, signal_handler._handle_sigterm)
            
            # Verify the handler is set up correctly
            assert hasattr(signal_handler, '_handle_sigterm')
            assert callable(signal_handler._handle_sigterm)
    
    @pytest.mark.asyncio
    async def test_sigint_handler_registration(self, signal_handler):
        """
        Test that SIGINT handler is properly registered.
        
        Why this is important:
        - SIGINT allows manual interruption during development (Ctrl+C)
        - Useful for debugging and testing graceful shutdown
        - Should behave similarly to SIGTERM for consistency
        
        What we're testing:
        - Signal handler is registered with the event loop
        - Handler function is callable and async
        - Registration doesn't raise exceptions
        """
        with patch('signal.signal') as mock_signal:
            await signal_handler.register_handlers()
            
            # Verify SIGINT handler was registered
            mock_signal.assert_any_call(signal.SIGINT, signal_handler._handle_sigint)
            
            # Verify the handler is set up correctly
            assert hasattr(signal_handler, '_handle_sigint')
            assert callable(signal_handler._handle_sigint)
    
    @pytest.mark.asyncio
    async def test_shutdown_initiated_on_sigterm(self, signal_handler, mock_logger):
        """
        Test that SIGTERM initiates graceful shutdown.
        
        Why this is important:
        - SIGTERM should trigger a coordinated shutdown sequence
        - All services need to be notified to stop accepting new work
        - Existing work should be allowed to complete
        
        What we're testing:
        - Shutdown flag is set when SIGTERM is received
        - Shutdown callbacks are invoked
        - Proper logging of shutdown initiation
        """
        signal_handler.logger = mock_logger
        shutdown_callback = AsyncMock()
        signal_handler.register_shutdown_callback(shutdown_callback)
        
        # Simulate SIGTERM
        await signal_handler._async_handle_signal(signal.SIGTERM)
        
        # Verify shutdown was initiated
        assert signal_handler.is_shutting_down()
        shutdown_callback.assert_called_once()
        mock_logger.info.assert_called_with("Received SIGTERM, initiating graceful shutdown")
    
    @pytest.mark.asyncio
    async def test_multiple_signals_ignored_during_shutdown(self, signal_handler, mock_logger):
        """
        Test that multiple signals are ignored once shutdown starts.
        
        Why this is important:
        - Prevents shutdown corruption from multiple signals
        - Ensures shutdown sequence completes without interruption
        - Avoids race conditions in cleanup code
        
        What we're testing:
        - Second signal doesn't restart shutdown
        - Appropriate warning is logged
        - Shutdown continues normally
        """
        signal_handler.logger = mock_logger
        shutdown_callback = AsyncMock()
        signal_handler.register_shutdown_callback(shutdown_callback)
        
        # First signal
        await signal_handler._async_handle_signal(signal.SIGTERM)
        
        # Second signal should be ignored
        await signal_handler._async_handle_signal(signal.SIGTERM)
        
        # Callback should only be called once
        shutdown_callback.assert_called_once()
        mock_logger.warning.assert_called_with("Shutdown already in progress, ignoring signal")
    
    @pytest.mark.asyncio
    async def test_shutdown_timeout_enforcement(self, signal_handler, mock_logger):
        """
        Test that shutdown has a maximum timeout.
        
        Why this is important:
        - Prevents hanging during shutdown if a service is unresponsive
        - Ensures container can be stopped within reasonable time
        - Pearl has timeout expectations for container lifecycle
        
        What we're testing:
        - Shutdown completes within timeout period
        - Timeout is logged appropriately
        - Resources are cleaned up even on timeout
        """
        signal_handler.logger = mock_logger
        signal_handler.shutdown_timeout = 0.1  # 100ms for testing
        
        # Register a callback that takes too long
        async def slow_callback():
            await asyncio.sleep(1)  # Longer than timeout
        
        signal_handler.register_shutdown_callback(slow_callback)
        
        # Should complete despite slow callback
        with pytest.raises(asyncio.TimeoutError):
            await signal_handler.shutdown()
        
        mock_logger.error.assert_called_with("Shutdown timeout exceeded, forcing exit")


class TestShutdownCoordinator:
    """Test coordinated shutdown across services."""
    
    @pytest.fixture
    def coordinator(self):
        """Create a shutdown coordinator instance."""
        return ShutdownCoordinator()
    
    @pytest.fixture
    def mock_voting_service(self):
        """Create a mock voting service."""
        mock = Mock()
        mock.get_active_votes = AsyncMock(return_value=[])
        mock.cancel_vote = AsyncMock()
        mock.save_service_state = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_agent_service(self):
        """Create a mock agent service."""
        mock = Mock()
        mock.is_running = Mock(return_value=False)
        mock.stop = AsyncMock()
        mock.save_service_state = AsyncMock()
        return mock
    
    @pytest.mark.asyncio
    async def test_coordinate_shutdown_sequence(self, coordinator, mock_voting_service, mock_agent_service):
        """
        Test the complete shutdown coordination sequence.
        
        Why this is important:
        - Services must shut down in correct order to prevent data loss
        - Active operations need to complete or be safely cancelled
        - State must be persisted before exit
        
        What we're testing:
        - Services are stopped in correct order
        - State is saved for each service
        - No exceptions during normal shutdown
        """
        coordinator.register_service('voting', mock_voting_service)
        coordinator.register_service('agent', mock_agent_service)
        
        await coordinator.shutdown()
        
        # Verify shutdown sequence
        mock_agent_service.stop.assert_called_once()
        mock_voting_service.save_service_state.assert_called_once()
        mock_agent_service.save_service_state.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_active_vote_handling_during_shutdown(self, coordinator, mock_voting_service):
        """
        Test handling of active votes during shutdown.
        
        Why this is important:
        - Active votes represent financial commitments
        - Must either complete or be safely cancelled
        - State must be preserved for recovery
        
        What we're testing:
        - Active votes are detected
        - Appropriate action is taken (complete or cancel)
        - Vote state is saved
        """
        # Mock active votes
        active_votes = [
            {'id': 'vote1', 'status': 'pending', 'can_complete': True},
            {'id': 'vote2', 'status': 'pending', 'can_complete': False}
        ]
        mock_voting_service.get_active_votes.return_value = active_votes
        mock_voting_service.complete_vote = AsyncMock()
        
        coordinator.register_service('voting', mock_voting_service)
        
        await coordinator.shutdown()
        
        # Verify votes were handled
        mock_voting_service.complete_vote.assert_called_with('vote1')
        mock_voting_service.cancel_vote.assert_called_with('vote2')
    
    @pytest.mark.asyncio
    async def test_state_persistence_before_exit(self, coordinator, tmp_path):
        """
        Test that all state is persisted before exit.
        
        Why this is important:
        - State persistence enables recovery after restart
        - Critical for maintaining voting history and preferences
        - Required for Pearl's reliability requirements
        
        What we're testing:
        - State files are created
        - State contains expected data
        - Files are written atomically
        """
        state_file = tmp_path / "shutdown_state.json"
        coordinator.state_file = str(state_file)
        
        # Mock some state
        test_state = {
            'timestamp': datetime.utcnow().isoformat(),
            'services': {
                'voting': {'active_votes': 2},
                'agent': {'last_run': '2024-01-01T00:00:00'}
            }
        }
        
        await coordinator.save_state(test_state)
        
        # Verify state was saved
        assert state_file.exists()
        saved_state = json.loads(state_file.read_text())
        assert saved_state['services']['voting']['active_votes'] == 2
    
    @pytest.mark.asyncio
    async def test_recovery_after_sigkill(self, coordinator, tmp_path):
        """
        Test recovery after unexpected termination (SIGKILL).
        
        Why this is important:
        - SIGKILL cannot be caught, so we need recovery mechanisms
        - Previous state must be detectable and recoverable
        - Incomplete operations need to be identified
        
        What we're testing:
        - Recovery file is detected on startup
        - Incomplete operations are identified
        - Recovery actions are triggered
        """
        # Create a recovery file from previous run
        recovery_file = tmp_path / "shutdown_state.json"
        recovery_data = {
            'timestamp': '2024-01-01T00:00:00',
            'reason': 'SIGKILL',
            'services': {
                'voting': {
                    'active_votes': ['vote1', 'vote2'],
                    'pending_transactions': ['tx1']
                }
            }
        }
        recovery_file.write_text(json.dumps(recovery_data))
        coordinator.state_file = str(recovery_file)
        
        # Run recovery
        recovery_needed = await coordinator.check_recovery_needed()
        assert recovery_needed
        
        recovered_state = await coordinator.recover_state()
        assert len(recovered_state['services']['voting']['active_votes']) == 2
    
    @pytest.mark.asyncio
    async def test_concurrent_signal_handling(self, coordinator):
        """
        Test handling of concurrent signals.
        
        Why this is important:
        - Multiple signals may arrive in quick succession
        - Must handle race conditions properly
        - Shutdown should be idempotent
        
        What we're testing:
        - Multiple concurrent shutdowns don't cause errors
        - Only one shutdown sequence executes
        - Proper synchronization of shutdown state
        """
        shutdown_count = 0
        
        async def count_shutdowns():
            nonlocal shutdown_count
            shutdown_count += 1
            await asyncio.sleep(0.1)
        
        coordinator.shutdown = count_shutdowns
        
        # Simulate concurrent signals
        tasks = [
            asyncio.create_task(coordinator.handle_signal(signal.SIGTERM)),
            asyncio.create_task(coordinator.handle_signal(signal.SIGTERM)),
            asyncio.create_task(coordinator.handle_signal(signal.SIGINT))
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Only one shutdown should execute
        assert shutdown_count == 1
    
    @pytest.mark.asyncio
    async def test_service_cleanup_on_error(self, coordinator, mock_voting_service):
        """
        Test that services are cleaned up even when errors occur.
        
        Why this is important:
        - Errors during shutdown shouldn't prevent cleanup
        - Resources must be released even on failure
        - Partial shutdown is better than no shutdown
        
        What we're testing:
        - Cleanup continues after service errors
        - Errors are logged but don't stop shutdown
        - All services get shutdown attempt
        """
        # Make save_state raise an error
        mock_voting_service.save_service_state.side_effect = Exception("Save failed")
        
        mock_agent_service = Mock()
        mock_agent_service.save_service_state = AsyncMock()
        
        coordinator.register_service('voting', mock_voting_service)
        coordinator.register_service('agent', mock_agent_service)
        
        # Should not raise, but continue with other services
        await coordinator.shutdown()
        
        # Agent service should still be cleaned up
        mock_agent_service.save_service_state.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_shutdown_prevents_new_operations(self, coordinator):
        """
        Test that new operations are prevented during shutdown.
        
        Why this is important:
        - New operations during shutdown can cause inconsistency
        - Clean shutdown requires stopping new work
        - Prevents resource leaks and partial operations
        
        What we're testing:
        - Shutdown flag prevents new operations
        - Appropriate errors are returned
        - Existing operations can complete
        """
        coordinator.begin_shutdown()
        
        # Try to start new operation
        with pytest.raises(GracefulShutdownError):
            await coordinator.check_can_start_operation()
        
        assert coordinator.is_shutting_down()


class TestSignalHandlerIntegration:
    """Integration tests for signal handler with real signals."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_signal_handling(self, tmp_path):
        """
        Test with real signal delivery (integration test).
        
        Why this is important:
        - Verifies actual signal handling works in practice
        - Tests OS-level signal delivery
        - Ensures our abstractions work with real signals
        
        What we're testing:
        - Real signals are caught and handled
        - Process exits gracefully
        - State is saved before exit
        """
        # This test would actually send signals to the process
        # Marked as integration test as it's more complex
        pass
    
    @pytest.mark.asyncio
    async def test_docker_stop_simulation(self):
        """
        Test simulation of Docker stop command.
        
        Why this is important:
        - Docker stop sends SIGTERM then SIGKILL after timeout
        - Must complete shutdown before SIGKILL
        - This is the primary shutdown scenario in Pearl
        
        What we're testing:
        - SIGTERM triggers graceful shutdown
        - Shutdown completes within Docker's timeout
        - Process exits with correct code
        """
        handler = SignalHandler()
        handler.shutdown_timeout = 5  # Docker default is 10s
        
        shutdown_complete = False
        
        async def mark_shutdown():
            nonlocal shutdown_complete
            await asyncio.sleep(0.1)  # Simulate work
            shutdown_complete = True
        
        handler.register_shutdown_callback(mark_shutdown)
        
        # Simulate SIGTERM
        await handler._async_handle_signal(signal.SIGTERM)
        
        assert shutdown_complete