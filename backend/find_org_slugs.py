#!/usr/bin/env python3
"""Script to find correct organization slugs for Arbitrum, Uniswap, and Aave in Tally API."""

import asyncio
import sys
from typing import List, Dict, Any

from services.tally_service import TallyService


async def search_organizations_by_name(service: TallyService, search_terms: List[str]) -> List[Dict[str, Any]]:
    """Search for organizations by name patterns."""
    results = []
    
    try:
        # Get all organizations (paginated)
        organizations, cursor = await service.get_organizations(limit=100)
        all_orgs = organizations
        
        # Continue fetching if there are more pages
        while cursor:
            organizations, cursor = await service.get_organizations(limit=100, after_cursor=cursor)
            all_orgs.extend(organizations)
            
        print(f"Found {len(all_orgs)} total organizations")
        
        # Search for matching organizations
        for search_term in search_terms:
            matches = []
            for org in all_orgs:
                if (search_term.lower() in org.name.lower() or 
                    search_term.lower() in org.slug.lower()):
                    matches.append({
                        'search_term': search_term,
                        'id': org.id,
                        'name': org.name,
                        'slug': org.slug,
                        'proposals_count': org.proposals_count,
                        'has_active_proposals': org.has_active_proposals
                    })
            
            if matches:
                results.extend(matches)
                print(f"\nMatches for '{search_term}':")
                for match in matches:
                    print(f"  Name: {match['name']}")
                    print(f"  Slug: {match['slug']}")
                    print(f"  ID: {match['id']}")
                    print(f"  Proposals: {match['proposals_count']}")
                    print(f"  Has active: {match['has_active_proposals']}")
                    print("  ---")
            else:
                print(f"\nNo matches found for '{search_term}'")
                
    except Exception as e:
        print(f"Error searching organizations: {e}")
        
    return results


async def test_specific_slugs(service: TallyService, slugs: List[str]) -> Dict[str, Any]:
    """Test specific slugs to see if they exist."""
    results = {}
    
    for slug in slugs:
        try:
            org_data = await service._get_organization_by_slug(slug)
            if org_data:
                results[slug] = {
                    'found': True,
                    'data': org_data
                }
                print(f"✓ Found organization for slug '{slug}': {org_data['name']}")
            else:
                results[slug] = {
                    'found': False,
                    'data': None
                }
                print(f"✗ No organization found for slug '{slug}'")
        except Exception as e:
            results[slug] = {
                'found': False,
                'error': str(e)
            }
            print(f"✗ Error checking slug '{slug}': {e}")
            
    return results


async def main():
    """Main function to find correct organization slugs."""
    print("🔍 Searching for correct organization slugs for Arbitrum, Uniswap, and Aave...")
    
    service = TallyService()
    
    # Test the current slugs first
    current_slugs = ["arbitrum", "uniswap", "aave"]
    print("\n" + "="*60)
    print("TESTING CURRENT SLUGS")
    print("="*60)
    
    current_results = await test_specific_slugs(service, current_slugs)
    
    # Search for organizations by name
    search_terms = ["arbitrum", "uniswap", "aave", "compound", "makerdao", "maker"]
    print("\n" + "="*60)
    print("SEARCHING BY NAME PATTERNS")  
    print("="*60)
    
    search_results = await search_organizations_by_name(service, search_terms)
    
    # Try some common variations
    possible_slugs = [
        "arbitrum-dao", "arbitrum-one", "arbitrum-foundation",
        "uniswap-dao", "uniswap-labs", "uniswap-governance",
        "aave-dao", "aave-governance", "aave-protocol"
    ]
    
    print("\n" + "="*60)
    print("TESTING POSSIBLE SLUG VARIATIONS")
    print("="*60)
    
    variation_results = await test_specific_slugs(service, possible_slugs)
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    print("\nWorking slugs found:")
    all_results = {**current_results, **variation_results}
    working_slugs = []
    
    for slug, result in all_results.items():
        if result.get('found'):
            working_slugs.append(slug)
            data = result['data']
            print(f"  ✓ {slug} -> {data['name']} (ID: {data['id']}, Proposals: {data['proposals_count']})")
    
    if working_slugs:
        print(f"\n💡 Suggested TOP_ORGANIZATIONS environment variable:")
        print(f"TOP_ORGANIZATIONS={','.join(working_slugs)}")
    else:
        print("\n⚠️  No working slugs found. You may need to browse all organizations manually.")
        
    print(f"\n📊 Found {len(search_results)} organizations matching search terms.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Search cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)