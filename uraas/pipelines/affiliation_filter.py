import re
from scrapy.exceptions import DropItem
from uraas.utils.staff_validator import staff_validator

UNILAG_PATTERNS = [
    r'university\s+of\s+lagos',
    r'\bunilag\b',
    r'u\.?\s*of\s*lagos',
    r'lagos\s+university',
]

UNILAG_DOMAINS = [
    '@unilag.edu.ng',
    '@cmul.edu.ng'
]

class AffiliationFilterPipeline:
    """
    CRITICAL FILTER: Only allows papers with at least ONE confirmed UNILAG staff member.
    This prevents false positives from papers that just mention "Lagos" or "University of Lagos".
    """
    
    def __init__(self):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in UNILAG_PATTERNS]
        self.staff_validator = staff_validator

    def is_unilag_affiliated(self, text: str) -> bool:
        """Check if unstructured text contains UNILAG references."""
        if not text:
            return False
        return any(pattern.search(text) for pattern in self.patterns)
    
    def has_unilag_email(self, emails: list) -> bool:
        """Check if any email belongs to UNILAG domain."""
        if not emails:
            return False
        for email in emails:
            email_lower = email.lower()
            if any(domain in email_lower for domain in UNILAG_DOMAINS):
                return True
        return False

    def process_item(self, item, spider):
        """
        WORLD-CLASS VALIDATION:
        1. Check if at least ONE author is a confirmed UNILAG staff member (MANDATORY)
        2. Optionally verify UNILAG affiliation text or email as secondary confirmation
        
        Uses RELAXED 75% fuzzy matching threshold to avoid dropping legitimate papers.
        """
        try:
            authors = item.get('authors', [])
            
            # Handle empty or invalid authors list
            if not authors or not isinstance(authors, list):
                raise DropItem(
                    f"Paper '{item.get('title', 'Unknown')[:60]}...' has no valid authors list."
                )
            
            # CRITICAL: Validate against actual staff list with RELAXED threshold
            matching_staff = []
            for author in authors:
                try:
                    if self.staff_validator.is_staff_member(author, fuzzy_threshold=75):
                        matching_staff.append(author)
                except Exception as e:
                    spider.logger.error(f"Error validating author '{author}': {str(e)}")
                    continue
            
            if not matching_staff:
                raise DropItem(
                    f"Paper '{item.get('title', 'Unknown')[:60]}...' has NO confirmed UNILAG staff authors. "
                    f"Authors: {', '.join(str(a) for a in authors[:3])}"
                )
            
            # Store which authors are UNILAG staff for metadata
            item['unilag_staff_authors'] = matching_staff
            
            # Secondary validation: Check affiliation text or email (optional but recommended)
            has_affiliation = False
            
            try:
                # Check explicit affiliations list
                affiliations = item.get('affiliations', [])
                if isinstance(affiliations, list):
                    if any(self.is_unilag_affiliated(aff) for aff in affiliations if aff):
                        has_affiliation = True

                # Check raw string summary
                if not has_affiliation:
                    raw_text = ' '.join(str(a) for a in affiliations if a) if isinstance(affiliations, list) else ''
                    raw_text += " " + str(item.get('raw_affiliation', ''))
                    if self.is_unilag_affiliated(raw_text):
                        has_affiliation = True
                        
                # Check author emails
                if not has_affiliation:
                    emails = item.get('author_emails', [])
                    if emails and isinstance(emails, list):
                        if self.has_unilag_email(emails):
                            has_affiliation = True
            except Exception as e:
                spider.logger.error(f"Error checking affiliations for paper '{item.get('title', 'Unknown')[:60]}': {str(e)}")
            
            # Log warning if staff member found but no affiliation text
            if not has_affiliation:
                spider.logger.warning(
                    f"Paper has UNILAG staff ({item['unilag_staff_authors']}) but no affiliation text. "
                    f"Proceeding with caution."
                )
                
            return item
            
        except DropItem:
            raise
        except Exception as e:
            spider.logger.error(f"Unexpected error in affiliation filter for paper '{item.get('title', 'Unknown')[:60]}': {str(e)}")
            raise DropItem(f"Failed to process item due to error: {str(e)}")
