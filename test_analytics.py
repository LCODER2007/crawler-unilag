#!/usr/bin/env python3
"""Test analytics endpoints directly."""
from uraas.database import SessionLocal, Item, Author, Community, File

session = SessionLocal()

print("=" * 70)
print("ANALYTICS DATA CHECK")
print("=" * 70)

total_papers = session.query(Item).count()
total_authors = session.query(Author).count()
total_faculties = session.query(Community).count()
oa_papers = session.query(Item).filter(Item.dc_rights.like('%openAccess%')).count()
papers_with_pdf = session.query(File).count()

print(f"\nTotal Papers: {total_papers}")
print(f"Total Authors: {total_authors}")
print(f"Total Faculties: {total_faculties}")
print(f"Open Access Papers: {oa_papers}")
print(f"Papers with PDF: {papers_with_pdf}")
print(f"OA Percentage: {round((oa_papers / total_papers * 100) if total_papers else 0, 1)}%")

print("\n" + "=" * 70)
print("STATUS")
print("=" * 70)

if total_papers > 0:
    print("✓ Analytics data is available")
    print("✓ Dashboard should show these numbers")
    print("\nIf dashboard shows 0, the issue is:")
    print("1. Dashboard not running - run: python start_dashboard.py")
    print("2. JavaScript error - check browser console (F12)")
    print("3. API endpoint error - check terminal for errors")
else:
    print("✗ No papers in database")
    print("Run crawler to add papers: python crawl_10_validated.py --target 20")

session.close()
