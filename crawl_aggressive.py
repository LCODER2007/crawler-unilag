#!/usr/bin/env python3
"""
Aggressive Crawler - Keeps searching until target is reached (up to 3000 pages).
"""
import sys
import os

# Windows UTF-8 fix
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
import argparse
import concurrent.futures
from uraas.database import SessionLocal, Item, Author, File, Collection
from uraas.utils.staff_validator import staff_validator
from uraas.utils.pdf_downloader import pdf_downloader
from uraas.utils.unilag_classifier import classifier
from datetime import datetime

UNILAG_ROR = "05rk03822"
BATCH_SIZE = 10

def fetch_page(page, per_page=50):
    """Fetch a single page from OpenAlex."""
    url = (
        f"https://api.openalex.org/works"
        f"?filter=institutions.ror:{UNILAG_ROR}"
        f"&select=id,doi,title,authorships,publication_date,open_access,primary_location,abstract_inverted_index"
        f"&per-page={per_page}&page={page}"
        f"&mailto=library@unilag.edu.ng"
    )
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        return resp.json().get('results', [])
    except Exception as e:
        print(f"  [WARN] Page {page} failed: {e}")
        return []

def reconstruct_abstract(inverted_index):
    """Reconstruct abstract from OpenAlex inverted index format."""
    if not inverted_index:
        return None
    try:
        words = {}
        for word, positions in inverted_index.items():
            for pos in positions:
                words[pos] = word
        return ' '.join(words[i] for i in sorted(words))
    except Exception:
        return None

def crawl_until_target(target_count=20):
    """Keep crawling until we get the target number of papers."""
    print("=" * 70)
    print("URAAS AGGRESSIVE CRAWLER - SEARCHES UP TO 100,000 PAGES")
    print("=" * 70)
    print(f"This crawler will NOT stop until {target_count} papers are found!")
    print(f"It will search through thousands of pages if needed!")
    print("=" * 70)
    
    # Check staff list
    staff_count = len(staff_validator.staff_names)
    if staff_count < 100:
        print(f"[ERROR] Staff list too small ({staff_count} names)")
        return
    print(f"[INIT] Staff list confirmed: {staff_count} names loaded")
    
    # Check existing papers
    session = SessionLocal()
    existing_count = session.query(Item).count()
    start_page = max(1, (existing_count // 50) + 1)
    session.close()
    
    print(f"[INIT] Database has {existing_count} papers")
    print(f"[INIT] Starting from page {start_page}")
    print(f"[INIT] Target: {target_count} papers")
    print(f"[INIT] Will search up to 100,000 pages if needed")
    print(f"[INIT] This may take a while - be patient!")
    print()
    
    session = SessionLocal()
    stored_count = 0
    checked_count = 0
    duplicate_count = 0
    no_staff_count = 0
    current_page = start_page
    max_pages = 100000
    
    # Pre-load collections
    collections_map = {}
    for coll in session.query(Collection).all():
        collections_map[coll.name] = coll
    
    while stored_count < target_count and current_page <= max_pages:
        # Fetch batch of pages
        batch_size = 10
        print(f"[BATCH] Fetching pages {current_page}-{current_page + batch_size - 1}...")
        
        all_works = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_page, p): p for p in range(current_page, current_page + batch_size)}
            for future in concurrent.futures.as_completed(futures):
                results = future.result()
                all_works.extend(results)
        
        if not all_works:
            print(f"[WARN] No papers found at page {current_page}, stopping")
            break
        
        print(f"[BATCH] Processing {len(all_works)} candidates...")
        
        # Process papers
        for work in all_works:
            if stored_count >= target_count:
                break
                
            checked_count += 1
            title = (work.get('title') or '').strip()
            if not title:
                continue
            
            # Check duplicates
            doi = work.get('doi', '')
            url_val = (work.get('primary_location') or {}).get('landing_page_url') or doi or f"https://openalex.org/{work.get('id','')}"
            
            if doi and session.query(Item).filter_by(doi=doi).first():
                duplicate_count += 1
                continue
            if session.query(Item).filter_by(url=url_val).first():
                duplicate_count += 1
                continue
            
            # Check authors
            authors = [
                a.get('author', {}).get('display_name', '')
                for a in work.get('authorships', [])
                if a.get('author', {}).get('display_name')
            ]
            if not authors:
                continue
            
            # Staff validation
            matching_staff = [a for a in authors if staff_validator.is_staff_member(a, fuzzy_threshold=75)]
            if not matching_staff:
                no_staff_count += 1
                continue
            
            # Create paper
            abstract = reconstruct_abstract(work.get('abstract_inverted_index'))
            oa = work.get('open_access') or {}
            pdf_url = oa.get('oa_url') if oa.get('is_oa') else None
            
            doc = Item(
                title=title,
                abstract=abstract,
                dc_title=title,
                dc_identifier_uri=doi or url_val,
                dc_identifier_doi=doi,
                dc_description_provenance=f"Aggressive Crawler - {datetime.now().date()}",
                dc_rights='info:eu-repo/semantics/openAccess' if oa.get('is_oa') else 'info:eu-repo/semantics/restrictedAccess',
                doi=doi or None,
                url=url_val,
                source_repository='OpenAlex',
                pdf_url=pdf_url,
                publication_date=datetime.fromisoformat(work['publication_date']) if work.get('publication_date') else None
            )
            
            # Add authors
            for name in authors[:10]:
                norm = name.lower().strip()
                author_obj = session.query(Author).filter_by(normalized_name=norm).first()
                if not author_obj:
                    author_obj = Author(name=name, normalized_name=norm)
                    session.add(author_obj)
                doc.authors.append(author_obj)
            
            # Classify
            text_for_classification = f"{title} {abstract or ''}"
            classification = classifier.get_best_classification(text_for_classification)
            faculty_hints = staff_validator.get_all_faculty_hints(authors)
            hint_faculties = list({fac for _, fac in faculty_hints})
            
            linked_collections = set()
            if classification:
                coll = collections_map.get(classification[1])
                if coll:
                    linked_collections.add(coll)
            
            for hint_faculty in hint_faculties:
                faculty_results = [r for r in classifier.classify(text_for_classification) if r[0] == hint_faculty]
                if faculty_results:
                    coll = collections_map.get(faculty_results[0][1])
                    if coll:
                        linked_collections.add(coll)
                else:
                    for coll_name, coll_obj in collections_map.items():
                        if hasattr(coll_obj, 'community') and coll_obj.community and coll_obj.community.name == hint_faculty:
                            linked_collections.add(coll_obj)
                            break
            
            for coll in linked_collections:
                doc.collections.append(coll)
            
            dept_label = classification[1] if classification else (hint_faculties[0] if hint_faculties else 'Unclassified')
            
            try:
                session.add(doc)
                session.flush()
                stored_count += 1
                
                print(f"  [OK] [{stored_count}/{target_count}] {title[:65]}...")
                print(f"       Staff: {', '.join(matching_staff[:3])} | Dept: {dept_label}")
                
                # Download PDF
                if pdf_url:
                    pdf_result = pdf_downloader.download_pdf(pdf_url, doc.id, doi=doi, timeout=15)
                    if pdf_result:
                        policy = 'Public' if oa.get('oa_status') in ('gold', 'green', 'diamond') else 'Private'
                        session.add(File(
                            item_id=doc.id,
                            file_path=pdf_result['file_path'],
                            sha256_hash=pdf_result['sha256_hash'],
                            access_policy=policy
                        ))
                        print(f"       PDF: {pdf_result['file_size']//1024}KB saved ({policy})")
                
                # Commit every 5 papers
                if stored_count % 5 == 0:
                    session.commit()
                    
            except Exception as e:
                session.rollback()
                print(f"       [ERROR] Failed to store: {str(e)}")
                continue
        
        # Move to next batch
        current_page += batch_size
        
        if stored_count < target_count:
            remaining = target_count - stored_count
            print(f"[PROGRESS] Found {stored_count}/{target_count} papers. Need {remaining} more.")
            print(f"[PROGRESS] Continuing to page {current_page}... (checked {checked_count} total)")
            print(f"[PROGRESS] Will keep searching until target is reached!")
        
        # Add small delay to avoid overwhelming the API
        import time
        time.sleep(1)
    
    # Final commit
    try:
        session.commit()
    except Exception:
        session.rollback()
    session.close()
    
    print()
    print("=" * 70)
    if stored_count >= target_count:
        print(f"SUCCESS! Found {stored_count} papers (target: {target_count})")
        print(f"Checked {checked_count} candidates total")
        print(f"Searched up to page {current_page-1}")
    else:
        print(f"PARTIAL: Found {stored_count}/{target_count} papers")
        print(f"Searched up to page {current_page-1}")
        print(f"Try running again - more papers may be available!")
    print(f"Duplicates skipped: {duplicate_count}")
    print(f"No staff match: {no_staff_count}")
    print("=" * 70)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', type=int, default=20, help='Number of papers to find')
    args = parser.parse_args()
    
    crawl_until_target(target_count=args.target)