import scrapy
from scholarly import scholarly, ProxyGenerator
import uuid
import time
import random
import os
import json

class ScholarSpider(scrapy.Spider):
    name = "scholar_unilag"
    custom_settings = {
        'DOWNLOAD_DELAY': 5.0,
    }

    def start_requests(self):
        # Set up free proxy rotation to avoid Google IP blocks
        try:
            pg = ProxyGenerator()
            pg.FreeProxies()
            scholarly.use_proxy(pg)
            self.logger.info("ScholarSpider: ProxyGenerator active.")
        except Exception as e:
            self.logger.warning(f"ScholarSpider: Could not set up proxy ({e}). Proceeding without proxy.")

        yield scrapy.Request(url="data:,", callback=self.fetch_scholarly)

    def fetch_scholarly(self, response):
        staff_names = []
        staff_cache = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'unilag_staff.json')
        
        if os.path.exists(staff_cache):
            try:
                with open(staff_cache, 'r', encoding='utf-8') as f:
                    staff_names = json.load(f)
                self.logger.info(f"ScholarSpider: Loaded {len(staff_names)} staff names from cache.")
            except Exception as e:
                self.logger.error(f"ScholarSpider: Failed to load staff cache ({e})")

        if staff_names:
            # Targeted search for actual faculty members
            targets = random.sample(staff_names, min(len(staff_names), 5))
            for name in targets:
                self.logger.info(f"ScholarSpider: Searching for faculty member: {name}")
                query = scholarly.search_author(f"{name}, University of Lagos")
                yield from self._process_author_query(query)
                time.sleep(random.uniform(5, 10)) # Polite delay
        else:
            # Fallback to generic institutional search
            self.logger.info("ScholarSpider: No staff cache found. Performing generic institutional search.")
            query = scholarly.search_author('University of Lagos')
            yield from self._process_author_query(query)

    def _process_author_query(self, query):
        # We process a limited number of results from the query
        try:
            for _ in range(5): # Extract up to 5 authors per page for more volume
                author = next(query)
                author = scholarly.fill(author)
                profile_name = author.get('name', 'Unknown')
                publications = author.get('publications', [])
                
                for pub in publications[:10]: # Up to 10 papers per author
                    pub_filled = scholarly.fill(pub)
                    bib = pub_filled.get('bib', {})
                    title = bib.get('title', '')
                    if not title: continue
                    
                    authors_str = bib.get('author', '')
                    authors_list = [a.strip() for a in authors_str.split(' and ')] if authors_str else [profile_name]
                    
                    yield {
                        'title': title,
                        'abstract': bib.get('abstract', ''),
                        'authors': authors_list,
                        'doi': '',
                        'pdf_url': pub_filled.get('eprint_url', ''),
                        'url': pub_filled.get('pub_url', '') or f"https://scholar.google.com/#id={uuid.uuid4()}",
                        'source_repository': 'Google Scholar',
                        'is_unilag_author': True,
                        'raw_affiliation': 'University of Lagos'
                    }
        except StopIteration:
            pass
        except Exception as e:
            self.logger.error(f"ScholarSpider: Error processing author ({e})")
