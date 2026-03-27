import os
import sys
import argparse

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapy.crawler import CrawlerProcess
from uraas.spiders.sources.arxiv_spider import ArxivSpider
from uraas.spiders.sources.scholar_spider import ScholarSpider
from uraas.spiders.sources.openalex_spider import OpenAlexSpider
from uraas.spiders.sources.faculty_directory_spider import FacultyDirectorySpider

def main(target_count=100):
    """
    Run the URAAS crawler with specified target count.
    
    Args:
        target_count: Number of papers to crawl (default: 100, max: 250)
    """
    # Enforce limits
    target_count = min(max(target_count, 1), 250)
    
    print("=" * 70)
    print("URAAS Advanced IR Harvester - World-Class Edition")
    print("=" * 70)
    print(f"Target: {target_count} validated UNILAG papers")
    print()
    
    process = CrawlerProcess(settings={
        'USER_AGENT': 'URAAS-IR-Harvester/1.0 (University of Lagos institutional repository bot; contact: library@unilag.edu.ng)',
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_DELAY': 2.0,
        'CONCURRENT_REQUESTS': 8,
        'RETRY_ENABLED': True,
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],
        'ITEM_PIPELINES': {
            'uraas.pipelines.affiliation_filter.AffiliationFilterPipeline': 300,
            'uraas.pipelines.unpaywall.UnpaywallPipeline': 350,
            'uraas.pipelines.gap_analysis.GapAnalysisPipeline': 380,
            'uraas.pipelines.database.DatabaseStoragePipeline': 400,
        },
        'LOG_LEVEL': 'INFO',
        'LOG_FORMAT': '%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        'CLOSESPIDER_ITEMCOUNT': target_count
    })

    print("Phase 0: Faculty Directory Seeding")
    print("-" * 70)
    process.crawl(FacultyDirectorySpider)
    
    print("\nPhase 1: Multi-Source Discovery")
    print("-" * 70)
    process.crawl(ArxivSpider)
    process.crawl(ScholarSpider)
    process.crawl(OpenAlexSpider)
    
    from uraas.spiders.sources.crossref_spider import CrossrefSpider
    process.crawl(CrossrefSpider)
    
    print("\nStarting crawl... Press Ctrl+C to stop.")
    print("=" * 70)
    process.start()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='URAAS Crawler - Harvest UNILAG papers')
    parser.add_argument('--target', type=int, default=100, 
                       help='Number of papers to crawl (1-250, default: 100)')
    args = parser.parse_args()
    
    main(target_count=args.target)
