#!/usr/bin/env python3
"""Lightweight script to test specific organization slugs."""

import asyncio
import sys
from services.tally_service import TallyService


async def test_single_slug(service: TallyService, slug: str) -> dict:
    """Test a single slug."""
    try:
        org_data = await service._get_organization_by_slug(slug)
        if org_data:
            return {
                'slug': slug,
                'found': True,
                'name': org_data['name'],
                'id': org_data['id'],
                'proposals_count': org_data['proposals_count'],
                'has_active': org_data['has_active_proposals']
            }
        else:
            return {'slug': slug, 'found': False}
    except Exception as e:
        return {'slug': slug, 'found': False, 'error': str(e)}


async def main():
    """Test common organization slug patterns."""
    service = TallyService()
    
    # Common slug patterns for major DAOs based on Tally.xyz patterns
    test_slugs = [
        # Arbitrum variations
        "arbitrum", "arbitrum-dao", "arbitrum-one", "arbitrum-foundation", 
        "arbitrumdao", "arbitrum-governance",
        
        # Uniswap variations  
        "uniswap", "uniswap-dao", "uniswap-labs", "uniswap-governance",
        "uniswapgovernance", "uniswap-v3",
        
        # Aave variations
        "aave", "aave-dao", "aave-governance", "aave-protocol",
        "aavegovernance", "aave-v3",
        
        # Other major DAOs that might be worth checking
        "compound", "compound-governance", "makerdao", "maker",
        "ens", "ens-dao", "gitcoin", "gitcoin-dao"
    ]
    
    print(f"🔍 Testing {len(test_slugs)} potential organization slugs...")
    print("This approach tests each slug individually to avoid rate limits.\n")
    
    found_orgs = []
    
    for slug in test_slugs:
        result = await test_single_slug(service, slug)
        
        if result['found']:
            found_orgs.append(result)
            print(f"✅ FOUND: {slug}")
            print(f"   Name: {result['name']}")
            print(f"   ID: {result['id']}")
            print(f"   Proposals: {result['proposals_count']}")
            print(f"   Has active: {result['has_active']}")
            print()
        else:
            print(f"❌ Not found: {slug}")
            if 'error' in result:
                print(f"   Error: {result['error']}")
        
        # Small delay to be respectful to the API
        await asyncio.sleep(0.5)
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    if found_orgs:
        print(f"\n🎉 Found {len(found_orgs)} working organization slugs:")
        
        # Sort by proposal count for best recommendations
        sorted_orgs = sorted(found_orgs, key=lambda x: x['proposals_count'], reverse=True)
        
        for org in sorted_orgs:
            print(f"  • {org['slug']} -> {org['name']} ({org['proposals_count']} proposals)")
        
        # Create recommendations for top 3 most active
        top_3_slugs = [org['slug'] for org in sorted_orgs[:3]]
        print(f"\n💡 Recommended TOP_ORGANIZATIONS setting:")
        print(f"TOP_ORGANIZATIONS={','.join(top_3_slugs)}")
        
    else:
        print("\n⚠️  No working organization slugs found.")
        print("The API might be using different slug patterns or there might be API issues.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Search cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)