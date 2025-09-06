#!/usr/bin/env python3
"""
Integration test script for OpenRouter API key functionality.
Tests the complete flow: start services → test API → test UI → verify functionality.
"""

import sys
import subprocess
import time
import requests
from pathlib import Path


def run_command_background(cmd, cwd, log_file=None):
    """Start a command in the background."""
    print(f"Starting: {' '.join(cmd)} in {cwd}")

    if log_file:
        with open(log_file, "w") as f:
            process = subprocess.Popen(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT)
    else:
        process = subprocess.Popen(cmd, cwd=cwd)

    return process


def wait_for_service(url, timeout=60, interval=2):
    """Wait for a service to be ready."""
    print(f"Waiting for service at {url}...")

    for i in range(0, timeout, interval):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ Service ready at {url}")
                return True
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            time.sleep(interval)

    print(f"❌ Service at {url} not ready after {timeout}s")
    return False


def test_api_endpoints():
    """Test the OpenRouter API key endpoints."""
    print("\n🔍 Testing API endpoints...")

    base_url = "http://localhost:8716"

    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        print(f"Health check: {response.status_code}")
        if response.status_code == 200:
            print("✅ Backend health check passed")
        else:
            print("❌ Backend health check failed")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

    # Test API key status endpoint (GET)
    try:
        response = requests.get(f"{base_url}/config/openrouter-key", timeout=10)
        print(f"Get API key status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"API key status response: {data}")
            print("✅ Get API key status endpoint working")
        else:
            print("❌ Get API key status endpoint failed")
            return False
    except Exception as e:
        print(f"❌ Get API key status error: {e}")
        return False

    # Test setting API key (POST)
    test_key = "sk-or-test1234567890123456789012345"
    try:
        response = requests.post(
            f"{base_url}/config/openrouter-key",
            json={"api_key": test_key},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        print(f"Set API key: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Set API key response: {data}")
            print("✅ Set API key endpoint working")
        else:
            print("❌ Set API key endpoint failed")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Set API key error: {e}")
        return False

    # Verify key is set
    try:
        response = requests.get(f"{base_url}/config/openrouter-key", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if (
                data.get("data", {}).get("configured")
                and data.get("data", {}).get("source") == "user"
            ):
                print("✅ API key successfully stored and verified")
            else:
                print(f"❌ API key not properly stored: {data}")
                return False
        else:
            print("❌ Could not verify API key storage")
            return False
    except Exception as e:
        print(f"❌ API key verification error: {e}")
        return False

    # Test removing API key
    try:
        response = requests.post(
            f"{base_url}/config/openrouter-key",
            json={"api_key": ""},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        print(f"Remove API key: {response.status_code}")

        if response.status_code == 200:
            print("✅ Remove API key endpoint working")
        else:
            print("❌ Remove API key endpoint failed")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Remove API key error: {e}")
        return False

    return True


def main():
    project_root = Path(__file__).parent
    backend_dir = project_root / "backend"
    frontend_dir = project_root / "frontend"

    # Check directories exist
    if not backend_dir.exists():
        print("❌ Backend directory not found")
        return False

    if not frontend_dir.exists():
        print("❌ Frontend directory not found")
        return False

    print("Starting integration test...")
    print(f"Backend dir: {backend_dir}")
    print(f"Frontend dir: {frontend_dir}")

    backend_process = None
    frontend_process = None

    try:
        # Start backend server
        backend_log = project_root / "backend_test.log"
        backend_process = run_command_background(
            ["uv", "run", "main.py"], backend_dir, backend_log
        )

        # Wait for backend to be ready
        if not wait_for_service("http://localhost:8716/health", 30):
            print("❌ Backend failed to start")
            return False

        # Test API endpoints
        if not test_api_endpoints():
            print("❌ API endpoint tests failed")
            return False

        print("✅ All API endpoint tests passed!")

        # Optionally start frontend and test UI
        print("\n🔍 Starting frontend for UI testing...")
        frontend_log = project_root / "frontend_test.log"
        frontend_process = run_command_background(
            ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"],
            frontend_dir,
            frontend_log,
        )

        # Wait a bit for frontend to start
        time.sleep(10)

        # Check if frontend is accessible
        if wait_for_service("http://localhost:5173", 30):
            print("✅ Frontend started successfully!")
            print("You can now test the UI manually at:")
            print("- Settings page: http://localhost:5173/settings")
            print("- Use the OpenRouter API key field to test the functionality")
        else:
            print("⚠️  Frontend may not be accessible, but API tests passed")

        print("\n✅ Integration test completed successfully!")
        print("\nServices running:")
        print("- Backend: http://localhost:8716")
        print("- Frontend: http://localhost:5173")
        print("\nPress Ctrl+C to stop services...")

        # Keep running until interrupted
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down services...")

        return True

    except Exception as e:
        print(f"❌ Integration test error: {e}")
        return False

    finally:
        # Clean up processes
        if backend_process:
            backend_process.terminate()
            try:
                backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                backend_process.kill()

        if frontend_process:
            frontend_process.terminate()
            try:
                frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                frontend_process.kill()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
