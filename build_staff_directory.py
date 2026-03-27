"""
Build authoritative staff directory from OpenAlex.
Queries OpenAlex for all authors affiliated with UNILAG (ROR: 05rk03822),
cross-references with our staff list, and builds unilag_staff_detailed.json
with name, faculty, department, ORCID, and OpenAlex ID per person.
"""
import sys, os, json, re, time
sys.path.insert(0, '.')

import requests
from uraas.utils.staff_validator import StaffValidator

UNILAG_ROR = "05rk03822"
OUTPUT_PATH = "data/unilag_staff_detailed.json"
STAFF_PATH = "data/unilag_staff.json"

# UNILAG department keywords — maps department name to keywords found in affiliation strings
DEPT_KEYWORDS = {
    # College of Medicine
    "Anatomy": ["anatomy", "morphology", "histology", "embryology"],
    "Physiology": ["physiology"],
    "Pharmacology": ["pharmacology", "toxicology"],
    "Morbid Anatomy": ["morbid anatomy", "pathology", "histopathology", "forensic"],
    "Chemical Pathology": ["chemical pathology", "clinical chemistry"],
    "Haematology and Blood Transfusion": ["haematology", "hematology", "blood transfusion"],
    "Medical Microbiology and Parasitology": ["medical microbiology", "parasitology"],
    "Community Health and Primary Care": ["community health", "public health", "primary care", "epidemiology", "preventive medicine"],
    "Medicine": ["internal medicine", "cardiology", "nephrology", "endocrinology", "gastroenterology", "department of medicine"],
    "Obstetrics and Gynaecology": ["obstetrics", "gynaecology", "gynecology", "reproductive"],
    "Paediatrics": ["paediatrics", "pediatrics", "child health", "neonatology"],
    "Surgery": ["surgery", "surgical"],
    "Anaesthesia": ["anaesthesia", "anesthesia", "intensive care"],
    "Ophthalmology": ["ophthalmology", "eye"],
    "Orthopaedics and Traumatology": ["orthopaedics", "orthopedics", "trauma"],
    "Psychiatry": ["psychiatry", "mental health"],
    "Radiology": ["radiology", "imaging", "radiography"],
    # Faculty of Science
    "Biochemistry": ["biochemistry", "molecular biology"],
    "Botany": ["botany", "plant biology", "plant science"],
    "Cell Biology and Genetics": ["cell biology", "genetics", "cytology"],
    "Chemistry": ["chemistry", "chemical science"],
    "Computer Science": ["computer science", "computing", "information technology", "software"],
    "Geosciences": ["geology", "geophysics", "earth science"],
    "Marine Sciences": ["marine", "oceanography", "aquatic", "fisheries"],
    "Mathematics": ["mathematics", "statistics", "applied mathematics"],
    "Microbiology": ["microbiology", "bacteriology", "virology", "mycology"],
    "Physics": ["physics", "quantum", "optics", "astrophysics"],
    "Zoology": ["zoology", "animal biology", "entomology"],
    # Faculty of Engineering
    "Chemical and Polymer Engineering": ["chemical engineering", "polymer engineering"],
    "Civil and Environmental Engineering": ["civil engineering", "structural engineering", "environmental engineering"],
    "Electrical and Electronics Engineering": ["electrical engineering", "electronics", "telecommunications"],
    "Mechanical Engineering": ["mechanical engineering", "mechatronics", "manufacturing"],
    "Metallurgical and Materials Engineering": ["metallurgy", "materials engineering", "materials science"],
    "Systems Engineering": ["systems engineering", "industrial engineering"],
    # Faculty of Pharmacy
    "Clinical Pharmacy and Pharmacy Administration": ["clinical pharmacy", "pharmacy administration", "pharmacy practice"],
    "Pharmaceutical Chemistry": ["pharmaceutical chemistry", "medicinal chemistry"],
    "Pharmaceutics and Pharmaceutical Technology": ["pharmaceutics", "drug delivery", "pharmaceutical technology"],
    "Pharmacognosy": ["pharmacognosy", "natural products", "phytochemistry", "herbal"],
    # Faculty of Dental Sciences
    "Oral and Maxillofacial Surgery": ["oral surgery", "maxillofacial"],
    "Preventive Dentistry": ["preventive dentistry", "dental public health"],
    "Restorative Dentistry": ["restorative dentistry", "prosthodontics", "endodontics"],
    "Child Dental Health": ["paediatric dentistry", "pediatric dentistry"],
    # Faculty of Social Sciences
    "Economics": ["economics", "econometrics"],
    "Geography": ["geography", "gis", "remote sensing", "geoinformatics"],
    "Mass Communication": ["mass communication", "journalism", "media studies"],
    "Political Science": ["political science", "governance", "international relations"],
    "Psychology": ["psychology", "cognitive", "behavioural"],
    "Sociology": ["sociology", "social work", "demography"],
    # Faculty of Arts
    "Creative Arts": ["creative arts", "theatre", "drama", "music", "dance", "visual arts"],
    "English": ["english", "literature", "linguistics", "language studies"],
    "History and Strategic Studies": ["history", "strategic studies"],
    "Philosophy": ["philosophy", "ethics", "logic"],
    "Languages": ["french", "german", "arabic", "russian", "foreign language", "translation"],
    # Faculty of Law
    "Public Law": ["public law", "constitutional law", "administrative law", "human rights"],
    "Private and Property Law": ["private law", "property law", "land law", "tort"],
    "Commercial and Industrial Law": ["commercial law", "corporate law", "intellectual property"],
    "International and Comparative Law": ["international law", "comparative law"],
    # Faculty of Education
    "Arts and Social Sciences Education": ["arts education", "social sciences education", "education"],
    "Science and Technology Education": ["science education", "technology education", "stem"],
    "Educational Administration": ["educational administration", "school management"],
    # Faculty of Environmental Sciences
    "Architecture": ["architecture", "architectural"],
    "Estate Management": ["estate management", "property valuation", "real estate"],
    "Quantity Surveying": ["quantity surveying", "construction economics"],
    "Surveying and Geoinformatics": ["surveying", "geodesy", "land surveying"],
    "Urban and Regional Planning": ["urban planning", "regional planning", "town planning"],
    # Faculty of Management Sciences
    "Actuarial Science and Insurance": ["actuarial", "insurance", "risk management"],
    "Accounting": ["accounting", "auditing", "taxation"],
    "Business Administration": ["business administration", "management", "organisational"],
    "Employment Relations and Human Resource Management": ["human resource", "industrial relations", "employment"],
    "Finance": ["finance", "investment", "financial markets", "banking"],
    # Faculty of Basic Medical Sciences
    "Basic Medical Sciences": ["basic medical", "basic sciences", "preclinical"],
}

FACULTY_MAP = {
    "College of Medicine": ["anatomy", "physiology", "pharmacology", "morbid anatomy", "chemical pathology",
                            "haematology", "medical microbiology", "community health", "medicine", "obstetrics",
                            "paediatrics", "surgery", "anaesthesia", "ophthalmology", "orthopaedics",
                            "psychiatry", "radiology", "lagos university teaching hospital", "luth",
                            "college of medicine", "cmul"],
    "Faculty of Science": ["biochemistry", "botany", "cell biology", "chemistry", "computer science",
                           "geosciences", "marine", "mathematics", "microbiology", "physics", "zoology",
                           "faculty of science"],
    "Faculty of Engineering": ["chemical engineering", "civil engineering", "electrical engineering",
                               "mechanical engineering", "metallurgy", "systems engineering",
                               "faculty of engineering"],
    "Faculty of Pharmacy": ["pharmacy", "pharmacognosy", "pharmaceutics", "faculty of pharmacy"],
    "Faculty of Dental Sciences": ["dentistry", "dental", "oral", "faculty of dental"],
    "Faculty of Basic Medical Sciences": ["basic medical sciences", "basic sciences"],
    "Faculty of Social Sciences": ["economics", "geography", "mass communication", "political science",
                                   "psychology", "sociology", "faculty of social sciences"],
    "Faculty of Arts": ["creative arts", "english", "history", "philosophy", "languages",
                        "faculty of arts", "humanities"],
    "Faculty of Law": ["law", "faculty of law"],
    "Faculty of Education": ["education", "faculty of education"],
    "Faculty of Environmental Sciences": ["architecture", "estate management", "quantity surveying",
                                          "surveying", "urban planning", "faculty of environmental"],
    "Faculty of Management Sciences": ["actuarial", "accounting", "business administration",
                                       "human resource", "finance", "faculty of management"],
}


def detect_faculty(affiliation_text: str) -> str:
    text = affiliation_text.lower()
    for faculty, keywords in FACULTY_MAP.items():
        if any(kw in text for kw in keywords):
            return faculty
    return "Unknown"


def detect_department(affiliation_text: str) -> str:
    text = affiliation_text.lower()
    best_dept = None
    best_score = 0
    for dept, keywords in DEPT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best_dept = dept
    return best_dept or "Unknown"


def fetch_unilag_authors():
    """
    Extract authors + affiliations from UNILAG papers via OpenAlex works API.
    This is the reliable path since we know works?filter=institutions.ror works.
    """
    print("Fetching UNILAG papers from OpenAlex to extract author affiliations...")
    author_data = {}  # name -> {faculty, department, orcid, openalex_id, affiliation_raw}
    page = 1
    total_works = 0

    while page <= 50:  # cap at 50 pages = 2500 papers
        url = (
            f"https://api.openalex.org/works"
            f"?filter=institutions.ror:{UNILAG_ROR}"
            f"&select=id,authorships"
            f"&per-page=50&page={page}"
            f"&mailto=library@unilag.edu.ng"
        )
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            results = data.get('results', [])
            meta = data.get('meta', {})

            if not results:
                break

            total_works += len(results)

            for work in results:
                for authorship in work.get('authorships', []):
                    author = authorship.get('author', {}) or {}
                    name = author.get('display_name', '').strip()
                    if not name:
                        continue

                    orcid = author.get('orcid', '') or ''
                    openalex_id = (author.get('id') or '').replace('https://openalex.org/', '')

                    # Get affiliation strings for this author on this paper
                    raw_affs = authorship.get('raw_affiliation_strings', []) or []
                    institutions = authorship.get('institutions', []) or []

                    aff_text = ' '.join(raw_affs)
                    for inst in institutions:
                        aff_text += ' ' + (inst.get('display_name', '') or '')
                        if UNILAG_ROR in (inst.get('ror', '') or ''):
                            aff_text += ' university of lagos unilag'
                        # Only include authors who have UNILAG in their affiliation
                    is_unilag_author = False
                    for inst in institutions:
                        inst_ror = inst.get('ror', '') or ''
                        inst_name = (inst.get('display_name', '') or '').lower()
                        if UNILAG_ROR in inst_ror or 'university of lagos' in inst_name or 'unilag' in inst_name:
                            is_unilag_author = True
                            break
                    # Also check raw affiliation strings
                    if not is_unilag_author:
                        for raw in raw_affs:
                            if 'university of lagos' in raw.lower() or 'unilag' in raw.lower():
                                is_unilag_author = True
                                break

                    if not is_unilag_author:
                        continue

                    aff_text = aff_text.strip().lower()

                    if name not in author_data:
                        author_data[name] = {
                            'orcid': orcid or None,
                            'openalex_id': openalex_id,
                            'affiliation_texts': set(),
                            'paper_count': 0,
                        }

                    if aff_text:
                        author_data[name]['affiliation_texts'].add(aff_text[:300])
                    if orcid and not author_data[name]['orcid']:
                        author_data[name]['orcid'] = orcid
                    author_data[name]['paper_count'] += 1

            print(f"  Page {page}: {total_works} works processed, {len(author_data)} unique authors found")

            if len(results) < 50:
                break

            page += 1
            time.sleep(0.3)

        except Exception as e:
            print(f"  Error on page {page}: {e}")
            break

    # Convert sets to strings
    result = []
    for name, info in author_data.items():
        combined_aff = ' '.join(info['affiliation_texts'])
        result.append({
            'name': name,
            'orcid': info['orcid'],
            'openalex_id': info['openalex_id'],
            'affiliation_raw': combined_aff[:400] if combined_aff else None,
            'paper_count': info['paper_count'],
        })

    return result


def build_detailed_directory():
    # Load existing staff names for cross-reference
    validator = StaffValidator()
    print(f"Staff list loaded: {len(validator.staff_names)} names")

    # Fetch from OpenAlex
    oa_authors = fetch_unilag_authors()
    print(f"\nTotal OpenAlex authors: {len(oa_authors)}")

    records = []
    oa_names_lower = set()
    unmatched = []

    for author in oa_authors:
        name = author.get('name', '').strip()
        if not name:
            continue

        orcid = author.get('orcid')
        openalex_id = author.get('openalex_id', '')
        affiliation_text = author.get('affiliation_raw', '') or ''

        faculty = detect_faculty(affiliation_text) if affiliation_text else 'Unknown'
        department = detect_department(affiliation_text) if affiliation_text else 'Unknown'

        is_confirmed = validator.is_staff_member(name, fuzzy_threshold=75)

        record = {
            "name": name,
            "faculty": faculty,
            "department": department,
            "orcid": orcid,
            "openalex_id": openalex_id,
            "affiliation_raw": affiliation_text[:200] if affiliation_text else None,
            "confirmed_staff": is_confirmed,
            "paper_count": author.get('paper_count', 0),
        }
        records.append(record)
        oa_names_lower.add(name.lower())

        if not is_confirmed:
            unmatched.append(name)

    # Also add all staff from our list that weren't found in OpenAlex
    with open(STAFF_PATH, 'r', encoding='utf-8') as f:
        staff_list = json.load(f)

    added_from_list = 0
    for raw_name in staff_list:
        cleaned = validator._clean_name(raw_name)
        if not cleaned or cleaned.lower() in oa_names_lower:
            continue
        records.append({
            "name": cleaned,
            "faculty": "Unknown",
            "department": "Unknown",
            "orcid": None,
            "openalex_id": None,
            "affiliation_raw": None,
            "confirmed_staff": True,
        })
        added_from_list += 1

    # Save
    os.makedirs('data', exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    # Stats
    confirmed = sum(1 for r in records if r['confirmed_staff'])
    with_faculty = sum(1 for r in records if r['faculty'] != 'Unknown')
    with_dept = sum(1 for r in records if r['department'] != 'Unknown')
    with_orcid = sum(1 for r in records if r['orcid'])

    print(f"\n{'='*60}")
    print(f"STAFF DIRECTORY BUILT")
    print(f"{'='*60}")
    print(f"Total records:        {len(records)}")
    print(f"Confirmed staff:      {confirmed}")
    print(f"With faculty:         {with_faculty}")
    print(f"With department:      {with_dept}")
    print(f"With ORCID:           {with_orcid}")
    print(f"Added from staff list:{added_from_list}")
    print(f"Saved to:             {OUTPUT_PATH}")

    # Show sample
    print(f"\nSample records:")
    for r in [x for x in records if x['faculty'] != 'Unknown'][:8]:
        print(f"  {r['name'][:35]:<35} | {r['faculty'][:25]:<25} | {r['department'][:30]}")


if __name__ == '__main__':
    build_detailed_directory()
