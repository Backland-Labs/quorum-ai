"""
Test suite for main.py Pearl logging integration.

This test suite ensures that the main FastAPI application correctly integrates
with Pearl-compliant logging infrastructure. It tests:
1. Application startup/shutdown logging
2. Exception handler logging
3. Endpoint logging with spans
4. Log format compliance
5. Removal of all Logfire dependencies
"""

import asyncio
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

import pytest
from fastapi.testclient import TestClient

# Pearl log format regex for validation
PEARL_LOG_REGEX = re.compile(
    r'^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}\] \[(ERROR|WARN|INFO|DEBUG|TRACE)\] \[agent\] .+$'
)


@pytest.fixture
def mock_services():
    """Mock all service dependencies."""
    with patch('main.AIService') as ai_mock, \
         patch('main.AgentRunService') as agent_mock, \
         patch('main.SafeService') as safe_mock, \
         patch('main.ActivityService') as activity_mock, \
         patch('main.UserPreferencesService') as prefs_mock, \
         patch('main.VotingService') as voting_mock, \
         patch('main.SnapshotService') as snapshot_mock:
        
        # Configure snapshot service mock
        snapshot_instance = MagicMock()
        snapshot_instance.get_proposals = AsyncMock(return_value=[])
        snapshot_instance.get_proposal = AsyncMock(return_value=None)
        snapshot_instance.get_votes = AsyncMock(return_value=[])
        snapshot_mock.return_value = snapshot_instance
        
        # Configure AI service mock
        ai_instance = MagicMock()
        ai_instance.summarize_multiple_proposals = AsyncMock(return_value=[])
        ai_mock.return_value = ai_instance
        
        # Configure agent run service mock
        agent_instance = MagicMock()
        agent_instance.execute_agent_run = AsyncMock(return_value=MagicMock(
            proposals_analyzed=0,
            votes_cast=[],
            execution_time=0.0,
            errors=[]
        ))
        agent_mock.return_value = agent_instance
        
        yield {
            'ai': ai_mock,
            'agent': agent_mock,
            'safe': safe_mock,
            'activity': activity_mock,
            'prefs': prefs_mock,
            'voting': voting_mock,
            'snapshot': snapshot_mock
        }


@pytest.fixture
def temp_log_file():
    """Create a temporary log file for testing."""
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as f:
        log_path = f.name
    yield log_path
    # Cleanup
    if os.path.exists(log_path):
        os.unlink(log_path)


@pytest.fixture
def mock_pearl_logger(temp_log_file):
    """Mock Pearl logger that writes to a temporary file."""
    with patch('main.setup_pearl_logger') as setup_mock:
        logger = MagicMock()
        
        # Create a function that writes to our temp file
        def write_log(level: str, message: str, **kwargs):
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
            formatted_msg = f"[{timestamp}] [{level.upper()}] [agent] {message}"
            
            # Add key-value pairs if provided
            if kwargs:
                pairs = " ".join(f"{k}={v}" for k, v in kwargs.items())
                formatted_msg += f" {pairs}"
            
            with open(temp_log_file, 'a') as f:
                f.write(formatted_msg + "\n")
        
        # Configure logger methods
        logger.info = lambda msg, **kw: write_log('info', msg, **kw)
        logger.error = lambda msg, **kw: write_log('error', msg, **kw)
        logger.debug = lambda msg, **kw: write_log('debug', msg, **kw)
        logger.warning = lambda msg, **kw: write_log('warn', msg, **kw)
        
        setup_mock.return_value = logger
        yield logger, temp_log_file


@pytest.fixture
def mock_log_span():
    """Mock log_span context manager."""
    with patch('main.log_span') as span_mock:
        @contextmanager
        def mock_span(logger_arg, name: str, **kwargs):
            # Log span entry using the provided logger
            context_str = ' '.join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
            start_msg = f"Starting span: {name}"
            if context_str:
                start_msg += f" {context_str}"
            logger_arg.info(start_msg)
            yield {}  # Return empty dict like real log_span
            # Log span exit
            logger_arg.info(f"Completed span: {name}")
        
        span_mock.side_effect = mock_span
        yield span_mock


class TestMainPearlLogging:
    """Test Pearl logging integration in main.py."""
    
    def test_no_logfire_imports(self):
        """
        Test that main.py has no Logfire imports.
        
        This is critical to ensure complete migration to Pearl logging.
        """
        main_path = Path(__file__).parent.parent / "main.py"
        with open(main_path, 'r') as f:
            content = f.read()
        
        # Check for any logfire imports
        assert 'import logfire' not in content, "main.py should not import logfire"
        assert 'from logfire' not in content, "main.py should not import from logfire"
    
    def test_pearl_logger_import(self):
        """
        Test that main.py imports Pearl logging components.
        
        Ensures the correct logging infrastructure is imported.
        """
        main_path = Path(__file__).parent.parent / "main.py"
        with open(main_path, 'r') as f:
            content = f.read()
        
        # Check for Pearl logging imports
        assert 'from logging_config import setup_pearl_logger' in content
        assert 'from logging_config import' in content and 'log_span' in content
    
    @pytest.mark.asyncio
    async def test_application_startup_logging(self, mock_services, temp_log_file, monkeypatch):
        """
        Test that application startup is logged with Pearl format.
        
        This ensures the application lifecycle is properly logged for observability.
        """
        # Configure Pearl logger to write to temp file
        with patch('main.setup_pearl_logger') as setup_mock:
            from logging_config import setup_pearl_logger
            # Create real Pearl logger that writes to temp file
            real_logger = setup_pearl_logger('main', log_file_path=temp_log_file)
            setup_mock.return_value = real_logger
            
            # Import after mocks are set up
            from main import app
            
            # Use TestClient to trigger lifespan
            with TestClient(app) as client:
                pass
            
            # Read the log file
            with open(temp_log_file, 'r') as f:
                logs = f.read()
            
            # Verify startup log exists
            assert "Application started" in logs
            assert "version=0.1.0" in logs
            
            # Verify format compliance
            for line in logs.strip().split('\n'):
                if line:
                    assert PEARL_LOG_REGEX.match(line), f"Log format invalid: {line}"
    
    @pytest.mark.asyncio
    async def test_application_shutdown_logging(self, mock_services, mock_pearl_logger):
        """
        Test that application shutdown is logged with Pearl format.
        
        This ensures graceful shutdown is tracked for debugging.
        """
        logger, log_file = mock_pearl_logger
        
        # Import after mocks are set up
        from main import app
        
        # Use TestClient to trigger lifespan
        with TestClient(app) as client:
            pass  # Context manager exit triggers shutdown
        
        # Read the log file
        with open(log_file, 'r') as f:
            logs = f.read()
        
        # Verify shutdown log exists
        assert "Application shutdown" in logs
        
        # Verify all logs are Pearl compliant
        for line in logs.strip().split('\n'):
            if line:
                assert PEARL_LOG_REGEX.match(line), f"Log format invalid: {line}"
    
    @pytest.mark.asyncio
    async def test_exception_handler_logging(self, mock_services, mock_pearl_logger):
        """
        Test that unhandled exceptions are logged with Pearl format.
        
        This is critical for debugging production issues.
        """
        logger, log_file = mock_pearl_logger
        
        # Import after mocks are set up  
        from main import app
        
        # Create a test endpoint that raises an exception
        @app.get("/test-exception")
        async def test_exception():
            raise ValueError("Test exception for logging")
        
        with TestClient(app) as client:
            response = client.get("/test-exception")
            assert response.status_code == 500
        
        # Read the log file
        with open(log_file, 'r') as f:
            logs = f.read()
        
        # Verify exception was logged
        assert "Unhandled exception" in logs
        assert "Test exception for logging" in logs
        assert "path=/test-exception" in logs
        
        # Verify Pearl format
        for line in logs.strip().split('\n'):
            if line and "Unhandled exception" in line:
                assert PEARL_LOG_REGEX.match(line)
                assert "[ERROR]" in line
    
    @pytest.mark.asyncio
    async def test_endpoint_span_logging(self, mock_services, mock_pearl_logger, mock_log_span):
        """
        Test that endpoint operations use Pearl-compliant spans.
        
        This ensures distributed tracing works correctly with Pearl.
        """
        logger, log_file = mock_pearl_logger
        
        # Import after mocks are set up
        from main import app
        
        with TestClient(app) as client:
            # Test get_proposals endpoint
            response = client.get("/proposals?space_id=test.eth")
            assert response.status_code == 200
        
        # Verify span was called correctly
        mock_log_span.assert_called_with(
            "get_proposals",
            space_id="test.eth",
            state=None,
            limit=20
        )
    
    @pytest.mark.asyncio
    async def test_summarize_endpoint_logging(self, mock_services, mock_pearl_logger, mock_log_span):
        """
        Test that AI summarization endpoint uses Pearl logging.
        
        This validates that complex operations are properly traced.
        """
        logger, log_file = mock_pearl_logger
        
        # Import after mocks are set up
        from main import app
        
        with TestClient(app) as client:
            response = client.post(
                "/proposals/summarize",
                json={"proposal_ids": ["0x123", "0x456"]}
            )
            assert response.status_code == 200
        
        # Read logs
        with open(log_file, 'r') as f:
            logs = f.read()
        
        # Verify span usage
        mock_log_span.assert_any_call("summarize_proposals", proposal_count=2)
        mock_log_span.assert_any_call("fetch_proposals_for_summarization")
        mock_log_span.assert_any_call("generate_proposal_summaries")
        
        # Verify log messages
        assert "Fetched proposals for summarization" in logs
        assert "Generated proposal summaries" in logs
    
    @pytest.mark.asyncio  
    async def test_agent_run_endpoint_logging(self, mock_services, mock_pearl_logger, mock_log_span):
        """
        Test that agent run endpoint uses Pearl logging correctly.
        
        This is critical as agent runs are the core autonomous functionality.
        """
        logger, log_file = mock_pearl_logger
        
        # Import after mocks are set up
        from main import app
        
        with TestClient(app) as client:
            response = client.post(
                "/agent-run",
                json={"space_id": "test.eth", "dry_run": True}
            )
            assert response.status_code == 200
        
        # Read logs
        with open(log_file, 'r') as f:
            logs = f.read()
        
        # Verify agent run completion log
        assert "Agent run completed" in logs
        assert "space_id=test.eth" in logs
        assert "dry_run=True" in logs
        
        # Verify span was used
        mock_log_span.assert_called_with(
            "agent_run",
            space_id="test.eth", 
            dry_run=True
        )
    
    def test_logfire_configuration_removed(self):
        """
        Test that Logfire configuration code is removed from main.py.
        
        This ensures no Logfire initialization happens even if token is present.
        """
        main_path = Path(__file__).parent.parent / "main.py"
        with open(main_path, 'r') as f:
            content = f.read()
        
        # Check that logfire.configure is not called
        assert 'logfire.configure' not in content
        assert 'settings.logfire_token' not in content
        assert 'settings.logfire_project' not in content
    
    @pytest.mark.asyncio
    async def test_log_format_compliance(self, mock_services, mock_pearl_logger):
        """
        Test that all logs from main.py are Pearl format compliant.
        
        This comprehensive test ensures every log message follows the exact format.
        """
        logger, log_file = mock_pearl_logger
        
        # Import after mocks are set up
        from main import app
        
        with TestClient(app) as client:
            # Hit multiple endpoints to generate various logs
            client.get("/health")
            client.get("/proposals?space_id=test.eth")
            client.get("/proposals/0x123")  # Will 404
            client.get("/proposals/0x123/top-voters")
            
            # Trigger an error
            with patch('main.snapshot_service.get_proposals', side_effect=Exception("Test error")):
                client.get("/proposals?space_id=error.eth")
        
        # Read and validate all logs
        with open(log_file, 'r') as f:
            logs = f.read()
        
        # Every non-empty line should match Pearl format
        lines = logs.strip().split('\n')
        assert len(lines) > 0, "No logs were generated"
        
        for line in lines:
            if line:
                assert PEARL_LOG_REGEX.match(line), f"Invalid Pearl format: {line}"


# Additional test for contextmanager import
from contextlib import contextmanager
import logging


class TestPearlLoggingIntegration:
    """Integration tests for Pearl logging in main.py."""
    
    @pytest.mark.asyncio
    async def test_real_log_file_creation(self, mock_services, monkeypatch):
        """
        Test that real Pearl logger creates log.txt file.
        
        This integration test verifies the actual file creation behavior.
        """
        # Create a temporary directory for the test
        with tempfile.TemporaryDirectory() as tmpdir:
            # Set STORE_PATH to temp directory
            monkeypatch.setenv('STORE_PATH', tmpdir)
            
            # Import logging_config to get real implementation
            from logging_config import setup_pearl_logger, log_span
            
            # Patch the imports in main.py
            with patch('main.setup_pearl_logger', setup_pearl_logger), \
                 patch('main.log_span', log_span):
                
                # Import after patches
                from main import app
                
                # Trigger application startup
                with TestClient(app) as client:
                    client.get("/health")
                
                # Check that log.txt was created
                log_path = Path(tmpdir) / 'log.txt'
                assert log_path.exists(), "log.txt was not created"
                
                # Verify content is Pearl compliant
                with open(log_path, 'r') as f:
                    logs = f.read()
                
                assert logs, "Log file is empty"
                for line in logs.strip().split('\n'):
                    if line:
                        assert PEARL_LOG_REGEX.match(line), f"Invalid format: {line}"