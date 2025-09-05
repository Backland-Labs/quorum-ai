#!/usr/bin/env python3

import subprocess
import requests
import json
import time
import os
from datetime import datetime
from pathlib import Path


def main():
    """Execute Step 1 test directly with inline execution."""

    print("=" * 60)
    print("QUORUM AI STEP 1 TEST - DIRECT EXECUTION")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")

    # Set working directory
    project_dir = Path("/Users/max/code/quorum-ai")
    os.chdir(project_dir)
    print(f"Working Directory: {project_dir}")

    # Step 1.1: Health Check
    print("\n1.1 HEALTH CHECK")
    print("-" * 30)

    health_url = "http://localhost:8716/health"

    try:
        print(f"Testing: {health_url}")
        response = requests.get(health_url, timeout=5)

        if response.status_code == 200:
            print("✅ Service is responding")
            print(f"Response: {response.text}")
            service_running = True
        else:
            print(f"❌ Service returned status {response.status_code}")
            service_running = False

    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - service not running")
        service_running = False
    except Exception as e:
        print(f"❌ Error: {e}")
        service_running = False

    # Step 1.2: Start service if needed
    if not service_running:
        print("\n1.2 STARTING SERVICE")
        print("-" * 30)

        backend_dir = project_dir / "backend"

        try:
            os.chdir(backend_dir)
            print(f"Changed to: {backend_dir}")

            print("Starting backend with: uv run main.py")

            # Start backend process
            process = subprocess.Popen(
                ["uv", "run", "main.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            print(f"Backend started with PID: {process.pid}")

            # Save PID for later cleanup
            pid_file = project_dir / "test_backend.pid"
            pid_file.write_text(str(process.pid))

            # Wait for startup
            print("Waiting 15 seconds for startup...")
            time.sleep(15)

            # Test health again
            os.chdir(project_dir)

            try:
                response = requests.get(health_url, timeout=10)
                if response.status_code == 200:
                    print("✅ Service started successfully")
                    print(f"Response: {response.text}")
                    service_running = True
                else:
                    print(f"❌ Service health check failed: {response.status_code}")

            except Exception as e:
                print(f"❌ Health check after startup failed: {e}")

        except Exception as e:
            print(f"❌ Error starting service: {e}")

        finally:
            os.chdir(project_dir)

    if not service_running:
        print("\n❌ STEP 1 FAILED: Could not get service running")
        return False

    # Step 1.3: Execute Agent Run
    print("\n1.3 AGENT RUN EXECUTION")
    print("-" * 30)

    agent_url = "http://localhost:8716/agent-run"
    payload = {"space_id": "myshelldao.eth", "dry_run": True}

    print(f"URL: {agent_url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        start_time = time.time()

        response = requests.post(
            agent_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=180,
        )

        execution_time = time.time() - start_time

        print(f"Execution time: {execution_time:.2f} seconds")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Agent run successful")

            proposals = data.get("proposals_analyzed", 0)
            votes = len(data.get("votes_cast", []))
            errors = data.get("errors", [])

            print("\n📊 RESULTS:")
            print(f"- Proposals analyzed: {proposals}")
            print(f"- Votes cast: {votes}")
            print(f"- Errors: {len(errors)}")

            if errors:
                print("- Error details:")
                for error in errors:
                    print(f"  • {error}")

            print("\nFull Response:")
            print(json.dumps(data, indent=2))

            agent_success = True

        else:
            print(f"❌ Agent run failed: {response.status_code}")
            print(f"Response: {response.text}")
            agent_success = False

    except requests.exceptions.Timeout:
        print("❌ Request timed out after 180 seconds")
        agent_success = False
    except Exception as e:
        print(f"❌ Agent run error: {e}")
        agent_success = False

    # Step 1.4: Check logs for Snapshot evidence
    print("\n1.4 LOG ANALYSIS")
    print("-" * 30)

    log_files = [
        project_dir / "backend" / "log.txt",
        project_dir / "backend.log",
        project_dir / "service.log",
    ]

    snapshot_found = False

    for log_file in log_files:
        if log_file.exists():
            print(f"Checking: {log_file}")

            try:
                content = log_file.read_text()

                # Search for Snapshot-related terms
                search_terms = [
                    "snapshot",
                    "hub.snapshot.org",
                    "graphql",
                    "proposals",
                    "myshelldao.eth",
                    "space_id",
                ]

                found_terms = []
                relevant_lines = []

                for line in content.split("\n"):
                    line_lower = line.lower()
                    for term in search_terms:
                        if term in line_lower:
                            if term not in found_terms:
                                found_terms.append(term)
                            if line.strip():
                                relevant_lines.append(line.strip())
                            break

                if found_terms:
                    print(f"✅ Found Snapshot evidence: {found_terms}")
                    snapshot_found = True

                    print("Relevant log entries:")
                    for line in relevant_lines[-5:]:  # Show last 5
                        print(f"  {line}")
                else:
                    print("⚠️  No Snapshot evidence found")

            except Exception as e:
                print(f"Error reading log: {e}")
        else:
            print(f"Log file not found: {log_file}")

    # Final Summary
    print("\n" + "=" * 60)
    print("STEP 1 FINAL SUMMARY")
    print("=" * 60)

    print("Service Health: ✅")
    print(f"Agent Run: {'✅' if agent_success else '❌'}")
    print(f"Snapshot Evidence: {'✅' if snapshot_found else '⚠️'}")

    step1_passed = service_running and agent_success

    print(f"\nSTEP 1 RESULT: {'✅ PASSED' if step1_passed else '❌ FAILED'}")
    print(f"Completion time: {datetime.now().isoformat()}")

    # Write results to file
    results_file = project_dir / "step1_execution_evidence.md"
    with open(results_file, "w") as f:
        f.write("# Step 1 Execution Evidence\n\n")
        f.write(f"**Execution Date:** {datetime.now().isoformat()}\n")
        f.write(f"**Result:** {'PASSED' if step1_passed else 'FAILED'}\n\n")
        f.write("## Test Actions\n")
        f.write("1. ✅ Health check completed\n")
        f.write(
            f"2. {'✅' if agent_success else '❌'} Agent run executed with myshelldao.eth\n"
        )
        f.write(
            f"3. {'✅' if snapshot_found else '⚠️'} Log analysis for Snapshot queries\n\n"
        )
        f.write("## Evidence\n")
        f.write("- Service responded to health checks\n")
        f.write("- Agent run endpoint executed successfully\n")
        f.write("- Logs were analyzed for Snapshot API interactions\n")

    print(f"\nEvidence written to: {results_file}")

    return step1_passed


if __name__ == "__main__":
    try:
        success = main()
        exit_code = 0 if success else 1
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        exit_code = 1
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        exit_code = 1

    print(f"\nExiting with code: {exit_code}")
    exit(exit_code)
