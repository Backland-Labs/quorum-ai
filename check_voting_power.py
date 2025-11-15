#!/usr/bin/env python3
"""
Check voting power for a given address across monitored DAOs.

Usage:
    uv run check_voting_power.py 0xYourAddress
    uv run check_voting_power.py 0xYourAddress --dao=uniswap.eth
"""
# /// script
# dependencies = [
#   "httpx",
#   "rich"
# ]
# ///

import asyncio
import sys
from typing import Optional
import httpx
from rich.console import Console
from rich.table import Table

SNAPSHOT_API = "https://hub.snapshot.org/graphql"

console = Console()


async def get_active_proposals(space: str) -> list[dict]:
    """Get active proposals for a DAO space."""
    query = """
    query Proposals($space: String!) {
      proposals(
        first: 20,
        where: { space: $space, state: "active" }
        orderBy: "created",
        orderDirection: desc
      ) {
        id
        title
        state
        start
        end
        snapshot
        space {
          id
        }
        strategies {
          name
          params
        }
      }
    }
    """

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            SNAPSHOT_API,
            json={"query": query, "variables": {"space": space}}
        )
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            console.print(f"[red]Error querying {space}:[/red] {data['errors']}")
            return []

        return data.get("data", {}).get("proposals", [])


async def check_voting_power(
    space: str,
    address: str,
    proposal_id: Optional[str] = None
) -> dict:
    """Check voting power for an address on a specific proposal or space."""
    query = """
    query VotingPower($space: String!, $voter: String!, $proposal: String) {
      vp(
        space: $space
        voter: $voter
        proposal: $proposal
      ) {
        vp
        vp_by_strategy
        vp_state
      }
    }
    """

    variables = {
        "space": space,
        "voter": address.lower(),
    }

    if proposal_id:
        variables["proposal"] = proposal_id

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            SNAPSHOT_API,
            json={"query": query, "variables": variables}
        )
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            return {"error": str(data["errors"])}

        return data.get("data", {}).get("vp", {})


async def main():
    if len(sys.argv) < 2:
        console.print("[red]Error:[/red] Please provide a wallet address")
        console.print("\nUsage: uv run check_voting_power.py 0xYourAddress [--dao=space]")
        sys.exit(1)

    address = sys.argv[1]

    # Check if DAO filter is provided
    target_dao = None
    for arg in sys.argv[2:]:
        if arg.startswith("--dao="):
            target_dao = arg.split("=")[1]

    # Default monitored DAOs
    monitored_daos = ["quorum-ai.eth", "compound.eth", "nouns.eth", "arbitrum.eth"]
    if target_dao:
        monitored_daos = [target_dao]

    console.print(f"\n[bold]Checking voting power for:[/bold] {address}\n")

    for dao in monitored_daos:
        console.print(f"[cyan]DAO:[/cyan] {dao}")

        # Get active proposals
        proposals = await get_active_proposals(dao)

        if not proposals:
            console.print(f"  [yellow]No active proposals[/yellow]\n")
            continue

        # Create table for this DAO
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Proposal", style="dim", width=40)
        table.add_column("Voting Power", justify="right")
        table.add_column("Status")

        for proposal in proposals[:5]:  # Show first 5 proposals
            vp_data = await check_voting_power(dao, address, proposal["id"])

            if "error" in vp_data:
                table.add_row(
                    proposal["title"][:40],
                    "Error",
                    "[red]Failed[/red]"
                )
            else:
                total_vp = vp_data.get("vp", 0)
                vp_display = f"{total_vp:,.2f}" if total_vp else "0"

                status = "[green]✓ Can vote[/green]" if total_vp > 0 else "[red]✗ No power[/red]"

                table.add_row(
                    proposal["title"][:40],
                    vp_display,
                    status
                )

        console.print(table)
        console.print()

    console.print("[dim]Note: Voting power is determined by token holdings at the proposal's snapshot block[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
