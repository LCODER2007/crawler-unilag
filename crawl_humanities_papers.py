#!/usr/bin/env python3
"""
Crawl papers from Arts, Education, and Social Sciences faculty at UNILAG.
Targets specific authors to get real humanities/social science papers.
"""
import sys
import os
import json

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
import time
from uraas.database import SessionLocal, Item, Author, File, Collection
from uraas.utils.staff_validator import staff_validator
from uraas.utils.pdf_downloader import pdf_downloader
from datetime import datetime
from sqlalchemy.exc import OperationalError

def load_humanities_authors():
    """Load Arts, Education, and Social Sciences faculty with OpenAlex IDs."""
    with open('data/unilag_staff_detailed.json', 'r', encoding='utf-8') as f:
        staff = json.load(f)
    
    target_faculties = ['Faculty of Arts', 'Faculty of Education', 'Faculty of Social Sciences']
    
    authors = []
    for person in staff:
        if person.get('faculty') in target_faculties and person.get('openalex_id'):
            authors.append({
                'name': person['name'],
                'openalex_id': person['openalex_id'],
                'faculty': person['faculty'],
                'department': person.get('department', 'Unknown')
            })
    
    return authors

def fetch_author_papers(openalex_id, per_page=50):
    """Fetch all papers by a specific author from OpenAlex."""
    url = (
        f"https://api.openalex.org/works"
        f"?filter=author.id:{openalex_id}"
        f"&select=id,doi,title,authorships,publication_date,open_access,primary_location,abstract_inverted_index"
        f"&per-page={per_page}"
        f"&mailto=library@unilag.edu.ng"
    )
    
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json().get('results', [])
    except Exception as e:
        return []

def reconstruct_abstract(inverted_index):
    """Reconstruct abstract from OpenAlex inverted index."""
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

def crawl_humanities_papers(target=50):
    """Crawl papers from humanities faculty."""
    print("=" * 70)
    print("📚 HUMANITIES & SOCIAL SCIENCES CRAWLER")
    print("=" * 70)
    print(f"Target: {target} papers from Arts/Education/Social Sciences")
    print("=" * 70)
    
    # Load humanities authors
    authors = load_humanities_authors()
    print(f"[INIT] Found {len(authors)} faculty with OpenAlex IDs")
    print(f"       Arts: {sum(1 for a in authors if 'Arts' in a['faculty'])}")
    print(f"       Education: {sum(1 for a in authors if 'Education' in a['faculty'])}")
    print(f"       Social Sciences: {sum(1 for a in authors if 'Social Sciences' in a['faculty'])}")
    print()
    
    session = SessionLocal()
    
    # Get or create Language Research collection
    lang_collection = session.query(Collection).filter_by(name='Language Research Papers').first()
    if not lang_collection:
        # Get any collection to get community_id
        any_coll = session.query(Collection).first()
        lang_collection = Collection(
            name='Language Research Papers',
            community_id=any_coll.community_id if any_coll else 1,
            keywords='linguistics,language,literature,humanities,social sciences'
        )
        session.add(lang_collection)
        session.commit()
    
    stored_count = 0
    duplicate_count = 0
    processed_authors = 0
    
    for author_info in authors:
        if stored_count >= target:
            break
        
        processed_authors += 1
        print(f"[{processed_authors}/{len(authors)}] Checking {author_info['name']} ({author_info['faculty']})...")
        
        works = fetch_author_papers(author_info['openalex_id'])
        
        if not works:
            print(f"  No papers found")
            continue
        
        print(f"  Found {len(works)} papers")
        
        for work in works:
            if stored_count >= target:
                break
            
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
            
            # Get all authors
            authors_list = [
                a.get('author', {}).get('display_name', '')
                for a in work.get('authorships', [])
                if a.get('author', {}).get('display_name')
            ]
            
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
                dc_description_provenance=f"Humanities Crawler - {datetime.now().date()}",
                dc_rights='info:eu-repo/semantics/openAccess' if oa.get('is_oa') else 'info:eu-repo/semantics/restrictedAccess',
                doi=doi or None,
                url=url_val,
                source_repository='OpenAlex',
                pdf_url=pdf_url,
                publication_date=datetime.fromisoformat(work['publication_date']) if work.get('publication_date') else None
            )
            
            # Add authors
            for name in authors_list[:10]:
                norm = name.lower().strip()
                author_obj = session.query(Author).filter_by(normalized_name=norm).first()
                if not author_obj:
                    author_obj = Author(name=name, normalized_name=norm)
                    session.add(author_obj)
                doc.authors.append(author_obj)
            
            # Add to Language Research collection
            doc.collections.append(lang_collection)
            
            # Retry logic for database locks
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    session.add(doc)
                    session.flush()
                    stored_count += 1
                    
                    print(f"  ✅ [{stored_count}/{target}] {title[:55]}...")
                    print(f"     Faculty: {author_info['faculty']} | Dept: {author_info['department']}")
                    
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
                    
                    # Commit every 5 papers
                    if stored_count % 5 == 0:
                        session.commit()
                    
                    break  # Success, exit retry loop
                    
                except OperationalError as e:
                    if 'locked' in str(e) and attempt < max_retries - 1:
                        session.rollback()
                        print(f"     ⏳ Database locked, retrying in {attempt + 1}s...")
                        time.sleep(attempt + 1)
                    else:
                        session.rollback()
                        print(f"     ❌ Failed after {attempt + 1} attempts: {str(e)[:50]}")
                        break
                except Exception as e:
                    session.rollback()
                    print(f"     ❌ Failed: {str(e)[:50]}")
                    break
    
    # Final commit
    try:
        session.commit()
    except Exception:
        session.rollback()
    session.close()
    
    print()
    print("=" * 70)
    if stored_count >= target:
        print(f"🎉 SUCCESS! Crawled {stored_count} humanities papers")
    else:
        print(f"✅ Crawled {stored_count} papers (target: {target})")
    print(f"📊 Duplicates skipped: {duplicate_count}")
    print(f"👥 Authors checked: {processed_authors}/{len(authors)}")
    print("=" * 70)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', type=int, default=50, help='Number of papers to crawl')
    args = parser.parse_args()
    
    crawl_humanities_papers(target=args.target)
