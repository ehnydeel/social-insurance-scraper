import asyncio
import json
from pathlib import Path
from urllib.parse import urljoin

from src.crawler.base_crawler import BaseCrawler
from src.downloader.playwright_downloader import PlaywrightDownloader
from src.storage.file_storage import FileStorage
from src.storage.version_manager import VersionManager
from src.utils import sha256_content
from src.config import CONFIG
from src.indexing.fulltext_index import index_document
from src.logger import logger

INDEX_URL = "https://entscheidsuche.ch/docs/Index/CH_BGer/last"
DOCS_BASE = "https://entscheidsuche.ch/docs/"
CATEGORY = "bundesgericht"
SUBCATEGORY = "entscheide"


class BundesgerichtCrawler(BaseCrawler):

    def __init__(self):
        self.storage = FileStorage()
        self.version_manager = VersionManager()

    def run(self):
        if not CONFIG.get("sources", {}).get("bundesgericht", {}).get("enabled", True):
            logger.info("Bundesgericht Crawler disabled via config")
            return
        asyncio.run(self._run_async())

    async def _run_async(self):
        async with PlaywrightDownloader() as pw:
            index_bytes = await pw.fetch_binary(INDEX_URL, timeout=120000)
            if not index_bytes:
                logger.error("Failed to fetch Bundesgericht index file")
                return

            try:
                index_data = json.loads(index_bytes.decode("utf-8"))
            except json.JSONDecodeError as ex:
                logger.error(f"Failed to parse index JSON: {ex}")
                return

            actions = index_data.get("actions", {})
            new_entries = [
                path for path, status in actions.items()
                if status == "new" and path.endswith(".json")
            ]

            logger.info(f"Found {len(new_entries)} new document(s) from Bundesgericht")

            for entry_path in new_entries:
                try:
                    await self._process_entry(pw, entry_path)
                except Exception as ex:
                    logger.warning(f"Failed to process {entry_path}: {ex}")

    async def _process_entry(self, pw: PlaywrightDownloader, entry_path: str) -> None:
        json_url = urljoin(DOCS_BASE, entry_path)
        json_bytes = await pw.fetch_binary(json_url, timeout=60000)
        if not json_bytes:
            logger.warning(f"Failed to fetch JSON: {json_url}")
            return

        try:
            meta = json.loads(json_bytes.decode("utf-8"))
        except json.JSONDecodeError as ex:
            logger.warning(f"Failed to parse JSON {entry_path}: {ex}")
            return

        signature = meta.get("Signatur", "unknown")
        case_date = meta.get("Datum", "unknown")

        base_name = Path(entry_path).stem

        json_sha = sha256_content(json_bytes)
        if not self.version_manager.exists(json_sha):
            json_filename = f"{base_name}.json"
            self._save_file(json_bytes, CATEGORY, SUBCATEGORY, json_filename, json_sha, json_url)

        html_info = meta.get("HTML")
        if html_info and "Datei" in html_info:
            html_path = html_info["Datei"]
            html_url = urljoin(DOCS_BASE, html_path)
            await self._download_and_save(pw, html_url, f"{base_name}.html")

        pdf_info = meta.get("PDF")
        if pdf_info and "Datei" in pdf_info:
            pdf_path = pdf_info["Datei"]
            pdf_url = urljoin(DOCS_BASE, pdf_path)
            await self._download_and_save(pw, pdf_url, f"{base_name}.pdf")

        logger.info(f"Processed: {signature} ({case_date})")

    async def _download_and_save(
        self, pw: PlaywrightDownloader, url: str, filename: str
    ) -> None:
        tmp_dir = Path("data") / "tmp" / "downloads"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = tmp_dir / filename

        success = await pw.download_file(url, str(tmp_path), timeout=120000)
        if not success:
            logger.warning(f"Download failed: {url}")
            return

        content = Path(tmp_path).read_bytes()
        sha256 = sha256_content(content)

        if self.version_manager.exists(sha256):
            logger.info(f"Already existing: {url}")
            Path(tmp_path).unlink(missing_ok=True)
            return

        self._save_file(content, CATEGORY, SUBCATEGORY, filename, sha256, url)
        Path(tmp_path).unlink(missing_ok=True)

    def _save_file(
        self, content: bytes, category: str, subcategory: str, filename: str,
        sha256: str, source_url: str
    ) -> None:
        ext = Path(filename).suffix
        current_path, archive_path = self.storage.build_path(category, subcategory, filename)

        self.storage.save(current_path, content)
        self.storage.save(archive_path, content)

        self.version_manager.add(
            title=filename,
            category=category,
            file_format=ext,
            sha256=sha256,
            local_path=current_path,
            source_url=source_url,
        )

        index_document(current_path, filename, category, ext)

        logger.info(f"Saved: {filename}")
