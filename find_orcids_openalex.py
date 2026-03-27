"""
Find ORCID IDs for UNILAG staff using OpenAlex API.
OpenAlex has better name matching and already links authors to their ORCIDs.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import requests
import time

UNILAG_ROR = "04jpmwt24"

def find_orcids_via_openalex():
    """
    Use OpenAlex to find UNILAG authors and their ORCID IDs.
    This is more reliable than searching ORCID directly.
    """
    print("=" * 70)
    print("ORCID Finder via OpenAlex for UNILAG Staff")
    print("=" * 70)
    print()
    
    print("Querying OpenAlex for UNILAG authors...")
    print()
    
    # Query OpenAlex for authors affiliated with UNILAG
    url = (
        f"https://api.openalex.org/authors"
        f"?filter=last_known_institutions.ror:{UNILAG_ROR}"
        f"&per-page=200"
        f"&mailto=library@unilag.edu.ng"
    )
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        authors = data.get('results', [])
        print(f"✓ Found {len(authors)} UNILAG authors in OpenAlex")
        print()
        
        orcid_data = {}
        orcid_count = 0
        
        print("Extracting ORCID IDs...")
        print("-" * 70)
        
        for i, author in enumerate(authors, 1):
            name = author.get('display_name', '')
            orcid_url = author.get('orcid')
            
            if orcid_url:
                # Extract ORCID ID from URL (format: https://orcid.org/0000-0002-1234-5678)
                orcid_id = orcid_url.replace('https://orcid.org/', '')
                orcid_data[name] = orcid_id
                orcid_count += 1
                
                # Get additional info
                works_count = author.get('works_count', 0)
                cited_by = author.get('cited_by_count', 0)
                
                print(f"{i:3}. ✓ {name:45} → {orcid_id}")
                print(f"      Works: {works_count:4} | Citations: {cited_by:6}")
            else:
                orcid_data[name] = None
                print(f"{i:3}. ✗ {name:45} → No ORCID")
        
        print()
        print("=" * 70)
        print(f"✓ Found {orcid_count} ORCIDs out of {len(authors)} authors")
        print(f"  Success rate: {(orcid_count/len(authors)*100):.1f}%")
        print("=" * 70)
        print()
        
        # Save to file
        os.makedirs('data', exist_ok=True)
        orcid_file = 'data/unilag_orcids.json'
        
        with open(orcid_file, 'w', encoding='utf-8') as f:
            json.dump(orcid_data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Saved {len(orcid_data)} author records to: {orcid_file}")
        print()
        
        # Also save detailed author info
        author_details = {}
        for author in authors:
            name = author.get('display_name', '')
            author_details[name] = {
                'orcid': author.get('orcid', '').replace('https://orcid.org/', '') if author.get('orcid') else None,
                'openalex_id': author.get('id', ''),
                'works_count': author.get('works_count', 0),
                'cited_by_count': author.get('cited_by_count', 0),
                'h_index': author.get('summary_stats', {}).get('h_index', 0),
                'i10_index': author.get('summary_stats', {}).get('i10_index', 0),
                'last_known_institution': author.get('last_known_institutions', [{}])[0].get('display_name', '') if author.get('last_known_institutions') else ''
            }
        
        details_file = 'data/unilag_authors_detailed.json'
        with open(details_file, 'w', encoding='utf-8') as f:
            json.dump(author_details, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Saved detailed author info to: {details_file}")
        print()
        
        # Show top researchers by citations
        print("Top 10 UNILAG Researchers by Citations:")
        print("-" * 70)
        sorted_authors = sorted(
            author_details.items(),
            key=lambda x: x[1]['cited_by_count'],
            reverse=True
        )[:10]
        
        for i, (name, info) in enumerate(sorted_authors, 1):
            print(f"{i:2}. {name:45} | {info['cited_by_count']:6} citations")
            if info['orcid']:
                print(f"    ORCID: {info['orcid']}")
        
        print()
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    find_orcids_via_openalex()
