"""
Crawl EXACTLY N papers from ACTUAL UNILAG staff members.
Uses OpenAlex ROR ID + staff validation with relaxed fuzzy matching (75%).
Speed optimized: parallel pages, pre-built staff index, batch commits.
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
import concurrent.futures
from uraas.database import SessionLocal, Item, Author, File, Collection
from uraas.utils.staff_validator import staff_validator
from uraas.utils.pdf_downloader import pdf_downloader
from uraas.utils.unilag_classifier import classifier
from datetime import datetime

UNILAG_ROR = "05rk03822"
BATCH_SIZE = 10  # commit every N papers


def confirm_staff_list():
    """Verify staff list is loaded before crawling."""
    count = len(staff_validator.staff_names)
    if count < 100:
        print(f"[ERROR] Staff list too small ({count} names). Check data/unilag_staff.json")
        sys.exit(1)
    print(f"[INIT] Staff list confirmed: {count} names loaded")
    return count


def fetch_page(page, per_page=50, from_date=None):
    """Fetch a single page from OpenAlex."""
    url = (
        f"https://api.openalex.org/works"
        f"?filter=institutions.ror:{UNILAG_ROR}"
    )
    
    # Add date filter if specified
    if from_date:
        url += f",from_publication_date:{from_date}"
    
    url += (
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


def crawl_papers(target_count=100):
    target_count = min(max(target_count, 1), 250)

    print("=" * 70)
    print("URAAS PRODUCTION CRAWLER")
    print("=" * 70)

    # Step 1: Confirm staff list
    confirm_staff_list()

    # Step 2: Check how many papers we already have to determine starting page
    session = SessionLocal()
    existing_count = session.query(Item).count()
    session.close()
    
    # Start from later pages if we have many papers already
    start_page = max(1, (existing_count // 50) + 1)  # Skip pages we likely already crawled
    print(f"[INIT] Database has {existing_count} papers, starting from page {start_page}")

    # Step 3: Pre-fetch pages in parallel for speed
    # Fetch more candidates since ~40% match rate
    print(f"[INIT] Pre-fetching pages from OpenAlex (target: {target_count})...")
    pages_needed = max(5, (target_count // 5) + 3)  # fetch 5x target for ~40% match rate
    all_works = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_page, p): p for p in range(start_page, start_page + pages_needed)}
        for future in concurrent.futures.as_completed(futures):
            results = future.result()
            all_works.extend(results)
            if len(all_works) % 50 == 0:
                print(f"[INIT] Fetched {len(all_works)} candidates so far...")

    print(f"[INIT] Total candidates: {len(all_works)}")
    print(f"[INIT] Starting validation and storage...")
    print()

    session = SessionLocal()
    stored_count = 0
    skipped_count = 0
    checked_count = 0
    batch_count = 0
    duplicate_count = 0
    no_staff_count = 0

    # Pre-load all collection objects for classification
    collections_map = {}
    for coll in session.query(Collection).all():
        collections_map[coll.name] = coll

    for work in all_works:
        if stored_count >= target_count:
            break

        checked_count += 1
        title = (work.get('title') or '').strip()
        if not title:
            continue

        doi = work.get('doi', '')
        url_val = (work.get('primary_location') or {}).get('landing_page_url') or doi or f"https://openalex.org/{work.get('id','')}"

        # Duplicate check
        if doi and session.query(Item).filter_by(doi=doi).first():
            duplicate_count += 1
            if checked_count <= 10:
                print(f"  [DUP] {title[:50]}... (duplicate DOI)")
            continue
        if session.query(Item).filter_by(url=url_val).first():
            duplicate_count += 1
            if checked_count <= 10:
                print(f"  [DUP] {title[:50]}... (duplicate URL)")
            continue

        # Extract authors
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
            if checked_count <= 10:  # Show first 10 skips for debugging
                print(f"  [SKIP] {title[:50]}... (no staff match)")
            continue

        # Reconstruct abstract
        abstract = reconstruct_abstract(work.get('abstract_inverted_index'))

        oa = work.get('open_access') or {}
        pdf_url = oa.get('oa_url') if oa.get('is_oa') else None

        doc = Item(
            title=title,
            abstract=abstract,
            dc_title=title,
            dc_identifier_uri=doi or url_val,
            dc_identifier_doi=doi,
            dc_description_provenance=f"Validated UNILAG Staff - {datetime.now().date()}",
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

        # Classify into faculty/department — combine keyword + author-name hints
        text_for_classification = f"{title} {abstract or ''}"
        classification = classifier.get_best_classification(text_for_classification)

        # Author-name based faculty hints (handles multiple UNILAG authors)
        faculty_hints = staff_validator.get_all_faculty_hints(authors)
        hint_faculties = list({fac for _, fac in faculty_hints})

        # Build set of collections to link
        linked_collections = set()

        # 1. Keyword classification result
        if classification:
            coll = collections_map.get(classification[1])
            if coll:
                linked_collections.add(coll)

        # 2. Author-name faculty hints — find best dept within each hinted faculty
        for hint_faculty in hint_faculties:
            # Try to find a dept match within that faculty using keywords
            faculty_results = [
                r for r in classifier.classify(text_for_classification)
                if r[0] == hint_faculty
            ]
            if faculty_results:
                coll = collections_map.get(faculty_results[0][1])
                if coll:
                    linked_collections.add(coll)
            else:
                # No keyword match — link to first collection in that faculty
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
            batch_count += 1
            print(f"  [OK] [{stored_count}/{target_count}] {title[:65]}...")
            print(f"       Staff: {', '.join(matching_staff[:3])} | Dept: {dept_label}")

            # Download PDF (non-blocking — skip if slow)
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

            # Batch commit for speed
            if batch_count >= BATCH_SIZE:
                session.commit()
                batch_count = 0

        except Exception as e:
            session.rollback()
            batch_count = 0
            continue

    # Final commit
    try:
        session.commit()
    except Exception:
        session.rollback()
    session.close()

    print()
    print("=" * 70)
    print(f"[DONE] Checked: {checked_count} | Duplicates: {duplicate_count} | No Staff: {no_staff_count} | Stored: {stored_count}")
    
    # If we didn't find enough papers, suggest trying recent papers
    if stored_count == 0 and target_count > 0:
        print("=" * 70)
        print("💡 SUGGESTION: No new papers found in current pages.")
        print("   Try fetching recent papers with date filter:")
        print("   python crawl_10_validated.py --target 20 --recent")
        print("   Or increase target: --target 50")
    
    print("=" * 70)


def crawl_recent_papers(target_count=100):
    """Crawl recent papers (2023+) to find new content."""
    target_count = min(max(target_count, 1), 250)

    print("=" * 70)
    print("URAAS RECENT PAPERS CRAWLER")
    print("=" * 70)

    # Step 1: Confirm staff list
    confirm_staff_list()

    # Step 2: Fetch recent papers with date filter
    print(f"[INIT] Fetching recent papers (2023+) from OpenAlex (target: {target_count})...")
    pages_needed = max(3, (target_count // 10) + 2)
    all_works = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_page, p, 50, "2023-01-01"): p for p in range(1, pages_needed + 1)}
        for future in concurrent.futures.as_completed(futures):
            results = future.result()
            all_works.extend(results)
            if len(all_works) % 50 == 0:
                print(f"[INIT] Fetched {len(all_works)} recent candidates so far...")

    print(f"[INIT] Total recent candidates: {len(all_works)}")
    print(f"[INIT] Starting validation and storage...")
    print()

    # Use the same processing logic as regular crawler
    session = SessionLocal()
    stored_count = 0
    skipped_count = 0
    checked_count = 0
    batch_count = 0
    duplicate_count = 0
    no_staff_count = 0

    # Pre-load all collection objects for classification
    collections_map = {}
    for coll in session.query(Collection).all():
        collections_map[coll.name] = coll

    for work in all_works:
        if stored_count >= target_count:
            break

        checked_count += 1
        title = (work.get('title') or '').strip()
        if not title:
            continue

        doi = work.get('doi', '')
        url_val = (work.get('primary_location') or {}).get('landing_page_url') or doi or f"https://openalex.org/{work.get('id','')}"

        # Duplicate check
        if doi and session.query(Item).filter_by(doi=doi).first():
            duplicate_count += 1
            if checked_count <= 10:
                print(f"  [DUP] {title[:50]}... (duplicate DOI)")
            continue
        if session.query(Item).filter_by(url=url_val).first():
            duplicate_count += 1
            if checked_count <= 10:
                print(f"  [DUP] {title[:50]}... (duplicate URL)")
            continue

        # Extract authors
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
            if checked_count <= 10:
                print(f"  [SKIP] {title[:50]}... (no staff match)")
            continue

        # Process the paper (same as regular crawler)
        abstract = reconstruct_abstract(work.get('abstract_inverted_index'))
        oa = work.get('open_access') or {}
        pdf_url = oa.get('oa_url') if oa.get('is_oa') else None

        doc = Item(
            title=title,
            abstract=abstract,
            dc_title=title,
            dc_identifier_uri=doi or url_val,
            dc_identifier_doi=doi,
            dc_description_provenance=f"Recent Papers Crawler - {datetime.now().date()}",
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

        # Classify and link collections (same logic)
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
            faculty_results = [
                r for r in classifier.classify(text_for_classification)
                if r[0] == hint_faculty
            ]
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
            batch_count += 1
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

            # Batch commit
            if batch_count >= BATCH_SIZE:
                session.commit()
                batch_count = 0

        except Exception as e:
            session.rollback()
            batch_count = 0
            continue

    # Final commit
    try:
        session.commit()
    except Exception:
        session.rollback()
    session.close()

    print()
    print("=" * 70)
    print(f"[DONE] Recent Papers | Checked: {checked_count} | Duplicates: {duplicate_count} | No Staff: {no_staff_count} | Stored: {stored_count}")
    print("=" * 70)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', type=int, default=100)
    parser.add_argument('--recent', action='store_true', help='Fetch recent papers (2023+)')
    args = parser.parse_args()
    
    if args.recent:
        print("🔥 RECENT MODE: Fetching papers from 2023 onwards")
        crawl_recent_papers(target_count=args.target)
    else:
        crawl_papers(target_count=args.target)
