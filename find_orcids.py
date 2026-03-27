"""
ORCID Finder for UNILAG Staff
Searches for ORCID IDs for staff members and stores them for enhanced harvesting.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import requests
import time
from uraas.database import SessionLocal, Author

UNILAG_ROR = "04jpmwt24"

def search_orcid_for_person(name, affiliation="University of Lagos"):
    """
    Search ORCID public API for a person's ORCID ID.
    
    Args:
        name: Person's name
        affiliation: Institution name
        
    Returns:
        ORCID ID if found, None otherwise
    """
    try:
        # ORCID Public API search
        url = "https://pub.orcid.org/v3.0/search/"
        
        # Build query: name AND affiliation
        query = f'given-and-family-names:"{name}" AND affiliation-org-name:"University of Lagos"'
        
        params = {
            'q': query,
            'rows': 5
        }
        
        headers = {
            'Accept': 'application/json'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('result', [])
            
            if results:
                # Get the first result's ORCID
                orcid_id = results[0].get('orcid-identifier', {}).get('path')
                return orcid_id
        
        return None
        
    except Exception as e:
        print(f"  Error searching ORCID for {name}: {e}")
        return None

def find_orcids_for_staff():
    """Find ORCID IDs for all staff in the cache."""
    print("=" * 70)
    print("ORCID Finder for UNILAG Staff")
    print("=" * 70)
    print()
    
    # Load staff cache
    staff_cache = 'data/unilag_staff.json'
    if not os.path.exists(staff_cache):
        print(f"✗ Staff cache not found: {staff_cache}")
        print("  Run the faculty directory spider first.")
        return
    
    with open(staff_cache, 'r', encoding='utf-8') as f:
        staff_names = json.load(f)
    
    print(f"✓ Loaded {len(staff_names)} staff names")
    print()
    
    # Load existing ORCIDs if any
    orcid_cache = 'data/unilag_orcids.json'
    if os.path.exists(orcid_cache):
        with open(orcid_cache, 'r', encoding='utf-8') as f:
            orcid_data = json.load(f)
        print(f"✓ Loaded {len(orcid_data)} existing ORCIDs")
    else:
        orcid_data = {}
    
    print()
    print("Searching for ORCIDs (this may take a while)...")
    print("Note: ORCID API has rate limits, searching first 50 staff members")
    print("-" * 70)
    
    found_count = 0
    searched_count = 0
    
    # Search for ORCIDs (limit to first 50 to avoid rate limits)
    for i, name in enumerate(staff_names[:50], 1):
        # Skip if already have ORCID
        if name in orcid_data and orcid_data[name]:
            print(f"{i}. CACHED: {name:40} → {orcid_data[name]}")
            found_count += 1
            continue
        
        # Clean name for search
        clean_name = name.replace('Prof.', '').replace('Dr.', '').replace('Mr.', '').replace('Mrs.', '').replace('Miss.', '').strip()
        
        print(f"{i}. Searching: {clean_name:40} ... ", end='', flush=True)
        
        orcid_id = search_orcid_for_person(clean_name)
        searched_count += 1
        
        if orcid_id:
            orcid_data[name] = orcid_id
            found_count += 1
            print(f"✓ {orcid_id}")
        else:
            orcid_data[name] = None
            print("✗ Not found")
        
        # Rate limiting: 1 request per second
        if searched_count % 10 == 0:
            print(f"  [Pausing for rate limit...]")
            time.sleep(2)
        else:
            time.sleep(1)
    
    # Save ORCIDs
    os.makedirs('data', exist_ok=True)
    with open(orcid_cache, 'w', encoding='utf-8') as f:
        json.dump(orcid_data, f, indent=2, ensure_ascii=False)
    
    print()
    print("=" * 70)
    print(f"✓ Found {found_count} ORCIDs out of {min(50, len(staff_names))} staff searched")
    print(f"✓ Saved to: {orcid_cache}")
    print("=" * 70)
    print()
    
    # Update database with ORCIDs
    print("Updating database with ORCID IDs...")
    session = SessionLocal()
    updated = 0
    
    for name, orcid_id in orcid_data.items():
        if orcid_id:
            # Find author in database
            author = session.query(Author).filter_by(normalized_name=name.lower().strip()).first()
            if author and not author.profile_url:
                author.profile_url = f"https://orcid.org/{orcid_id}"
                updated += 1
    
    session.commit()
    session.close()
    
    print(f"✓ Updated {updated} author records with ORCID URLs")
    print()
    
    # Show summary
    print("Summary:")
    print(f"  Total staff: {len(staff_names)}")
    print(f"  Searched: {min(50, len(staff_names))}")
    print(f"  ORCIDs found: {found_count}")
    print(f"  Success rate: {(found_count/min(50, len(staff_names))*100):.1f}%")

if __name__ == '__main__':
    find_orcids_for_staff()
