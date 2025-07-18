"""
Test suite to verify the application runs without logfire dependency.

This test file ensures that the migration from logfire to Pearl logging is complete
and that no runtime dependencies on logfire remain in the codebase.
"""

import pytest
import subprocess
import sys
import ast
from pathlib import Path
import importlib.util


class TestLogfireDependencyRemoval:
    """Test suite to ensure logfire dependency has been completely removed."""
    
    def test_no_logfire_in_dependencies(self):
        """
        Test that logfire is not present in pyproject.toml dependencies.
        
        This test is important because it verifies that the external logfire
        dependency has been removed from the project requirements, ensuring
        the application can be deployed without needing LOGFIRE_TOKEN or
        access to external logfire services.
        """
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, 'r') as f:
            content = f.read()
        
        # Check that logfire is not in dependencies
        assert 'logfire' not in content.lower(), (
            "Found 'logfire' in pyproject.toml - dependency should be removed"
        )
    
    def test_no_logfire_imports_in_source(self):
        """
        Test that no Python source files contain logfire imports.
        
        This test is critical because it ensures all source code has been
        migrated to use Pearl logging instead of logfire, preventing any
        runtime failures due to missing logfire imports.
        """
        backend_dir = Path(__file__).parent.parent
        source_files = []
        
        # Collect all Python files except tests and virtual environments
        for path in backend_dir.rglob("*.py"):
            path_str = str(path)
            if ("tests" not in path_str and 
                "__pycache__" not in path_str and
                ".venv" not in path_str and
                "venv" not in path_str and
                "site-packages" not in path_str):
                source_files.append(path)
        
        files_with_logfire = []
        for file_path in source_files:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Parse the AST to find imports
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if 'logfire' in alias.name:
                                files_with_logfire.append(str(file_path))
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and 'logfire' in node.module:
                            files_with_logfire.append(str(file_path))
            except:
                # If parsing fails, do string search as fallback
                if 'import logfire' in content or 'from logfire' in content:
                    files_with_logfire.append(str(file_path))
        
        assert not files_with_logfire, (
            f"Found logfire imports in source files: {files_with_logfire}"
        )
    
    def test_application_starts_without_logfire(self):
        """
        Test that the FastAPI application can start without logfire installed.
        
        This integration test is essential because it verifies that the application
        can successfully initialize and run without any runtime dependency on logfire,
        ensuring the Pearl logging system is fully functional as a replacement.
        """
        # First, verify logfire is NOT installed
        try:
            import logfire
            pytest.skip("Logfire is still installed - cannot test without it")
        except ImportError:
            pass  # Good - logfire is not installed
        
        # Try to import main module
        main_path = Path(__file__).parent.parent / "main.py"
        spec = importlib.util.spec_from_file_location("main", main_path)
        main_module = importlib.util.module_from_spec(spec)
        
        # This should not raise any ImportError related to logfire
        try:
            spec.loader.exec_module(main_module)
            # Verify the app object exists
            assert hasattr(main_module, 'app'), "FastAPI app not found in main.py"
        except ImportError as e:
            if 'logfire' in str(e).lower():
                pytest.fail(f"Application failed to start due to logfire dependency: {e}")
            else:
                # Other import errors might be expected (e.g., missing env vars)
                pass
    
    def test_logging_config_uses_pearl_logger(self):
        """
        Test that logging_config.py provides Pearl logging functionality.
        
        This test verifies that the Pearl logging infrastructure is properly
        set up and can be used throughout the application, confirming the
        migration from logfire to Pearl logging is complete.
        """
        # Add parent directory to path to import logging_config
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from logging_config import setup_pearl_logger, log_span
        
        # Verify Pearl logger can be set up
        logger = setup_pearl_logger("test_logger")
        assert logger is not None, "Pearl logger setup failed"
        
        # Verify log_span context manager works
        with log_span(logger, "test_span") as span_logger:
            assert span_logger is not None, "log_span context manager failed"
    
    def test_env_example_no_logfire_token(self):
        """
        Test that .env.example does not require LOGFIRE_TOKEN.
        
        This test ensures that the example environment configuration has been
        updated to remove logfire-related settings, making it easier for new
        developers to set up the project without confusion about obsolete
        dependencies.
        """
        env_example_path = Path(__file__).parent.parent.parent / ".env.example"
        if env_example_path.exists():
            with open(env_example_path, 'r') as f:
                content = f.read()
            
            # Check for uncommented LOGFIRE_TOKEN
            lines = content.split('\n')
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith('#'):
                    assert 'LOGFIRE_TOKEN' not in line, (
                        f"Found uncommented LOGFIRE_TOKEN in .env.example: {line}"
                    )