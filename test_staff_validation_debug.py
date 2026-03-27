"""
Debug staff validation to see why legitimate UNILAG papers are being dropped.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from uraas.database import SessionLocal, Item, Author
from uraas.utils.staff_validator import staff_validator

def test_validation():
    print("=" * 80)
    print("STAFF VALIDATION DEBUG TEST")
    print("=" * 80)
    print()
    
    # Load some papers from database
    session = SessionLocal()
    papers = session.query(Item).limit(20).all()
    
    print(f"Testing {len(papers)} papers from database...")
    print(f"Staff cache has {len(staff_validator.staff_names)} names loaded")
    print()
    
    passed = 0
    failed = 0
    
    for paper in papers:
        title = paper.title[:60] if paper.title else "Unknown"
        authors = [a.name for a in paper.authors]
        
        # Test validation
        is_valid = staff_validator.validate_authors(authors, require_all=False)
        matching_staff = staff_validator.get_matching_staff(authors)
        
        if is_valid:
            passed += 1
            print(f"✓ PASS: {title}...")
            print(f"  Authors: {', '.join(authors[:3])}")
            print(f"  Matching Staff: {', '.join(matching_staff)}")
        else:
            failed += 1
            print(f"✗ FAIL: {title}...")
            print(f"  Authors: {', '.join(authors[:3])}")
            
            # Test each author individually with different thresholds
            print(f"  Individual tests:")
            for author in authors[:3]:
                score_85 = staff_validator.is_staff_member(author, fuzzy_threshold=85)
                score_80 = staff_validator.is_staff_member(author, fuzzy_threshold=80)
                score_75 = staff_validator.is_staff_member(author, fuzzy_threshold=75)
                print(f"    - {author}: 85%={score_85}, 80%={score_80}, 75%={score_75}")
        
        print()
    
    session.close()
    
    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)

if __name__ == '__main__':
    test_validation()
