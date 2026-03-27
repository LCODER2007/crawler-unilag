import scrapy
from datetime import datetime
from scrapy.http import Request

class ArxivSpider(scrapy.Spider):
    name = "arxiv_unilag"
    allowed_domains = ["arxiv.org"]
    
    # Example search query for 'University of Lagos'
    # ArXiv advanced search endpoint with 'all' field matching lagos
    start_urls = [
        "https://arxiv.org/search/advanced?advanced=1&terms-0-operator=AND&terms-0-term=University+of+Lagos&terms-0-field=all&date-filter_by=all_dates&date-year=&date-from_date=&date-to_date=&date-date_type=submitted_date&abstracts=show&size=50&order=-announced_date_first"
    ]

    def parse(self, response):
        # Extract individual paper listings from the search results
        papers = response.css('li.arxiv-result')
        
        for paper in papers:
            title = paper.css('p.title.is-5.mathjax::text').get(default="").strip()
            authors = paper.css('p.authors a::text').getall()
            abstract = paper.css('span.abstract-full::text').get(default="").strip()
            
            # The URL to the paper's specific page
            paper_url = paper.css('p.list-title.is-inline-block a::attr(href)').get()
            if paper_url:
                if paper_url.startswith('/'):
                    paper_url = f"https://arxiv.org{paper_url}"
                
                # Yield request to the paper page to get full affiliations/DOI/pdf
                yield Request(url=paper_url, callback=self.parse_paper, meta={
                    'title': title,
                    'authors': authors,
                    'abstract': abstract,
                    'url': paper_url
                })
                
        # Handle pagination
        next_page = response.css('a.pagination-next::attr(href)').get()
        if next_page:
            yield Request(response.urljoin(next_page), callback=self.parse)

    def parse_paper(self, response):
        """Parse individual paper page for detailed metadata."""
        item = response.meta.copy()
        
        # arXiv doesn't always have explicit affiliation tags easily extractable,
        # but the abstract or comments sometimes mention "University of Lagos".
        # We will parse the raw_text from the whole page as a fallback for the filter pipeline.
        
        item['doi'] = response.css('td.tablecell.arxivdoi a::text').get()
        
        # Determine the PDF url
        pdf_link = response.css('div.extra-services ul li a.download-pdf::attr(href)').get()
        if pdf_link:
            item['pdf_url'] = f"https://arxiv.org{pdf_link}"
            
        # Get raw text for affiliation matching
        item['raw_affiliation'] = " ".join(response.css('div.leftcolumn ::text').getall())
        item['source_repository'] = "arXiv"
        item['is_unilag_author'] = True  # ArXiv search itself is scoped to UNILAG
        
        yield item
