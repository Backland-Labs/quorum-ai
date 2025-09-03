#!/usr/bin/env python3

import subprocess
import requests
import json
import sys
import time
import os
from datetime import datetime

def test_step_1():
    """Execute Step 1: Query agent run endpoint and monitor Snapshot queries"""
    print("=== STEP 1: Query Agent Run Endpoint ===")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # First, test service health
    print("\n1.1 Testing service connectivity...")
    
    try:
        # Basic curl health check
        result = subprocess.run([
            'curl', '-s', '-w', '%{http_code}', '-o', '/tmp/health_response.json',
            'http://localhost:8716/health'
        ], capture_output=True, text=True, timeout=10)
        
        status_code = result.stdout.strip()
        print(f"Health endpoint status: {status_code}")
        
        if status_code == "200":
            print("✅ Service is running")
            
            # Read response
            try:
                with open('/tmp/health_response.json', 'r') as f:
                    health_data = f.read()
                    print(f"Health response: {health_data}")
            except:
                pass
                
        else:
            print("❌ Service not responding, attempting to start...")
            
            # Try to start the backend service
            os.chdir("/Users/max/code/quorum-ai/backend")
            
            print("Starting backend service...")
            process = subprocess.Popen([
                "uv", "run", "main.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            print(f"Backend started with PID: {process.pid}")
            
            # Wait for service to be ready
            print("Waiting for service to initialize...")
            time.sleep(10)
            
            # Re-test health
            result = subprocess.run([
                'curl', '-s', '-w', '%{http_code}', '-o', '/tmp/health_response2.json',
                'http://localhost:8716/health'
            ], capture_output=True, text=True, timeout=10)
            
            new_status = result.stdout.strip()
            if new_status == "200":
                print("✅ Service started successfully")
            else:
                print(f"❌ Service still not responding: {new_status}")
                return False
                
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    print("\n1.2 Executing agent run with myshelldao.eth...")
    
    # Change back to root directory
    os.chdir("/Users/max/code/quorum-ai")
    
    # Execute agent run
    payload = json.dumps({
        "space_id": "myshelldao.eth",
        "dry_run": True
    })
    
    print(f"Payload: {payload}")
    
    try:
        start_time = time.time()
        
        result = subprocess.run([
            'curl', '-X', 'POST',
            'http://localhost:8716/agent-run',
            '-H', 'Content-Type: application/json',
            '-d', payload,
            '-w', '\\nHTTP_CODE:%{http_code}\\nTIME:%{time_total}',
            '--connect-timeout', '10',
            '--max-time', '120'
        ], capture_output=True, text=True)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"curl exit code: {result.returncode}")
        print(f"Execution time: {execution_time:.2f} seconds")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        
        # Parse response
        if "HTTP_CODE:200" in result.stdout:
            print("✅ Agent run completed successfully")
            
            # Extract JSON response (everything before HTTP_CODE line)
            response_parts = result.stdout.split("HTTP_CODE:")
            if len(response_parts) > 0:
                json_response = response_parts[0].strip()
                try:
                    data = json.loads(json_response)
                    print(f"Agent run response: {json.dumps(data, indent=2)}")
                    
                    proposals = data.get('proposals_analyzed', 0)
                    votes = len(data.get('votes_cast', []))
                    errors = data.get('errors', [])
                    
                    print(f"\n📊 Results:")
                    print(f"- Proposals analyzed: {proposals}")  
                    print(f"- Votes cast: {votes}")
                    print(f"- Errors: {len(errors)}")
                    
                    if errors:
                        print("- Error details:")
                        for error in errors:
                            print(f"  • {error}")
                            
                except json.JSONDecodeError as e:
                    print(f"⚠️ Could not parse JSON response: {e}")
                    print(f"Raw response: {json_response}")
                    
        else:
            print("❌ Agent run failed")
            print(f"Response: {result.stdout}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Agent run timed out after 120 seconds")
        return False
    except Exception as e:
        print(f"❌ Agent run error: {e}")
        return False
    
    print("\n1.3 Checking logs for Snapshot API queries...")
    
    # Check for log files and Snapshot interactions
    log_files = [
        "/Users/max/code/quorum-ai/backend/log.txt",
        "/Users/max/code/quorum-ai/backend/service.log"
    ]
    
    found_snapshot = False
    
    for log_file in log_files:
        if os.path.exists(log_file):
            print(f"Checking {log_file}...")
            try:
                with open(log_file, 'r') as f:
                    content = f.read()
                    
                if 'snapshot' in content.lower():
                    found_snapshot = True
                    print(f"✅ Found Snapshot interactions in {log_file}")
                    
                    # Show Snapshot-related lines
                    lines = content.split('\n')
                    snapshot_lines = [line for line in lines if 'snapshot' in line.lower()]
                    
                    print(f"Snapshot log entries ({len(snapshot_lines)}):")
                    for line in snapshot_lines[-10:]:  # Last 10 entries
                        print(f"  {line}")
                else:
                    print(f"⚠️ No Snapshot interactions in {log_file}")
                    
            except Exception as e:
                print(f"Error reading {log_file}: {e}")
        else:
            print(f"Log file not found: {log_file}")
    
    if found_snapshot:
        print("✅ Snapshot API queries verified in logs")
    else:
        print("⚠️ No Snapshot API queries found in logs")
        print("This might be normal if the DAO has no active proposals")
    
    print("\n✅ STEP 1 COMPLETED")
    return True

if __name__ == "__main__":
    success = test_step_1()
    print(f"\nStep 1 {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)