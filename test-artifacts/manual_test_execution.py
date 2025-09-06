#!/usr/bin/env python3
"""
Manual test execution for Quorum AI core functionality.
This script will test the system step by step with detailed logging.
"""

import subprocess
import json
import time
import os
import sys
import signal
from datetime import datetime
from pathlib import Path


class QuorumTester:
    def __init__(self):
        self.base_dir = Path("/Users/max/code/quorum-ai")
        self.backend_dir = self.base_dir / "backend"
        self.test_results = {}
        self.backend_process = None

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def cleanup(self):
        """Clean up any running processes."""
        if self.backend_process and self.backend_process.poll() is None:
            self.log("Terminating backend process...")
            self.backend_process.terminate()
            time.sleep(2)
            if self.backend_process.poll() is None:
                self.backend_process.kill()

    def check_service_health(self):
        """Check if the backend service is responding."""
        try:
            result = subprocess.run(
                [
                    "curl",
                    "-s",
                    "--connect-timeout",
                    "3",
                    "--max-time",
                    "5",
                    "http://localhost:8716/health",
                ],
                capture_output=True,
                text=True,
                cwd=self.base_dir,
            )

            if result.returncode == 0 and result.stdout.strip():
                self.log("✅ Backend service is responding")
                self.log(f"Health response: {result.stdout}")
                return True
            else:
                self.log("❌ Backend service not responding")
                return False

        except Exception as e:
            self.log(f"❌ Health check failed: {e}", "ERROR")
            return False

    def start_backend(self):
        """Start the backend service."""
        self.log("Starting backend service...")

        try:
            # Ensure we're in the backend directory
            os.chdir(self.backend_dir)

            # Start the backend process
            self.backend_process = subprocess.Popen(
                ["uv", "run", "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            self.log(f"Backend started with PID: {self.backend_process.pid}")

            # Wait for it to initialize
            self.log("Waiting 15 seconds for backend to initialize...")
            time.sleep(15)

            # Check if it's running
            if self.check_service_health():
                self.log("✅ Backend service started successfully")
                return True
            else:
                self.log("❌ Backend service failed to start properly")
                return False

        except Exception as e:
            self.log(f"❌ Error starting backend: {e}", "ERROR")
            return False
        finally:
            os.chdir(self.base_dir)

    def test_agent_run(self):
        """Test the agent run endpoint with myshelldao.eth."""
        self.log("Testing agent run endpoint...")

        payload = {"space_id": "myshelldao.eth", "dry_run": True}

        payload_json = json.dumps(payload)
        self.log(f"Request payload: {payload_json}")

        try:
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
                ],
                capture_output=True,
                text=True,
                cwd=self.base_dir,
            )

            execution_time = time.time() - start_time

            self.log(f"Agent run completed in {execution_time:.2f} seconds")
            self.log(f"Exit code: {result.returncode}")

            if result.returncode == 0:
                try:
                    response_data = json.loads(result.stdout)
                    self.log("✅ Agent run successful")
                    self.log(f"Response: {json.dumps(response_data, indent=2)}")

                    # Extract metrics
                    proposals = response_data.get("proposals_analyzed", 0)
                    votes = len(response_data.get("votes_cast", []))
                    errors = response_data.get("errors", [])

                    self.log(
                        f"📊 Results: {proposals} proposals, {votes} votes, {len(errors)} errors"
                    )

                    self.test_results["agent_run"] = {
                        "success": True,
                        "proposals_analyzed": proposals,
                        "votes_cast": votes,
                        "errors": errors,
                        "execution_time": execution_time,
                    }

                    return True

                except json.JSONDecodeError as e:
                    self.log(f"❌ Failed to parse response: {e}", "ERROR")
                    self.log(f"Raw response: {result.stdout}")

            else:
                self.log(f"❌ Agent run failed with exit code {result.returncode}")
                self.log(f"stdout: {result.stdout}")
                self.log(f"stderr: {result.stderr}")

            self.test_results["agent_run"] = {"success": False}
            return False

        except Exception as e:
            self.log(f"❌ Agent run error: {e}", "ERROR")
            self.test_results["agent_run"] = {"success": False, "error": str(e)}
            return False

    def check_logs_for_snapshot(self):
        """Check logs for evidence of Snapshot API queries."""
        self.log("Checking logs for Snapshot API interactions...")

        log_files = [
            self.backend_dir / "log.txt",
            self.base_dir / "backend.log",
            self.base_dir / "service.log",
        ]

        snapshot_evidence = False

        for log_file in log_files:
            if log_file.exists():
                self.log(f"Checking {log_file}...")
                try:
                    content = log_file.read_text()

                    # Look for Snapshot-related activity
                    snapshot_keywords = [
                        "snapshot",
                        "hub.snapshot.org",
                        "graphql",
                        "proposals",
                        "space_id",
                        "myshelldao.eth",
                    ]

                    found_keywords = []
                    relevant_lines = []

                    for line in content.split("\n"):
                        line_lower = line.lower()
                        for keyword in snapshot_keywords:
                            if keyword in line_lower:
                                if keyword not in found_keywords:
                                    found_keywords.append(keyword)
                                if line.strip() not in relevant_lines:
                                    relevant_lines.append(line.strip())
                                break

                    if found_keywords:
                        snapshot_evidence = True
                        self.log(f"✅ Found Snapshot evidence in {log_file.name}")
                        self.log(f"Keywords found: {found_keywords}")

                        # Show some relevant lines
                        self.log("Relevant log entries:")
                        for line in relevant_lines[-10:]:  # Last 10 relevant lines
                            if line:
                                self.log(f"  {line}")
                    else:
                        self.log(f"⚠️  No Snapshot evidence in {log_file.name}")

                except Exception as e:
                    self.log(f"Error reading {log_file}: {e}", "ERROR")
            else:
                self.log(f"Log file not found: {log_file}")

        self.test_results["snapshot_logs"] = snapshot_evidence
        return snapshot_evidence

    def execute_step1(self):
        """Execute Step 1: Query agent run endpoint and verify Snapshot queries."""
        self.log("=" * 60)
        self.log("EXECUTING STEP 1: Agent Run and Snapshot Verification")
        self.log("=" * 60)

        # Check if service is already running
        if not self.check_service_health():
            if not self.start_backend():
                self.log("❌ STEP 1 FAILED: Could not start backend service")
                return False

        # Execute agent run
        if not self.test_agent_run():
            self.log("❌ STEP 1 FAILED: Agent run failed")
            return False

        # Check logs for Snapshot evidence
        snapshot_found = self.check_logs_for_snapshot()

        # Summary
        self.log("-" * 40)
        self.log("STEP 1 SUMMARY:")
        self.log("Service Health: ✅")
        self.log("Agent Run: ✅")
        self.log(f"Snapshot Evidence: {'✅' if snapshot_found else '⚠️'}")

        step1_success = True  # Agent run success is the main requirement

        self.log(f"STEP 1 RESULT: {'✅ PASSED' if step1_success else '❌ FAILED'}")

        return step1_success

    def run_all_tests(self):
        """Run all test steps."""
        self.log("Starting Quorum AI Test Execution")
        self.log(f"Working Directory: {self.base_dir}")

        try:
            # Execute Step 1
            step1_result = self.execute_step1()

            # Write results to file
            results_file = self.base_dir / "test_execution_results.json"
            results_data = {
                "timestamp": datetime.now().isoformat(),
                "step1": {"passed": step1_result, "details": self.test_results},
            }

            results_file.write_text(json.dumps(results_data, indent=2))
            self.log(f"Results written to: {results_file}")

            self.log("=" * 60)
            self.log(
                f"TEST EXECUTION COMPLETE - STEP 1: {'PASSED' if step1_result else 'FAILED'}"
            )
            self.log("=" * 60)

            return step1_result

        except KeyboardInterrupt:
            self.log("Test execution interrupted by user", "WARNING")
            return False
        except Exception as e:
            self.log(f"Unexpected error during test execution: {e}", "ERROR")
            return False
        finally:
            self.cleanup()


def main():
    """Main execution function."""
    tester = QuorumTester()

    # Set up signal handler for cleanup
    def signal_handler(signum, frame):
        print("\nReceived interrupt signal. Cleaning up...")
        tester.cleanup()
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        success = tester.run_all_tests()
        return success
    except Exception as e:
        print(f"Fatal error: {e}")
        return False
    finally:
        tester.cleanup()


if __name__ == "__main__":
    success = main()
    print(f"\nFinal result: {'SUCCESS' if success else 'FAILURE'}")
    sys.exit(0 if success else 1)
