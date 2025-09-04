#!/usr/bin/env python3
"""
Minimal test runner for OpenRouter API key functionality.
"""

import os
import subprocess
import sys
from pathlib import Path

def main():
    project_root = Path(__file__).parent
    backend_dir = project_root / "backend"
    
    if not backend_dir.exists():
        print("❌ Backend directory not found")
        return False
    
    # Change to backend directory
    original_dir = os.getcwd()
    os.chdir(backend_dir)
    
    try:
        print(f"Running tests from: {os.getcwd()}")
        
        # Check if OpenRouter key management test exists
        test_file = "tests/test_openrouter_key_management.py"
        if Path(test_file).exists():
            print(f"\n🔍 Testing: {test_file}")
            
            # Run the test
            cmd = ["uv", "run", "pytest", test_file, "-v", "-x"]
            print(f"Command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            print(f"Exit code: {result.returncode}")
            print(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                print(f"STDERR:\n{result.stderr}")
                
            if result.returncode == 0:
                print("✅ OpenRouter key management tests PASSED")
            else:
                print("❌ OpenRouter key management tests FAILED")
        else:
            print(f"❌ Test file not found: {test_file}")
            
        # Also test API endpoints
        test_file2 = "tests/test_api_endpoints.py" 
        if Path(test_file2).exists():
            print(f"\n🔍 Testing: {test_file2}")
            
            cmd = ["uv", "run", "pytest", test_file2, "-v", "-x"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            print(f"Exit code: {result.returncode}")
            print(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                print(f"STDERR:\n{result.stderr}")
                
            if result.returncode == 0:
                print("✅ API endpoints tests PASSED")
            else:
                print("❌ API endpoints tests FAILED")
        else:
            print(f"❌ Test file not found: {test_file2}")
        
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Tests timed out")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False
    finally:
        os.chdir(original_dir)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)