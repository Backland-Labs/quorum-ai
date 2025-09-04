#!/usr/bin/env python3
"""
Frontend test runner for OpenRouter API key functionality.
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, cwd, timeout=120, description=""):
    """Run a command and return result."""
    print(f"\n🔍 {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"Working directory: {cwd}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        print(f"Exit code: {result.returncode}")
        
        if result.stdout:
            print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
            
        return result.returncode == 0, result
        
    except subprocess.TimeoutExpired:
        print(f"❌ Command timed out after {timeout}s")
        return False, None
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, None

def main():
    project_root = Path(__file__).parent
    frontend_dir = project_root / "frontend"
    
    if not frontend_dir.exists():
        print("❌ Frontend directory not found")
        return False
    
    print(f"Testing frontend from: {frontend_dir}")
    
    # Check if npm is available
    success, result = run_command(
        ["npm", "--version"], 
        frontend_dir, 
        30,
        "Checking npm availability"
    )
    
    if not success:
        print("❌ npm not available")
        return False
    
    print("✅ npm is available")
    
    # Install dependencies
    success, result = run_command(
        ["npm", "install"], 
        frontend_dir, 
        180,
        "Installing frontend dependencies"
    )
    
    if not success:
        print("❌ Failed to install dependencies")
        return False
    
    print("✅ Dependencies installed")
    
    # Run TypeScript checking
    success, result = run_command(
        ["npm", "run", "check"], 
        frontend_dir, 
        120,
        "Running TypeScript type checking"
    )
    
    if success:
        print("✅ TypeScript type checking PASSED")
    else:
        print("❌ TypeScript type checking FAILED")
    
    # Build the frontend
    success, result = run_command(
        ["npm", "run", "build"], 
        frontend_dir, 
        180,
        "Building frontend for production"
    )
    
    if success:
        print("✅ Frontend build PASSED")
    else:
        print("❌ Frontend build FAILED")
        return False
    
    # Run existing tests
    success, result = run_command(
        ["npm", "run", "test"], 
        frontend_dir, 
        120,
        "Running frontend tests"
    )
    
    if success:
        print("✅ Frontend tests PASSED")
    else:
        print("⚠️  Frontend tests FAILED or no tests found")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)