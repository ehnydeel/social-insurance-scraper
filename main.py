import argparse
import sys
from src.crawler.bsv_crawler import BSVCrawler
from src.crawler.fedlex_crawler import FedlexCrawler
from src.crawler.ahv_iv_crawler import AHVIVCrawler
from src.crawler.bundesgericht_crawler import BundesgerichtCrawler
from src.crawler.kanton_crawler import KantonCrawler
from src.crawler.ak40_crawler import AK40Crawler

def run_all(sources_to_run=None, serve_mode=False):
    # Define crawler mapping
    crawler_map = {
        'bsv': BSVCrawler,
        'ahv_iv': AHVIVCrawler,
        'fedlex': FedlexCrawler,
        'bundesgericht': BundesgerichtCrawler,
        'ahon': KantonCrawler,
        'ak40': AK40Crawler
    }
    
    # Handle serve mode
    if serve_mode:
        from src.scheduler.scheduler import run_scheduler
        run_scheduler()
        return
    
    # Determine which crawlers to instantiate
    if sources_to_run is None or 'all' in sources_to_run:
        selected_crawlers = crawler_map.values()
    else:
        # Filter to only include valid sources
        selected_crawlers = []
        for source in sources_to_run:
            if source in crawler_map:
                selected_crawlers.append(crawler_map[source])
            else:
                print(f"Warning: Unknown source '{source}' ignored. Valid sources are: {', '.join(crawler_map.keys())}")
    
    # If no valid sources selected, run all as fallback
    if not selected_crawlers:
        selected_crawlers = crawler_map.values()
    
    # Instantiate and run selected crawlers
    crawlers = [cls() for cls in selected_crawlers]
    for crawler in crawlers:
        crawler.run()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Social Insurance Scraper - Download and archive Swiss social insurance documents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python main.py                           # Run all sources
  python main.py -s bsv,fedlex             # Run only BSV and Fedlex sources
  python main.py --sources ahv_iv,ak40     # Run AHV/IV and AK40 sources
  python main.py --serve                   # Run continuously using scheduler
  python main.py --help                    # Show this help message
        '''
    )
    
    parser.add_argument(
        '--sources', '-s',
        type=str,
        help='Comma-separated list of sources to run. Available sources: bsv, ahv_iv, fedlex, bundesgericht, ahon, ak40, all (default: all)'
    )
    
    parser.add_argument(
        '--serve',
        action='store_true',
        help='Run the application continuously using the internal scheduler'
    )
    
    args = parser.parse_args()
    
    # Parse sources argument
    sources_to_run = None
    if args.sources:
        sources_to_run = [s.strip().lower() for s in args.sources.split(',')]
    
    run_all(sources_to_run=sources_to_run, serve_mode=args.serve)
