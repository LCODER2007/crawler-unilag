"""
Get REAL UNILAG ORCIDs - Only for confirmed UNILAG staff members.
This validates authors against the actual staff list before extracting ORCIDs.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import requests
from uraas.utils.staff_validator import staff_validator

UNILAG_ROR = "05rk03822"

def get_real_unilag_orcids():
    """
    Query OpenAlex for papers, but ONLY extract ORCIDs for authors who are
    confirmed UNILAG staff members (validated against staff cache).
    """
    print("=" * 70)
    print("REAL UNILAG ORCID Extraction (Staff-Validated)")
    print("=" * 70)
    print()
    
    # Load staff cache
    print(f"Loading UNILAG staff cache...")
    staff_count = len(staff_validator.staff_names)
    print(f"✓ Loaded {staff_count} confirmed UNILAG staff members")
    print()
    
    print("Querying OpenAlex for papers with UNILAG ROR ID...")
    print("(Will validate authors against staff list)")
    print()
    
    # Query OpenAlex for papers
    url = (
        f"https://api.openalex.org/works"
        f"?filter=institutions.ror:{UNILAG_ROR}"
        f"&select=id,title,authorships"
        f"&per-page=200"
        f"&mailto=library@unilag.edu.ng"
    )
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        works = data.get('results', [])
        print(f"✓ Found {len(works)} papers with UNILAG ROR ID")
        print()
        
        # Extract ORCIDs but ONLY for validated UNILAG staff
        validated_orcids = {}  # name -> orcid
        author_stats = {}  # name -> stats
        
        total_authors = 0
        validated_authors = 0
        orcids_found = 0
        
        print("Validating authors and extracting ORCIDs...")
        print("-" * 70)
        
        for work in works:
            authorships = work.get('authorships', [])
            
            for authorship in authorships:
                # Check if affiliated with UNILAG
                institutions = authorship.get('institutions', [])
                is_unilag_affiliated = any(
                    inst.get('ror') == f"https://ror.org/{UNILAG_ROR}" 
                    for inst in institutions
                )
                
                if not is_unilag_affiliated:
                    continue
                
                author = authorship.get('author', {})
                name = author.get('display_name', '')
                orcid = author.get('orcid', '')
                
                if not name:
                    continue
                
                total_authors += 1
                
                # CRITICAL: Validate against staff list
                is_staff = staff_validator.is_staff_member(name)
                
                if not is_staff:
                    continue  # Skip non-staff authors
                
                validated_authors += 1
                
                # Extract ORCID ID
                orcid_id = None
                if orcid:
                    orcid_id = orcid.replace('https://orcid.org/', '')
                    orcids_found += 1
                
                # Track this validated staff member
                if name not in author_stats:
                    author_stats[name] = {
                        'orcid': orcid_id,
                        'paper_count': 0,
                        'openalex_id': author.get('id', ''),
                        'validated': True
                    }
                
                author_stats[name]['paper_count'] += 1
                
                # Update ORCID if found
                if orcid_id and not author_stats[name]['orcid']:
                    author_stats[name]['orcid'] = orcid_id
                    validated_orcids[name] = orcid_id
        
        print()
        print("=" * 70)
        print(f"Total authors in papers: {total_authors}")
        print(f"✓ Validated UNILAG staff: {validated_authors}")
        print(f"✓ Staff with ORCID IDs: {len(validated_orcids)}")
        print(f"✗ Staff without ORCIDs: {validated_authors - len(validated_orcids)}")
        print("=" * 70)
        print()
        
        if not validated_orcids:
            print("✗ No ORCIDs found for validated UNILAG staff!")
            print("  This might mean:")
            print("  1. The ROR ID is returning papers from wrong institution")
            print("  2. Staff names in cache don't match OpenAlex names")
            print("  3. UNILAG staff don't have ORCID IDs registered")
            return
        
        # Save validated ORCIDs
        os.makedirs('data', exist_ok=True)
        
        with open('data/unilag_orcids.json', 'w', encoding='utf-8') as f:
            json.dump(validated_orcids, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Saved {len(validated_orcids)} validated ORCIDs to: data/unilag_orcids.json")
        
        # Save detailed stats
        with open('data/unilag_authors_detailed.json', 'w', encoding='utf-8') as f:
            json.dump(author_stats, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Saved detailed stats to: data/unilag_authors_detailed.json")
        print()
        
        # Show validated staff with ORCIDs
        if validated_orcids:
            print("Validated UNILAG Staff with ORCID IDs:")
            print("-" * 70)
            
            sorted_staff = sorted(
                author_stats.items(),
                key=lambda x: x[1]['paper_count'],
                reverse=True
            )
            
            for i, (name, info) in enumerate(sorted_staff[:20], 1):
                if info['orcid']:
                    print(f"{i:2}. {name:45} | {info['paper_count']:3} papers")
                    print(f"    ORCID: {info['orcid']}")
            print()
        
        # Show validated staff WITHOUT ORCIDs
        staff_without_orcid = [
            (name, info) for name, info in author_stats.items()
            if not info['orcid']
        ]
        
        if staff_without_orcid:
            print("Validated UNILAG Staff WITHOUT ORCID IDs:")
            print("-" * 70)
            staff_without_orcid.sort(key=lambda x: x[1]['paper_count'], reverse=True)
            
            for i, (name, info) in enumerate(staff_without_orcid[:10], 1):
                print(f"{i:2}. {name:45} | {info['paper_count']:3} papers")
            print()
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    get_real_unilag_orcids()
