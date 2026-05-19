import asyncio
import re
from pathlib import Path
from urllib.parse import urlparse

from src.crawler.base_crawler import BaseCrawler
from src.downloader.playwright_downloader import PlaywrightDownloader
from src.parser.html_parser import HtmlParser
from src.storage.file_storage import FileStorage
from src.storage.version_manager import VersionManager
from src.utils import sha256_content
from src.config import CONFIG
from src.indexing.fulltext_index import index_document
from src.logger import logger

IGNORED_DOMAINS = {
    "www.admin.ch",
    "www.edi.admin.ch",
    "www.disclaimer.admin.ch",
    "www.bsv.admin.ch",
    "www.youtube.com",
    "www.linkedin.com",
    "abo.news.admin.ch",
}

# Download URLs from sozialversicherungen.admin.ch platform
DOWNLOAD_PATH_PATTERN = re.compile(r"^/de/d/\d+/download(\?.*)?$", re.IGNORECASE)


class AHVIVCrawler(BaseCrawler):

    def __init__(self):
        self.parser = HtmlParser()
        self.storage = FileStorage()
        self.version_manager = VersionManager()

    def run(self):
        if not CONFIG.get("sources", {}).get("ahv_iv", {}).get("enabled", True):
            logger.info("AHV/IV Crawler disabled via config")
            return
        asyncio.run(self._run_async())

    async def _run_async(self):
        async with PlaywrightDownloader() as pw:
            sources = CONFIG.get("sources", {}).get("ahv_iv", {})
            for group_key, entries in sources.items():
                if group_key == "enabled":
                    continue
                if not isinstance(entries, list):
                    continue
                await self._crawl_section(pw, entries, group_key)

    async def _crawl_section(self, pw: PlaywrightDownloader, entries: list, group_key: str) -> None:
        for entry in entries:
            url = entry["url"]
            document_type = entry.get("document_type", "Erläuterungen")
            category = entry.get("category", "ahv_iv")
            subcategory = entry.get("subcategory", group_key)

            html = await pw.fetch_page_html(url, timeout=60000)
            if not html:
                logger.warning(f"Empty page for {url}")
                continue

            all_links = self.parser.parse_documents(url, html)
            documents = [d for d in all_links if self._is_document_url(d["url"])]

            logger.info(f"Found {len(documents)} document(s) in {subcategory}: {entry.get('name')}")

            for doc in documents:
                try:
                    await self._process_document(pw, document_type, category, subcategory, doc)
                except Exception as ex:
                    logger.warning(f"Failed to download {doc['url']}: {ex}")

    @staticmethod
    def _is_document_url(url: str) -> bool:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return domain not in IGNORED_DOMAINS

    async def _process_document(
        self, pw: PlaywrightDownloader, document_type: str, category: str, subcategory: str, doc: dict
    ) -> None:
        url = doc["url"]

        tmp_dir = Path("data") / "tmp" / "downloads"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        downloaded_path = await pw.download_file(url, tmp_dir, timeout=120000)
        if not downloaded_path:
            logger.warning(f"Download failed: {url}")
            return

        content = downloaded_path.read_bytes()
        sha256 = sha256_content(content)

        if self.version_manager.exists(sha256):
            logger.info(f"Already existing: {url}")
            downloaded_path.unlink(missing_ok=True)
            return

        filename = downloaded_path.name
        current_path = self.storage.build_path(document_type, category, filename)

        self.storage.save(current_path, content)

        ext = downloaded_path.suffix

        self.version_manager.add(
            title=doc["title"] or filename,
            category=category,
            file_format=ext,
            sha256=sha256,
            local_path=current_path,
            source_url=url,
        )

        index_document(current_path, doc["title"] or filename, category, ext)

        logger.info(f"Saved: {filename}")
