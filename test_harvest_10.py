"""
Quick test to harvest exactly 10 UNILAG papers using OpenAlex ROR ID.
This bypasses the complex spider system and directly queries OpenAlex API.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from uraas.database import SessionLocal, Item, Author, Collection, Community
from datetime import datetime

# UNILAG ROR ID (correct - verified)
UNILAG_ROR = "05rk03822"

def harvest_10_papers():
    print("=" * 70)
    print("URAAS Quick Harvest - 10 Papers Test")
    print("=" * 70)
    print()
    
    # Query OpenAlex for UNILAG papers
    url = (
        f"https://api.openalex.org/works"
        f"?filter=institutions.ror:{UNILAG_ROR}"
        f"&select=id,doi,title,authorships,publication_date,open_access,primary_location"
        f"&per-page=10"
        f"&mailto=library@unilag.edu.ng"
    )
    
    print(f"Querying OpenAlex API...")
    print(f"ROR ID: {UNILAG_ROR}")
    print()
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        results = data.get('results', [])
        print(f"✓ Found {len(results)} papers from OpenAlex")
        print()
        
        if not results:
            print("✗ No papers found. This might mean:")
            print("  1. UNILAG has no papers indexed in OpenAlex")
            print("  2. The ROR ID is incorrect")
            print("  3. Network/API issue")
            return
        
        # Store in database
        session = SessionLocal()
        stored_count = 0
        
        for i, work in enumerate(results, 1):
            title = work.get('title', '').strip()
            if not title:
                continue
            
            doi = work.get('doi', '')
            
            # Check if already exists
            existing = session.query(Item).filter_by(doi=doi).first() if doi else None
            if existing:
                print(f"{i}. SKIP (duplicate): {title[:60]}...")
                continue
            
            # Extract authors
            authors = []
            for authorship in work.get('authorships', []):
                author_name = authorship.get('author', {}).get('display_name', '')
                if author_name:
                    authors.append(author_name)
            
            # Get PDF URL
            pdf_url = None
            oa = work.get('open_access', {})
            if oa.get('is_oa') and oa.get('oa_url'):
                pdf_url = oa['oa_url']
            
            url_val = work.get('primary_location', {}).get('landing_page_url') or doi or ''
            
            # Create item
            doc = Item(
                title=title,
                dc_title=title,
                dc_identifier_uri=doi or url_val,
                dc_identifier_doi=doi,
                dc_description_provenance=f"Harvested via OpenAlex ROR - {datetime.now().date()}",
                dc_rights='info:eu-repo/semantics/openAccess' if oa.get('is_oa') else 'info:eu-repo/semantics/restrictedAccess',
                doi=doi or None,
                url=url_val or f"https://openalex.org/{work.get('id', '')}",
                source_repository='OpenAlex',
                pdf_url=pdf_url,
                publication_date=datetime.fromisoformat(work.get('publication_date')) if work.get('publication_date') else None
            )
            
            # Add authors
            for author_name in authors[:5]:  # Limit to first 5 authors
                author_obj = session.query(Author).filter_by(
                    normalized_name=author_name.lower().strip()
                ).first()
                
                if not author_obj:
                    author_obj = Author(
                        name=author_name,
                        normalized_name=author_name.lower().strip()
                    )
                    session.add(author_obj)
                
                doc.authors.append(author_obj)
            
            session.add(doc)
            session.flush()
            
            stored_count += 1
            print(f"{i}. ✓ STORED: {title[:60]}...")
            print(f"   Authors: {', '.join(authors[:3])}")
            print(f"   DOI: {doi or 'N/A'}")
            print(f"   Open Access: {'Yes' if oa.get('is_oa') else 'No'}")
            print()
        
        session.commit()
        session.close()
        
        print("=" * 70)
        print(f"✓ Successfully stored {stored_count} papers in database")
        print("=" * 70)
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    harvest_10_papers()
