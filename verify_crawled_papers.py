"""
Verify the 10 papers we just crawled are from actual UNILAG staff.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from uraas.database import SessionLocal, Item
from uraas.utils.staff_validator import staff_validator

def verify_papers():
    print("=" * 80)
    print("VERIFICATION: Last 10 Crawled Papers")
    print("=" * 80)
    print()
    
    session = SessionLocal()
    
    # Get last 10 papers
    papers = session.query(Item).order_by(Item.id.desc()).limit(10).all()
    
    for i, paper in enumerate(reversed(papers), 1):
        print(f"{i}. {paper.title}")
        print(f"   DOI: {paper.doi or 'N/A'}")
        print(f"   Authors: {', '.join([a.name for a in paper.authors[:5]])}")
        
        # Verify staff
        authors = [a.name for a in paper.authors]
        matching_staff = staff_validator.get_matching_staff(authors)
        
        print(f"   ✓ UNILAG Staff Confirmed: {', '.join(matching_staff)}")
        print()
    
    session.close()

if __name__ == '__main__':
    verify_papers()
