from src.crawler.base_crawler import BaseCrawler
from src.logger import logger

class BundesgerichtCrawler(BaseCrawler):

    def run(self):

        logger.info(
            f"Bundesgericht Crawler started"
        )

        # TODO
        # Gerichtsentscheide