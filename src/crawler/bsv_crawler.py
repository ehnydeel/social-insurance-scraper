import os
import time
from urllib.parse import urlparse

import requests

from src.crawler.base_crawler import BaseCrawler
from src.downloader.file_downloader import HEADERS
from src.parser.html_parser import HtmlParser
from src.downloader.file_downloader import FileDownloader
from src.storage.file_storage import FileStorage
from src.storage.version_manager import VersionManager
from src.utils import sha256_content
from src.config import CONFIG
from src.logger import logger

BSV_TARGET_DOMAINS = {
    "www.bsv.admin.ch",
    "bsv.admin.ch",
}


class BSVCrawler(BaseCrawler):
    def __init__(self):
        self.parser = HtmlParser()
        self.downloader = FileDownloader()
        self.storage = FileStorage()
        self.version_manager = VersionManager()
        self.sources = CONFIG.get("sources", {}).get("bsv", {}).get("gesetze", [])

    def run(self):
        if not CONFIG.get("sources", {}).get("bsv", {}).get("enabled", True):
            logger.info("BSV Crawler disabled via config")
            return

        logger.info("BSV Crawl started.")

        for src in self.sources:
            category = src.get("category", "bsv")
            subcategory = src.get("subcategory", "allgemein")
            url = src["url"]

            try:
                response = requests.get(url, headers=HEADERS, timeout=60)

                all_links = self.parser.parse_documents(url, response.text)
                documents = [
                    d for d in all_links
                    if self._is_document_url(d["url"])
                ]

                for doc in documents:
                    self.process_document(
                        category,
                        subcategory,
                        doc
                    )
                    time.sleep(0.5)
            except Exception as ex:
                logger.exception(ex)

    @staticmethod
    def _is_document_url(url: str) -> bool:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return domain in BSV_TARGET_DOMAINS

    def process_document(
            self,
            category: str,
            subcategory: str,
            doc: dict
    ) -> None:
        content = self.downloader.download(doc["url"])

        if not content:
            return

        sha256 = sha256_content(content)

        if self.version_manager.exists(sha256):
            logger.info(
                f"Already existing: {doc['url']}"
            )
            return

        filename = os.path.basename(
            urlparse(doc["url"]).path
        )

        current_path, archive_path = (
            self.storage.build_path(
                category,
                subcategory,
                filename
            )
        )

        self.storage.save(current_path, content)
        self.storage.save(archive_path, content)

        ext = os.path.splitext(filename)[1]

        self.version_manager.add(
            title=doc["title"],
            category=category,
            file_format=ext,
            sha256=sha256,
            local_path=current_path,
            source_url=doc["url"],
        )

        logger.info(
            f"Saved: {filename}"
        )