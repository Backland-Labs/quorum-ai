#!/usr/bin/env python3
"""
Script to run OpenRouter API key management tests from the correct directory.
"""

import os
import sys
import subprocess

def run_tests():
    # Change to backend directory
    backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
    os.chdir(backend_dir)
    
    print("Changed to backend directory:", os.getcwd())
    print("Running OpenRouter API key management tests...\n")
    
    # Check what test files exist
    test_files = [
        "tests/test_openrouter_key_management.py",
        "tests/test_api_endpoints.py", 
        "tests/test_key_manager.py",
        "tests/test_user_preferences_service.py"
    ]
    
    for test_file in test_files:
        print(f"\nChecking if {test_file} exists: {os.path.exists(test_file)}")
        
        if os.path.exists(test_file):
            print(f"\n{'='*60}")
            print(f"RUNNING: {test_file}")
            print(f"{'='*60}")
            
            try:
                result = subprocess.run(
                    ["uv", "run", "pytest", test_file, "-v", "--tb=short"], 
                    capture_output=True, 
                    text=True,
                    timeout=120
                )
                
                print(f"EXIT CODE: {result.returncode}")
                print(f"STDOUT:\n{result.stdout}")
                if result.stderr:
                    print(f"STDERR:\n{result.stderr}")
                    
            except subprocess.TimeoutExpired:
                print("Test timed out after 120 seconds")
            except Exception as e:
                print(f"Error running test: {e}")
        else:
            print(f"⚠️  Test file not found: {test_file}")
    
    # Also try running all tests to check for any regressions
    print(f"\n{'='*60}")
    print("RUNNING: Full backend test suite")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            ["uv", "run", "pytest", "--tb=short", "-x"], 
            capture_output=True, 
            text=True,
            timeout=300
        )
        
        print(f"EXIT CODE: {result.returncode}")
        print(f"STDOUT (last 100 lines):")
        stdout_lines = result.stdout.split('\n')
        print('\n'.join(stdout_lines[-100:]))
        
        if result.stderr:
            print(f"STDERR (last 50 lines):")
            stderr_lines = result.stderr.split('\n')  
            print('\n'.join(stderr_lines[-50:]))
            
    except subprocess.TimeoutExpired:
        print("Full test suite timed out after 300 seconds")
    except Exception as e:
        print(f"Error running full test suite: {e}")

if __name__ == "__main__":
    run_tests()