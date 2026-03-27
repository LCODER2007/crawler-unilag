"""
Smart ORCID Extraction - Get ORCIDs from papers we harvest.
When we harvest papers from OpenAlex, the authorship data includes ORCID IDs.
This is the BEST way to get accurate ORCIDs for UNILAG researchers.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import requests

UNILAG_ROR = "04jpmwt24"

def extract_orcids_from_works():
    """
    Query OpenAlex for UNILAG papers and extract ORCID IDs from the authorship data.
    This gives us ORCIDs for people who actually published from UNILAG.
    """
    print("=" * 70)
    print("Smart ORCID Extraction from UNILAG Papers")
    print("=" * 70)
    print()
    
    print("Querying OpenAlex for UNILAG papers with full authorship data...")
    print()
    
    # Query for papers with detailed authorship info
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
        print(f"✓ Found {len(works)} UNILAG papers")
        print()
        
        # Extract ORCIDs from authorships
        orcid_map = {}  # name -> orcid
        author_stats = {}  # name -> {orcid, paper_count, institutions}
        
        print("Extracting ORCIDs from authorship data...")
        print("-" * 70)
        
        for work in works:
            authorships = work.get('authorships', [])
            
            for authorship in authorships:
                # Check if this author is affiliated with UNILAG
                institutions = authorship.get('institutions', [])
                is_unilag = any(
                    inst.get('ror') == f"https://ror.org/{UNILAG_ROR}" 
                    for inst in institutions
                )
                
                if not is_unilag:
                    continue
                
                # Get author info
                author = authorship.get('author', {})
                name = author.get('display_name', '')
                orcid = author.get('orcid', '')
                
                if not name:
                    continue
                
                # Extract ORCID ID from URL
                orcid_id = None
                if orcid:
                    orcid_id = orcid.replace('https://orcid.org/', '')
                
                # Track this author
                if name not in author_stats:
                    author_stats[name] = {
                        'orcid': orcid_id,
                        'paper_count': 0,
                        'openalex_id': author.get('id', ''),
                        'has_orcid': bool(orcid_id)
                    }
                
                author_stats[name]['paper_count'] += 1
                
                # Update ORCID if we found one
                if orcid_id and not author_stats[name]['orcid']:
                    author_stats[name]['orcid'] = orcid_id
        
        print(f"✓ Found {len(author_stats)} unique UNILAG authors in papers")
        print()
        
        # Count how many have ORCIDs
        with_orcid = sum(1 for a in author_stats.values() if a['orcid'])
        
        print("=" * 70)
        print(f"✓ {with_orcid} authors have ORCID IDs ({with_orcid/len(author_stats)*100:.1f}%)")
        print(f"✗ {len(author_stats) - with_orcid} authors without ORCID IDs")
        print("=" * 70)
        print()
        
        # Save ORCIDs
        os.makedirs('data', exist_ok=True)
        
        # Simple ORCID map
        orcid_simple = {name: info['orcid'] for name, info in author_stats.items()}
        with open('data/unilag_orcids.json', 'w', encoding='utf-8') as f:
            json.dump(orcid_simple, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Saved ORCID map to: data/unilag_orcids.json")
        
        # Detailed author stats
        with open('data/unilag_authors_detailed.json', 'w', encoding='utf-8') as f:
            json.dump(author_stats, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Saved detailed stats to: data/unilag_authors_detailed.json")
        print()
        
        # Show top authors with ORCIDs
        print("Top 20 UNILAG Authors with ORCID IDs (by paper count):")
        print("-" * 70)
        
        authors_with_orcid = [
            (name, info) for name, info in author_stats.items() 
            if info['orcid']
        ]
        authors_with_orcid.sort(key=lambda x: x[1]['paper_count'], reverse=True)
        
        for i, (name, info) in enumerate(authors_with_orcid[:20], 1):
            print(f"{i:2}. {name:45} | {info['paper_count']:3} papers")
            print(f"    ORCID: {info['orcid']}")
        
        print()
        
        # Show authors without ORCIDs (top 10 by paper count)
        print("Top 10 UNILAG Authors WITHOUT ORCID IDs:")
        print("-" * 70)
        
        authors_without_orcid = [
            (name, info) for name, info in author_stats.items() 
            if not info['orcid']
        ]
        authors_without_orcid.sort(key=lambda x: x[1]['paper_count'], reverse=True)
        
        for i, (name, info) in enumerate(authors_without_orcid[:10], 1):
            print(f"{i:2}. {name:45} | {info['paper_count']:3} papers")
        
        print()
        print("These authors should be encouraged to create ORCID accounts!")
        print()
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    extract_orcids_from_works()
