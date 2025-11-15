#!/usr/bin/env python3
# /// script
# dependencies = [
#   "httpx",
#   "pydantic"
# ]
# ///

"""Script to test the voting agent with an active DAO that has real proposals."""

import httpx
import json
from typing import List, Dict, Any

# GraphQL endpoint for Snapshot
GRAPHQL_URL = "https://hub.snapshot.org/graphql"

# Active DAOs to test (these usually have ongoing proposals)
ACTIVE_DAOS = [
    "arbitrumfoundation.eth",
    "compound-governance-2.eth",
    "nouns.eth",
    "uniswap",
    "aave.eth",
    "gitcoin.eth",
    "ens.eth",
]

def fetch_active_proposals(space_id: str) -> List[Dict[str, Any]]:
    """Fetch active proposals for a given space."""
    query = """
    query GetProposals($space_id: String!) {
        proposals(
            first: 10
            where: {
                space_in: [$space_id]
                state: "active"
            }
            orderBy: "created"
            orderDirection: desc
        ) {
            id
            title
            body
            state
            choices
            start
            end
            author
            votes
            scores
            scores_total
            space {
                id
                name
            }
        }
    }
    """

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                GRAPHQL_URL,
                json={
                    "query": query,
                    "variables": {"space_id": space_id}
                },
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("data", {}).get("proposals", [])
            else:
                print(f"  ❌ Error fetching from {space_id}: HTTP {response.status_code}")
                return []
    except Exception as e:
        print(f"  ❌ Error fetching from {space_id}: {str(e)}")
        return []

def main():
    """Find DAOs with active proposals for testing."""
    print("🔍 Searching for DAOs with active proposals...")
    print("=" * 60)

    active_found = []

    for dao in ACTIVE_DAOS:
        print(f"\n📊 Checking {dao}...")
        proposals = fetch_active_proposals(dao)

        if proposals:
            print(f"  ✅ Found {len(proposals)} active proposals!")
            active_found.append((dao, proposals))

            # Show first proposal as example
            if proposals:
                first = proposals[0]
                print(f"  📋 Example: \"{first['title'][:60]}...\"")
                print(f"     Votes: {first['votes']}, Ends: {first['end']}")
        else:
            print(f"  ⚠️  No active proposals")

    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)

    if active_found:
        print(f"✅ Found {len(active_found)} DAOs with active proposals:")
        for dao, proposals in active_found:
            print(f"   - {dao}: {len(proposals)} proposals")

        # Recommend the best one for testing
        best_dao = max(active_found, key=lambda x: len(x[1]))
        print(f"\n💡 Recommended for testing: {best_dao[0]}")
        print(f"   Has {len(best_dao[1])} active proposals")

        print(f"\n🚀 To test with this DAO, run:")
        print(f"   export MONITORED_DAOS=\"{best_dao[0]}\"")
        print(f"   cd backend && uv run main.py")

    else:
        print("⚠️  No DAOs with active proposals found.")
        print("💡 Consider using mock mode for testing:")
        print("   export MOCK_MODE=1")
        print("   export MONITORED_DAOS=\"test.eth\"")

if __name__ == "__main__":
    main()