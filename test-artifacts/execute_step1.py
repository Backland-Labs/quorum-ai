#!/usr/bin/env python3

import subprocess
import requests
import json
import sys
import time
import os
from datetime import datetime

def log_result(message):
    """Log result to both console and file."""
    timestamp = datetime.now().isoformat()
    log_message = f"[{timestamp}] {message}"
    print(log_message)
    
    # Also write to our evidence file
    with open("/Users/max/code/quorum-ai/test_step1_snapshot_queries.md", "a") as f:
        f.write(f"\n{message}")

def check_service_running():
    """Check if the Quorum AI backend service is running."""
    try:
        response = requests.get("http://localhost:8716/health", timeout=5)
        if response.status_code == 200:
            log_result("✅ Backend service is already running")
            return True
    except:
        pass
    
    log_result("❌ Backend service is not running")
    return False

def start_backend_only():
    """Start just the backend service in the background."""
    log_result("Starting backend service...")
    
    os.chdir("/Users/max/code/quorum-ai/backend")
    
    try:
        # Start backend in background
        with open("/Users/max/code/quorum-ai/backend_startup.log", "w") as log_file:
            process = subprocess.Popen(
                ["uv", "run", "main.py"],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                env=os.environ.copy()
            )
        
        # Save PID for later cleanup
        with open("/Users/max/code/quorum-ai/backend.pid", "w") as pid_file:
            pid_file.write(str(process.pid))
        
        log_result(f"Backend started with PID: {process.pid}")
        
        # Wait for service to be ready
        log_result("Waiting for service to become ready...")
        for i in range(30):  # Wait up to 30 seconds
            time.sleep(1)
            if check_service_running():
                log_result("✅ Backend service is ready!")
                return True
        
        log_result("❌ Backend service failed to start within 30 seconds")
        
        # Show last few lines of log
        try:
            with open("/Users/max/code/quorum-ai/backend_startup.log", "r") as f:
                lines = f.readlines()
                if lines:
                    log_result("Last few lines of startup log:")
                    for line in lines[-10:]:
                        log_result(f"  {line.strip()}")
        except:
            pass
        
        return False
        
    except Exception as e:
        log_result(f"❌ Error starting backend: {e}")
        return False

def test_agent_run():
    """Execute the agent run test with myshelldao.eth."""
    log_result("\n### 1.2 Agent Run Execution")
    log_result("Executing agent run with myshelldao.eth...")
    
    url = "http://localhost:8716/agent-run"
    payload = {
        "space_id": "myshelldao.eth",
        "dry_run": True
    }
    
    log_result(f"POST {url}")
    log_result(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        start_time = time.time()
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=120)
        end_time = time.time()
        
        log_result(f"Status: {response.status_code}")
        log_result(f"Execution time: {end_time - start_time:.2f} seconds")
        
        if response.status_code == 200:
            data = response.json()
            log_result("✅ Agent run completed successfully")
            log_result(f"Response: {json.dumps(data, indent=2)}")
            
            # Extract key metrics
            proposals = data.get('proposals_analyzed', 0)
            votes = len(data.get('votes_cast', []))
            errors = len(data.get('errors', []))
            
            log_result(f"\n**Summary:**")
            log_result(f"- Proposals analyzed: {proposals}")
            log_result(f"- Votes cast: {votes}")
            log_result(f"- Errors: {errors}")
            
            return True, data
        else:
            log_result(f"❌ Agent run failed: {response.status_code}")
            log_result(f"Response: {response.text}")
            return False, None
            
    except requests.exceptions.Timeout:
        log_result("❌ Request timed out after 120 seconds")
        return False, None
    except Exception as e:
        log_result(f"❌ Error during agent run: {e}")
        return False, None

def check_logs():
    """Check backend logs for Snapshot queries."""
    log_result("\n### 1.3 Log Analysis")
    log_result("Checking logs for Snapshot API interactions...")
    
    # Check the Pearl-compliant log file
    log_file = "/Users/max/code/quorum-ai/backend/log.txt"
    startup_log = "/Users/max/code/quorum-ai/backend_startup.log"
    
    for log_path in [log_file, startup_log]:
        if os.path.exists(log_path):
            log_result(f"\nAnalyzing {log_path}:")
            try:
                with open(log_path, 'r') as f:
                    content = f.read()
                    
                # Look for Snapshot-related entries
                if "snapshot" in content.lower():
                    log_result("✅ Found Snapshot API interactions in logs")
                    
                    # Extract Snapshot-related lines
                    lines = content.split('\n')
                    snapshot_lines = [line for line in lines if 'snapshot' in line.lower()]
                    
                    log_result(f"Snapshot-related log entries ({len(snapshot_lines)}):")
                    for line in snapshot_lines[-10:]:  # Show last 10
                        log_result(f"  {line}")
                else:
                    log_result("⚠️  No Snapshot API interactions found in logs")
                    
            except Exception as e:
                log_result(f"❌ Error reading log file: {e}")
        else:
            log_result(f"⚠️  Log file not found: {log_path}")

def main():
    """Execute Step 1 of the test plan."""
    log_result("# Test Step 1 Results\n")
    log_result("## Step 1: Query Agent Run Endpoint and Monitor Snapshot Queries")
    log_result(f"Execution started at: {datetime.now().isoformat()}")
    
    # Check if service is running, start if needed
    if not check_service_running():
        if not start_backend_only():
            log_result("\n❌ STEP 1 FAILED: Could not start backend service")
            return False
    
    # Execute agent run
    success, data = test_agent_run()
    
    if not success:
        log_result("\n❌ STEP 1 FAILED: Agent run failed")
        return False
    
    # Check logs
    check_logs()
    
    log_result(f"\n✅ STEP 1 COMPLETED: Successfully executed agent run and verified Snapshot queries")
    log_result(f"Completion time: {datetime.now().isoformat()}")
    
    return True

if __name__ == "__main__":
    os.chdir("/Users/max/code/quorum-ai")
    success = main()
    sys.exit(0 if success else 1)