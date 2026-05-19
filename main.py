from src.crawler.bsv_crawler import BSVCrawler
from src.crawler.fedlex_crawler import FedlexCrawler
from src.crawler.ahv_iv_crawler import AHVIVCrawler
from src.crawler.bundesgericht_crawler import BundesgerichtCrawler
from src.crawler.kanton_crawler import KantonCrawler

def run_all():
    crawlers = [
        BSVCrawler(),
        FedlexCrawler(),
        AHVIVCrawler(),
        BundesgerichtCrawler(),
        KantonCrawler()
    ]

    for crawler in crawlers:
        crawler.run()

if __name__ == '__main__':
    run_all()
