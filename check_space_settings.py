#!/usr/bin/env python3
"""
Check space settings and proposal requirements for a Snapshot DAO.

Usage:
    uv run check_space_settings.py quorum-ai.eth
"""
# /// script
# dependencies = [
#   "httpx",
#   "rich"
# ]
# ///

import asyncio
import sys
import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

SNAPSHOT_API = "https://hub.snapshot.org/graphql"

console = Console()


async def get_space_info(space: str) -> dict:
    """Get detailed space configuration."""
    query = """
    query Space($space: String!) {
      space(id: $space) {
        id
        name
        about
        network
        symbol
        website
        twitter
        github
        coingecko
        strategies {
          name
          network
          params
        }
        validation {
          name
          params
        }
        filters {
          minScore
          onlyMembers
        }
        voting {
          delay
          period
          type
          quorum
          hideAbstain
        }
        admins
        moderators
        members
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
            console.print(f"[red]Error:[/red] {data['errors']}")
            return {}

        return data.get("data", {}).get("space", {})


async def check_proposal_permissions(space: str, address: str) -> dict:
    """Check if an address can create proposals."""
    query = """
    query VotingPower($space: String!, $voter: String!) {
      vp(
        space: $space
        voter: $voter
      ) {
        vp
        vp_by_strategy
        vp_state
      }
    }
    """

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            SNAPSHOT_API,
            json={"query": query, "variables": {"space": space, "voter": address.lower()}}
        )
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            return {"error": str(data["errors"])}

        return data.get("data", {}).get("vp", {})


async def main():
    if len(sys.argv) < 2:
        space = "quorum-ai.eth"
    else:
        space = sys.argv[1]

    console.print(f"\n[bold cyan]Checking Snapshot space:[/bold cyan] {space}\n")

    # Get space info
    space_info = await get_space_info(space)

    if not space_info:
        console.print("[red]Failed to fetch space info[/red]")
        sys.exit(1)

    # Display basic info
    console.print(Panel.fit(
        f"[bold]{space_info.get('name', space)}[/bold]\n"
        f"{space_info.get('about', 'No description')}\n\n"
        f"Network: {space_info.get('network', 'Unknown')}\n"
        f"Symbol: {space_info.get('symbol', 'Unknown')}",
        title="Space Info"
    ))

    # Display voting settings
    voting = space_info.get('voting', {})
    console.print("\n[bold]Voting Settings:[/bold]")
    table = Table(show_header=False)
    table.add_row("Voting Delay", f"{voting.get('delay', 0)} seconds")
    table.add_row("Voting Period", f"{voting.get('period', 0)} seconds ({voting.get('period', 0) // 3600} hours)")
    table.add_row("Voting Type", str(voting.get('type', 'single-choice')))
    table.add_row("Quorum", str(voting.get('quorum', 'None')))
    console.print(table)

    # Display filters
    filters = space_info.get('filters', {})
    console.print("\n[bold]Proposal Filters:[/bold]")
    filter_table = Table(show_header=False)
    filter_table.add_row("Minimum Score", str(filters.get('minScore', 0)))
    filter_table.add_row("Only Members", str(filters.get('onlyMembers', False)))
    console.print(filter_table)

    # Display validation
    validation = space_info.get('validation', {})
    if validation:
        console.print(f"\n[bold]Validation Strategy:[/bold] {validation.get('name', 'None')}")
        if validation.get('params'):
            console.print(f"[dim]Params: {validation.get('params')}[/dim]")

    # Display strategies
    strategies = space_info.get('strategies', [])
    if strategies:
        console.print("\n[bold]Voting Strategies:[/bold]")
        for i, strategy in enumerate(strategies, 1):
            console.print(f"{i}. {strategy.get('name')} (network: {strategy.get('network', 'unknown')})")

    # Display admins/moderators
    admins = space_info.get('admins', [])
    moderators = space_info.get('moderators', [])
    members = space_info.get('members', [])

    if admins:
        console.print(f"\n[bold]Admins ({len(admins)}):[/bold]")
        for admin in admins[:5]:
            console.print(f"  • {admin}")

    if moderators:
        console.print(f"\n[bold]Moderators ({len(moderators)}):[/bold]")
        for mod in moderators[:5]:
            console.print(f"  • {mod}")

    if members:
        console.print(f"\n[bold]Members:[/bold] {len(members)} total")

    # Check our address
    our_address = "0x8925F6569F7eBa0Ed3e40e54E83D36A579Aa5101"
    console.print(f"\n[bold]Checking permissions for:[/bold] {our_address}")

    vp_data = await check_proposal_permissions(space, our_address)
    if "error" not in vp_data:
        total_vp = vp_data.get("vp", 0)
        console.print(f"Voting Power: {total_vp:,.2f}")

        min_score = filters.get('minScore', 0)
        only_members = filters.get('onlyMembers', False)

        can_propose = total_vp >= min_score
        if only_members:
            is_member = our_address.lower() in [m.lower() for m in (members or [])]
            can_propose = can_propose and is_member

        is_admin = our_address.lower() in [a.lower() for a in (admins or [])]
        is_mod = our_address.lower() in [m.lower() for m in (moderators or [])]

        if is_admin:
            console.print("[green]✓ You are an admin - can create proposals[/green]")
        elif is_mod:
            console.print("[green]✓ You are a moderator - can create proposals[/green]")
        elif can_propose:
            console.print("[green]✓ You can create proposals[/green]")
        else:
            console.print(f"[red]✗ Cannot create proposals[/red]")
            console.print(f"  Required: {min_score} voting power")
            console.print(f"  Your power: {total_vp}")
            if only_members:
                console.print("  Also requires membership")

    console.print(f"\n[dim]Create proposals at: https://snapshot.org/#/{space}/create[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
