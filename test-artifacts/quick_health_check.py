#!/usr/bin/env python3

import requests
import subprocess
import sys
import os

def check_service_health():
    """Quick health check to see if service is running."""
    try:
        response = requests.get("http://localhost:8716/health", timeout=5)
        if response.status_code == 200:
            print("✅ Service is already running!")
            return True
    except:
        pass
    
    print("❌ Service is not running. Need to start it.")
    return False

def start_backend_service():
    """Start only the backend service for testing."""
    print("Starting backend service...")
    
    # Change to backend directory
    os.chdir("/Users/max/code/quorum-ai/backend")
    
    # Start the backend using uv run
    try:
        process = subprocess.Popen(
            ["uv", "run", "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        print(f"Backend started with PID: {process.pid}")
        
        # Wait a moment for startup
        import time
        print("Waiting 5 seconds for service to start...")
        time.sleep(5)
        
        # Check if it's running
        if check_service_health():
            return True
        else:
            print("❌ Service failed to start properly")
            return False
            
    except Exception as e:
        print(f"❌ Failed to start service: {e}")
        return False

if __name__ == "__main__":
    if not check_service_health():
        if not start_backend_service():
            sys.exit(1)
    
    print("✅ Service is ready for testing!")