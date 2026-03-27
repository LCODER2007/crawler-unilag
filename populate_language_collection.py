#!/usr/bin/env python3
"""
Populate Language Research Papers collection from existing papers.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from uraas.database import SessionLocal, Item, Collection, Community

def populate_language_collection():
    """Find existing language papers and add them to Language Research collection."""
    print("=" * 70)
    print("📚 POPULATING LANGUAGE RESEARCH COLLECTION")
    print("=" * 70)
    
    session = SessionLocal()
    
    # Get or create Language Research collection
    lang_collection = session.query(Collection).filter_by(name='Language Research Papers').first()
    
    if not lang_collection:
        print("[INIT] Creating 'Language Research Papers' collection...")
        
        # Get Faculty of Arts community
        arts_community = session.query(Community).filter_by(name='Faculty of Arts').first()
        
        if not arts_community:
            print("[ERROR] Faculty of Arts community not found")
            return
        
        lang_collection = Collection(
            name='Language Research Papers',
            community_id=arts_community.id,
            keywords='linguistics,language,literature,yoruba,igbo,hausa,african literature,oral tradition'
        )
        session.add(lang_collection)
        session.commit()
        print(f"[OK] Created collection with ID {lang_collection.id}")
    else:
        print(f"[OK] Found existing collection with ID {lang_collection.id}")
    
    # Find papers with language-related keywords in title/abstract
    language_terms = [
        '%language%', '%linguistic%', '%literature%', '%literary%',
        '%yoruba%', '%igbo%', '%hausa%', '%pidgin%', '%creole%',
        '%oral tradition%', '%folklore%', '%translation%'
    ]
    
    added_count = 0
    
    for term in language_terms:
        # Find papers matching this term
        papers = session.query(Item).filter(
            (Item.title.ilike(term)) | (Item.abstract.ilike(term))
        ).all()
        
        print(f"[SEARCH] Found {len(papers)} papers matching '{term.strip('%')}'")
        
        for paper in papers:
            # Check if already in collection
            if lang_collection in paper.collections:
                continue
            
            # Add to collection
            paper.collections.append(lang_collection)
            added_count += 1
            print(f"  ✅ Added: {paper.title[:60]}...")
    
    session.commit()
    session.close()
    
    print()
    print("=" * 70)
    print(f"🎉 Added {added_count} papers to Language Research collection")
    print("=" * 70)

if __name__ == '__main__':
    populate_language_collection()
