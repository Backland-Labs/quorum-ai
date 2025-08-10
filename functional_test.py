#!/usr/bin/env python3
"""
Functional test for healthcheck endpoint - GitHub issue #150
"""

import sys
import os
import time
import traceback
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

# Set environment variables
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("DEBUG", "true")

def test_health_check_service():
    """Test the HealthCheckService functionality."""
    print("=== Testing HealthCheckService ===")
    
    try:
        from unittest.mock import Mock
        from services.health_check_service import HealthCheckService
        from services.state_transition_tracker import AgentState
        from datetime import datetime, timedelta
        
        # Create mock dependencies
        mock_activity_service = Mock()
        mock_safe_service = Mock()
        mock_state_tracker = Mock()
        
        # Configure mocks
        mock_state_tracker.seconds_since_last_transition = 42.5
        mock_state_tracker.is_transitioning_fast.return_value = False
        mock_state_tracker.fast_transition_window = 5
        mock_state_tracker.fast_transition_threshold = 0.5
        mock_state_tracker.transition_history = []
        
        mock_activity_service.get_activity_status.return_value = {
            "daily_activity_needed": False,
            "last_activity_date": "2025-01-30",
        }
        mock_activity_service.is_daily_activity_needed.return_value = False
        mock_safe_service.has_sufficient_funds.return_value = True
        
        # Initialize service
        service = HealthCheckService(
            activity_service=mock_activity_service,
            safe_service=mock_safe_service,
            state_transition_tracker=mock_state_tracker,
            cache_ttl_seconds=10,
        )
        
        # Test service initialization
        assert service.activity_service == mock_activity_service
        assert service.safe_service == mock_safe_service
        assert service.state_transition_tracker == mock_state_tracker
        print("✅ Service initialization: PASSED")
        
        # Test complete health status
        result = service.get_complete_health_status()
        
        # Verify required fields
        required_fields = [
            "seconds_since_last_transition",
            "is_transitioning_fast",
            "is_tm_healthy",
            "agent_health",
            "rounds",
            "rounds_info",
        ]
        
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        print("✅ Complete health status structure: PASSED")
        
        # Test agent_health structure
        agent_health = result["agent_health"]
        agent_health_fields = [
            "is_making_on_chain_transactions",
            "is_staking_kpi_met",
            "has_required_funds",
        ]
        
        for field in agent_health_fields:
            assert field in agent_health, f"Missing agent_health field: {field}"
            assert isinstance(agent_health[field], bool), f"agent_health.{field} must be boolean"
        
        print("✅ Agent health structure: PASSED")
        
        # Test rounds_info structure
        rounds_info = result["rounds_info"]
        rounds_info_fields = [
            "total_rounds",
            "latest_round",
            "average_round_duration",
        ]
        
        for field in rounds_info_fields:
            assert field in rounds_info, f"Missing rounds_info field: {field}"
        
        print("✅ Rounds info structure: PASSED")
        
        # Test performance (should be fast due to caching)
        start_time = time.time()
        result2 = service.get_complete_health_status()
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        assert response_time < 100, f"Response time {response_time:.2f}ms exceeds 100ms requirement"
        print(f"✅ Performance test: PASSED ({response_time:.2f}ms)")
        
        return True
        
    except Exception as e:
        print(f"❌ HealthCheckService test failed: {e}")
        traceback.print_exc()
        return False

def test_healthcheck_endpoint():
    """Test the healthcheck endpoint functionality."""
    print("\n=== Testing Healthcheck Endpoint ===")
    
    try:
        from fastapi.testclient import TestClient
        from unittest.mock import Mock, patch
        import main
        
        # Create test client
        client = TestClient(main.app)
        
        # Test endpoint exists
        response = client.get("/healthcheck")
        assert response.status_code in [200, 503], f"Expected 200 or 503, got {response.status_code}"
        print("✅ Endpoint exists: PASSED")
        
        # Test response is JSON
        data = response.json()
        assert isinstance(data, dict), "Response should be JSON object"
        print("✅ JSON response: PASSED")
        
        # Test required fields
        required_fields = [
            "seconds_since_last_transition",
            "is_transitioning_fast",
            "is_tm_healthy",
            "agent_health",
            "rounds",
            "rounds_info",
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        print("✅ Required fields present: PASSED")
        
        # Test field types
        assert isinstance(data["seconds_since_last_transition"], (int, float)), \
            "seconds_since_last_transition must be a number"
        assert isinstance(data["is_transitioning_fast"], bool), \
            "is_transitioning_fast must be a boolean"
        assert isinstance(data["is_tm_healthy"], bool), \
            "is_tm_healthy must be a boolean"
        assert isinstance(data["agent_health"], dict), \
            "agent_health must be a dictionary"
        assert isinstance(data["rounds"], list), \
            "rounds must be a list"
        assert isinstance(data["rounds_info"], dict), \
            "rounds_info must be a dictionary"
        
        print("✅ Field types correct: PASSED")
        
        # Test agent_health structure
        agent_health = data["agent_health"]
        agent_health_fields = [
            "is_making_on_chain_transactions",
            "is_staking_kpi_met",
            "has_required_funds"
        ]
        
        for field in agent_health_fields:
            assert field in agent_health, f"Missing agent_health field: {field}"
            assert isinstance(agent_health[field], bool), \
                f"agent_health.{field} must be a boolean"
        
        print("✅ Agent health structure: PASSED")
        
        # Test rounds_info structure
        rounds_info = data["rounds_info"]
        assert "total_rounds" in rounds_info
        assert "latest_round" in rounds_info
        assert "average_round_duration" in rounds_info
        assert isinstance(rounds_info["total_rounds"], int)
        assert isinstance(rounds_info["average_round_duration"], (int, float))
        
        print("✅ Rounds info structure: PASSED")
        
        # Test response time
        start_time = time.time()
        response = client.get("/healthcheck")
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000
        assert response_time < 100, f"Response time {response_time:.2f}ms exceeds 100ms requirement"
        print(f"✅ Response time: PASSED ({response_time:.2f}ms)")
        
        return True
        
    except Exception as e:
        print(f"❌ Healthcheck endpoint test failed: {e}")
        traceback.print_exc()
        return False

def test_integration():
    """Test integration between service and endpoint."""
    print("\n=== Testing Integration ===")
    
    try:
        from fastapi.testclient import TestClient
        from unittest.mock import Mock, patch
        import main
        from services.health_check_service import HealthCheckService
        
        # Mock dependencies
        mock_activity_service = Mock()
        mock_safe_service = Mock()
        mock_state_tracker = Mock()
        
        mock_state_tracker.seconds_since_last_transition = 30.0
        mock_state_tracker.is_transitioning_fast.return_value = False
        mock_state_tracker.fast_transition_window = 5
        mock_state_tracker.fast_transition_threshold = 0.5
        mock_state_tracker.transition_history = []
        
        mock_activity_service.get_activity_status.return_value = {
            "daily_activity_needed": False,
            "last_activity_date": "2025-01-30",
        }
        mock_activity_service.is_daily_activity_needed.return_value = False
        mock_safe_service.has_sufficient_funds.return_value = True
        
        # Create service
        health_service = HealthCheckService(
            activity_service=mock_activity_service,
            safe_service=mock_safe_service,
            state_transition_tracker=mock_state_tracker,
        )
        
        # Patch the global service
        with patch.object(main, 'health_check_service', health_service):
            client = TestClient(main.app)
            response = client.get("/healthcheck")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify the endpoint uses the service
            assert data["seconds_since_last_transition"] == 30.0
            assert data["is_transitioning_fast"] is False
            assert data["is_tm_healthy"] is True  # Should be healthy with recent transitions
            
            print("✅ Service integration: PASSED")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all functional tests."""
    print("=== Healthcheck Functional Tests for Issue #150 ===")
    print(f"Backend path: {backend_path}")
    print()
    
    results = []
    
    # Run tests
    results.append(("HealthCheckService", test_health_check_service()))
    results.append(("Healthcheck Endpoint", test_healthcheck_endpoint()))
    results.append(("Integration", test_integration()))
    
    # Summary
    print("\n=== Test Results Summary ===")
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 All functional tests PASSED!")
        return 0
    else:
        print("💥 Some functional tests FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())