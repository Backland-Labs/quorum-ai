#!/usr/bin/env python3
"""
Create a proposal on Snapshot for a given DAO space.

Usage:
    uv run create_proposal.py --space=quorum-ai.eth --title="Test Proposal" --body="Description"
"""
# /// script
# dependencies = [
#   "httpx",
#   "eth-account",
#   "web3",
#   "rich"
# ]
# ///

import asyncio
import json
import sys
import time
from typing import Optional
import httpx
from eth_account import Account
from eth_account.messages import encode_typed_data
from rich.console import Console
from rich.prompt import Prompt, Confirm

SNAPSHOT_API = "https://hub.snapshot.org/graphql"
SNAPSHOT_SEQUENCER = "https://seq.snapshot.org"

console = Console()


async def get_space_info(space: str) -> dict:
    """Get space configuration and settings."""
    query = """
    query Space($space: String!) {
      space(id: $space) {
        id
        name
        about
        network
        symbol
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


async def create_proposal(
    space: str,
    title: str,
    body: str,
    choices: list[str],
    start: int,
    end: int,
    private_key: str,
    snapshot: Optional[int] = None,
    discussion: str = "",
) -> dict:
    """Create a proposal on Snapshot."""

    # Create account from private key
    account = Account.from_key(private_key)
    address = account.address

    console.print(f"\n[cyan]Creating proposal from:[/cyan] {address}")

    # Get current block if snapshot not provided
    if snapshot is None:
        # Use latest block number (would need Web3 for accurate value)
        snapshot = int(time.time())  # Placeholder

    # Create proposal message
    proposal_data = {
        "from": address,
        "space": space,
        "timestamp": int(time.time()),
        "type": "single-choice",  # or "approval", "quadratic", "ranked-choice", "weighted"
        "title": title,
        "body": body,
        "choices": choices,
        "start": start,
        "end": end,
        "snapshot": snapshot,
        "network": "1",  # Ethereum mainnet
        "strategies": json.dumps([]),  # Will use space defaults
        "plugins": json.dumps({}),
        "metadata": json.dumps({}),
    }

    if discussion:
        proposal_data["discussion"] = discussion

    # Create EIP-712 message
    message = {
        "domain": {
            "name": "snapshot",
            "version": "0.1.4",
        },
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
            ],
            "Proposal": [
                {"name": "from", "type": "address"},
                {"name": "space", "type": "string"},
                {"name": "timestamp", "type": "uint64"},
                {"name": "type", "type": "string"},
                {"name": "title", "type": "string"},
                {"name": "body", "type": "string"},
                {"name": "choices", "type": "string[]"},
                {"name": "start", "type": "uint64"},
                {"name": "end", "type": "uint64"},
                {"name": "snapshot", "type": "uint64"},
                {"name": "network", "type": "string"},
                {"name": "strategies", "type": "string"},
                {"name": "plugins", "type": "string"},
                {"name": "metadata", "type": "string"},
            ],
        },
        "primaryType": "Proposal",
        "message": proposal_data,
    }

    # Sign the message
    encoded_message = encode_typed_data(full_message=message)
    signed = account.sign_message(encoded_message)

    # Prepare submission
    submission = {
        "address": address,
        "msg": json.dumps(proposal_data),
        "sig": signed.signature.hex(),
    }

    console.print("[cyan]Submitting proposal to Snapshot...[/cyan]")

    # Submit to Snapshot sequencer
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            SNAPSHOT_SEQUENCER,
            json=submission,
        )

        console.print(f"[dim]Response status: {response.status_code}[/dim]")

        try:
            result = response.json()
            return result
        except Exception as e:
            console.print(f"[red]Error parsing response:[/red] {e}")
            console.print(f"[dim]Response text: {response.text}[/dim]")
            return {"error": str(e), "response": response.text}


async def main():
    console.print("[bold]Snapshot Proposal Creator[/bold]\n")

    # Get space
    space = None
    for arg in sys.argv[1:]:
        if arg.startswith("--space="):
            space = arg.split("=")[1]

    if not space:
        space = Prompt.ask("Enter DAO space (e.g., quorum-ai.eth)", default="quorum-ai.eth")

    # Get space info
    console.print(f"\n[cyan]Fetching space info for {space}...[/cyan]")
    space_info = await get_space_info(space)

    if not space_info:
        console.print("[red]Failed to fetch space info[/red]")
        sys.exit(1)

    console.print(f"[green]✓[/green] Space: {space_info.get('name', space)}")
    console.print(f"[dim]Network: {space_info.get('network', 'Unknown')}[/dim]")
    console.print(f"[dim]Symbol: {space_info.get('symbol', 'Unknown')}[/dim]\n")

    # Get proposal details
    title = Prompt.ask("Proposal title", default="Test Proposal: Agent Voting System")

    body = Prompt.ask(
        "Proposal body",
        default="This is a test proposal to verify the autonomous voting agent can participate in DAO governance."
    )

    choices_input = Prompt.ask(
        "Choices (comma-separated)",
        default="For,Against,Abstain"
    )
    choices = [c.strip() for c in choices_input.split(",")]

    # Time settings
    start_offset = int(Prompt.ask("Start in X seconds", default="60"))
    duration = int(Prompt.ask("Duration in seconds", default="86400"))  # 24 hours default

    start = int(time.time()) + start_offset
    end = start + duration

    console.print(f"\n[yellow]Proposal will:[/yellow]")
    console.print(f"  • Start in {start_offset} seconds")
    console.print(f"  • Run for {duration} seconds ({duration // 3600} hours)")
    console.print(f"  • Choices: {', '.join(choices)}\n")

    # Get private key from wallet
    try:
        with open("../quickstart-quorum/.operate/services/sc-ddcf5c34-4cb3-4263-9a90-940d30fd6dd9/keys.json") as f:
            keys_data = json.load(f)
            private_key = None

            # Extract private key from keys.json structure
            if isinstance(keys_data, list) and len(keys_data) > 0:
                agent_keys = keys_data[0]
                if "ethereum_private_key" in agent_keys:
                    private_key = agent_keys["ethereum_private_key"]
                    if not private_key.startswith("0x"):
                        private_key = "0x" + private_key

            if not private_key:
                console.print("[red]Could not find private key in keys.json[/red]")
                private_key = Prompt.ask("Enter private key (0x...)", password=True)
    except FileNotFoundError:
        console.print("[yellow]Wallet keys file not found[/yellow]")
        private_key = Prompt.ask("Enter private key (0x...)", password=True)

    if not Confirm.ask("\n[bold]Create this proposal?[/bold]"):
        console.print("[yellow]Cancelled[/yellow]")
        sys.exit(0)

    # Create proposal
    result = await create_proposal(
        space=space,
        title=title,
        body=body,
        choices=choices,
        start=start,
        end=end,
        private_key=private_key,
    )

    if "error" in result:
        console.print(f"\n[red]✗ Failed to create proposal[/red]")
        console.print(f"[dim]{result}[/dim]")
    elif "id" in result or "ipfsHash" in result:
        proposal_id = result.get("id") or result.get("ipfsHash")
        console.print(f"\n[green]✓ Proposal created successfully![/green]")
        console.print(f"[cyan]Proposal ID:[/cyan] {proposal_id}")
        console.print(f"[cyan]View at:[/cyan] https://snapshot.org/#/{space}/proposal/{proposal_id}")
    else:
        console.print(f"\n[yellow]Response:[/yellow]")
        console.print(result)


if __name__ == "__main__":
    asyncio.run(main())
