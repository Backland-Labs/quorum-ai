"""Safe transaction service for handling multi-signature wallet operations."""

import json
from typing import Dict, Optional, Any
from web3 import Web3
from eth_account import Account
from safe_eth.eth import EthereumClient
from safe_eth.safe import Safe
from safe_eth.safe.api import TransactionServiceApi
import logfire

from config import settings


SAFE_SERVICE_URLS = {
    "ethereum": "https://safe-transaction-mainnet.safe.global/",
    "gnosis": "https://safe-transaction-gnosis-chain.safe.global/",
    "base": "https://safe-transaction-base.safe.global/",
    "celo": "https://safe-transaction-celo.safe.global/",
    "mode": "https://safe-transaction-mode.safe.global/",
}


class SafeService:
    """Service for handling Safe multi-signature wallet transactions."""
    
    def __init__(self):
        """Initialize Safe service with configuration."""
        self.safe_addresses = json.loads(settings.safe_contract_addresses)
        self.rpc_endpoints = {
            "ethereum": settings.ethereum_ledger_rpc,
            "gnosis": settings.gnosis_ledger_rpc,
            "base": settings.base_ledger_rpc,
            "celo": settings.celo_ledger_rpc,
            "mode": settings.mode_ledger_rpc,
        }
        
        # Initialize account from private key
        with open("ethereum_private_key.txt", "r") as f:
            private_key = f.read().strip()
        
        self.account = Account.from_key(private_key)
        self._web3_connections = {}
        
        logfire.info(
            "SafeService initialized",
            eoa_address=self.account.address,
            safe_addresses=self.safe_addresses,
            available_chains=list(self.rpc_endpoints.keys())
        )
    
    def get_web3_connection(self, chain: str) -> Web3:
        """Get Web3 connection for specified chain.
        
        Args:
            chain: Blockchain network name
            
        Returns:
            Web3 instance connected to the chain
            
        Raises:
            ValueError: If no RPC endpoint configured for chain
            ConnectionError: If connection to network fails
        """
        if chain in self._web3_connections:
            return self._web3_connections[chain]
        
        rpc_url = self.rpc_endpoints.get(chain)
        if not rpc_url:
            raise ValueError(f"No RPC endpoint configured for chain: {chain}")
        
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            raise ConnectionError(f"Failed to connect to {chain} network")
        
        self._web3_connections[chain] = w3
        return w3
    
    def select_optimal_chain(self) -> str:
        """Select the cheapest chain for Safe transactions.
        
        Returns:
            Chain name with lowest expected gas costs
            
        Raises:
            ValueError: If no valid chain configuration found
        """
        # Priority order: cheapest to most expensive gas fees
        chain_priority = ["gnosis", "celo", "mode", "base", "ethereum"]
        
        for chain in chain_priority:
            if (chain in self.safe_addresses and 
                chain in self.rpc_endpoints and 
                self.rpc_endpoints[chain]):
                return chain
        
        # Fallback to first available
        available_chains = [
            chain for chain in self.safe_addresses.keys() 
            if chain in self.rpc_endpoints and self.rpc_endpoints[chain]
        ]
        
        if available_chains:
            return available_chains[0]
        
        raise ValueError("No valid chain configuration found")
    
    async def perform_activity_transaction(self, chain: Optional[str] = None) -> Dict[str, Any]:
        """Perform Safe transaction for daily activity requirement.
        
        Creates a 0-ETH transaction from the Safe to itself to satisfy activity tracking.
        
        Args:
            chain: Specific chain to use, or None to select optimal
            
        Returns:
            Dict with transaction details and success status
        """
        if not chain:
            chain = self.select_optimal_chain()
        
        with logfire.span("safe_service.perform_activity_transaction", chain=chain):
            logfire.info(f"Creating Safe activity transaction on {chain}")
            
            try:
                safe_address = self.safe_addresses.get(chain)
                if not safe_address:
                    raise ValueError(f"No Safe address configured for chain: {chain}")
                
                safe_address = Web3.to_checksum_address(safe_address)
                
                # Get Web3 and Ethereum client
                w3 = self.get_web3_connection(chain)
                eth_client = EthereumClient(self.rpc_endpoints[chain])
                
                # Initialize Safe instance
                safe_instance = Safe(safe_address, eth_client)
                
                # Get Safe service for this chain
                safe_service_url = SAFE_SERVICE_URLS.get(chain)
                if not safe_service_url:
                    raise ValueError(f"No Safe service URL configured for chain: {chain}")
                
                safe_service = TransactionServiceApi(
                    network=chain, 
                    base_url=safe_service_url
                )

                # Build dummy transaction: 0 ETH to self (minimal cost)
                safe_tx = safe_instance.build_multisig_tx(
                    to=safe_address,  # Send to itself
                    value=0,          # 0 ETH value  
                    data=b'',         # Empty data
                    operation=0,      # CALL operation
                )

                # Sign Safe transaction hash
                signed_safe_tx_hash = self.account.unsafe_sign_hash(safe_tx.safe_tx_hash)
                safe_tx.signatures = signed_safe_tx_hash.signature
                
                logfire.info(
                    "Safe transaction built",
                    chain=chain,
                    safe_address=safe_address,
                    nonce=safe_tx.safe_nonce,
                    safe_tx_hash=safe_tx.safe_tx_hash.hex()
                )

                # Propose transaction to Safe Transaction Service
                safe_service.post_transaction(safe_tx)
                logfire.info("Transaction proposed to Safe service")

                # Execute Safe transaction on-chain
                ethereum_tx_sent = safe_instance.send_multisig_tx(
                    to=safe_tx.to,
                    value=safe_tx.value,
                    data=safe_tx.data,
                    operation=safe_tx.operation,
                    safe_tx_gas=safe_tx.safe_tx_gas,
                    base_gas=safe_tx.base_gas,
                    gas_price=safe_tx.gas_price,
                    gas_token=safe_tx.gas_token,
                    refund_receiver=safe_tx.refund_receiver,
                    signatures=safe_tx.signatures,
                    tx_sender_private_key=self.account.key.hex()
                )
                
                tx_hash = ethereum_tx_sent.tx_hash
                logfire.info(f"On-chain transaction sent: {tx_hash.hex()}")
                
                # Wait for confirmation
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
                
                if receipt["status"] == 1:
                    logfire.info(
                        "Safe activity transaction successful",
                        tx_hash=tx_hash.hex(),
                        block_number=receipt['blockNumber'],
                        gas_used=receipt['gasUsed']
                    )
                    
                    return {
                        "success": True, 
                        "tx_hash": tx_hash.hex(), 
                        "chain": chain,
                        "safe_address": safe_address,
                        "block_number": receipt['blockNumber'],
                        "gas_used": receipt['gasUsed']
                    }
                else:
                    logfire.error("Safe transaction reverted")
                    return {
                        "success": False, 
                        "error": "Transaction reverted",
                        "tx_hash": tx_hash.hex()
                    }

            except Exception as e:
                logfire.error(f"Error creating Safe activity transaction: {e}")
                return {"success": False, "error": str(e)}
    
    async def get_safe_nonce(self, chain: str, safe_address: str) -> int:
        """Get current nonce for a Safe on specified chain.
        
        Args:
            chain: Blockchain network name
            safe_address: Safe contract address
            
        Returns:
            Current Safe nonce
        """
        eth_client = EthereumClient(self.rpc_endpoints[chain])
        safe_instance = Safe(Web3.to_checksum_address(safe_address), eth_client)
        return safe_instance.retrieve_nonce()
    
    async def build_safe_transaction(
        self, 
        chain: str, 
        to: str, 
        value: int = 0, 
        data: bytes = b'',
        operation: int = 0
    ) -> Dict[str, Any]:
        """Build a Safe transaction for execution.
        
        Args:
            chain: Blockchain network name
            to: Recipient address
            value: ETH value to send
            data: Transaction data
            operation: Safe operation type (0=CALL, 1=DELEGATECALL)
            
        Returns:
            Dict with transaction details
        """
        safe_address = self.safe_addresses.get(chain)
        if not safe_address:
            raise ValueError(f"No Safe address configured for chain: {chain}")
        
        safe_address = Web3.to_checksum_address(safe_address)
        eth_client = EthereumClient(self.rpc_endpoints[chain])
        safe_instance = Safe(safe_address, eth_client)
        
        safe_tx = safe_instance.build_multisig_tx(
            to=to,
            value=value,
            data=data,
            operation=operation,
        )
        
        return {
            "safe_address": safe_address,
            "to": safe_tx.to,
            "value": safe_tx.value,
            "data": safe_tx.data.hex() if safe_tx.data else "",
            "operation": safe_tx.operation,
            "safe_tx_gas": safe_tx.safe_tx_gas,
            "base_gas": safe_tx.base_gas,
            "gas_price": safe_tx.gas_price,
            "gas_token": safe_tx.gas_token,
            "refund_receiver": safe_tx.refund_receiver,
            "nonce": safe_tx.safe_nonce,
            "safe_tx_hash": safe_tx.safe_tx_hash.hex()
        }