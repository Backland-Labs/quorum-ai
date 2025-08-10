#!/usr/bin/env python3
"""
Test runner for healthcheck functional tests - GitHub issue #150
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd, 
            cwd=cwd, 
            capture_output=True, 
            text=True, 
            check=False
        )
        return result
    except Exception as e:
        print(f"Error running command: {e}")
        return None

def main():
    """Main test runner function."""
    print("=== Running Healthcheck Functional Tests for Issue #150 ===")
    print()
    
    # Set up paths
    project_root = Path(__file__).parent
    backend_dir = project_root / "backend"
    
    if not backend_dir.exists():
        print(f"❌ Backend directory not found: {backend_dir}")
        return 1
    
    print(f"Backend directory: {backend_dir}")
    print()
    
    # Check if we can run uv
    uv_check = run_command(["which", "uv"])
    if uv_check and uv_check.returncode == 0:
        print("✅ Found uv command")
        test_cmd = ["uv", "run", "pytest"]
    else:
        print("⚠️  uv not found, trying pytest directly")
        test_cmd = ["pytest"]
    
    # Test files to run
    test_files = [
        "tests/test_health_check_service.py",
        "tests/test_healthcheck_endpoint.py"
    ]
    
    results = {}
    
    for test_file in test_files:
        print(f"=== Running {test_file} ===")
        
        cmd = test_cmd + [test_file, "-v"]
        result = run_command(cmd, cwd=backend_dir)
        
        if result:
            print("STDOUT:")
            print(result.stdout)
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
            
            results[test_file] = result.returncode == 0
            print(f"Exit code: {result.returncode}")
        else:
            results[test_file] = False
            print("❌ Failed to run test")
        
        print()
    
    # Summary
    print("=== Test Results Summary ===")
    all_passed = True
    for test_file, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_file}: {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 All healthcheck tests PASSED!")
        return 0
    else:
        print("💥 Some healthcheck tests FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())