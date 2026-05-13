from src.crawler.bsv_crawler import BSVCrawler
from src.crawler.fedlex_crawler import FedlexCrawler
from src.crawler.ahv_iv_crawler import AHVIVCrawler
from src.crawler.bundesgericht_crawler import BundesgerichtCrawler

def run_all():
    crawlers = [
        BSVCrawler(),
        FedlexCrawler(),
        AHVIVCrawler(),
        BundesgerichtCrawler()
    ]

    for crawler in crawlers:
        crawler.run()

if __name__ == '__main__':
    run_all()
