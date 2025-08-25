#!/usr/bin/env python3
"""Test runner for ActivityService functional tests"""

import os
import subprocess
import sys
import time


def run_command(command, description):
    """Run a command and return results"""
    print(f"\n{'='*80}")
    print(f"RUNNING: {description}")
    print(f"COMMAND: {command}")
    print(f"{'='*80}")

    try:
        start_time = time.time()
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,
            cwd="/Users/max/code/quorum-ai/backend",
            check=False,
        )
        end_time = time.time()
        duration = end_time - start_time

        print(f"Duration: {duration:.2f} seconds")
        print(f"Exit Code: {result.returncode}")

        if result.returncode == 0:
            print("✅ PASSED")
        else:
            print("❌ FAILED")

        print("\nSTDOUT:")
        print(result.stdout)

        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)

        return result.returncode == 0, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        print("❌ TIMEOUT: Command took longer than 5 minutes")
        return False, "", "Timeout"
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False, "", str(e)


def main():
    os.chdir("/Users/max/code/quorum-ai/backend")
    print(f"Working directory: {os.getcwd()}")

    # Test commands
    test_cases = [
        (
            "uv run pytest tests/test_activity_service.py -v",
            "ActivityService Core Tests",
        ),
        (
            "uv run pytest tests/test_service_integration.py -v",
            "Service Integration Tests",
        ),
        ("uv run pytest tests/test_models.py -v", "Pydantic Models Tests"),
        ("uv run pytest tests/test_main.py -v", "API Endpoints Tests"),
    ]

    results = {}

    for command, description in test_cases:
        success, stdout, stderr = run_command(command, description)
        results[description] = {"success": success, "stdout": stdout, "stderr": stderr}

    # Summary
    print(f"\n{'='*80}")
    print("FINAL TEST SUMMARY")
    print(f"{'='*80}")

    passed = 0
    failed = 0

    for test_name, result in results.items():
        if result["success"]:
            print(f"✅ PASSED: {test_name}")
            passed += 1
        else:
            print(f"❌ FAILED: {test_name}")
            failed += 1

    print(f"\nTotal: {passed + failed} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed > 0:
        sys.exit(1)
    else:
        print("\n🎉 All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
