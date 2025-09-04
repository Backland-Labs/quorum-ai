#!/usr/bin/env python3

import os
import subprocess
import sys
from pathlib import Path

def main():
    """Run the core test execution."""
    # Change to project directory
    os.chdir("/Users/max/code/quorum-ai")
    
    print("=== Starting Quorum AI Core Tests ===")
    
    # Make script executable and run it
    try:
        # Run the test execution script
        result = subprocess.run([
            sys.executable, "execute_core_tests.py"
        ], capture_output=False, text=True)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"Error running tests: {e}")
        return False

if __name__ == "__main__":
    success = main()
    print(f"\n=== Test execution {'completed successfully' if success else 'failed'} ===")
    sys.exit(0 if success else 1)