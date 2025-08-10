#!/bin/bash

# Script to run healthcheck functional tests for GitHub issue #150

echo "=== Running Healthcheck Functional Tests for Issue #150 ==="
echo ""

# Change to backend directory
cd /Users/max/code/q-issue-150/backend

echo "Current directory: $(pwd)"
echo ""

# Check if uv is available
if command -v uv &> /dev/null; then
    echo "Using uv to run tests..."
    
    # Run healthcheck service tests
    echo "=== Running HealthCheckService Tests ==="
    uv run pytest tests/test_health_check_service.py -v
    service_exit_code=$?
    echo ""
    
    # Run healthcheck endpoint tests
    echo "=== Running Healthcheck Endpoint Tests ==="
    uv run pytest tests/test_healthcheck_endpoint.py -v
    endpoint_exit_code=$?
    echo ""
    
    # Summary
    echo "=== Test Results Summary ==="
    if [ $service_exit_code -eq 0 ]; then
        echo "✅ HealthCheckService tests: PASSED"
    else
        echo "❌ HealthCheckService tests: FAILED (exit code: $service_exit_code)"
    fi
    
    if [ $endpoint_exit_code -eq 0 ]; then
        echo "✅ Healthcheck endpoint tests: PASSED"
    else
        echo "❌ Healthcheck endpoint tests: FAILED (exit code: $endpoint_exit_code)"
    fi
    
    # Overall result
    if [ $service_exit_code -eq 0 ] && [ $endpoint_exit_code -eq 0 ]; then
        echo ""
        echo "🎉 All healthcheck tests PASSED!"
        exit 0
    else
        echo ""
        echo "💥 Some healthcheck tests FAILED!"
        exit 1
    fi
    
else
    echo "❌ uv not found. Please install uv or run tests manually with pytest."
    exit 1
fi