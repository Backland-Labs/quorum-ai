#!/usr/bin/env python3

import subprocess
import sys
import os


def main():
    """Execute the Step 1 test and capture output."""

    print("Executing Quorum AI Step 1 Test...")
    print("=" * 50)

    # Change to the correct directory
    os.chdir("/Users/max/code/quorum-ai")

    try:
        # Execute the test script
        result = subprocess.run(
            [sys.executable, "run_step1_test.py"], text=True, capture_output=False
        )

        print("=" * 50)
        print(f"Test execution completed with exit code: {result.returncode}")

        return result.returncode == 0

    except Exception as e:
        print(f"Error executing test: {e}")
        return False


if __name__ == "__main__":
    success = main()
    print(f"Step 1 test {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)
