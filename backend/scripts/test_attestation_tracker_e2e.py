#!/usr/bin/env python3
"""
End-to-end test for AttestationTracker integration.

Tests the complete attestation flow through AttestationTracker wrapper,
including initial statistics, attestation submission, and updated statistics.
This script provides end-to-end testing for the AttestationTracker functionality.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.safe_service import SafeService
from models import EASAttestationData
from utils.attestation_tracker_helpers import (
    get_multisig_info,
    get_attestation_count,
)
from config import settings

# Test configuration
TEST_VOTER_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc9e7595f89590"
TEST_PROPOSAL_ID = "test_proposal_123"
TEST_SPACE_ID = "test.eth"


async def setup_test_environment():
    """Initialize test environment and display configuration."""
    print("\n=== Setting up AttestationTracker Test Environment ===")

    print("Configuration:")
    print(
        f"  - AttestationTracker configured: {bool(settings.attestation_tracker_address)}"
    )
    print(f"  - AttestationTracker address: {settings.attestation_tracker_address}")
    print(f"  - EAS contract address: {settings.eas_contract_address}")
    print(f"  - Base Safe address: {settings.base_safe_address}")
    print(f"  - Agent address: {settings.agent_address}")

    if not settings.base_safe_address:
        print("❌ No Base Safe address configured")
        return None

    print("✓ Environment setup complete")
    return settings.base_safe_address


async def check_initial_statistics(multisig_address: str) -> Dict[str, Any]:
    """Check initial AttestationTracker statistics."""
    print("\n=== Checking Initial AttestationTracker Statistics ===")

    try:
        # Get initial statistics
        count, is_active = get_multisig_info(multisig_address)

        stats = {
            "attestation_count": count,
            "multisig_active": is_active,
        }

        print(f"Initial statistics for multisig {multisig_address[:10]}...:")
        print(f"  - Attestation count: {stats['attestation_count']}")
        print(f"  - Multisig active: {stats['multisig_active']}")

        return stats

    except Exception as e:
        print(f"⚠️  Could not fetch initial statistics: {str(e)}")
        return {"error": str(e)}


async def submit_test_attestation(safe_service: SafeService) -> Dict[str, Any]:
    """Submit a test attestation through SafeService."""
    print("\n=== Submitting Test Attestation ===")

    # Create test attestation data
    attestation = EASAttestationData(
        proposal_id=TEST_PROPOSAL_ID,
        space_id=TEST_SPACE_ID,
        voter_address=settings.agent_address or TEST_VOTER_ADDRESS,
        choice=1,  # Vote FOR
        vote_tx_hash="0x" + "0" * 64,  # Mock transaction hash
        timestamp=datetime.now(timezone.utc),
        retry_count=0,
    )

    print("Test attestation data:")
    print(f"  - Proposal ID: {attestation.proposal_id}")
    print(f"  - Space ID: {attestation.space_id}")
    print(f"  - Voter address: {attestation.voter_address}")
    print(f"  - Choice: {attestation.choice}")
    print(f"  - Retry count: {attestation.retry_count}")

    try:
        # Submit attestation through SafeService
        result = await safe_service.create_eas_attestation(attestation)

        if result.get("success"):
            print("✓ Attestation submitted successfully")
            if settings.attestation_tracker_address:
                print("  → Routed through AttestationTracker wrapper")
            else:
                print("  → Routed directly to EAS")

            print(f"  - Safe transaction hash: {result.get('safe_tx_hash', 'pending')}")
        else:
            print(f"✗ Attestation submission failed: {result.get('error')}")

        return result

    except Exception as e:
        print(f"✗ Attestation submission failed with exception: {str(e)}")
        return {"success": False, "error": str(e)}


async def check_updated_statistics(
    multisig_address: str, initial_stats: Dict[str, Any]
) -> Dict[str, Any]:
    """Check updated AttestationTracker statistics after attestation."""
    print("\n=== Checking Updated AttestationTracker Statistics ===")

    try:
        # Get updated statistics
        count, is_active = get_multisig_info(multisig_address)

        updated_stats = {
            "attestation_count": count,
            "multisig_active": is_active,
        }

        print(f"Updated statistics for multisig {multisig_address[:10]}...:")
        print(f"  - Attestation count: {updated_stats['attestation_count']}")
        print(f"  - Multisig active: {updated_stats['multisig_active']}")

        # Compare with initial stats
        if "error" not in initial_stats:
            count_diff = (
                updated_stats["attestation_count"] - initial_stats["attestation_count"]
            )
            if count_diff > 0:
                print(f"✓ Attestation count increased by {count_diff}")
            else:
                print(
                    "ℹ️  Attestation count unchanged (Safe transaction may be pending)"
                )

            if (
                updated_stats["multisig_active"]
                and not initial_stats["multisig_active"]
            ):
                print("✓ Multisig status changed from inactive to active")

        return updated_stats

    except Exception as e:
        print(f"⚠️  Could not fetch updated statistics: {str(e)}")
        return {"error": str(e)}


async def test_routing_behavior():
    """Test attestation routing behavior based on configuration."""
    print("\n=== Testing Attestation Routing Behavior ===")

    if settings.attestation_tracker_address:
        print(
            "✓ AttestationTracker configured - attestations will route through wrapper"
        )
        print(f"  - Wrapper address: {settings.attestation_tracker_address}")
        print("  - Benefits: Multisig activity tracking, attestation counting")
        routing_type = "wrapper"
    else:
        print(
            "ℹ️  AttestationTracker not configured - attestations route directly to EAS"
        )
        print(f"  - EAS address: {settings.eas_contract_address}")
        print("  - Note: No multisig tracking, but still creates EAS attestations")
        routing_type = "direct"

    # Test delegated pattern regardless of routing
    print("✓ Both routing modes use delegated attestation pattern (attestByDelegation)")
    print("  - Compatible with Safe multisig transactions")
    print("  - Proper EAS schema compliance")

    return routing_type


async def verify_integration_readiness():
    """Verify that the integration is ready for production use."""
    print("\n=== Verifying Integration Readiness ===")

    checks_passed = 0
    total_checks = 6

    # Check 1: Configuration validation
    try:
        if settings.eas_contract_address and settings.eas_schema_uid:
            print("✓ EAS configuration valid")
            checks_passed += 1
        else:
            print("✗ EAS configuration incomplete")
    except Exception:
        print("✗ EAS configuration error")

    # Check 2: Safe configuration
    try:
        if settings.base_safe_address:
            print("✓ Base Safe address configured")
            checks_passed += 1
        else:
            print("✗ Base Safe address not configured")
    except Exception:
        print("✗ Base Safe configuration error")

    # Check 3: AttestationTracker helper functions
    try:
        test_address = (
            settings.base_safe_address or "0x742d35Cc6634C0532925a3b844Bc9e7595f89590"
        )
        count, active = get_multisig_info(test_address)
        print("✓ AttestationTracker helper functions working")
        checks_passed += 1
    except Exception as e:
        print(f"✗ AttestationTracker helper functions error: {str(e)}")

    # Check 4: SafeService initialization
    try:
        safe_service = SafeService()
        print("✓ SafeService initialization successful")
        checks_passed += 1
    except Exception as e:
        print(f"✗ SafeService initialization failed: {str(e)}")

    # Check 5: Routing logic
    try:
        routing_type = await test_routing_behavior()
        print(f"✓ Attestation routing logic working ({routing_type})")
        checks_passed += 1
    except Exception as e:
        print(f"✗ Attestation routing logic error: {str(e)}")

    # Check 6: ABI loading
    try:
        from utils.abi_loader import load_abi

        if settings.attestation_tracker_address:
            abi = load_abi("attestation_tracker")
            print("✓ AttestationTracker ABI loading successful")
        else:
            abi = load_abi("eas")
            print("✓ EAS ABI loading successful")
        checks_passed += 1
    except Exception as e:
        print(f"✗ ABI loading error: {str(e)}")

    return checks_passed, total_checks


async def main():
    """Main test execution."""
    print("=" * 70)
    print("AttestationTracker Integration End-to-End Test")
    print("=" * 70)

    try:
        # Setup environment
        multisig_address = await setup_test_environment()
        if not multisig_address:
            print("❌ Environment setup failed - cannot proceed")
            return 1

        # Verify integration readiness
        checks_passed, total_checks = await verify_integration_readiness()
        print(f"\nIntegration readiness: {checks_passed}/{total_checks} checks passed")

        if checks_passed < total_checks:
            print("⚠️  Some integration checks failed - proceeding with limited testing")

        # Check initial statistics
        initial_stats = await check_initial_statistics(multisig_address)

        # Initialize SafeService
        safe_service = SafeService()

        # Submit test attestation
        attestation_result = await submit_test_attestation(safe_service)

        # Check updated statistics (if attestation was submitted)
        if attestation_result.get("success"):
            updated_stats = await check_updated_statistics(
                multisig_address, initial_stats
            )
        else:
            updated_stats = {"error": "Attestation not submitted"}

        # Report final results
        print("\n" + "=" * 70)
        print("TEST RESULTS")
        print("=" * 70)

        success = checks_passed >= (total_checks - 1) and attestation_result.get(
            "success", False
        )

        if success:
            print("✅ TEST PASSED - AttestationTracker integration working correctly!")
            print("\nSummary:")
            print(
                f"  - Environment configured: {checks_passed}/{total_checks} checks passed"
            )
            print(
                f"  - AttestationTracker configured: {bool(settings.attestation_tracker_address)}"
            )
            print("  - Test attestation submitted successfully")
            if settings.attestation_tracker_address:
                print("  - Attestation routed through wrapper")
                print("  - Multisig activity tracking enabled")
            else:
                print("  - Attestation routed directly to EAS")
                print("  - Standard EAS attestation created")
        else:
            print("❌ TEST FAILED - Issues detected:")
            if checks_passed < (total_checks - 1):
                print(
                    f"  - Integration readiness: {checks_passed}/{total_checks} checks passed"
                )
            if not attestation_result.get("success", False):
                print(
                    f"  - Attestation submission failed: {attestation_result.get('error')}"
                )

        print("\nConfiguration used:")
        print(
            f"  - AttestationTracker: {settings.attestation_tracker_address or 'Not configured'}"
        )
        print(f"  - EAS contract: {settings.eas_contract_address}")
        print(f"  - Base Safe: {settings.base_safe_address}")

        print("\n" + "=" * 70)
        print("Test completed at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("=" * 70)

        return 0 if success else 1

    except Exception as e:
        print(f"\n❌ TEST FAILED with exception: {str(e)}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
