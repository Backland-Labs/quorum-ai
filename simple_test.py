#!/usr/bin/env python3
"""
Simple test execution for healthcheck tests
"""

import os
import sys
import subprocess

# Add backend to Python path
backend_path = "/Users/max/code/q-issue-150/backend"
sys.path.insert(0, backend_path)

# Change to backend directory
os.chdir(backend_path)

def run_test(test_file):
    """Run a single test file."""
    print(f"\n=== Running {test_file} ===")
    
    # Try different ways to run the test
    commands_to_try = [
        ["uv", "run", "pytest", test_file, "-v", "--tb=short"],
        ["python", "-m", "pytest", test_file, "-v", "--tb=short"],
        ["pytest", test_file, "-v", "--tb=short"]
    ]
    
    for cmd in commands_to_try:
        try:
            print(f"Trying: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print("✅ SUCCESS!")
                print("STDOUT:")
                print(result.stdout)
                return True
            else:
                print(f"❌ FAILED (exit code: {result.returncode})")
                print("STDOUT:")
                print(result.stdout)
                if result.stderr:
                    print("STDERR:")
                    print(result.stderr)
                # Try next command
                continue
                
        except subprocess.TimeoutExpired:
            print("⏰ Test timed out")
            continue
        except FileNotFoundError:
            print(f"Command not found: {cmd[0]}")
            continue
        except Exception as e:
            print(f"Error: {e}")
            continue
    
    print("❌ All test execution methods failed")
    return False

def main():
    print("=== Healthcheck Functional Tests for Issue #150 ===")
    print(f"Working directory: {os.getcwd()}")
    
    test_files = [
        "tests/test_health_check_service.py",
        "tests/test_healthcheck_endpoint.py"
    ]
    
    results = {}
    
    for test_file in test_files:
        if os.path.exists(test_file):
            results[test_file] = run_test(test_file)
        else:
            print(f"❌ Test file not found: {test_file}")
            results[test_file] = False
    
    # Summary
    print("\n=== Test Results Summary ===")
    all_passed = True
    for test_file, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_file}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All healthcheck tests PASSED!")
        return 0
    else:
        print("\n💥 Some healthcheck tests FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())