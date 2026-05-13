import os
from urllib.parse import urlparse

import requests

from src.crawler.base_crawler import BaseCrawler
from src.parser.html_parser import HtmlParser
from src.downloader.file_downloader import FileDownloader
from src.storage.file_storage import FileStorage
from src.storage.version_manager import VersionManager
from src.utils import sha256_content
from src.config import CONFIG
from src.logger import logger

IGNORED_DOMAINS = {
    "www.bsv.admin.ch",
    "www.admin.ch",
    "www.edi.admin.ch",
    "www.disclaimer.admin.ch",
    "sozialversicherungen.admin.ch",
    "www.sozialversicherungen.admin.ch",
    "www.youtube.com",
    "www.linkedin.com",
    "abo.news.admin.ch",
}


class AHVIVCrawler(BaseCrawler):

    def __init__(self):
        self.parser = HtmlParser()
        self.downloader = FileDownloader()
        self.storage = FileStorage()
        self.version_manager = VersionManager()

    def run(self):
        if not CONFIG.get("sources", {}).get("ahv_iv", {}).get("enabled", True):
            logger.info("AHV/IV Crawler disabled via config")
            return

        logger.info("AHV/IV Crawler started")

        sources = CONFIG.get("sources", {}).get("ahv_iv", {})
        self._crawl_section(sources.get("wegleitungen", []), "weisungen")
        self._crawl_section(sources.get("kreisschreiben", []), "kreisschreiben")

    def _crawl_section(self, entries: list, subcategory: str) -> None:
        for entry in entries:
            url = entry["url"]
            category = entry.get("category", "ahv_iv")

            try:
                response = requests.get(url, timeout=60)
                all_links = self.parser.parse_documents(url, response.text)
                documents = [
                    d for d in all_links
                    if self._is_document_url(d["url"])
                ]

                for doc in documents:
                    self._process_document(category, subcategory, doc)
            except Exception as ex:
                logger.exception(f"Failed to crawl {url}: {ex}")

    @staticmethod
    def _is_document_url(url: str) -> bool:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return domain not in IGNORED_DOMAINS

    def _process_document(
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
            logger.info(f"Already existing: {doc['url']}")
            return

        filename = os.path.basename(urlparse(doc["url"]).path)
        if not filename:
            filename = f"doc_{sha256[:16]}.pdf"

        current_path, archive_path = self.storage.build_path(
            category, subcategory, filename
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

        logger.info(f"Saved: {filename}")
