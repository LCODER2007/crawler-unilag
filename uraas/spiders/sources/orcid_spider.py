"""
ORCID Spider - Harvests papers using ORCID IDs of UNILAG staff.
This is the most accurate way to get papers from specific researchers.
"""
import scrapy
import json
import os

class ORCIDSpider(scrapy.Spider):
    """Spider that uses ORCID IDs to harvest papers from specific UNILAG researchers."""
    
    name = "orcid_unilag"
    custom_settings = {
        'DOWNLOAD_DELAY': 2.0,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 3,
    }

    def start_requests(self):
        """Load ORCID IDs and query ORCID API for each researcher's works."""
        orcid_cache = os.path.join(
            os.path.dirname(__file__), '..', '..', '..', 'data', 'unilag_orcids.json'
        )
        
        if not os.path.exists(orcid_cache):
            self.logger.warning("No ORCID cache found. Run find_orcids.py first.")
            return
        
        with open(orcid_cache, 'r', encoding='utf-8') as f:
            orcid_data = json.load(f)
        
        # Filter to only those with ORCIDs
        orcids = [(name, orcid) for name, orcid in orcid_data.items() if orcid]
        
        self.logger.info(f"Found {len(orcids)} staff members with ORCID IDs")
        
        # Query ORCID API for each person's works
        for name, orcid_id in orcids[:20]:  # Limit to first 20 to avoid overwhelming
            url = f"https://pub.orcid.org/v3.0/{orcid_id}/works"
            yield scrapy.Request(
                url=url,
                callback=self.parse_works,
                headers={'Accept': 'application/json'},
                meta={'orcid': orcid_id, 'name': name},
                errback=self.errback_httpbin
            )
    
    def errback_httpbin(self, failure):
        """Handle request failures."""
        self.logger.error(f"Request failed: {failure.request.url}")
    
    def parse_works(self, response):
        """Parse works from ORCID API response."""
        orcid = response.meta['orcid']
        name = response.meta['name']
        
        try:
            data = response.json()
            works = data.get('group', [])
            
            self.logger.info(f"Found {len(works)} works for {name} (ORCID: {orcid})")
            
            for work_group in works:
                work_summary = work_group.get('work-summary', [])
                if not work_summary:
                    continue
                
                # Get first work summary
                work = work_summary[0]
                
                title_data = work.get('title', {})
                title = title_data.get('title', {}).get('value', '')
                
                if not title:
                    continue
                
                # Get external IDs (DOI, etc.)
                external_ids = work.get('external-ids', {}).get('external-id', [])
                doi = None
                url = None
                
                for ext_id in external_ids:
                    if ext_id.get('external-id-type') == 'doi':
                        doi = ext_id.get('external-id-value')
                        url = f"https://doi.org/{doi}"
                        break
                
                # Get publication date
                pub_date = work.get('publication-date')
                pub_year = pub_date.get('year', {}).get('value') if pub_date else None
                
                # Get journal/source
                journal = work.get('journal-title', {}).get('value', '')
                
                yield {
                    'title': title,
                    'authors': [name],  # We know this person is an author
                    'doi': doi,
                    'url': url or f"https://orcid.org/{orcid}",
                    'source_repository': 'ORCID',
                    'is_unilag_author': True,
                    'raw_affiliation': 'University of Lagos',
                    'orcid': orcid,
                    'publication_year': pub_year,
                    'journal': journal,
                    'abstract': ''  # ORCID doesn't provide abstracts
                }
                
        except Exception as e:
            self.logger.error(f"Error parsing works for {name}: {e}")
