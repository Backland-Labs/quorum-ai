#!/usr/bin/env python3
"""Attestation Tracker Functional Test Runner"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a shell command and capture output."""
    print(f"\n{'='*60}")
    print(f"RUNNING: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    try:
        # Change to backend directory
        os.chdir('/Users/max/code/quorum-ai/backend')
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            cwd='/Users/max/code/quorum-ai/backend'
        )
        
        print(f"Exit Code: {result.returncode}")
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
            
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            
        return result.returncode == 0, result.stdout, result.stderr
        
    except Exception as e:
        print(f"ERROR: Failed to run command: {e}")
        return False, "", str(e)

def main():
    print("AttestationTracker Functional Test Suite")
    print("========================================")
    
    # Change to the backend directory
    backend_dir = Path("/Users/max/code/quorum-ai/backend")
    if not backend_dir.exists():
        print(f"ERROR: Backend directory not found: {backend_dir}")
        return 1
        
    test_commands = [
        (
            ["uv", "run", "pytest", "tests/test_config.py::TestAttestationTrackerConfiguration", "-v"],
            "Configuration Tests - AttestationTracker address validation"
        ),
        (
            ["uv", "run", "pytest", "tests/test_safe_service_eas.py::TestAttestationTrackerRouting", "-v"],
            "SafeService Routing Tests - Attestation routing logic"
        ),
        (
            ["uv", "run", "pytest", "tests/test_attestation_tracker_helpers.py", "-v"],
            "Helper Function Tests - Graceful handling with/without tracker"
        ),
        (
            ["uv", "run", "pytest", "tests/test_agent_run_attestation.py::test_attestation_retry_with_tracker", "-v"],
            "Agent Run Tests - Retry logic with tracker"
        ),
        (
            ["uv", "run", "pytest", "-k", "attestation_tracker", "-v"],
            "Overall AttestationTracker Tests - All tests with attestation_tracker keyword"
        )
    ]
    
    results = []
    
    for cmd, description in test_commands:
        success, stdout, stderr = run_command(cmd, description)
        results.append((description, success, stdout, stderr))
        
    # Summary
    print("\n" + "="*80)
    print("FUNCTIONAL TEST SUMMARY")
    print("="*80)
    
    all_passed = True
    for description, success, stdout, stderr in results:
        status = "PASS" if success else "FAIL"
        print(f"{status:<6} {description}")
        if not success:
            all_passed = False
            
    print("\n" + "="*80)
    
    if all_passed:
        print("✅ ALL TESTS PASSED - AttestationTracker implementation is ready for deployment!")
    else:
        print("❌ SOME TESTS FAILED - Review failures before deployment")
        
    print("="*80)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())