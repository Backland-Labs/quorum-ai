#!/usr/bin/env python3
"""
Direct test runner for OpenRouter API key functionality.
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, cwd, timeout=120):
    """Run a command and capture output."""
    try:
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result
    except subprocess.TimeoutExpired:
        print(f"Command timed out after {timeout}s")
        return None
    except Exception as e:
        print(f"Error running command: {e}")
        return None

def main():
    # Set up paths
    project_root = Path(__file__).parent
    backend_dir = project_root / "backend"
    
    print(f"Project root: {project_root}")
    print(f"Backend dir: {backend_dir}")
    
    if not backend_dir.exists():
        print("❌ Backend directory not found")
        return False
    
    os.chdir(backend_dir)
    print(f"Changed to: {os.getcwd()}")
    
    # Check what test files exist
    test_dir = Path("tests")
    target_tests = [
        "test_openrouter_key_management.py",
        "test_api_endpoints.py", 
        "test_key_manager.py",
        "test_user_preferences_service.py"
    ]
    
    existing_tests = []
    for test_file in target_tests:
        test_path = test_dir / test_file
        if test_path.exists():
            existing_tests.append(str(test_path))
            print(f"✅ Found: {test_path}")
        else:
            print(f"❌ Missing: {test_path}")
    
    if not existing_tests:
        print("❌ No target test files found")
        return False
    
    # Test if uv is working
    result = run_command(["uv", "--version"], backend_dir, 30)
    if not result or result.returncode != 0:
        print("❌ uv not available")
        return False
    
    print(f"✅ UV available: {result.stdout.strip()}")
    
    # Install dependencies if needed
    print("\nInstalling dependencies...")
    result = run_command(["uv", "sync"], backend_dir, 180)
    if result and result.returncode == 0:
        print("✅ Dependencies synchronized")
    else:
        print("⚠️  Dependency sync had issues")
        if result:
            print(f"Exit code: {result.returncode}")
            print(f"Stdout: {result.stdout}")
            print(f"Stderr: {result.stderr}")
    
    # Run each test file
    all_passed = True
    for test_path in existing_tests:
        print(f"\n{'='*60}")
        print(f"RUNNING: {test_path}")
        print(f"{'='*60}")
        
        result = run_command(
            ["uv", "run", "pytest", test_path, "-v", "--tb=short"], 
            backend_dir, 
            120
        )
        
        if result:
            print(f"Exit code: {result.returncode}")
            
            if result.returncode == 0:
                print(f"✅ {test_path} PASSED")
            else:
                print(f"❌ {test_path} FAILED")
                all_passed = False
            
            # Print output
            if result.stdout:
                print("STDOUT:")
                print(result.stdout)
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
        else:
            print(f"❌ {test_path} - Failed to execute")
            all_passed = False
    
    # Run a small regression test
    print(f"\n{'='*60}")
    print("RUNNING: Quick regression test")
    print(f"{'='*60}")
    
    regression_tests = []
    for test_file in ["test_models.py", "test_config.py"]:
        if (test_dir / test_file).exists():
            regression_tests.append(f"tests/{test_file}")
    
    if regression_tests:
        result = run_command(
            ["uv", "run", "pytest"] + regression_tests + ["-v", "--tb=short", "-x"], 
            backend_dir, 
            120
        )
        
        if result and result.returncode == 0:
            print("✅ Regression test PASSED")
        else:
            print("❌ Regression test FAILED") 
            if result:
                print(f"Exit code: {result.returncode}")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)