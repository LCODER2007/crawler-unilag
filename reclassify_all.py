"""
Reclassify ALL papers in the database using improved classification.
Runs once to fix the 449 unclassified papers.
"""
import sys, os
sys.path.insert(0, '.')

from uraas.database import SessionLocal, Item, Collection, Community
from uraas.utils.unilag_classifier import classifier
from uraas.utils.staff_validator import staff_validator
from sqlalchemy import text

def reclassify():
    session = SessionLocal()
    
    # Pre-load all collections
    collections_map = {c.name: c for c in session.query(Collection).all()}
    community_map = {comm.name: comm for comm in session.query(Community).all()}
    
    # Get all items
    items = session.query(Item).all()
    print(f"Reclassifying {len(items)} papers...")
    
    updated = 0
    for item in items:
        text_corpus = f"{item.title or ''} {item.abstract or ''}"
        
        # Get all classifications (not just best)
        results = classifier.classify(text_corpus, threshold=0.3)  # lower threshold
        
        # Also try author-based hints
        author_names = [a.name for a in item.authors]
        faculty_hints = staff_validator.get_all_faculty_hints(author_names)
        hint_faculties = list({fac for _, fac in faculty_hints})
        
        new_collections = set()
        
        # Add keyword-based classifications
        for faculty, dept, score in results[:3]:  # top 3 matches
            coll = collections_map.get(dept)
            if coll:
                new_collections.add(coll)
        
        # Add author-hint based classifications
        for hint_faculty in hint_faculties:
            faculty_results = [r for r in results if r[0] == hint_faculty]
            if faculty_results:
                coll = collections_map.get(faculty_results[0][1])
                if coll:
                    new_collections.add(coll)
            else:
                # Find first collection in that faculty
                for coll_name, coll_obj in collections_map.items():
                    if coll_obj.community and coll_obj.community.name == hint_faculty:
                        new_collections.add(coll_obj)
                        break
        
        # If still nothing, try harder with just title keywords
        if not new_collections and item.title:
            title_lower = item.title.lower()
            # Direct keyword matching for common medical/science terms
            if any(w in title_lower for w in ['cancer','tumour','tumor','cervical','malaria','hiv','hepatitis','surgery','clinical','patient','hospital','drug','antibiotic','infection','disease','health','medical','medicine','paediatric','obstetric','gynaecol']):
                coll = collections_map.get('Medicine') or collections_map.get('Community Health and Primary Care')
                if coll: new_collections.add(coll)
            elif any(w in title_lower for w in ['engineering','structural','concrete','circuit','electrical','mechanical','chemical','polymer','petroleum']):
                coll = collections_map.get('Civil and Environmental Engineering') or collections_map.get('Electrical and Electronics Engineering')
                if coll: new_collections.add(coll)
            elif any(w in title_lower for w in ['microbiol','bacteria','virus','fungi','microorganism','biosurfactant','degradation','petroleum hydrocarbon']):
                coll = collections_map.get('Microbiology')
                if coll: new_collections.add(coll)
            elif any(w in title_lower for w in ['biochem','enzyme','protein','metabol','molecular','gene','dna','rna']):
                coll = collections_map.get('Biochemistry')
                if coll: new_collections.add(coll)
            elif any(w in title_lower for w in ['econom','gdp','inflation','fiscal','monetary','trade','market','finance','accounting','business']):
                coll = collections_map.get('Economics') or collections_map.get('Finance')
                if coll: new_collections.add(coll)
            elif any(w in title_lower for w in ['language','linguistic','literature','english','french','arabic','translation','phonetic','semantic']):
                coll = collections_map.get('English') or collections_map.get('Languages')
                if coll: new_collections.add(coll)
            elif any(w in title_lower for w in ['urban','planning','architecture','estate','surveying','geoinformat','gis','remote sensing']):
                coll = collections_map.get('Urban and Regional Planning') or collections_map.get('Architecture')
                if coll: new_collections.add(coll)
            elif any(w in title_lower for w in ['law','legal','court','constitution','rights','contract','property','international']):
                coll = collections_map.get('Public Law') or collections_map.get('Commercial and Industrial Law')
                if coll: new_collections.add(coll)
            elif any(w in title_lower for w in ['education','teaching','learning','curriculum','pedagogy','school','student']):
                coll = collections_map.get('Arts and Social Sciences Education')
                if coll: new_collections.add(coll)
            elif any(w in title_lower for w in ['pharmacy','pharmaceutical','drug formulation','dosage','pharmacognosy','herbal']):
                coll = collections_map.get('Pharmaceutics and Pharmaceutical Technology') or collections_map.get('Pharmacognosy')
                if coll: new_collections.add(coll)
            elif any(w in title_lower for w in ['dental','tooth','oral','maxillofacial','orthodont','periodon']):
                coll = collections_map.get('Oral and Maxillofacial Surgery') or collections_map.get('Restorative Dentistry')
                if coll: new_collections.add(coll)
            elif any(w in title_lower for w in ['sociology','social','community','gender','poverty','migration','demograph']):
                coll = collections_map.get('Sociology') or collections_map.get('Political Science')
                if coll: new_collections.add(coll)
            elif any(w in title_lower for w in ['computer','software','algorithm','machine learning','artificial intelligence','network','data science']):
                coll = collections_map.get('Computer Science')
                if coll: new_collections.add(coll)
            elif any(w in title_lower for w in ['physics','quantum','optic','thermodynamic','nuclear','astrophysic']):
                coll = collections_map.get('Physics')
                if coll: new_collections.add(coll)
            elif any(w in title_lower for w in ['mathematics','algebra','calculus','statistic','probability','topology']):
                coll = collections_map.get('Mathematics')
                if coll: new_collections.add(coll)
        
        if new_collections:
            # Clear existing and set new
            item.collections = list(new_collections)
            updated += 1
        
        if updated % 50 == 0 and updated > 0:
            session.commit()
            print(f"  Committed {updated} updates...")
    
    session.commit()
    session.close()
    print(f"\nDone. Reclassified {updated}/{len(items)} papers.")

if __name__ == '__main__':
    reclassify()
