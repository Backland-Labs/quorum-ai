#!/usr/bin/env python3

import subprocess
import json
import time
import os
import sys
from datetime import datetime


def run_step1_test():
    """Execute Step 1 test with comprehensive logging."""

    print("=" * 60)
    print("QUORUM AI - STEP 1 TEST EXECUTION")
    print("=" * 60)
    print(f"Start Time: {datetime.now().isoformat()}")
    print(f"Working Directory: {os.getcwd()}")
    print()

    # Ensure we're in the right directory
    os.chdir("/Users/max/code/quorum-ai")
    print(f"Changed to directory: {os.getcwd()}")

    # Step 1.1: Check if service is running
    print("\n1.1 TESTING SERVICE CONNECTIVITY")
    print("-" * 40)

    # Simple curl health check
    try:
        print("Testing health endpoint...")
        result = subprocess.run(
            [
                "curl",
                "-s",
                "--connect-timeout",
                "5",
                "--max-time",
                "10",
                "http://localhost:8716/health",
            ],
            capture_output=True,
            text=True,
        )

        print(f"Health check exit code: {result.returncode}")
        print(f"Health response: {result.stdout}")

        if result.returncode == 0 and result.stdout:
            print("✅ Service is responding")
            service_running = True
        else:
            print("❌ Service not responding")
            service_running = False

    except Exception as e:
        print(f"❌ Health check error: {e}")
        service_running = False

    # If service not running, try to start it
    if not service_running:
        print("\n1.2 STARTING BACKEND SERVICE")
        print("-" * 40)

        try:
            print("Changing to backend directory...")
            os.chdir("/Users/max/code/quorum-ai/backend")

            print("Starting backend with uv run main.py...")

            # Start backend in background
            process = subprocess.Popen(
                ["uv", "run", "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=dict(os.environ),
            )

            print(f"Backend process started with PID: {process.pid}")

            # Save PID for cleanup
            with open("/Users/max/code/quorum-ai/test_backend.pid", "w") as f:
                f.write(str(process.pid))

            # Wait for service to start
            print("Waiting for service to initialize (15 seconds)...")
            time.sleep(15)

            # Test again
            os.chdir("/Users/max/code/quorum-ai")
            result = subprocess.run(
                [
                    "curl",
                    "-s",
                    "--connect-timeout",
                    "5",
                    "--max-time",
                    "10",
                    "http://localhost:8716/health",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0 and result.stdout:
                print("✅ Service started successfully")
                service_running = True
            else:
                print("❌ Service failed to start properly")
                print(f"Health check result: {result.stdout}")
                print(f"Health check stderr: {result.stderr}")

                # Try to get process output
                try:
                    stdout, stderr = process.communicate(timeout=1)
                    print(f"Process stdout: {stdout.decode()}")
                    print(f"Process stderr: {stderr.decode()}")
                except:
                    pass

        except Exception as e:
            print(f"❌ Error starting service: {e}")

    if not service_running:
        print("\n❌ STEP 1 FAILED: Could not get service running")
        return False

    # Step 1.3: Execute agent run
    print("\n1.3 EXECUTING AGENT RUN")
    print("-" * 40)

    payload = {"space_id": "myshelldao.eth", "dry_run": True}

    payload_json = json.dumps(payload)
    print(f"Request payload: {payload_json}")

    try:
        print("Executing agent run...")
        start_time = time.time()

        result = subprocess.run(
            [
                "curl",
                "-X",
                "POST",
                "http://localhost:8716/agent-run",
                "-H",
                "Content-Type: application/json",
                "-d",
                payload_json,
                "--connect-timeout",
                "10",
                "--max-time",
                "180",
                "-v",  # Verbose output
            ],
            capture_output=True,
            text=True,
        )

        end_time = time.time()
        execution_time = end_time - start_time

        print(f"Agent run completed in {execution_time:.2f} seconds")
        print(f"Exit code: {result.returncode}")
        print(f"Response: {result.stdout}")

        if result.stderr:
            print(f"Curl stderr: {result.stderr}")

        # Try to parse JSON response
        try:
            if result.stdout:
                data = json.loads(result.stdout)
                print("\n📊 AGENT RUN RESULTS:")
                print(f"Proposals analyzed: {data.get('proposals_analyzed', 'N/A')}")
                print(f"Votes cast: {len(data.get('votes_cast', []))}")
                print(f"Errors: {len(data.get('errors', []))}")

                if data.get("errors"):
                    print("Errors encountered:")
                    for error in data.get("errors", []):
                        print(f"  - {error}")

                agent_run_success = True

            else:
                print("❌ Empty response from agent run")
                agent_run_success = False

        except json.JSONDecodeError as e:
            print(f"⚠️ Could not parse JSON response: {e}")
            print(f"Raw response: {result.stdout}")
            agent_run_success = False

    except Exception as e:
        print(f"❌ Agent run error: {e}")
        agent_run_success = False

    # Step 1.4: Check logs for Snapshot queries
    print("\n1.4 CHECKING LOGS FOR SNAPSHOT QUERIES")
    print("-" * 40)

    log_files_to_check = [
        "/Users/max/code/quorum-ai/backend/log.txt",
        "/Users/max/code/quorum-ai/backend/service.log",
    ]

    snapshot_found = False

    for log_file in log_files_to_check:
        if os.path.exists(log_file):
            print(f"Checking {log_file}...")
            try:
                with open(log_file, "r") as f:
                    content = f.read()

                # Look for Snapshot-related terms
                snapshot_terms = [
                    "snapshot",
                    "graphql",
                    "hub.snapshot.org",
                    "proposals",
                ]
                found_terms = []

                for term in snapshot_terms:
                    if term.lower() in content.lower():
                        found_terms.append(term)

                if found_terms:
                    print(f"✅ Found Snapshot-related terms: {found_terms}")
                    snapshot_found = True

                    # Show relevant lines
                    lines = content.split("\n")
                    relevant_lines = []

                    for line in lines:
                        for term in snapshot_terms:
                            if term.lower() in line.lower():
                                relevant_lines.append(line.strip())
                                break

                    if relevant_lines:
                        print("Relevant log entries:")
                        for line in relevant_lines[-10:]:  # Last 10 relevant lines
                            print(f"  {line}")
                else:
                    print(f"⚠️ No Snapshot-related terms found in {log_file}")

            except Exception as e:
                print(f"Error reading {log_file}: {e}")
        else:
            print(f"Log file not found: {log_file}")

    # Summary
    print("\n" + "=" * 60)
    print("STEP 1 SUMMARY")
    print("=" * 60)

    if service_running and agent_run_success:
        status = "✅ PASSED"
    else:
        status = "❌ FAILED"

    print(f"Service Running: {'✅' if service_running else '❌'}")
    print(f"Agent Run Success: {'✅' if agent_run_success else '❌'}")
    print(f"Snapshot Queries Found: {'✅' if snapshot_found else '⚠️'}")
    print(f"Overall Status: {status}")
    print(f"End Time: {datetime.now().isoformat()}")

    return service_running and agent_run_success


if __name__ == "__main__":
    success = run_step1_test()

    # Write results to evidence file
    with open("/Users/max/code/quorum-ai/step1_test_results.md", "w") as f:
        f.write("# Step 1 Test Results\n\n")
        f.write(f"Execution Date: {datetime.now().isoformat()}\n")
        f.write(f"Result: {'PASSED' if success else 'FAILED'}\n\n")
        f.write("## Test Objective\n")
        f.write(
            "Query the agent run endpoint and monitor logs to verify successful Snapshot queries.\n\n"
        )
        f.write("## Evidence\n")
        f.write("See console output above for detailed execution log.\n")

    print("\nResults written to: /Users/max/code/quorum-ai/step1_test_results.md")
    sys.exit(0 if success else 1)
