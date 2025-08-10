#!/usr/bin/env python3
"""
Live endpoint test for healthcheck - GitHub issue #150
Tests the actual running backend server
"""

import requests
import json
import time
import sys
from typing import Dict, Any

def test_endpoint_accessibility():
    """Test that the endpoint is accessible."""
    print("=== Testing Endpoint Accessibility ===")
    
    try:
        response = requests.get("http://localhost:8716/healthcheck", timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response Time: {response.elapsed.total_seconds() * 1000:.2f}ms")
        
        if response.status_code == 200:
            print("✅ Endpoint accessible: PASSED")
            return True, response.json()
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            return False, None
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - server may not be running")
        return False, None
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False, None
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False, None

def test_response_structure(data: Dict[str, Any]):
    """Test the response structure matches Pearl requirements."""
    print("\n=== Testing Response Structure ===")
    
    try:
        # Test required fields
        required_fields = [
            "seconds_since_last_transition",
            "is_transitioning_fast",
            "is_tm_healthy",
            "agent_health",
            "rounds",
            "rounds_info",
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ Missing required fields: {missing_fields}")
            return False
        
        print("✅ All required fields present: PASSED")
        
        # Test field types
        type_checks = [
            ("seconds_since_last_transition", (int, float)),
            ("is_transitioning_fast", bool),
            ("is_tm_healthy", bool),
            ("agent_health", dict),
            ("rounds", list),
            ("rounds_info", (dict, type(None))),  # Can be null
        ]
        
        for field, expected_type in type_checks:
            if not isinstance(data[field], expected_type):
                print(f"❌ Field '{field}' has wrong type: expected {expected_type}, got {type(data[field])}")
                return False
        
        print("✅ Field types correct: PASSED")
        
        # Test agent_health structure
        agent_health = data["agent_health"]
        agent_health_fields = [
            "is_making_on_chain_transactions",
            "is_staking_kpi_met",
            "has_required_funds"
        ]
        
        for field in agent_health_fields:
            if field not in agent_health:
                print(f"❌ Missing agent_health field: {field}")
                return False
            if not isinstance(agent_health[field], bool):
                print(f"❌ agent_health.{field} must be boolean, got {type(agent_health[field])}")
                return False
        
        print("✅ Agent health structure: PASSED")
        
        # Test rounds_info structure (if not null)
        if data["rounds_info"] is not None:
            rounds_info = data["rounds_info"]
            rounds_info_fields = ["total_rounds", "latest_round", "average_round_duration"]
            
            for field in rounds_info_fields:
                if field not in rounds_info:
                    print(f"❌ Missing rounds_info field: {field}")
                    return False
            
            if not isinstance(rounds_info["total_rounds"], int):
                print(f"❌ rounds_info.total_rounds must be int, got {type(rounds_info['total_rounds'])}")
                return False
            
            if not isinstance(rounds_info["average_round_duration"], (int, float)):
                print(f"❌ rounds_info.average_round_duration must be number, got {type(rounds_info['average_round_duration'])}")
                return False
            
            print("✅ Rounds info structure: PASSED")
        else:
            print("✅ Rounds info is null (acceptable): PASSED")
        
        return True
        
    except Exception as e:
        print(f"❌ Structure test failed: {e}")
        return False

def test_response_time():
    """Test that response time meets Pearl requirements (<100ms)."""
    print("\n=== Testing Response Time ===")
    
    try:
        # Warm up
        requests.get("http://localhost:8716/healthcheck", timeout=5)
        
        # Measure multiple requests
        times = []
        for i in range(5):
            start_time = time.time()
            response = requests.get("http://localhost:8716/healthcheck", timeout=5)
            end_time = time.time()
            
            if response.status_code == 200:
                response_time = (end_time - start_time) * 1000
                times.append(response_time)
            else:
                print(f"❌ Request {i+1} failed with status {response.status_code}")
                return False
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)
        
        print(f"Response times: min={min_time:.2f}ms, avg={avg_time:.2f}ms, max={max_time:.2f}ms")
        
        if max_time < 100:
            print("✅ Response time requirement met: PASSED")
            return True
        else:
            print(f"❌ Response time too slow: {max_time:.2f}ms exceeds 100ms requirement")
            return False
            
    except Exception as e:
        print(f"❌ Response time test failed: {e}")
        return False

def test_concurrent_requests():
    """Test concurrent request handling."""
    print("\n=== Testing Concurrent Requests ===")
    
    try:
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            try:
                response = requests.get("http://localhost:8716/healthcheck", timeout=5)
                results.put(("success", response.status_code, response.json()))
            except Exception as e:
                results.put(("error", str(e), None))
        
        # Launch 10 concurrent requests
        threads = []
        for _ in range(10):
            t = threading.Thread(target=make_request)
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Check results
        success_count = 0
        error_count = 0
        
        while not results.empty():
            status, data, json_data = results.get()
            if status == "success" and data == 200:
                success_count += 1
            else:
                error_count += 1
        
        print(f"Successful requests: {success_count}/10")
        print(f"Failed requests: {error_count}/10")
        
        if success_count == 10:
            print("✅ Concurrent requests: PASSED")
            return True
        else:
            print(f"❌ Some concurrent requests failed: {error_count} failures")
            return False
            
    except Exception as e:
        print(f"❌ Concurrent request test failed: {e}")
        return False

def test_optional_fields(data: Dict[str, Any]):
    """Test optional fields if present."""
    print("\n=== Testing Optional Fields ===")
    
    try:
        optional_fields = ["period", "reset_pause_duration"]
        
        for field in optional_fields:
            if field in data:
                if not isinstance(data[field], (int, float)):
                    print(f"❌ Optional field '{field}' must be a number, got {type(data[field])}")
                    return False
                if data[field] <= 0:
                    print(f"❌ Optional field '{field}' must be positive, got {data[field]}")
                    return False
                print(f"✅ Optional field '{field}': {data[field]} (valid)")
            else:
                print(f"ℹ️  Optional field '{field}': not present")
        
        print("✅ Optional fields validation: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Optional fields test failed: {e}")
        return False

def print_response_details(data: Dict[str, Any]):
    """Print detailed response information."""
    print("\n=== Response Details ===")
    print(json.dumps(data, indent=2))

def main():
    """Run all live endpoint tests."""
    print("=== Live Healthcheck Endpoint Tests for Issue #150 ===")
    print("Testing against: http://localhost:8716/healthcheck")
    print()
    
    # Test endpoint accessibility
    accessible, data = test_endpoint_accessibility()
    if not accessible:
        print("\n💥 Cannot access endpoint - tests cannot continue")
        return 1
    
    # Print response details
    print_response_details(data)
    
    # Run all tests
    tests = [
        ("Response Structure", lambda: test_response_structure(data)),
        ("Response Time", test_response_time),
        ("Concurrent Requests", test_concurrent_requests),
        ("Optional Fields", lambda: test_optional_fields(data)),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
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
        print("🎉 All live endpoint tests PASSED!")
        print("✅ Healthcheck endpoint is Pearl-compliant and working correctly!")
        return 0
    else:
        print("💥 Some live endpoint tests FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())