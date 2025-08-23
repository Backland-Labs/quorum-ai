#!/usr/bin/env python3
"""Script to run tests and capture output"""

import subprocess
import os


def run_test_command(command, description):
    """Run a test command and capture output"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}")

    try:
        # Change to backend directory
        os.chdir("/Users/max/code/quorum-ai/backend")

        # Run the command
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        print(f"Exit code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")

        if result.stderr:
            print(f"STDERR:\n{result.stderr}")

        return result.returncode == 0, result.stdout, result.stderr

    except Exception as e:
        print(f"Error running command: {e}")
        return False, "", str(e)


def main():
    # Test commands to run
    test_commands = [
        (
            "uv run pytest tests/test_activity_service.py -v",
            "ActivityService core functionality tests",
        ),
        (
            "uv run pytest tests/test_service_integration.py -v",
            "Service integration tests",
        ),
        ("uv run pytest tests/test_models.py -v", "Pydantic models tests"),
        ("uv run pytest tests/test_main.py -v", "API endpoints tests (main.py)"),
    ]

    results = []

    for command, description in test_commands:
        success, stdout, stderr = run_test_command(command, description)
        results.append((description, success, stdout, stderr))

        if not success:
            print(f"❌ {description} FAILED")
        else:
            print(f"✅ {description} PASSED")

    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")

    for description, success, _, _ in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {description}")


if __name__ == "__main__":
    main()
