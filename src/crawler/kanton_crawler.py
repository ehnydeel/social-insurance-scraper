import asyncio
from pathlib import Path
from urllib.parse import urljoin, urlparse

from src.crawler.base_crawler import BaseCrawler
from src.downloader.playwright_downloader import PlaywrightDownloader
from src.storage.file_storage import FileStorage
from src.storage.version_manager import VersionManager
from src.utils import sha256_content
from src.config import CONFIG
from src.indexing.fulltext_index import index_document
from src.logger import logger


class KantonCrawler(BaseCrawler):
    def __init__(self):
        self.storage = FileStorage()
        self.version_manager = VersionManager()
        self.sources = CONFIG.get("sources", {}).get("kanton", [])

    def run(self):
        if not CONFIG.get("sources", {}).get("kanton", {}).get("enabled", True):
            logger.info("Kanton Crawler disabled via config")
            return
        asyncio.run(self._run_async())

    async def _run_async(self):
        async with PlaywrightDownloader() as pw:
            for source in self.sources:
                canton = source.get("abbreviation")
                url = source.get("url")
                if not canton or not url:
                    logger.warning(f"Kanton source missing abbreviation or url: {source}")
                    continue
                try:
                    await self._canton_crawl_page(pw, canton, url)
                except Exception as ex:
                    logger.exception(f"Failed to crawl {url}: {ex}")

    async def _canton_crawl_page(self, pw: PlaywrightDownloader, canton: str, url: str) -> None:
        logger.info(f"Crawling kantonal laws for {canton} from {url}")
        html = await pw.fetch_page_html(url, timeout=60000)
        if not html:
            logger.warning(f"Empty page for {url}")
            return

        # Parse HTML for PDF links
        from src.parser.html_parser import HtmlParser
        parser = HtmlParser()
        all_links = parser.parse_documents(url, html)
        pdf_links = [d for d in all_links if d.get("url", "").lower().endswith('.pdf')]

        logger.info(f"Found {len(pdf_links)} PDF document(s) for {canton}")

        for doc in pdf_links:
            try:
                await self._process_document(pw, canton, doc)
            except Exception as ex:
                logger.warning(f"Failed to download {doc.get('url')}: {ex}")

    async def _process_document(
        self, pw: PlaywrightDownloader, canton: str, doc: dict
    ) -> None:
        url = doc["url"]
        title = doc.get("title", "")

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
        # Use document_type = "Kanton", source = canton abbreviation
        current_path = self.storage.build_path("Kanton", canton, filename)

        self.storage.save(current_path, content)

        ext = downloaded_path.suffix

        self.version_manager.add(
            title=title or filename,
            category="kanton",
            file_format=ext,
            sha256=sha256,
            local_path=current_path,
            source_url=url,
        )

        # Index the document for full-text search
        index_document(current_path, title or filename, "kanton", ext)

        logger.info(f"Saved: {filename}")
        downloaded_path.unlink(missing_ok=True)