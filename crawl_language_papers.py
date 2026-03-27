#!/usr/bin/env python3
"""
Specialized crawler for LANGUAGE RESEARCH papers from UNILAG.
Targets: Nigerian languages, African linguistics, literature, oral traditions.
"""
import sys
import os

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
import argparse
from uraas.database import SessionLocal, Item, Author, File, Collection
from uraas.utils.staff_validator import staff_validator
from uraas.utils.pdf_downloader import pdf_downloader
from uraas.utils.unilag_classifier import classifier
from datetime import datetime

UNILAG_ROR = "05rk03822"

# Language research keywords - strict matching
LANGUAGE_KEYWORDS = [
    'yoruba language', 'igbo language', 'hausa language', 'nigerian language',
    'african linguistics', 'phonology', 'morphology', 'syntax', 'semantics',
    'sociolinguistics', 'discourse analysis', 'pragmatics',
    'oral literature', 'oral tradition', 'folklore', 'proverbs',
    'african literature', 'nigerian literature', 'literary criticism',
    'translation studies', 'bilingualism', 'multilingualism',
    'language policy', 'language education', 'language acquisition',
    'pidgin', 'creole', 'code-switching', 'language contact'
]

def is_language_paper(title, abstract):
    """Check if paper is actually about language research."""
    text = f"{title} {abstract or ''}".lower()
    
    # Exclude medical/health/engineering papers first
    exclude_terms = [
        'patient', 'clinical', 'disease', 'treatment', 'therapy', 'diagnosis',
        'hospital', 'medical', 'health care', 'surgery', 'drug',
        'concrete', 'steel', 'corrosion', 'mechanical', 'thermal',
        'covid', 'pandemic', 'virus', 'infection'
    ]
    
    if any(term in text for term in exclude_terms):
        return False
    
    # Check for language-related terms (more lenient)
    language_terms = [
        'language', 'linguistic', 'literature', 'literary', 'yoruba', 'igbo', 'hausa',
        'phonology', 'morphology', 'syntax', 'semantics', 'discourse',
        'oral', 'folklore', 'proverb', 'translation', 'bilingual',
        'pidgin', 'creole', 'dialect', 'grammar', 'lexicon'
    ]
    
    # Must contain at least one language term
    return any(term in text for term in language_terms)

def fetch_language_papers(page=1, per_page=50):
    """Fetch papers from UNILAG and filter for language-related ones."""
    url = (
        f"https://api.openalex.org/works"
        f"?filter=institutions.ror:{UNILAG_ROR}"
        f"&select=id,doi,title,authorships,publication_date,open_access,primary_location,abstract_inverted_index"
        f"&per-page={per_page}&page={page}"
        f"&mailto=library@unilag.edu.ng"
    )
    
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json().get('results', [])
    except Exception as e:
        print(f"[ERROR] Failed to fetch page {page}: {e}")
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

def crawl_language_papers(target=50):
    """Crawl language research papers."""
    print("=" * 70)
    print("📚 LANGUAGE RESEARCH PAPER CRAWLER")
    print("=" * 70)
    print(f"Target: {target} language research papers")
    print("Searching for: Nigerian languages, linguistics, African literature")
    print("=" * 70)
    
    # Check staff list
    staff_count = len(staff_validator.staff_names)
    if staff_count < 100:
        print(f"[ERROR] Staff list too small ({staff_count} names)")
        return
    print(f"[INIT] Staff list: {staff_count} names loaded")
    
    session = SessionLocal()
    
    # Get or create Language Research collection
    lang_collection = session.query(Collection).filter_by(name='Language Research Papers').first()
    if not lang_collection:
        print("[INIT] Creating 'Language Research Papers' collection...")
        
        # Get Faculty of Arts community (language research typically falls under Arts)
        arts_community = session.query(Collection).join(Collection.community).filter(
            Collection.community.has(name='Faculty of Arts')
        ).first()
        
        if arts_community:
            community_id = arts_community.community_id
        else:
            # Fallback: get any community
            any_collection = session.query(Collection).first()
            community_id = any_collection.community_id if any_collection else 1
        
        lang_collection = Collection(
            name='Language Research Papers',
            community_id=community_id,
            keywords='linguistics,language,literature,yoruba,igbo,hausa,african literature,oral tradition'
        )
        session.add(lang_collection)
        session.commit()
    
    stored_count = 0
    checked_count = 0
    duplicate_count = 0
    no_staff_count = 0
    not_language_count = 0
    page = 1
    max_pages = 100
    
    existing_count = session.query(Item).count()
    print(f"[INIT] Database has {existing_count} papers already")
    print(f"[INIT] Starting crawl from page 1...")
    print()
    
    while stored_count < target and page <= max_pages:
        print(f"[PAGE {page}] Fetching candidates...")
        
        works = fetch_language_papers(page=page, per_page=50)
        
        if not works:
            print(f"[WARN] No more papers found at page {page}")
            break
        
        print(f"[PAGE {page}] Processing {len(works)} candidates...")
        
        for work in works:
            if stored_count >= target:
                break
            
            checked_count += 1
            title = (work.get('title') or '').strip()
            if not title:
                continue
            
            # Check if it's actually a language paper
            abstract = reconstruct_abstract(work.get('abstract_inverted_index'))
            if not is_language_paper(title, abstract):
                not_language_count += 1
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
            oa = work.get('open_access') or {}
            pdf_url = oa.get('oa_url') if oa.get('is_oa') else None
            
            doc = Item(
                title=title,
                abstract=abstract,
                dc_title=title,
                dc_identifier_uri=doi or url_val,
                dc_identifier_doi=doi,
                dc_description_provenance=f"Language Research Crawler - {datetime.now().date()}",
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
            
            # Add to Language Research collection
            doc.collections.append(lang_collection)
            
            try:
                session.add(doc)
                session.flush()
                stored_count += 1
                
                print(f"  ✅ [{stored_count}/{target}] {title[:60]}...")
                print(f"     Staff: {', '.join(matching_staff[:2])}")
                
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
                        print(f"     📄 PDF saved ({policy})")
                
                # Commit every 10 papers
                if stored_count % 10 == 0:
                    session.commit()
                    print(f"  💾 Committed {stored_count} papers")
                    
            except Exception as e:
                session.rollback()
                print(f"     ❌ Failed to store: {str(e)}")
                continue
        
        page += 1
        
        if stored_count < target:
            print(f"[PROGRESS] {stored_count}/{target} papers found. Continuing...")
            print()
    
    # Final commit
    try:
        session.commit()
    except Exception:
        session.rollback()
    session.close()
    
    print()
    print("=" * 70)
    if stored_count >= target:
        print(f"🎉 SUCCESS! Found {stored_count} language research papers")
    else:
        print(f"⚠️  Found {stored_count}/{target} papers")
    print(f"📊 Checked: {checked_count} | Duplicates: {duplicate_count}")
    print(f"👥 No staff: {no_staff_count} | Not language: {not_language_count}")
    print("=" * 70)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', type=int, default=50, help='Number of language papers to find')
    args = parser.parse_args()
    
    crawl_language_papers(target=args.target)
