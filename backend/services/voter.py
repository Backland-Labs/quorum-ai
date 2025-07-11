"""Web3 connection and wallet management service."""

import os
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get environment variables
WEB3_PROVIDER_URL = os.getenv("ETHEREUM_RPC_URL")
GNOSIS_PRIVATE_KEY = os.getenv("GNOSIS_PRIVATE_KEY")
GNOSIS_SAFE_ADDRESS = os.getenv("GNOSIS_SAFE_ADDRESS")
ETHEREUM_RPC_URL=f"https://sepolia.infura.io/v3/{os.getenv('INFURA_API_KEY')}"

# Initialize Web3
w3 = Web3(Web3.HTTPProvider(ETHEREUM_RPC_URL))

# Verify connection
if not w3.is_connected():
    raise ConnectionError("Failed to connect to Ethereum network")

# Create account using web3's eth.account
account = w3.eth.account.from_key(GNOSIS_PRIVATE_KEY)

# Print wallet address to confirm
print(f"Connected to Ethereum network")
print(f"Wallet address: {account.address}")
print(f"Gnosis Safe address: {GNOSIS_SAFE_ADDRESS}")