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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SocialInsuranceBot/1.0)"
}

FEDLEX_PDF_QUERY = "?format=pdf"


class FedlexCrawler(BaseCrawler):

    def __init__(self):
        self.parser = HtmlParser()
        self.downloader = FileDownloader()
        self.storage = FileStorage()
        self.version_manager = VersionManager()
        self.sources = CONFIG.get("sources", {}).get("fedlex", {}).get("sr_gesetze", [])

    def run(self):
        if not CONFIG.get("sources", {}).get("fedlex", {}).get("enabled", True):
            logger.info("Fedlex Crawler disabled via config")
            return

        logger.info("Fedlex Crawler started")

        for src in self.sources:
            name = src["name"]
            url = src["url"]

            try:
                if "admin.ch/opc" in url:
                    self._crawl_opc_page(name, url)
                else:
                    self._crawl_fedlex_page(name, url)
            except Exception as ex:
                logger.exception(f"Failed to crawl {name} ({url}): {ex}")

    def _crawl_fedlex_page(self, name: str, url: str) -> None:
        """Fetch a fedlex.admin.ch SR page and look for PDF downloads."""
        logger.info(f"Fetching fedlex page: {name} ({url})")

        try:
            response = requests.get(url, headers=HEADERS, timeout=60)
            if response.status_code != 200:
                logger.warning(f"HTTP {response.status_code} for {url}")

            documents = self.parser.parse_documents(url, response.text)

            if not documents:
                logger.info(f"No PDF links found on fedlex page, trying direct PDF: {name}")
                pdf_url = self._construct_pdf_url(url)
                if pdf_url:
                    self._process_pdf_download(name, pdf_url)

            for doc in documents:
                self._process_document(name, doc)

        except Exception as ex:
            logger.exception(f"Failed to fetch fedlex page {url}: {ex}")

    def _crawl_opc_page(self, name: str, url: str) -> None:
        """Fetch an admin.ch/opc page (standard HTML) and parse for PDFs."""
        logger.info(f"Fetching OPC page: {name} ({url})")

        try:
            response = requests.get(url, headers=HEADERS, timeout=60)

            # Akamai returns 200 with an "Access Denied" HTML body instead of 403
            if response.status_code != 200 or len(response.text) < 1000 or "Access Denied" in response.text:
                logger.warning(f"OPC page blocked (HTTP {response.status_code}) for {name}: {url}")
                return

            documents = self.parser.parse_documents(url, response.text)

            if not documents:
                logger.info(f"No PDF links found on OPC page for {name}")

            for doc in documents:
                self._process_document(name, doc)

        except Exception as ex:
            logger.exception(f"Failed to fetch OPC page {url}: {ex}")

    @staticmethod
    def _construct_pdf_url(url: str) -> str | None:
        """Try to construct a PDF download URL from a fedlex page URL."""
        parsed = urlparse(url)

        if "fedlex.admin.ch" not in parsed.netloc:
            return None

        pdf_url = url.rstrip("/") + FEDLEX_PDF_QUERY
        return pdf_url

    def _process_pdf_download(self, name: str, pdf_url: str) -> None:
        """Try direct PDF download and store if successful."""
        content = self.downloader.download(pdf_url)
        if not content:
            logger.debug(f"No PDF content at {pdf_url}")
            return

        sha256 = sha256_content(content)

        if self.version_manager.exists(sha256):
            logger.info(f"Already existing: {pdf_url}")
            return

        filename = f"{name}.pdf"

        current_path, archive_path = self.storage.build_path(
            "fedlex", "sr", filename
        )

        self.storage.save(current_path, content)
        self.storage.save(archive_path, content)

        self.version_manager.add(
            title=name,
            category="fedlex",
            file_format=".pdf",
            sha256=sha256,
            local_path=current_path,
            source_url=pdf_url,
        )

        logger.info(f"Saved SR document: {name} ({filename})")

    def _process_document(
            self,
            name: str,
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
            filename = f"{name}{os.path.splitext(doc['url'])[1] or '.pdf'}"

        current_path, archive_path = self.storage.build_path(
            "fedlex", "sr", filename
        )

        self.storage.save(current_path, content)
        self.storage.save(archive_path, content)

        ext = os.path.splitext(filename)[1]

        self.version_manager.add(
            title=doc["title"] or name,
            category="fedlex",
            file_format=ext,
            sha256=sha256,
            local_path=current_path,
            source_url=doc["url"],
        )

        logger.info(f"Saved: {filename}")
