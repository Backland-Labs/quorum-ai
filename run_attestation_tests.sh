#!/bin/bash

# AttestationTracker Functional Testing Script
# This script runs comprehensive functional tests for the AttestationTracker integration

echo "=========================================="
echo "AttestationTracker Functional Test Suite"
echo "=========================================="
echo ""

cd /Users/max/code/quorum-ai/backend

echo "1. Running Configuration Tests..."
echo "Command: uv run pytest tests/test_config.py::TestAttestationTrackerConfiguration -v"
uv run pytest tests/test_config.py::TestAttestationTrackerConfiguration -v
echo ""

echo "2. Running SafeService Routing Tests..."
echo "Command: uv run pytest tests/test_safe_service_eas.py::TestAttestationTrackerRouting -v"
uv run pytest tests/test_safe_service_eas.py::TestAttestationTrackerRouting -v
echo ""

echo "3. Running Helper Function Tests..."
echo "Command: uv run pytest tests/test_attestation_tracker_helpers.py -v"
uv run pytest tests/test_attestation_tracker_helpers.py -v
echo ""

echo "4. Running Agent Run Attestation Tests..."
echo "Command: uv run pytest tests/test_agent_run_attestation.py::test_attestation_retry_with_tracker -v"
uv run pytest tests/test_agent_run_attestation.py::test_attestation_retry_with_tracker -v
echo ""

echo "5. Running Overall AttestationTracker Tests..."
echo "Command: uv run pytest -k attestation_tracker -v"
uv run pytest -k attestation_tracker -v
echo ""

echo "=========================================="
echo "AttestationTracker Test Suite Complete"
echo "=========================================="