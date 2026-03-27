import scrapy

# UNILAG ROR ID (correct - verified)
UNILAG_ROR = "05rk03822"
OPENALEX_BASE = "https://api.openalex.org/works"

class OpenAlexSpider(scrapy.Spider):
    name = "openalex_unilag"
    custom_settings = {
        'DOWNLOAD_DELAY': 1.0,
        'AUTOTHROTTLE_ENABLED': True,
    }

    def start_requests(self):
        """
        Start from cursor=* for full exhaustive pagination.
        Uses both ROR ID and ORCID IDs for comprehensive coverage.
        """
        # Strategy 1: Query by institution ROR ID
        url = (
            f"{OPENALEX_BASE}"
            f"?filter=institutions.ror:{UNILAG_ROR}"
            f"&select=id,doi,title,abstract_inverted_index,authorships,publication_date,open_access,primary_location"
            f"&per-page=50"
            f"&cursor=*"
            f"&mailto=uraas-bot@unilag.edu.ng"
        )
        yield scrapy.Request(url=url, callback=self.parse, meta={'source': 'ror'})
        
        # Strategy 2: Query by ORCID IDs (if available)
        import os
        import json
        orcid_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'unilag_orcids.json')
        
        if os.path.exists(orcid_file):
            with open(orcid_file, 'r', encoding='utf-8') as f:
                orcid_data = json.load(f)
            
            # Get ORCIDs (filter out None values)
            orcids = [orcid for orcid in orcid_data.values() if orcid]
            
            if orcids:
                self.logger.info(f"Found {len(orcids)} ORCID IDs to query")
                
                # Query by ORCID (batch query - OpenAlex supports OR queries)
                # Limit to top 50 ORCIDs to avoid overwhelming the API
                for orcid in orcids[:50]:
                    orcid_url = (
                        f"{OPENALEX_BASE}"
                        f"?filter=authorships.author.orcid:https://orcid.org/{orcid}"
                        f"&select=id,doi,title,abstract_inverted_index,authorships,publication_date,open_access,primary_location"
                        f"&per-page=50"
                        f"&mailto=uraas-bot@unilag.edu.ng"
                    )
                    yield scrapy.Request(url=orcid_url, callback=self.parse, meta={'source': 'orcid', 'orcid': orcid})

    def parse(self, response):
        data = response.json()
        results = data.get('results', [])
        
        source = response.meta.get('source', 'ror')
        if source == 'orcid':
            self.logger.info(f"Processing {len(results)} works from ORCID: {response.meta.get('orcid')}")

        for work in results:
            title = (work.get('title') or '').strip()
            if not title:
                continue

            doi = work.get('doi', '')

            # Reconstruct abstract from inverted index
            abstract = self._reconstruct_abstract(
                work.get('abstract_inverted_index', {})
            )

            # Authors with affiliations and ORCIDs
            authors = []
            author_orcids = []
            for authorship in work.get('authorships', []):
                author_name = authorship.get('author', {}).get('display_name', '')
                author_orcid = authorship.get('author', {}).get('orcid', '')
                
                if author_name:
                    authors.append(author_name)
                    if author_orcid:
                        # Extract ORCID ID from URL
                        orcid_id = author_orcid.replace('https://orcid.org/', '')
                        author_orcids.append(orcid_id)

            pub_date = work.get('publication_date', '')

            # Get best open-access PDF
            pdf_url = None
            oa = work.get('open_access', {})
            if oa.get('is_oa') and oa.get('oa_url'):
                pdf_url = oa['oa_url']

            url = work.get('primary_location', {}).get('landing_page_url') or doi or ''

            yield {
                'title': title,
                'abstract': abstract,
                'authors': authors,
                'author_orcids': author_orcids,  # NEW: Include ORCID IDs
                'doi': doi,
                'url': url or f"https://openalex.org/{work.get('id', '')}",
                'pdf_url': pdf_url,
                'publication_date': pub_date,
                'source_repository': 'OpenAlex',
                'is_unilag_author': True,
                'raw_affiliation': 'University of Lagos',
            }

        # Cursor-based pagination for ROR queries only
        if source == 'ror':
            meta = data.get('meta', {})
            next_cursor = meta.get('next_cursor')
            if next_cursor and results:
                next_url = (
                    f"{OPENALEX_BASE}"
                    f"?filter=institutions.ror:{UNILAG_ROR}"
                    f"&select=id,doi,title,abstract_inverted_index,authorships,publication_date,open_access,primary_location"
                    f"&per-page=50"
                    f"&cursor={next_cursor}"
                    f"&mailto=uraas-bot@unilag.edu.ng"
                )
                yield scrapy.Request(url=next_url, callback=self.parse, meta={'source': 'ror'})

    def _reconstruct_abstract(self, inverted_index: dict) -> str:
        """OpenAlex stores abstracts as word→[position] inverted index."""
        if not inverted_index:
            return ''
        word_positions = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))
        word_positions.sort()
        return ' '.join(w for _, w in word_positions)
