#!/usr/bin/env python3
"""
Verify QuorumTracker deployment and activity registration.
This script checks the deployed contract and verifies all activity types work.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.quorum_tracker_service import QuorumTrackerService
from services.safe_service import SafeService
from models import ActivityType
from config import settings

# Contract deployment information
DEPLOYED_CONTRACT = "0x0451830c7F76ca89b52a4dbecF22f58a507282b9"
DEPLOYMENT_CHAIN = "base"
DEPLOYMENT_BLOCK = "22773606"


async def verify_deployment():
    """Verify the QuorumTracker contract deployment."""
    print("=" * 60)
    print("QuorumTracker Deployment Verification")
    print("=" * 60)

    print("\n📋 Deployment Details:")
    print(f"  - Contract Address: {DEPLOYED_CONTRACT}")
    print(f"  - Chain: {DEPLOYMENT_CHAIN}")
    print(f"  - Block: {DEPLOYMENT_BLOCK}")
    print(f"  - Explorer: https://sepolia.basescan.org/address/{DEPLOYED_CONTRACT}")

    # Update settings
    settings.quorum_tracker_address = DEPLOYED_CONTRACT

    # Initialize services
    safe_service = SafeService()
    quorum_tracker = QuorumTrackerService(safe_service=safe_service)

    print("\n✅ Services initialized successfully")
    print("  - QuorumTracker service ready")
    print("  - Safe service ready")

    return quorum_tracker, safe_service


async def test_activity_registration(quorum_tracker: QuorumTrackerService):
    """Test registering each activity type."""
    print("\n🧪 Testing Activity Registration:")

    # Get or create test multisig address
    safe_service = SafeService()
    multisig_address = safe_service.safe_addresses.get(
        "base", "0x1234567890123456789012345678901234567890"
    )

    activity_types = [
        (ActivityType.OPPORTUNITY_CONSIDERED, "OPPORTUNITY_CONSIDERED"),
        (ActivityType.VOTE_CAST, "VOTE_CAST"),
        (ActivityType.NO_OPPORTUNITY, "NO_OPPORTUNITY"),
    ]

    results = []
    for activity_type, name in activity_types:
        print(f"\n  Testing {name}...")
        try:
            result = await quorum_tracker.register_activity(
                multisig_address=multisig_address, activity_type=activity_type.value
            )

            if result.get("success"):
                print(f"    ✅ {name} registration successful")
                print(f"       Transaction: {result.get('tx_hash', 'pending')}")
                results.append((name, True, None))
            else:
                error = result.get("error", "Unknown error")
                print(f"    ⚠️  {name} registration failed: {error}")
                results.append((name, False, error))

        except Exception as e:
            print(f"    ❌ {name} registration error: {str(e)}")
            results.append((name, False, str(e)))

    return results


async def verify_integration():
    """Verify the complete integration with agent run service."""
    print("\n🔗 Verifying Agent Integration:")

    from services.agent_run_service import AgentRunService
    from services.state_manager import StateManager

    # Initialize agent run service
    state_manager = StateManager()
    agent_run_service = AgentRunService(state_manager=state_manager)
    await agent_run_service.initialize()

    # Check QuorumTracker integration
    if agent_run_service.quorum_tracker_service:
        print("  ✅ Agent run service has QuorumTracker integration")
        print("     - Activity tracking enabled")
        print(f"     - Contract: {settings.quorum_tracker_address}")
    else:
        print("  ❌ QuorumTracker not integrated with agent run service")

    # Verify activity tracking method exists
    if hasattr(agent_run_service, "_track_activity"):
        print("  ✅ Activity tracking method available")
    else:
        print("  ❌ Activity tracking method missing")

    return agent_run_service.quorum_tracker_service is not None


def print_summary(registration_results, integration_verified):
    """Print final summary of verification."""
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    # Registration results
    print("\n📊 Activity Registration Results:")
    all_passed = True
    for name, success, error in registration_results:
        if success:
            print(f"  ✅ {name}: PASS")
        else:
            print(f"  ❌ {name}: FAIL - {error}")
            all_passed = False

    # Integration status
    print("\n🔗 Integration Status:")
    if integration_verified:
        print("  ✅ Agent Run Service: INTEGRATED")
    else:
        print("  ❌ Agent Run Service: NOT INTEGRATED")

    # Overall status
    print("\n🎯 Overall Status:")
    if all_passed and integration_verified:
        print("  ✅ QuorumTracker feature is FULLY OPERATIONAL")
        print("\n  The QuorumTracker feature is successfully deployed and integrated!")
        print(f"  - Contract is deployed at {DEPLOYED_CONTRACT}")
        print("  - All activity types can be registered")
        print("  - Agent run service integration is working")
        print("  - Activities will be tracked on-chain during agent runs")
    else:
        print("  ⚠️  QuorumTracker feature has issues that need attention")
        if not all_passed:
            print("     - Some activity registrations failed")
        if not integration_verified:
            print("     - Agent integration needs configuration")

    print("\n" + "=" * 60)


async def main():
    """Main verification process."""
    try:
        # Verify deployment
        quorum_tracker, safe_service = await verify_deployment()

        # Test activity registration
        registration_results = await test_activity_registration(quorum_tracker)

        # Verify integration
        integration_verified = await verify_integration()

        # Print summary
        print_summary(registration_results, integration_verified)

        return 0

    except Exception as e:
        print(f"\n❌ Verification failed with error: {str(e)}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
