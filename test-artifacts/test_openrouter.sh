#!/bin/bash
set -e

echo "========================================"
echo "Testing OpenRouter API Key Management"
echo "========================================"

# Change to backend directory
cd backend

echo "Current directory: $(pwd)"

# Test 1: OpenRouter Key Management Tests
echo ""
echo "========================================="
echo "TEST 1: OpenRouter Key Management Tests"
echo "========================================="
uv run pytest tests/test_openrouter_key_management.py -v --tb=short --no-header || echo "❌ OpenRouter key management tests failed"

# Test 2: API Endpoints Tests
echo ""
echo "==============================="
echo "TEST 2: API Endpoints Tests"
echo "==============================="
uv run pytest tests/test_api_endpoints.py -v --tb=short --no-header || echo "❌ API endpoints tests failed"

# Test 3: Key Manager Tests
echo ""
echo "=========================="
echo "TEST 3: Key Manager Tests"
echo "=========================="
uv run pytest tests/test_key_manager.py -v --tb=short --no-header || echo "❌ Key manager tests failed"

# Test 4: User Preferences Service Tests
echo ""
echo "===================================="
echo "TEST 4: User Preferences Service Tests"
echo "===================================="
uv run pytest tests/test_user_preferences_service.py -v --tb=short --no-header || echo "❌ User preferences service tests failed"

echo ""
echo "========================================="
echo "Running quick backend regression test..."
echo "========================================="
uv run pytest tests/test_ai_service.py tests/test_models.py tests/test_config.py -v --tb=short --no-header || echo "❌ Some basic backend tests failed"

echo ""
echo "Backend test execution completed!"
