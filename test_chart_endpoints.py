#!/usr/bin/env python3
"""Test chart endpoints to see what data they return."""
from uraas.database import SessionLocal, Item, Community, Collection
from sqlalchemy import func, extract

session = SessionLocal()

print("=" * 70)
print("TESTING CHART ENDPOINTS")
print("=" * 70)

# Test 1: Publications by year
print("\n1. Publications by Year:")
rows = session.query(
    extract('year', Item.publication_date).label('year'),
    func.count(Item.id).label('count')
).filter(Item.publication_date.isnot(None)) \
 .group_by('year').order_by('year').all()

print(f"   Found {len(rows)} years with data")
if rows:
    print(f"   Sample: {rows[:3]}")
else:
    print("   ⚠️  NO DATA - All papers missing publication_date!")

# Test 2: Papers by faculty
print("\n2. Papers by Faculty:")
rows = session.query(
    Community.name,
    func.count(Item.id).label('count')
).join(Collection, Collection.community_id == Community.id) \
 .join(Collection.items) \
 .group_by(Community.name) \
 .order_by(func.count(Item.id).desc()).all()

print(f"   Found {len(rows)} faculties with papers")
if rows:
    for name, count in rows[:5]:
        print(f"   - {name}: {count} papers")
else:
    print("   ⚠️  NO DATA - Papers not linked to faculties!")

# Test 3: Check if papers have collections
print("\n3. Papers with Collections:")
total_papers = session.query(Item).count()
papers_with_collections = session.query(Item).join(Item.collections).distinct().count()
papers_without = total_papers - papers_with_collections

print(f"   Total papers: {total_papers}")
print(f"   With collections: {papers_with_collections}")
print(f"   Without collections: {papers_without}")

if papers_without > 0:
    print(f"   ⚠️  {papers_without} papers are not classified!")
    print("   Run: python reclassify_all.py")

# Test 4: Check publication dates
print("\n4. Publication Dates:")
with_dates = session.query(Item).filter(Item.publication_date.isnot(None)).count()
without_dates = session.query(Item).filter(Item.publication_date.is_(None)).count()

print(f"   With dates: {with_dates}")
print(f"   Without dates: {without_dates}")

if without_dates > 0:
    print(f"   ⚠️  {without_dates} papers missing publication dates!")

print("\n" + "=" * 70)
print("DIAGNOSIS")
print("=" * 70)

if len(rows) == 0 and papers_without > 0:
    print("❌ ISSUE: Papers are not classified into faculties")
    print("   Solution: Run 'python reclassify_all.py'")
elif without_dates > total_papers * 0.5:
    print("❌ ISSUE: Most papers missing publication dates")
    print("   Charts by year won't work")
else:
    print("✅ Data looks good - charts should work")
    print("   If charts still empty, check browser console (F12)")

session.close()
