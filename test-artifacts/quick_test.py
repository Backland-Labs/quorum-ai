#!/usr/bin/env python3

import subprocess
import json
import time
import os
from datetime import datetime


def main():
    print("=== QUORUM AI STEP 1 TEST ===")
    print(f"Time: {datetime.now().isoformat()}")

    # Change to project directory
    os.chdir("/Users/max/code/quorum-ai")

    # Quick health check
    print("\n1. Health Check:")
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:8716/health"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        print(f"  Status: {result.returncode}")
        print(f"  Response: {result.stdout}")

        if result.returncode != 0 or not result.stdout.strip():
            print("  ❌ Service not running - need to start it")

            # Try to start backend
            print("\n2. Starting Backend:")
            os.chdir("backend")

            # Start backend in background
            process = subprocess.Popen(["uv", "run", "main.py"])
            print(f"  Started backend with PID: {process.pid}")

            # Wait for startup
            print("  Waiting 20 seconds for startup...")
            time.sleep(20)

            # Test again
            os.chdir("/Users/max/code/quorum-ai")
            result = subprocess.run(
                ["curl", "-s", "http://localhost:8716/health"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            print(f"  Health recheck: {result.returncode}")
            print(f"  Response: {result.stdout}")

        else:
            print("  ✅ Service is running")

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return

    # Test agent run
    print("\n3. Testing Agent Run:")
    payload = json.dumps({"space_id": "myshelldao.eth", "dry_run": True})

    try:
        result = subprocess.run(
            [
                "curl",
                "-X",
                "POST",
                "http://localhost:8716/agent-run",
                "-H",
                "Content-Type: application/json",
                "-d",
                payload,
                "--connect-timeout",
                "10",
                "--max-time",
                "120",
            ],
            capture_output=True,
            text=True,
        )

        print(f"  Status: {result.returncode}")
        print(f"  Response length: {len(result.stdout)}")

        if result.stdout:
            try:
                data = json.loads(result.stdout)
                print(
                    f"  ✅ Success - Analyzed {data.get('proposals_analyzed', 0)} proposals"
                )
                print(f"  Votes cast: {len(data.get('votes_cast', []))}")
                print(f"  Errors: {len(data.get('errors', []))}")
            except:
                print(f"  Raw response: {result.stdout[:200]}...")

        if result.stderr:
            print(f"  Stderr: {result.stderr}")

    except subprocess.TimeoutExpired:
        print("  ❌ Timeout after 120 seconds")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    main()
