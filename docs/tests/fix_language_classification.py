#!/usr/bin/env python3
"""
Fix Language Research Papers Classification
Removes medical/engineering papers incorrectly classified as language research.
"""
import re
from uraas.database import SessionLocal, Item

# Core language/linguistics keywords with word boundaries
LANGUAGE_KEYWORDS = [
    r'\byoruba language\b', r'\bigbo language\b', r'\bhausa language\b',
    r'\bpidgin\b', r'\bnigerian english\b', r'\befik language\b', r'\bibibio language\b',
    r'\btiv language\b', r'\bfulani language\b', r'\bkanuri language\b',
    r'\bindigenous language\b', r'\blanguage preservation\b', r'\bendangered language\b',
    r'\bcode switching\b', r'\bcode-switching\b', r'\bbilingualism\b', r'\bmultilingualism\b',
    r'\bphonology\b', r'\bmorphology\b', r'\bsyntax\b', r'\bsemantics\b',
    r'\bpragmatics\b', r'\bdiscourse analysis\b', r'\bsociolinguistics\b',
    r'\bafrican literature\b', r'\boral tradition\b', r'\bfolklore\b',
    r'\bnigerian literature\b', r'\bpostcolonial literature\b',
    r'\bafrican drama\b', r'\bcreative writing\b', r'\bpoetry\b', r'\bprose\b',
    r'\bliterary criticism\b', r'\bliterary theory\b', r'\bnarrative analysis\b'
]

# Medical/health keywords that should EXCLUDE papers
EXCLUSION_KEYWORDS = [
    r'\bmaternal\b', r'\bneonatal\b', r'\bobstetric\b', r'\bpregnancy\b',
    r'\bcovid\b', r'\bpandemic\b', r'\bsars-cov\b', r'\bcoronavirus\b',
    r'\bpatient\b', r'\bclinical\b', r'\bmedical\b', r'\bhospital\b',
    r'\btreatment\b', r'\btherapy\b', r'\bdisease\b', r'\bdiagnosis\b',
    r'\bhealth care\b', r'\bhealth service\b', r'\bpublic health\b',
    r'\binsulator\b', r'\bvoltage\b', r'\bcomposite\b', r'\bengineering\b'
]

def is_language_paper(title: str, abstract: str) -> bool:
    """Check if paper is truly about language/literature research."""
    text = f"{title or ''} {abstract or ''}".lower()
    
    # First check exclusions
    is_excluded = any(re.search(pattern, text, re.IGNORECASE) for pattern in EXCLUSION_KEYWORDS)
    if is_excluded:
        return False
    
    # Then check for language/literature keywords
    has_language_keywords = any(re.search(pattern, text, re.IGNORECASE) for pattern in LANGUAGE_KEYWORDS)
    return has_language_keywords

def main():
    session = SessionLocal()
    try:
        items = session.query(Item).all()
        
        print("=" * 70)
        print("LANGUAGE RESEARCH PAPERS CLASSIFICATION AUDIT")
        print("=" * 70)
        
        true_language_papers = []
        false_positives = []
        
        for item in items:
            try:
                if is_language_paper(item.title, item.abstract):
                    true_language_papers.append(item)
                else:
                    # Check if it was previously considered a language paper
                    text = f"{item.title or ''} {item.abstract or ''}".lower()
                    old_keywords = ['yoruba', 'igbo', 'hausa', 'narrative', 'discourse', 
                                   'translation', 'dialect', 'theatre']
                    if any(kw in text for kw in old_keywords):
                        false_positives.append(item)
            except Exception as e:
                print(f"Error processing item {item.id}: {str(e)}")
                continue
        
        print(f"\nTrue Language Research Papers: {len(true_language_papers)}")
        print(f"False Positives Removed: {len(false_positives)}")
        
        if true_language_papers:
            print("\n" + "=" * 70)
            print("TRUE LANGUAGE RESEARCH PAPERS:")
            print("=" * 70)
            for item in true_language_papers[:10]:
                print(f"\n[{item.id}] {item.title}")
                authors = [a.name for a in item.authors[:3]]
                print(f"Authors: {', '.join(authors)}")
                print(f"Year: {item.publication_date.year if item.publication_date else 'Unknown'}")
        
        if false_positives:
            print("\n" + "=" * 70)
            print("FALSE POSITIVES (Medical/Engineering papers):")
            print("=" * 70)
            for item in false_positives[:10]:
                print(f"\n[{item.id}] {item.title}")
                authors = [a.name for a in item.authors[:3]]
                print(f"Authors: {', '.join(authors)}")
        
        print("\n" + "=" * 70)
        print("SUMMARY:")
        print("=" * 70)
        print(f"Total papers analyzed: {len(items)}")
        print(f"True language papers: {len(true_language_papers)}")
        print(f"False positives removed: {len(false_positives)}")
        print(f"Accuracy improvement: {len(false_positives)} papers corrected")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        session.close()

if __name__ == '__main__':
    main()
