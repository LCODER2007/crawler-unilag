import re
from typing import List, Tuple, Optional

# Complete UNILAG Faculty and Department Structure (2024)
UNILAG_STRUCTURE = {
    "Faculty of Arts": {
        "Creative Arts": ["creative arts", "theatre", "drama", "performance", "visual arts", "music", "dance"],
        "English": ["english literature", "linguistics", "language studies", "literary criticism", "phonetics"],
        "History and Strategic Studies": ["history", "strategic studies", "military", "warfare", "historical analysis"],
        "Philosophy": ["philosophy", "logic", "ethics", "metaphysics", "epistemology"],
        "Languages": ["french", "german", "russian", "arabic", "foreign language", "translation"]
    },
    "Faculty of Science": {
        "Biochemistry": ["biochemistry", "molecular biology", "enzymology", "metabolism", "protein"],
        "Botany": ["botany", "plant biology", "plant physiology", "taxonomy", "flora"],
        "Cell Biology and Genetics": ["cell biology", "genetics", "cytology", "heredity", "dna", "gene expression"],
        "Chemistry": ["chemistry", "organic chemistry", "inorganic chemistry", "analytical chemistry", "chemical"],
        "Computer Science": ["computer science", "machine learning", "artificial intelligence", "software engineering", "data science", "algorithm", "programming", "neural network", "deep learning"],
        "Geosciences": ["geology", "geophysics", "earth science", "mineralogy", "petrology"],
        "Marine Sciences": ["marine biology", "oceanography", "aquatic", "fisheries", "coastal"],
        "Mathematics": ["mathematics", "algebra", "calculus", "topology", "geometry", "statistics", "probability"],
        "Microbiology": ["microbiology", "bacteriology", "virology", "mycology", "microorganism"],
        "Physics": ["physics", "quantum", "thermodynamics", "optics", "mechanics", "astrophysics", "particle physics"],
        "Zoology": ["zoology", "animal biology", "entomology", "parasitology", "wildlife"]
    },
    "Faculty of Engineering": {
        "Chemical and Polymer Engineering": ["chemical engineering", "polymer", "petrochemical", "process engineering"],
        "Civil and Environmental Engineering": ["civil engineering", "structural", "concrete", "transportation", "environmental engineering", "geotechnical"],
        "Electrical and Electronics Engineering": ["electrical engineering", "circuit", "power systems", "electronics", "telecommunications", "signal processing"],
        "Mechanical Engineering": ["mechanical", "thermofluids", "mechatronics", "manufacturing", "robotics"],
        "Metallurgical and Materials Engineering": ["metallurgy", "materials science", "corrosion", "alloy", "ceramics"],
        "Systems Engineering": ["systems engineering", "operations research", "optimization", "industrial engineering"]
    },
    "College of Medicine": {
        "Anatomy": ["anatomy", "morphology", "histology", "embryology", "cadaver"],
        "Physiology": ["physiology", "cellular", "metabolism", "homeostasis", "organ function"],
        "Pharmacology": ["pharmacology", "drug", "toxicology", "pharmacokinetics", "therapeutics"],
        "Morbid Anatomy": ["pathology", "autopsy", "forensic", "histopathology"],
        "Chemical Pathology": ["clinical chemistry", "biochemical", "metabolic disorder"],
        "Haematology and Blood Transfusion": ["haematology", "blood", "transfusion", "anemia", "coagulation"],
        "Medical Microbiology and Parasitology": ["medical microbiology", "parasitology", "infectious disease", "antimicrobial"],
        "Community Health and Primary Care": ["public health", "epidemiology", "community medicine", "preventive medicine"],
        "Medicine": ["internal medicine", "cardiology", "nephrology", "endocrinology", "gastroenterology"],
        "Obstetrics and Gynaecology": ["obstetrics", "gynaecology", "pregnancy", "maternal", "reproductive health"],
        "Paediatrics": ["paediatrics", "pediatrics", "child health", "neonatology"],
        "Surgery": ["surgery", "surgical", "operation", "laparoscopy", "trauma"],
        "Anaesthesia": ["anaesthesia", "anesthesia", "pain management", "critical care"],
        "Ophthalmology": ["ophthalmology", "eye", "vision", "retina", "glaucoma"],
        "Orthopaedics and Traumatology": ["orthopaedics", "orthopedics", "bone", "fracture", "joint"],
        "Psychiatry": ["psychiatry", "mental health", "psychosis", "depression", "schizophrenia"],
        "Radiology": ["radiology", "imaging", "x-ray", "mri", "ct scan", "ultrasound"]
    },
    "Faculty of Pharmacy": {
        "Clinical Pharmacy and Pharmacy Administration": ["clinical pharmacy", "pharmaceutical care", "pharmacy practice"],
        "Pharmaceutical Chemistry": ["pharmaceutical chemistry", "drug synthesis", "medicinal chemistry"],
        "Pharmaceutics and Pharmaceutical Technology": ["pharmaceutics", "drug formulation", "dosage form", "tablet"],
        "Pharmacognosy": ["pharmacognosy", "natural products", "herbal medicine", "phytochemistry"]
    },
    "Faculty of Dental Sciences": {
        "Oral and Maxillofacial Surgery": ["oral surgery", "maxillofacial", "jaw", "dental surgery"],
        "Preventive Dentistry": ["preventive dentistry", "oral hygiene", "dental public health"],
        "Restorative Dentistry": ["restorative dentistry", "prosthodontics", "endodontics", "dental restoration"],
        "Child Dental Health": ["paediatric dentistry", "pediatric dentistry", "child dental"]
    },
    "Faculty of Basic Medical Sciences": {
        "Anatomy": ["anatomy", "morphology", "histology"],
        "Physiology": ["physiology", "cellular physiology"],
        "Biochemistry": ["biochemistry", "molecular biology"]
    },
    "Faculty of Social Sciences": {
        "Economics": ["economics", "macroeconomics", "microeconomics", "econometrics", "development economics"],
        "Geography": ["geography", "gis", "remote sensing", "cartography", "spatial analysis"],
        "Mass Communication": ["mass communication", "journalism", "media", "broadcasting", "public relations"],
        "Political Science": ["political science", "governance", "democracy", "international relations"],
        "Psychology": ["psychology", "cognitive", "behavioral", "clinical psychology"],
        "Sociology": ["sociology", "social theory", "social structure", "demography"]
    },
    "Faculty of Law": {
        "Public Law": ["constitutional law", "administrative law", "human rights", "public law"],
        "Private and Property Law": ["contract law", "property law", "land law", "tort"],
        "Commercial and Industrial Law": ["commercial law", "corporate law", "business law", "intellectual property"],
        "International and Comparative Law": ["international law", "comparative law", "treaty"]
    },
    "Faculty of Education": {
        "Arts and Social Sciences Education": ["education", "pedagogy", "curriculum", "teaching methods"],
        "Science and Technology Education": ["science education", "technology education", "stem education"],
        "Educational Administration": ["educational administration", "school management", "educational leadership"]
    },
    "Faculty of Environmental Sciences": {
        "Architecture": ["architecture", "architectural design", "building design", "urban design"],
        "Estate Management": ["estate management", "property valuation", "real estate", "land management"],
        "Quantity Surveying": ["quantity surveying", "cost estimation", "construction economics"],
        "Surveying and Geoinformatics": ["surveying", "geoinformatics", "geodesy", "land surveying"],
        "Urban and Regional Planning": ["urban planning", "regional planning", "town planning", "city planning"]
    },
    "Faculty of Management Sciences": {
        "Actuarial Science and Insurance": ["actuarial science", "insurance", "risk management", "actuarial"],
        "Accounting": ["accounting", "financial accounting", "auditing", "taxation"],
        "Business Administration": ["business administration", "management", "organizational behavior", "strategic management"],
        "Employment Relations and Human Resource Management": ["human resource", "hr management", "industrial relations", "personnel management"],
        "Finance": ["finance", "corporate finance", "investment", "financial markets"]
    }
}

# Email pattern for UNILAG staff
UNILAG_EMAIL_PATTERN = r'[a-z]+@(unilag\.edu\.ng|cmul\.edu\.ng)'

class UNILAGClassifier:
    """Advanced classifier for UNILAG papers with comprehensive faculty/department mapping."""

    def __init__(self):
        self.structure = UNILAG_STRUCTURE
        
    def classify(self, text_corpus: str, threshold: float = 0.5) -> List[Tuple[str, str, float]]:
        """
        Returns a list of (Faculty, Department, Score) based on keyword frequency.
        
        Args:
            text_corpus: Combined text (title + abstract + keywords)
            threshold: Minimum score to include in results
            
        Returns:
            List of (faculty, department, score) tuples sorted by confidence
        """
        if not text_corpus:
            return []
        
        try:
            text_corpus = str(text_corpus).lower()
        except Exception:
            return []
            
        results = []
        
        for faculty, departments in self.structure.items():
            for dept, keywords in departments.items():
                score = 0.0
                
                try:
                    # Count keyword matches with word boundaries
                    for kw in keywords:
                        try:
                            # Use word boundaries to avoid partial matches
                            pattern = fr'\b{re.escape(kw)}\b'
                            matches = len(re.findall(pattern, text_corpus))
                            if matches > 0:
                                # Weight by keyword specificity (longer keywords = more specific)
                                weight = len(kw.split()) * 0.5
                                score += (matches * weight)
                        except Exception:
                            # Skip problematic keywords
                            continue
                            
                    if score >= threshold:
                        results.append((faculty, dept, score))
                except Exception:
                    # Skip problematic departments
                    continue
                    
        # Sort by confidence score descending
        results.sort(key=lambda x: x[2], reverse=True)
        return results
    
    def get_best_classification(self, text_corpus: str) -> Optional[Tuple[str, str, float]]:
        """Returns the single best classification or None if no match."""
        try:
            results = self.classify(text_corpus)
            return results[0] if results else None
        except Exception:
            return None

classifier = UNILAGClassifier()
