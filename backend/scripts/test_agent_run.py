#!/usr/bin/env python3
"""
Test script for the /agent-run endpoint.

This script provides a simple way to test the autonomous voting agent
against real Snapshot spaces with various configurations.
"""

import json
import sys
import time
from datetime import datetime

import requests


class AgentRunTester:
    """Test harness for the agent-run endpoint."""

    def __init__(self, api_url: str = "http://localhost:8716"):
        self.api_url = api_url
        self.results = []

    def test_health(self) -> bool:
        """Check if the API is running."""
        try:
            response = requests.get(f"{self.api_url}/healthcheck")
            return response.status_code == 200
        except Exception:
            return False

    def test_agent_run(
        self, space_id: str, dry_run: bool = True, show_details: bool = True
    ) -> dict | None:
        """Test the agent-run endpoint with a specific space."""
        print(f"\n{'='*60}")
        print("🔍 Testing Agent Run")
        print(f"   Space: {space_id}")
        print(f"   Dry Run: {dry_run}")
        print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        start_time = time.time()

        try:
            response = requests.post(
                f"{self.api_url}/agent-run",
                json={"space_id": space_id, "dry_run": dry_run},
                timeout=60,  # 60 second timeout
            )

            elapsed = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                self._print_success_results(data, elapsed, show_details)

                # Store results
                self.results.append(
                    {
                        "space_id": space_id,
                        "success": True,
                        "data": data,
                        "elapsed": elapsed,
                    }
                )

                return data
            self._print_error_results(response, elapsed)

            # Store error
            self.results.append(
                {
                    "space_id": space_id,
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code,
                    "elapsed": elapsed,
                }
            )

            return None

        except requests.exceptions.Timeout:
            print("❌ Request timed out after 60 seconds")
            return None
        except Exception as e:
            print(f"❌ Error: {e!s}")
            return None

    def _print_success_results(self, data: dict, elapsed: float, show_details: bool):
        """Print successful test results."""
        print(f"\n✅ Success! (took {elapsed:.2f}s)")
        print("\n📊 Summary:")
        print(f"   • Proposals Analyzed: {data['proposals_analyzed']}")
        print(f"   • Votes Cast: {len(data['votes_cast'])}")
        print(f"   • Preferences Applied: {data['user_preferences_applied']}")
        print(f"   • Execution Time: {data['execution_time']:.2f}s")

        if data.get("errors"):
            print("\n⚠️  Errors encountered:")
            for error in data["errors"]:
                print(f"   • {error}")

        if show_details and data["votes_cast"]:
            print("\n🗳️  Voting Decisions:")
            for i, vote in enumerate(data["votes_cast"], 1):
                print(f"\n   Decision {i}:")
                print(f"   • Proposal: {vote['proposal_id'][:16]}...")
                print(f"   • Vote: {vote['vote']}")
                print(f"   • Confidence: {vote['confidence']:.1%}")
                print(f"   • Risk: {vote['risk_assessment']['risk_level']}")

                if vote["risk_assessment"].get("risk_factors"):
                    print(
                        f"   • Risk Factors: {', '.join(vote['risk_assessment']['risk_factors'])}"
                    )

                # Show reasoning preview
                if vote.get("reasoning"):
                    reason_preview = (
                        vote["reasoning"][:100] + "..."
                        if len(vote["reasoning"]) > 100
                        else vote["reasoning"]
                    )
                    print(f"   • Reasoning: {reason_preview}")
        elif data["proposals_analyzed"] == 0:
            print("\n📭 No active proposals found in this space")

    def _print_error_results(self, response: requests.Response, elapsed: float):
        """Print error results."""
        print(f"\n❌ Error! (took {elapsed:.2f}s)")
        print(f"   Status Code: {response.status_code}")

        try:
            error_data = response.json()
            if "detail" in error_data:
                print(f"   Error: {error_data['detail']}")
            else:
                print(f"   Response: {json.dumps(error_data, indent=2)}")
        except Exception:
            print(f"   Response: {response.text}")

    def test_multiple_spaces(self, spaces: list[str], dry_run: bool = True):
        """Test multiple spaces sequentially."""
        print(f"\n🚀 Testing {len(spaces)} spaces...")

        for space in spaces:
            self.test_agent_run(space, dry_run=dry_run, show_details=False)
            time.sleep(1)  # Be nice to the API

        self._print_summary()

    def _print_summary(self):
        """Print summary of all test results."""
        print(f"\n{'='*60}")
        print("📈 Test Summary")
        print(f"{'='*60}")

        total = len(self.results)
        successful = sum(1 for r in self.results if r["success"])

        print(f"\nTotal Tests: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {total - successful}")

        if successful > 0:
            print("\n✅ Successful Spaces:")
            for result in self.results:
                if result["success"]:
                    data = result["data"]
                    print(
                        f"   • {result['space_id']}: "
                        f"{data['proposals_analyzed']} proposals, "
                        f"{len(data['votes_cast'])} votes"
                    )

        if total - successful > 0:
            print("\n❌ Failed Spaces:")
            for result in self.results:
                if not result["success"]:
                    print(
                        f"   • {result['space_id']}: "
                        f"Status {result.get('status_code', 'N/A')}"
                    )


def main():
    """Main test execution."""
    # Popular Snapshot spaces that often have active proposals
    TEST_SPACES = [
        "ens.eth",  # ENS DAO
        "arbitrumfoundation.eth",  # Arbitrum
        "aave.eth",  # Aave
        "gitcoindao.eth",  # Gitcoin
        "compound.eth",  # Compound
        "uniswapgovernance.eth",  # Uniswap
        "snapshot.dcl.eth",  # Decentraland
        "bancornetwork.eth",  # Bancor
        "curve.eth",  # Curve
        "gnosis.eth",  # Gnosis
    ]

    # Initialize tester
    tester = AgentRunTester()

    # Check if API is running
    print("🔌 Checking API connection...")
    if not tester.test_health():
        print("❌ Cannot connect to API at http://localhost:8716")
        print("   Make sure the backend is running: uv run main.py")
        sys.exit(1)

    print("✅ API is running")

    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--all":
            # Test all spaces
            tester.test_multiple_spaces(TEST_SPACES, dry_run=True)
        elif sys.argv[1] == "--live" and len(sys.argv) > 2:
            # Live voting test (be careful!)
            space_id = sys.argv[2]
            print("\n⚠️  WARNING: Live voting mode - this will submit real votes!")
            confirm = input("Are you sure? (yes/no): ")
            if confirm.lower() == "yes":
                tester.test_agent_run(space_id, dry_run=False)
            else:
                print("Cancelled.")
        else:
            # Test specific space
            space_id = sys.argv[1]
            tester.test_agent_run(space_id, dry_run=True)
    else:
        # Default: test ENS with detailed output
        print("\n📖 Usage:")
        print("   python test_agent_run.py                    # Test ENS DAO")
        print("   python test_agent_run.py <space_id>         # Test specific space")
        print(
            "   python test_agent_run.py --all              # Test all popular spaces"
        )
        print("   python test_agent_run.py --live <space_id>  # Live voting (careful!)")
        print("\n🎯 Running default test with ENS DAO...")

        tester.test_agent_run("ens.eth", dry_run=True)


if __name__ == "__main__":
    main()
