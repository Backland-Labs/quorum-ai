#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "web3",
#     "python-dotenv",
#     "rich",
#     "typer",
# ]
# ///

"""
Deploy AttestationTracker contract to Base mainnet.

Usage:
    ./scripts/deploy_attestation_tracker.py --help
    ./scripts/deploy_attestation_tracker.py
    ./scripts/deploy_attestation_tracker.py --dry-run
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# Initialize Rich console for pretty output
console = Console()

# Base mainnet configuration
BASE_RPC_URL = "https://mainnet.base.org"
BASE_EAS_ADDRESS = "0xF095fE4b23958b08D38e52d5d5674bBF0C03cbF6" #EIP712Proxy address

app = typer.Typer(help="Deploy AttestationTracker contract")

def get_env_vars() -> tuple[str, str]:
    """Get required environment variables."""
    private_key = os.getenv("PRIVATE_KEY")
    owner_address = os.getenv("ATTESTATION_TRACKER_OWNER")
    
    if not private_key:
        console.print("[red]Error: PRIVATE_KEY not found in environment[/red]")
        sys.exit(1)
    
    if not owner_address:
        console.print("[red]Error: ATTESTATION_TRACKER_OWNER not found in environment[/red]")
        sys.exit(1)
    
    return private_key, owner_address

def compile_contract() -> dict:
    """Compile the AttestationTracker contract using forge."""
    console.print("[yellow]Compiling contracts...[/yellow]")
    
    contracts_dir = Path(__file__).parent.parent / "contracts"
    os.chdir(contracts_dir)
    
    # Build contracts
    result = os.system("forge build")
    if result != 0:
        console.print("[red]Failed to compile contracts[/red]")
        sys.exit(1)
    
    # Load the compiled contract
    artifact_path = contracts_dir / "out" / "AttestationTracker.sol" / "AttestationTracker.json"
    if not artifact_path.exists():
        console.print(f"[red]Contract artifact not found at {artifact_path}[/red]")
        sys.exit(1)
    
    with open(artifact_path) as f:
        contract_json = json.load(f)
    
    return {
        "abi": contract_json["abi"],
        "bytecode": contract_json["bytecode"]["object"]
    }

def deploy_contract(
    w3: Web3,
    private_key: str,
    owner_address: str,
    eas_address: str,
    contract_data: dict,
    dry_run: bool = False
) -> Optional[str]:
    """Deploy the AttestationTracker contract."""
    account = w3.eth.account.from_key(private_key)
    
    # Create contract instance
    contract = w3.eth.contract(
        abi=contract_data["abi"],
        bytecode=contract_data["bytecode"]
    )
    
    # Build constructor transaction
    constructor_tx = contract.constructor(
        owner_address,
        eas_address
    ).build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 2000000,
        'gasPrice': w3.eth.gas_price,
    })
    
    if dry_run:
        console.print("[yellow]Dry run mode - no actual deployment[/yellow]")
        console.print(f"Would deploy from: {account.address}")
        console.print(f"Estimated gas: {constructor_tx['gas']}")
        console.print(f"Gas price: {w3.from_wei(constructor_tx['gasPrice'], 'gwei')} gwei")
        return None
    
    # Sign and send transaction
    signed_tx = account.sign_transaction(constructor_tx)
    console.print("[yellow]Sending deployment transaction...[/yellow]")
    
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    console.print(f"Transaction hash: {tx_hash.hex()}")
    
    # Wait for confirmation
    console.print("[yellow]Waiting for confirmation...[/yellow]")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    if receipt.status == 1:
        contract_address = receipt.contractAddress
        console.print(f"[green]✓ Contract deployed at: {contract_address}[/green]")
        return contract_address
    else:
        console.print("[red]✗ Deployment failed[/red]")
        return None

def verify_deployment(w3: Web3, contract_address: str, owner_address: str, eas_address: str, contract_abi: list):
    """Verify the deployed contract."""
    contract = w3.eth.contract(address=contract_address, abi=contract_abi)
    
    # Check owner
    deployed_owner = contract.functions.owner().call()
    if deployed_owner.lower() != owner_address.lower():
        console.print(f"[red]Owner mismatch: expected {owner_address}, got {deployed_owner}[/red]")
        return False
    
    # Check EAS address
    deployed_eas = contract.functions.EAS().call()
    if deployed_eas.lower() != eas_address.lower():
        console.print(f"[red]EAS mismatch: expected {eas_address}, got {deployed_eas}[/red]")
        return False
    
    # Test getNumAttestations
    test_address = "0x0000000000000000000000000000000000000001"
    count = contract.functions.getNumAttestations(test_address).call()
    if count != 0:
        console.print(f"[red]Initial count should be 0, got {count}[/red]")
        return False
    
    console.print("[green]✓ Contract verification passed[/green]")
    return True

@app.command()
def deploy(
    dry_run: bool = typer.Option(False, "--dry-run", help="Perform a dry run without deploying"),
    skip_compile: bool = typer.Option(False, "--skip-compile", help="Skip contract compilation"),
    env_file: Optional[Path] = typer.Option(None, "--env-file", "-e", help="Path to .env file"),
):
    """Deploy AttestationTracker contract to Base mainnet."""
    
    # Load environment variables
    if env_file:
        load_dotenv(env_file)
    else:
        # Try to load from contracts/.env or .env
        contracts_env = Path(__file__).parent.parent / "contracts" / ".env"
        if contracts_env.exists():
            load_dotenv(contracts_env)
        else:
            load_dotenv()
    
    # Get configuration
    private_key, owner_address = get_env_vars()
    
    # Display configuration
    table = Table(title="Base Mainnet Deployment Configuration")
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Network", "Base Mainnet")
    table.add_row("RPC URL", BASE_RPC_URL)
    table.add_row("Owner Address", owner_address)
    table.add_row("EAS Address", BASE_EAS_ADDRESS)
    
    console.print(table)
    
    # Safety confirmation for Base mainnet
    if not dry_run:
        console.print(Panel.fit(
            "[bold yellow]⚠️  Deploying to Base Mainnet[/bold yellow]\n"
            "This will consume real ETH on Base.",
            title="Base Deployment"
        ))
        
        confirm = typer.confirm("Are you sure you want to proceed?")
        if not confirm:
            console.print("[yellow]Deployment cancelled[/yellow]")
            return
    
    # Compile contract
    if not skip_compile:
        contract_data = compile_contract()
    else:
        console.print("[yellow]Skipping compilation...[/yellow]")
        contracts_dir = Path(__file__).parent.parent / "contracts"
        artifact_path = contracts_dir / "out" / "AttestationTracker.sol" / "AttestationTracker.json"
        with open(artifact_path) as f:
            contract_json = json.load(f)
        contract_data = {
            "abi": contract_json["abi"],
            "bytecode": contract_json["bytecode"]["object"]
        }
    
    # Connect to Base mainnet
    console.print("[yellow]Connecting to Base mainnet...[/yellow]")
    w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))
    
    # Add POA middleware for Base network
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    if not w3.is_connected():
        console.print("[red]Failed to connect to network[/red]")
        sys.exit(1)
    
    # Check deployer balance
    account = w3.eth.account.from_key(private_key)
    balance = w3.eth.get_balance(account.address)
    console.print(f"Deployer address: {account.address}")
    console.print(f"Deployer balance: {w3.from_wei(balance, 'ether')} ETH")
    
    if balance < w3.to_wei(0.001, 'ether'):
        console.print("[red]Insufficient balance for deployment (need at least 0.001 ETH)[/red]")
        if not dry_run:
            sys.exit(1)
    
    # Deploy contract
    contract_address = deploy_contract(
        w3, private_key, owner_address, BASE_EAS_ADDRESS, 
        contract_data, dry_run
    )
    
    if contract_address and not dry_run:
        # Verify deployment
        console.print("[yellow]Verifying deployment...[/yellow]")
        if verify_deployment(w3, contract_address, owner_address, BASE_EAS_ADDRESS, contract_data["abi"]):
            # Save deployment info
            deployment_info = {
                "network": "base",
                "contract_address": contract_address,
                "owner": owner_address,
                "eas": BASE_EAS_ADDRESS,
                "deployer": account.address,
                "timestamp": str(w3.eth.get_block('latest')['timestamp'])
            }
            
            deployments_dir = Path(__file__).parent.parent / "contracts" / "deployments"
            deployments_dir.mkdir(exist_ok=True)
            
            deployment_file = deployments_dir / "base_attestation_tracker.json"
            with open(deployment_file, 'w') as f:
                json.dump(deployment_info, f, indent=2)
            
            console.print(f"[green]Deployment info saved to: {deployment_file}[/green]")
            
            # Print summary
            console.print(Panel.fit(
                f"[bold green]✅ Deployment Successful![/bold green]\n\n"
                f"Contract Address: [cyan]{contract_address}[/cyan]\n"
                f"Owner: [cyan]{owner_address}[/cyan]\n"
                f"Network: [cyan]Base Mainnet[/cyan]",
                title="Deployment Complete"
            ))
            
            console.print("\n[yellow]Next steps:[/yellow]")
            console.print("1. Verify the contract on BaseScan")
            console.print("2. Test the contract functions")
            console.print("3. Update any dependent systems with the new address")

@app.command()
def info():
    """Display Base network information and check for existing deployments."""
    table = Table(title="Base Network Configuration")
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Network", "Base Mainnet")
    table.add_row("RPC URL", BASE_RPC_URL)
    table.add_row("EAS Address", BASE_EAS_ADDRESS)
    
    console.print(table)
    
    # Check for existing deployments
    deployments_dir = Path(__file__).parent.parent / "contracts" / "deployments"
    if deployments_dir.exists():
        deployment_file = deployments_dir / "base_attestation_tracker.json"
        if deployment_file.exists():
            with open(deployment_file) as f:
                deployment = json.load(f)
            
            console.print("\n[green]Found existing Base deployment:[/green]")
            console.print(f"Contract: {deployment['contract_address']}")
            console.print(f"Owner: {deployment['owner']}")
            console.print(f"Deployed by: {deployment.get('deployer', 'Unknown')}")
            console.print(f"Timestamp: {deployment.get('timestamp', 'Unknown')}")
        else:
            console.print("\n[yellow]No existing Base deployment found[/yellow]")

if __name__ == "__main__":
    app()