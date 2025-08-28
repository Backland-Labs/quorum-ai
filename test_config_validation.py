#!/usr/bin/env python3
"""
Simple test script to verify AttestationTracker configuration validation.
"""

import os
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

try:
    from backend.config import Settings
except ImportError:
    # Try alternative import path
    sys.path.insert(0, str(Path(__file__).parent))
    from backend.config import Settings


def test_attestation_tracker_configuration():
    """Test AttestationTracker configuration validation."""
    print("=" * 60)
    print("Testing AttestationTracker Configuration Validation")
    print("=" * 60)
    
    # Test 1: Default configuration (None)
    print("\n1. Testing default configuration (should be None)")
    try:
        settings = Settings(_env_file=None)
        result = settings.attestation_tracker_address
        print(f"   Result: {result}")
        print(f"   Status: {'PASS' if result is None else 'FAIL'}")
    except Exception as e:
        print(f"   Error: {e}")
        print("   Status: FAIL")
        
    # Test 2: Valid address from environment
    print("\n2. Testing valid address from environment")
    test_address = "0x1234567890abcdef1234567890abcdef12345678"
    try:
        os.environ["ATTESTATION_TRACKER_ADDRESS"] = test_address
        settings = Settings(_env_file=None)
        result = settings.attestation_tracker_address
        print(f"   Input: {test_address}")
        print(f"   Result: {result}")
        # Note: Without validation, it should just use the input as-is
        print(f"   Status: {'PASS' if result == test_address else 'FAIL'}")
    except Exception as e:
        print(f"   Error: {e}")
        print("   Status: FAIL")
    finally:
        if "ATTESTATION_TRACKER_ADDRESS" in os.environ:
            del os.environ["ATTESTATION_TRACKER_ADDRESS"]
            
    # Test 3: Invalid address from environment
    print("\n3. Testing invalid address from environment")
    invalid_address = "0x123"  # Too short
    try:
        os.environ["ATTESTATION_TRACKER_ADDRESS"] = invalid_address
        settings = Settings(_env_file=None)
        result = settings.attestation_tracker_address
        print(f"   Input: {invalid_address}")
        print(f"   Result: {result}")
        # Without validation, invalid address should still be accepted
        print(f"   Status: {'WARN - No validation' if result == invalid_address else 'FAIL'}")
    except Exception as e:
        print(f"   Error: {e}")
        print("   Status: PASS - Validation working")
    finally:
        if "ATTESTATION_TRACKER_ADDRESS" in os.environ:
            del os.environ["ATTESTATION_TRACKER_ADDRESS"]
            
    # Test 4: Empty string
    print("\n4. Testing empty string from environment")
    try:
        os.environ["ATTESTATION_TRACKER_ADDRESS"] = ""
        settings = Settings(_env_file=None)
        result = settings.attestation_tracker_address
        print(f"   Input: (empty string)")
        print(f"   Result: {result}")
        print(f"   Status: {'PASS' if result in [None, ''] else 'FAIL'}")
    except Exception as e:
        print(f"   Error: {e}")
        print("   Status: FAIL")
    finally:
        if "ATTESTATION_TRACKER_ADDRESS" in os.environ:
            del os.environ["ATTESTATION_TRACKER_ADDRESS"]
    
    print("\n" + "=" * 60)
    print("Configuration validation test complete")
    print("=" * 60)


if __name__ == "__main__":
    test_attestation_tracker_configuration()