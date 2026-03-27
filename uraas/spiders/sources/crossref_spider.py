import scrapy
from habanero import Crossref

class CrossrefSpider(scrapy.Spider):
    name = "crossref_unilag"
    custom_settings = {
        'DOWNLOAD_DELAY': 1.0,
    }

    def start_requests(self):
        # We don't need a traditional start_url. We'll query the Crossref API directly.
        # But Scrapy requires at least one Request to start the engine cleanly.
        # We'll ping a dummy URL and do the real work in the callback, 
        # or we can construct an API request. Let's use the REST API URL directly.
        
        # Searching for 'University of Lagos' affiliation
        api_url = "https://api.crossref.org/works?query.affiliation=University+of+Lagos&select=DOI,title,abstract,author,issued,URL,link&rows=50"
        yield scrapy.Request(url=api_url, callback=self.parse)

    def parse(self, response):
        data = response.json()
        items = data.get('message', {}).get('items', [])
        
        for work in items:
            title = work.get('title', [''])[0] if work.get('title') else ''
            doi = work.get('DOI', '')
            url = work.get('URL', '')
            
            # Abstract might be in abstract or we might not have it
            abstract = work.get('abstract', '')
            
            # Authors
            authors = []
            for author in work.get('author', []):
                given = author.get('given', '')
                family = author.get('family', '')
                if given or family:
                    authors.append(f"{given} {family}".strip())
                    
            # Try to find a PDF link in the 'link' array if open access
            pdf_url = None
            for link in work.get('link', []):
                if link.get('content-type') == 'application/pdf':
                    pdf_url = link.get('URL')
                    break

            yield {
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'doi': doi,
                'url': url,
                'pdf_url': pdf_url,
                'source_repository': 'Crossref',
                'is_unilag_author': True,
                'raw_affiliation': 'University of Lagos'
            }
            
        # Deep pagination via offset (up to 500 results total)
        offset = response.meta.get('offset', 0) + 50
        if items and offset < 500:
            next_url = f"https://api.crossref.org/works?query.affiliation=University+of+Lagos&select=DOI,title,abstract,author,issued,URL,link&rows=50&offset={offset}"
            yield scrapy.Request(url=next_url, callback=self.parse, meta={'offset': offset})
