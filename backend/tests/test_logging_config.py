"""
Tests for Pearl-compliant logging infrastructure.

This module tests the core logging infrastructure required for Pearl platform compliance.
The logging system must produce log.txt file in exact format for Pearl monitoring.
"""

import logging
import re
import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from datetime import datetime
from contextlib import contextmanager


class TestPearlFormatter:
    """
    Test Pearl-compliant log formatter class.
    
    This test ensures the PearlFormatter produces exactly the format required by Pearl:
    [YYYY-MM-DD HH:MM:SS,mmm] [LOG_LEVEL] [agent] Message
    
    This is critical because Pearl platform monitors this specific format for agent health.
    """
    
    def test_pearl_formatter_basic_format(self):
        """
        Test that PearlFormatter produces the exact Pearl-required format.
        
        This test validates that log messages are formatted correctly with timestamp,
        log level, agent prefix, and message. Pearl platform depends on this exact format
        for monitoring and debugging agent behavior.
        """
        # This will fail until we implement PearlFormatter
        from logging_config import PearlFormatter
        
        formatter = PearlFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )
        record.created = 1647259800.123  # Fixed timestamp for testing
        
        formatted = formatter.format(record)
        
        # Expected format: [2022-03-14 10:30:00,123] [INFO] [agent] Test message
        pattern = r'^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}\] \[INFO\] \[agent\] Test message$'
        assert re.match(pattern, formatted), f"Formatted log doesn't match Pearl format: {formatted}"
    
    def test_pearl_formatter_timestamp_precision(self):
        """
        Test that PearlFormatter includes milliseconds in timestamp.
        
        Pearl platform requires millisecond precision for accurate agent timing analysis.
        This test ensures the timestamp format includes exactly 3 decimal places for milliseconds.
        """
        from logging_config import PearlFormatter
        
        formatter = PearlFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.DEBUG,
            pathname='test.py',
            lineno=1,
            msg='Debug message',
            args=(),
            exc_info=None
        )
        record.created = 1647259800.456789  # Test with microseconds
        
        formatted = formatter.format(record)
        
        # Should contain exactly 3 digits after comma in timestamp
        timestamp_pattern = r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}\]'
        assert re.search(timestamp_pattern, formatted), f"Timestamp doesn't have correct millisecond format: {formatted}"
        
        # Extract timestamp and verify it's exactly 456 milliseconds
        match = re.search(r',(\d{3})', formatted)
        assert match.group(1) == '456', f"Milliseconds should be 456, got {match.group(1)}"
    
    def test_pearl_formatter_all_log_levels(self):
        """
        Test that PearlFormatter handles all required Pearl log levels correctly.
        
        Pearl platform supports ERROR, WARN, INFO, DEBUG, TRACE levels.
        This test ensures all levels are formatted correctly with proper case sensitivity.
        """
        from logging_config import PearlFormatter
        
        formatter = PearlFormatter()
        levels = [
            (logging.ERROR, 'ERROR'),
            (logging.WARNING, 'WARNING'),  # Python uses WARNING, Pearl expects WARN
            (logging.INFO, 'INFO'),
            (logging.DEBUG, 'DEBUG'),
        ]
        
        for level_int, expected_name in levels:
            record = logging.LogRecord(
                name='test',
                level=level_int,
                pathname='test.py',
                lineno=1,
                msg='Test message',
                args=(),
                exc_info=None
            )
            record.created = 1647259800.123
            
            formatted = formatter.format(record)
            
            # Pearl expects WARN instead of WARNING
            expected_level = 'WARN' if expected_name == 'WARNING' else expected_name
            assert f'[{expected_level}]' in formatted, f"Log level {expected_level} not found in: {formatted}"
    
    def test_pearl_formatter_message_with_parameters(self):
        """
        Test that PearlFormatter correctly handles parameterized log messages.
        
        Many agent operations include parameters like transaction hashes, addresses.
        This test ensures parameterized messages are expanded correctly before formatting.
        """
        from logging_config import PearlFormatter
        
        formatter = PearlFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Processing transaction %s with amount %d',
            args=('0x123abc', 1000),
            exc_info=None
        )
        record.created = 1647259800.123
        
        formatted = formatter.format(record)
        
        assert 'Processing transaction 0x123abc with amount 1000' in formatted
        assert '[agent]' in formatted
    
    def test_pearl_formatter_special_characters(self):
        """
        Test that PearlFormatter handles special characters in log messages.
        
        Agent messages may contain special characters, newlines, unicode.
        This test ensures the formatter handles them safely without breaking Pearl parsing.
        """
        from logging_config import PearlFormatter
        
        formatter = PearlFormatter()
        special_messages = [
            'Message with [brackets]',
            'Message with "quotes"',
            'Message with ñ unicode',
            'Message with newline\ncharacter',
        ]
        
        for msg in special_messages:
            record = logging.LogRecord(
                name='test',
                level=logging.INFO,
                pathname='test.py',
                lineno=1,
                msg=msg,
                args=(),
                exc_info=None
            )
            record.created = 1647259800.123
            
            formatted = formatter.format(record)
            
            # Should still match basic pattern
            pattern = r'^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}\] \[INFO\] \[agent\] .*'
            assert re.match(pattern, formatted), f"Special character message broke format: {formatted}"


class TestPearlFormatterEdgeCases:
    """
    Test edge cases and error conditions for PearlFormatter.
    
    These tests ensure the formatter is robust and handles unusual conditions
    without breaking Pearl compliance or crashing the agent.
    """
    
    def test_pearl_formatter_empty_message(self):
        """
        Test PearlFormatter with empty log message.
        
        Edge case testing to ensure formatter doesn't break with empty messages.
        Agent should continue operating even with malformed log calls.
        """
        from logging_config import PearlFormatter
        
        formatter = PearlFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='',
            args=(),
            exc_info=None
        )
        record.created = 1647259800.123
        
        formatted = formatter.format(record)
        
        # Should still have proper structure even with empty message
        pattern = r'^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}\] \[INFO\] \[agent\] $'
        assert re.match(pattern, formatted), f"Empty message broke format: {formatted}"
    
    def test_pearl_formatter_with_exception_info(self):
        """
        Test PearlFormatter with exception information.
        
        When agent encounters exceptions, logging should include stack traces
        while maintaining Pearl format for the main log line.
        """
        from logging_config import PearlFormatter
        
        formatter = PearlFormatter()
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys
            record = logging.LogRecord(
                name='test',
                level=logging.ERROR,
                pathname='test.py',
                lineno=1,
                msg='Operation failed',
                args=(),
                exc_info=sys.exc_info()
            )
            record.created = 1647259800.123
            
            formatted = formatter.format(record)
            
            # First line should match Pearl format
            lines = formatted.split('\n')
            first_line = lines[0]
            pattern = r'^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}\] \[ERROR\] \[agent\] Operation failed$'
            assert re.match(pattern, first_line), f"Exception log first line broke format: {first_line}"
            
            # Should include exception details
            assert 'ValueError: Test exception' in formatted


class TestSetupPearlLogger:
    """
    Test setup_pearl_logger function for complete logger configuration.
    
    This test ensures the setup function properly configures a logger with Pearl-compliant
    formatting and file output. Critical for autonomous agent deployment on Pearl platform.
    """
    
    def teardown_method(self):
        """Clean up loggers after each test to avoid conflicts."""
        import logging
        # Clear all handlers from loggers to avoid conflicts
        for name in ['test_agent', 'agent', 'test_logger']:
            logger = logging.getLogger(name)
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
    
    def test_setup_pearl_logger_basic_configuration(self):
        """
        Test that setup_pearl_logger creates properly configured logger.
        
        This test validates that the setup function creates a logger with correct
        name, level, handler, and formatter. Essential for Pearl platform compliance.
        """
        from logging_config import setup_pearl_logger
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'test_log.txt')
            
            logger = setup_pearl_logger(
                name='test_agent',
                level=logging.DEBUG,
                log_file_path=log_file
            )
            
            assert logger.name == 'test_agent'
            assert logger.level == logging.DEBUG
            assert len(logger.handlers) == 1
            
            # Test logging works
            logger.info("Test message")
            
            # Verify file was created and contains Pearl format
            assert os.path.exists(log_file)
            with open(log_file, 'r') as f:
                content = f.read()
                assert '[INFO] [agent] Test message' in content
    
    def test_setup_pearl_logger_default_parameters(self):
        """
        Test setup_pearl_logger with default parameters.
        
        Validates that the function works with minimal configuration,
        using defaults appropriate for Pearl deployment.
        """
        from logging_config import setup_pearl_logger
        import tempfile
        import os
        
        # Change to temp directory for test
        original_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                os.chdir(temp_dir)
                
                logger = setup_pearl_logger()
                
                assert logger.name == 'agent'
                assert logger.level == logging.INFO
                
                # Test that log.txt is created in current directory
                logger.info("Default test")
                assert os.path.exists('log.txt')
        finally:
            os.chdir(original_cwd)
    
    def test_setup_pearl_logger_with_store_path(self):
        """
        Test setup_pearl_logger respects Pearl STORE_PATH environment variable.
        
        Pearl platform provides STORE_PATH for persistent data storage.
        Logger should place log.txt in this location when available.
        """
        from logging_config import setup_pearl_logger
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = os.path.join(temp_dir, 'store')
            os.makedirs(store_path)
            
            logger = setup_pearl_logger(store_path=store_path)
            
            expected_log_file = os.path.join(store_path, 'log.txt')
            
            logger.info("Store path test")
            
            assert os.path.exists(expected_log_file)
            with open(expected_log_file, 'r') as f:
                content = f.read()
                assert '[INFO] [agent] Store path test' in content
    
    def test_setup_pearl_logger_prevents_duplicate_handlers(self):
        """
        Test that setup_pearl_logger doesn't add duplicate handlers.
        
        Multiple calls should return the same logger instance without
        creating duplicate handlers that would cause duplicate log entries.
        """
        from logging_config import setup_pearl_logger
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'test_log.txt')
            
            logger1 = setup_pearl_logger(log_file_path=log_file)
            logger2 = setup_pearl_logger(log_file_path=log_file)
            
            assert logger1 is logger2
            assert len(logger1.handlers) == 1  # Should not duplicate handlers


class TestLogSpan:
    """
    Test log_span context manager for operation tracking.
    
    This replaces Logfire spans with Pearl-compliant operation logging.
    Critical for tracking agent operations and debugging issues.
    """
    
    def teardown_method(self):
        """Clean up loggers after each test to avoid conflicts."""
        import logging
        # Clear all handlers from loggers to avoid conflicts
        for name in ['agent', 'test_logger']:
            logger = logging.getLogger(name)
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
    
    def test_log_span_successful_operation(self):
        """
        Test log_span context manager for successful operations.
        
        Validates that operations are properly logged with start, duration,
        and completion messages. Essential for agent operation monitoring.
        """
        from logging_config import log_span, setup_pearl_logger
        import tempfile
        import os
        import time
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'test_log.txt')
            logger = setup_pearl_logger(log_file_path=log_file)
            
            with log_span(logger, "test_operation", user_id="123") as span:
                span['result'] = 'success'
                time.sleep(0.01)  # Small delay to test duration
            
            # Read log file and verify span logging
            with open(log_file, 'r') as f:
                content = f.read()
                
            assert 'Starting test_operation (user_id=123)' in content
            assert 'Completed test_operation successfully' in content
            assert 'result=success' in content
            assert 's (' in content  # Duration should be present
    
    def test_log_span_operation_failure(self):
        """
        Test log_span context manager handles operation failures.
        
        When operations fail, span should log the error and re-raise exception.
        Critical for proper error tracking in autonomous agent operations.
        """
        from logging_config import log_span, setup_pearl_logger
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'test_log.txt')
            logger = setup_pearl_logger(log_file_path=log_file)
            
            with pytest.raises(ValueError):
                with log_span(logger, "failing_operation") as span:
                    raise ValueError("Test failure")
            
            # Read log file and verify failure logging
            with open(log_file, 'r') as f:
                content = f.read()
                
            assert 'Starting failing_operation' in content
            assert 'Failed failing_operation after' in content
            assert 'Test failure' in content
    
    def test_log_span_without_context(self):
        """
        Test log_span context manager with minimal parameters.
        
        Should work with just logger and operation name,
        providing basic operation tracking for simple use cases.
        """
        from logging_config import log_span, setup_pearl_logger
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'test_log.txt')
            logger = setup_pearl_logger(log_file_path=log_file)
            
            with log_span(logger, "simple_operation"):
                pass  # Minimal operation
            
            # Read log file and verify basic logging
            with open(log_file, 'r') as f:
                content = f.read()
                
            assert 'Starting simple_operation' in content
            assert 'Completed simple_operation successfully' in content


class TestValidationFunctions:
    """
    Test validation and utility functions for Pearl compliance.
    
    These functions help ensure log format compliance and file operations
    work correctly in Pearl deployment environment.
    """
    
    def test_validate_log_format_valid_lines(self):
        """
        Test validate_log_format function with Pearl-compliant log lines.
        
        This function is used for testing and debugging to ensure all logs
        meet Pearl format requirements. Critical for deployment validation.
        """
        from logging_config import validate_log_format
        
        valid_lines = [
            '[2024-03-14 10:30:00,123] [INFO] [agent] Starting command execution',
            '[2024-03-14 10:30:01,456] [DEBUG] [agent] Command parameters: {...}',
            '[2024-03-14 10:30:02,789] [ERROR] [agent] Failed to connect to service',
            '[2024-12-31 23:59:59,999] [WARN] [agent] Warning message',
            '[2024-01-01 00:00:00,000] [TRACE] [agent] Trace message',
        ]
        
        for line in valid_lines:
            assert validate_log_format(line), f"Valid line rejected: {line}"
    
    def test_validate_log_format_invalid_lines(self):
        """
        Test validate_log_format function rejects invalid log lines.
        
        Ensures the validator correctly identifies lines that don't meet
        Pearl format requirements, helping catch configuration issues.
        """
        from logging_config import validate_log_format
        
        invalid_lines = [
            'Not a log line at all',
            '[2024-03-14 10:30:00] [INFO] [agent] Missing milliseconds',
            '[2024-03-14 10:30:00,123] [INFO] Missing agent prefix',
            '[2024-03-14 10:30:00,123] [INVALID] [agent] Bad log level',
            'INFO: Regular Python logging format',
            '[2024-03-14 10:30:00,123] [INFO] [wrong] Wrong prefix',
        ]
        
        for line in invalid_lines:
            assert not validate_log_format(line), f"Invalid line accepted: {line}"
    
    def test_ensure_log_file_exists_creates_file(self):
        """
        Test ensure_log_file_exists function creates log file correctly.
        
        This function ensures the log file is ready for writing,
        critical for Pearl platform initialization and monitoring.
        """
        from logging_config import ensure_log_file_exists
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'new_log.txt')
            
            # File shouldn't exist initially
            assert not os.path.exists(log_file)
            
            # Function should create it
            result = ensure_log_file_exists(log_file)
            
            assert result is True
            assert os.path.exists(log_file)
            
            # Should contain initialization message
            with open(log_file, 'r') as f:
                content = f.read()
                assert '[INFO] [agent] Log file initialized' in content
    
    def test_ensure_log_file_exists_handles_errors(self):
        """
        Test ensure_log_file_exists handles permission and path errors gracefully.
        
        Should not crash the agent if log file creation fails,
        allowing agent to continue operating even with logging issues.
        """
        from logging_config import ensure_log_file_exists
        
        # Try to create log file in non-existent directory without creating it
        invalid_path = '/nonexistent/directory/log.txt'
        
        result = ensure_log_file_exists(invalid_path)
        
        # Should return False but not crash
        assert result is False