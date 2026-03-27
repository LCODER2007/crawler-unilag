#!/usr/bin/env python3
"""Debug why crawler isn't finding matches."""
import requests
from uraas.utils.staff_validator import staff_validator

# Fetch sample from OpenAlex
url = "https://api.openalex.org/works?filter=institutions.ror:05rk03822&per-page=10&mailto=library@unilag.edu.ng"
resp = requests.get(url, timeout=20)
works = resp.json()['results']

print("=" * 70)
print("CRAWLER DEBUG - Author Name Matching")
print("=" * 70)

print(f"\nStaff validator has {len(staff_validator.staff_names)} names loaded")
print(f"Sample staff names: {list(staff_validator.staff_names)[:5]}")

print("\n" + "=" * 70)
print("CHECKING FIRST 10 PAPERS FROM OPENALEX")
print("=" * 70)

for i, work in enumerate(works[:10], 1):
    title = work.get('title', 'No title')
    print(f"\n[{i}] {title[:60]}")
    
    authors = [
        a.get('author', {}).get('display_name', '')
        for a in work.get('authorships', [])
        if a.get('author', {}).get('display_name')
    ]
    
    print(f"    Authors from OpenAlex: {authors[:3]}")
    
    # Check which match
    matches = []
    for author in authors:
        if staff_validator.is_staff_member(author, fuzzy_threshold=75):
            matches.append(author)
    
    if matches:
        print(f"    ✓ MATCHES: {matches}")
    else:
        print(f"    ✗ NO MATCHES (threshold=75)")
        
        # Try with lower threshold
        matches_60 = []
        for author in authors:
            if staff_validator.is_staff_member(author, fuzzy_threshold=60):
                matches_60.append(author)
        
        if matches_60:
            print(f"    ⚠ Would match at threshold=60: {matches_60}")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print("If no matches found, the issue is:")
print("1. Author name format mismatch (OpenAlex vs staff list)")
print("2. Fuzzy threshold too strict (75%)")
print("3. Staff list incomplete")
