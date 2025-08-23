#!/bin/bash

# Change to backend directory
cd /Users/max/code/quorum-ai/backend

echo "=================================================="
echo "Running ActivityService core functionality tests"
echo "=================================================="
echo "Command: uv run pytest tests/test_activity_service.py -v"
uv run pytest tests/test_activity_service.py -v > /tmp/activity_test_output.txt 2>&1
echo "Exit code: $?"
echo ""
cat /tmp/activity_test_output.txt

echo ""
echo "=================================================="
echo "Running Service integration tests"
echo "=================================================="
echo "Command: uv run pytest tests/test_service_integration.py -v"
uv run pytest tests/test_service_integration.py -v > /tmp/integration_test_output.txt 2>&1
echo "Exit code: $?"
echo ""
cat /tmp/integration_test_output.txt

echo ""
echo "=================================================="
echo "Running Pydantic models tests"
echo "=================================================="
echo "Command: uv run pytest tests/test_models.py -v"
uv run pytest tests/test_models.py -v > /tmp/models_test_output.txt 2>&1
echo "Exit code: $?"
echo ""
cat /tmp/models_test_output.txt

echo ""
echo "=================================================="
echo "Running API endpoints tests"
echo "=================================================="
echo "Command: uv run pytest tests/test_main.py -v"
uv run pytest tests/test_main.py -v > /tmp/main_test_output.txt 2>&1
echo "Exit code: $?"
echo ""
cat /tmp/main_test_output.txt
