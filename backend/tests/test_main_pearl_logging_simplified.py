"""
Simplified test suite for main.py Pearl logging integration.

This test suite verifies that main.py correctly integrates with Pearl-compliant 
logging infrastructure through focused integration tests.
"""

import os
import re
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# Pearl log format regex for validation
PEARL_LOG_REGEX = re.compile(
    r'^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}\] \[(ERROR|WARN|INFO|DEBUG|TRACE)\] \[agent\] .+$'
)


class TestMainPearlLoggingIntegration:
    """Integration tests for Pearl logging in main.py."""
    
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
        
        # Check that logfire configuration is removed
        assert 'logfire.configure' not in content
        assert 'settings.logfire_token' not in content
        assert 'settings.logfire_project' not in content
    
    def test_pearl_logger_import_and_initialization(self):
        """
        Test that main.py imports and initializes Pearl logging components.
        
        Ensures the correct logging infrastructure is set up.
        """
        main_path = Path(__file__).parent.parent / "main.py"
        with open(main_path, 'r') as f:
            content = f.read()
        
        # Check for Pearl logging imports
        assert 'from logging_config import setup_pearl_logger, log_span' in content
        
        # Check for logger initialization
        assert 'logger = setup_pearl_logger(__name__)' in content
        
        # Check that all logging calls use logger
        assert 'logger.info(' in content
        assert 'logger.error(' in content
        
        # Check that all spans use log_span with logger
        assert 'with log_span(logger,' in content
    
    def test_structured_logging_format(self):
        """
        Test that structured logging uses key=value format.
        
        This ensures logs are parseable and follow Pearl conventions.
        """
        main_path = Path(__file__).parent.parent / "main.py"
        with open(main_path, 'r') as f:
            content = f.read()
        
        # Check for structured logging patterns
        assert 'version=0.1.0' in content
        assert 'space_id=' in content
        assert 'error=' in content
        assert 'proposal_id=' in content
        assert 'count=' in content
        
        # Ensure no keyword argument style logging
        assert ', version=' not in content
        assert ', error=' not in content
    
    @pytest.mark.asyncio
    async def test_application_lifecycle_logging(self):
        """
        Test that application startup and shutdown are properly logged.
        
        This is an integration test that verifies the actual logging behavior.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / 'log.txt'
            
            # Set environment to use temp directory
            os.environ['STORE_PATH'] = tmpdir
            
            try:
                # Import main module fresh
                import main
                from importlib import reload
                reload(main)
                
                # Create test client
                with TestClient(main.app) as client:
                    # Make a simple request
                    response = client.get("/health")
                    assert response.status_code == 200
                
                # Verify log file was created
                assert log_file.exists(), "log.txt was not created"
                
                # Read and verify logs
                with open(log_file, 'r') as f:
                    logs = f.read()
                
                # Check for key log messages
                assert "Pearl logger initialized successfully" in logs
                assert "Application started version=0.1.0" in logs
                assert "Application shutdown" in logs
                
                # Verify all logs match Pearl format
                for line in logs.strip().split('\n'):
                    if line:
                        assert PEARL_LOG_REGEX.match(line), f"Invalid Pearl format: {line}"
                        
            finally:
                # Clean up environment
                if 'STORE_PATH' in os.environ:
                    del os.environ['STORE_PATH']
    
    @pytest.mark.asyncio
    async def test_error_logging(self):
        """
        Test that errors are properly logged with Pearl format.
        
        This ensures debugging information is available in production.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / 'log.txt'
            os.environ['STORE_PATH'] = tmpdir
            
            try:
                # Import main module fresh
                import main
                from importlib import reload
                reload(main)
                
                # Create test client and trigger an error
                with TestClient(main.app) as client:
                    # Try to get a non-existent proposal
                    response = client.get("/proposals/nonexistent")
                    # This will fail but that's expected
                    
                    # Try to fetch proposals without required parameter
                    response = client.get("/proposals")
                    assert response.status_code == 422  # Validation error
                
                # Verify error logging
                assert log_file.exists()
                with open(log_file, 'r') as f:
                    logs = f.read()
                
                # Should have error logs
                assert "[ERROR]" in logs or "Failed" in logs
                
                # All logs should be Pearl compliant
                for line in logs.strip().split('\n'):
                    if line:
                        assert PEARL_LOG_REGEX.match(line), f"Invalid format: {line}"
                        
            finally:
                if 'STORE_PATH' in os.environ:
                    del os.environ['STORE_PATH']
    
    def test_logging_completeness(self):
        """
        Test that all Logfire references have been replaced.
        
        This is a comprehensive check to ensure migration is complete.
        """
        main_path = Path(__file__).parent.parent / "main.py"
        with open(main_path, 'r') as f:
            lines = f.readlines()
        
        # Track logging usage
        logfire_count = 0
        logger_count = 0
        
        for i, line in enumerate(lines, 1):
            if 'logfire.' in line and 'import' not in line:
                logfire_count += 1
                print(f"Line {i}: Found logfire usage: {line.strip()}")
            
            if 'logger.' in line:
                logger_count += 1
        
        # Ensure no Logfire usage remains
        assert logfire_count == 0, f"Found {logfire_count} logfire usages"
        
        # Ensure logger is being used
        assert logger_count > 10, f"Expected more logger usage, found only {logger_count}"
        
        # Check that helper functions use logger
        content = ''.join(lines)
        assert '_fetch_proposals_for_summarization' in content
        assert '_generate_proposal_summaries' in content
        
        # These functions should use log_span
        assert 'with log_span(logger, "fetch_proposals_for_summarization")' in content
        assert 'with log_span(logger, "generate_proposal_summaries")' in content