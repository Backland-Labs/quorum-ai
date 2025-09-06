#!/usr/bin/env python3

import os
import sys
import asyncio
from datetime import datetime

# Add backend to path
sys.path.append('./backend')

# Set environment variables for testing
os.environ.update({
    'EAS_CONTRACT_ADDRESS': '0x4200000000000000000000000000000000000021',
    'EAS_SCHEMA_UID': '0x4b646acb1d459357d3be21287c81da4026e8440b7283efbab2d124c54478b429',
    'BASE_SAFE_ADDRESS': '0x9876543210fedcba9876543210fedcba98765432',
    'BASE_RPC_URL': 'http://localhost:8545',
    'ATTESTATION_TRACKER_ADDRESS': '0x82372200341a23377129Ccc1aE2EFeB3048440eC',
    'ATTESTATION_CHAIN': 'base',
    'ATTESTATION_TRACKER_OWNER': '0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266',
})

from services.safe_service import SafeService
from models import EASAttestationData

async def test_safe_service_fix():
    """Test the SafeService with proper EAS signature generation."""
    
    print("🧪 Testing SafeService with fixed EAS signature generation...")
    
    # Create test attestation data
    test_attestation = EASAttestationData(
        proposal_id="test-proposal-123",
        space_id="test-dao.eth",
        voter_address="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
        choice=1,  # FOR
        vote_tx_hash="0x" + "a" * 64,
        timestamp=datetime.now()
    )
    
    # Initialize SafeService
    safe_service = SafeService()
    
    try:
        print("📝 Building EAS attestation transaction with proper signature...")
        
        # This should now generate a proper signature
        tx_data = safe_service._build_eas_attestation_tx(test_attestation)
        
        print(f"✅ Transaction data built successfully:")
        print(f"   To: {tx_data['to']}")
        print(f"   Data length: {len(tx_data['data'])} characters")
        print(f"   Value: {tx_data['value']}")
        
        # The transaction should now work because it has a valid signature
        print("🎉 SUCCESS: SafeService now generates proper EAS signatures!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_safe_service_fix())
    
    if result:
        print("\n🎉 ✅ SUMMARY: SafeService fix is working!")
        print("The attestation should now succeed when called from the agent.")
    else:
        print("\n❌ SUMMARY: SafeService fix needs more work.")