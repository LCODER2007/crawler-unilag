"""
Staff Validator - Validates authors against UNILAG staff list.
Also provides faculty hints based on author surname matching.
"""
import os
import json
import re
from typing import List, Set, Optional, Dict, Tuple
from thefuzz import fuzz


class StaffValidator:

    def __init__(self, staff_cache_path: str = None):
        if staff_cache_path is None:
            staff_cache_path = os.path.join(
                os.path.dirname(__file__), '..', '..', 'data', 'unilag_staff.json'
            )
        self.staff_cache_path = staff_cache_path
        self.staff_names: Set[str] = set()
        self.normalized_staff: Set[str] = set()
        self._faculty_map: Dict[str, List[str]] = {}
        self._surname_to_faculty: Dict[str, str] = {}
        self._surname_to_dept: Dict[str, str] = {}
        self._fullname_to_faculty: Dict[str, str] = {}
        self._fullname_to_dept: Dict[str, str] = {}
        self._detailed_records: List = []
        self.load_staff_cache()
        self._load_faculty_map()

    def load_staff_cache(self):
        if not os.path.exists(self.staff_cache_path):
            return
        try:
            with open(self.staff_cache_path, 'r', encoding='utf-8') as f:
                staff_list = json.load(f)
            for name in staff_list:
                cleaned = self._clean_name(name)
                if cleaned:
                    self.staff_names.add(cleaned)
                    self.normalized_staff.add(self._normalize_name(cleaned))
        except Exception as e:
            print(f"Error loading staff cache: {e}")

    def _load_faculty_map(self):
        # First try the detailed scraped records (name → faculty/dept)
        detailed_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'data', 'unilag_staff_detailed.json'
        )
        if os.path.exists(detailed_path):
            try:
                with open(detailed_path, 'r', encoding='utf-8') as f:
                    records = json.load(f)
                self._detailed_records = records
                self._surname_to_faculty: Dict[str, str] = {}
                self._surname_to_dept: Dict[str, str] = {}
                self._fullname_to_faculty: Dict[str, str] = {}
                self._fullname_to_dept: Dict[str, str] = {}

                for r in records:
                    name = r.get('name', '')
                    faculty = r.get('faculty', 'Unknown')
                    dept = r.get('department', 'Unknown')
                    if not name or faculty == 'Unknown':
                        continue

                    # Store full normalized name lookup (most accurate)
                    norm = self._normalize_name(self._clean_name(name))
                    if norm:
                        self._fullname_to_faculty[norm] = faculty
                        if dept != 'Unknown':
                            self._fullname_to_dept[norm] = dept

                    # Store surname (last word) lookup as fallback
                    parts = name.strip().split()
                    if parts:
                        surname = re.sub(r'[^\w]', '', parts[-1].lower())
                        if len(surname) >= 4:
                            # Only set if not already set (first match wins)
                            if surname not in self._surname_to_faculty:
                                self._surname_to_faculty[surname] = faculty
                            if dept != 'Unknown' and surname not in self._surname_to_dept:
                                self._surname_to_dept[surname] = dept
                return
            except Exception as e:
                print(f"Warning: could not load detailed staff records: {e}")

        # Fallback: keyword map
        self._detailed_records = []
        self._surname_to_faculty = {}
        self._surname_to_dept = {}
        self._fullname_to_faculty = {}
        self._fullname_to_dept = {}
        map_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'data', 'staff_department_map.json'
        )
        if os.path.exists(map_path):
            try:
                with open(map_path, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                self._faculty_map = {
                    faculty: data.get('keywords', [])
                    for faculty, data in raw.items()
                }
            except Exception:
                pass

    def _clean_name(self, name: str) -> str:
        name = re.sub(
            r'\b(Prof\.?|Dr\.?|Mr\.?|Mrs\.?|Miss\.?|Ms\.?|Engr\.?|Pharm\.?|Assoc\.?|Associate)\s*',
            '', name, flags=re.IGNORECASE
        )
        name = re.sub(
            r'\b(Ph\.?D\.?|M\.?Sc\.?|B\.?Sc\.?|M\.?B\.?,?\s*B\.?S\.?|M\.?Phil\.?)\s*',
            '', name, flags=re.IGNORECASE
        )
        name = re.sub(r'\(Mrs\.?\)|(\(Mr\.?\))', '', name)
        name = re.sub(r'[,\.]', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        return name

    def _normalize_name(self, name: str) -> str:
        name = name.lower()
        name = re.sub(r'[^\w\s]', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        return name

    def is_staff_member(self, author_name: str, fuzzy_threshold: int = 75) -> bool:
        if not author_name:
            return False
        cleaned = self._clean_name(author_name)
        normalized = self._normalize_name(cleaned)
        if normalized in self.normalized_staff:
            return True
        for staff_name in self.normalized_staff:
            if fuzz.ratio(normalized, staff_name) >= fuzzy_threshold:
                return True
        return False

    def get_faculty_hint(self, author_name: str) -> Optional[str]:
        """Return most likely faculty — checks full name first, then surname."""
        if not author_name:
            return None
        # 1. Full normalized name lookup (most accurate)
        norm = self._normalize_name(self._clean_name(author_name))
        if norm in self._fullname_to_faculty:
            return self._fullname_to_faculty[norm]
        # 2. Fuzzy match against full name lookup
        from thefuzz import process
        if self._fullname_to_faculty:
            match = process.extractOne(norm, self._fullname_to_faculty.keys(), score_cutoff=80)
            if match:
                return self._fullname_to_faculty[match[0]]
        # 3. Surname fallback
        parts = author_name.strip().split()
        if parts:
            surname = re.sub(r'[^\w]', '', parts[-1].lower())
            if surname in self._surname_to_faculty:
                return self._surname_to_faculty[surname]
        # 4. Keyword map fallback
        for part in author_name.lower().split():
            part = re.sub(r'[^\w]', '', part)
            if len(part) < 4:
                continue
            for faculty, keywords in self._faculty_map.items():
                if any(part in kw or kw in part for kw in keywords):
                    return faculty
        return None

    def get_department_hint(self, author_name: str) -> Optional[str]:
        """Return most likely department."""
        if not author_name:
            return None
        norm = self._normalize_name(self._clean_name(author_name))
        if norm in self._fullname_to_dept:
            return self._fullname_to_dept[norm]
        from thefuzz import process
        if self._fullname_to_dept:
            match = process.extractOne(norm, self._fullname_to_dept.keys(), score_cutoff=80)
            if match:
                return self._fullname_to_dept[match[0]]
        parts = author_name.strip().split()
        if parts:
            surname = re.sub(r'[^\w]', '', parts[-1].lower())
            if surname in self._surname_to_dept:
                return self._surname_to_dept[surname]
        return None

    def get_all_faculty_hints(self, authors: List[str]) -> List[Tuple[str, str]]:
        """
        Returns (author, faculty) pairs for all confirmed UNILAG staff authors.
        Handles multiple UNILAG authors on the same paper.
        """
        results = []
        for author in authors:
            if self.is_staff_member(author, fuzzy_threshold=75):
                hint = self.get_faculty_hint(author)
                if hint:
                    results.append((author, hint))
        return results

    def validate_authors(self, authors: List[str], require_all: bool = False) -> bool:
        if not authors:
            return False
        matches = [self.is_staff_member(a) for a in authors]
        return all(matches) if require_all else any(matches)

    def get_matching_staff(self, authors: List[str]) -> List[str]:
        return [a for a in authors if self.is_staff_member(a)]


# Global instance
staff_validator = StaffValidator()
