import asyncio
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


class FedlexCrawler(BaseCrawler):

    def __init__(self):
        self.storage = FileStorage()
        self.version_manager = VersionManager()
        self.sources = CONFIG.get("sources", {}).get("fedlex", {}).get("sr_gesetze", [])

    def run(self):
        if not CONFIG.get("sources", {}).get("fedlex", {}).get("enabled", True):
            logger.info("Fedlex Crawler disabled via config")
            return
        asyncio.run(self._run_async())

    async def _run_async(self):
        async with PlaywrightDownloader() as pw:
            for src in self.sources:
                name = src["name"]
                url = src["url"]
                if "admin.ch/opc" in url:
                    logger.info(f"Skipping OPC URL (blocked): {name} ({url})")
                    continue
                try:
                    await self._crawl_fedlex_page(pw, name, url)
                except Exception as ex:
                    logger.exception(f"Failed to crawl {name} ({url}): {ex}")

    async def _crawl_fedlex_page(self, pw: PlaywrightDownloader, name: str, url: str) -> None:
        page = await pw.context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(3000)

            await self._dismiss_cookie_banner(page)

            version_dates = await self._find_version_dates(page)
            if not version_dates:
                logger.info(f"No consolidation versions found for {name}, using fallback")
                await self._fallback_download(pw, page, name, url)
                return

            logger.info(f"Found {len(version_dates)} version(s) for {name}: {version_dates}")

            for i, ver_date in enumerate(version_dates):
                try:
                    await self._process_version(page, pw, name, ver_date, i)
                except Exception as ex:
                    logger.warning(f"Failed version {ver_date} for {name}: {ex}")
                    continue
        finally:
            await page.close()

    @staticmethod
    async def _dismiss_cookie_banner(page) -> None:
        try:
            await page.evaluate("""
                () => {
                    const btns = document.querySelectorAll('button');
                    for (const btn of btns) {
                        const t = btn.textContent.trim().toLowerCase();
                        if (t.includes('akzeptieren') || t.includes('accept') || t.includes('zustimmen')) {
                            btn.click();
                            break;
                        }
                    }
                }
            """)
        except Exception:
            pass

    @staticmethod
    async def _find_version_dates(page) -> list[str]:
        return await page.evaluate("""
            () => {
                const dates = new Set();
                document.querySelectorAll('a[href*="filestore"]').forEach(el => {
                    const href = el.getAttribute('href');
                    const m = href.match(/\\/(\\d{8})\\//);
                    if (m) dates.add(m[1]);
                });
                return Array.from(dates).sort().reverse();
            }
        """)

    async def _process_version(
        self, page, pw: PlaywrightDownloader, name: str, ver_date: str, version_index: int
    ) -> None:
        logger.info(f"Processing {name} version {ver_date} (#{version_index})")

        # Use positional indexing: each version has XML a, DOC a, PDF btn, HTML btn at same index
        xml_links = page.locator('a[href*="filestore"][href*="/xml/"]')
        doc_links = page.locator('a[href*="filestore"][href*="/doc"]')
        pdf_btns = page.locator('button:has-text("PDF")')
        html_btns = page.locator('button:has-text("HTML")')

        # XML: extract href and download
        xml_href = await xml_links.nth(version_index).get_attribute("href")
        if xml_href:
            url = xml_href if xml_href.startswith("http") else urljoin("https://www.fedlex.admin.ch", xml_href)
            await self._download_direct(pw, name, ver_date, "xml", url)

        # DOC: extract href and download
        doc_href = await doc_links.nth(version_index).get_attribute("href")
        if doc_href:
            url = doc_href if doc_href.startswith("http") else urljoin("https://www.fedlex.admin.ch", doc_href)
            await self._download_direct(pw, name, ver_date, "doc", url)

        # PDF: click button to download
        pdf_count = await pdf_btns.count()
        if version_index < pdf_count:
            btn = pdf_btns.nth(version_index)
            if await btn.is_visible():
                tmp_dir = Path("data") / "tmp" / "downloads"
                tmp_dir.mkdir(parents=True, exist_ok=True)
                tmp_path = tmp_dir / f"{name}_{ver_date}_pdf"
                success = await pw.click_and_download(page, btn, str(tmp_path), timeout=60000)
                if success:
                    content = Path(tmp_path).read_bytes()
                    self._save_file(content, name, ver_date, "pdf", page.url)
                    Path(tmp_path).unlink(missing_ok=True)
                else:
                    logger.warning(f"PDF click download failed for {name} {ver_date}")

        # HTML: click button, capture navigation or download
        html_count = await html_btns.count()
        if version_index < html_count:
            btn = html_btns.nth(version_index)
            if await btn.is_visible():
                try:
                    async with page.expect_navigation(timeout=15000):
                        await btn.click(timeout=10000)
                    html_content = await page.content()
                    self._save_file(html_content.encode("utf-8"), name, ver_date, "html", page.url)
                    await page.go_back(timeout=30000)
                    await page.wait_for_timeout(1000)
                except Exception:
                    logger.debug(f"HTML click did not navigate for {name} {ver_date}")

    async def _download_direct(
        self, pw: PlaywrightDownloader, name: str, ver_date: str, fmt: str, url: str
    ) -> None:
        if fmt == "doc":
            # DOC filestore URLs trigger a browser download, use download_file
            tmp_dir = Path("data") / "tmp" / "downloads"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            tmp_path = tmp_dir / f"{name}_{ver_date}_{fmt}"
            success = await pw.download_file(url, str(tmp_path), timeout=60000)
            if not success:
                logger.warning(f"DOC download failed for {name} {ver_date}")
                return
            content = Path(tmp_path).read_bytes()
            self._save_file(content, name, ver_date, fmt, url)
            Path(tmp_path).unlink(missing_ok=True)
        else:
            content = await pw.fetch_binary(url)
            if not content:
                logger.warning(f"Empty response for {fmt} {name} {ver_date}")
                return
            self._save_file(content, name, ver_date, fmt, url)

    async def _download_via_click(
        self, page, pw: PlaywrightDownloader, name: str, ver_date: str, fmt: str
    ) -> None:
        fmt_upper = fmt.upper()
        candidates = page.locator(f'button:has-text("{fmt_upper}")')
        count = await candidates.count()
        if count == 0:
            candidates = page.locator(f'a:has-text("{fmt_upper}")')
            count = await candidates.count()
        if count == 0:
            logger.debug(f"No clickable {fmt} element for {name} {ver_date}")
            return

        locator = None
        for i in range(count):
            btn = candidates.nth(i)
            if await btn.is_visible():
                locator = btn
                break
        if locator is None:
            logger.debug(f"No visible {fmt} button for {name} {ver_date}")
            return

        if fmt == "html":
            # HTML button likely navigates rather than downloads
            try:
                async with page.expect_navigation(timeout=15000):
                    await locator.click(timeout=10000)
                html_content = await page.content()
                self._save_file(
                    html_content.encode("utf-8"), name, ver_date, fmt, page.url
                )
                return
            except Exception:
                logger.debug(f"HTML {name} {ver_date} click did not navigate, trying download capture")

        tmp_dir = Path("data") / "tmp" / "downloads"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = tmp_dir / f"{name}_{ver_date}_{fmt}"

        success = await pw.click_and_download(page, locator, str(tmp_path), timeout=60000)
        if not success:
            logger.warning(f"Click download failed for {fmt} {name} {ver_date}")
            return

        content = Path(tmp_path).read_bytes()
        self._save_file(content, name, ver_date, fmt, page.url)
        Path(tmp_path).unlink(missing_ok=True)

    def _save_file(self, content: bytes, name: str, ver_date: str, fmt: str, source_url: str) -> None:
        sha256 = sha256_content(content)
        if self.version_manager.exists(sha256):
            logger.info(f"Already existing: {name} {ver_date} .{fmt}")
            return

        filename = f"{name}_{ver_date}.{fmt}"
        current_path, archive_path = self.storage.build_path("fedlex", "sr", filename)

        self.storage.save(current_path, content)
        self.storage.save(archive_path, content)

        self.version_manager.add(
            title=f"{name} ({ver_date})",
            category="fedlex",
            file_format=f".{fmt}",
            sha256=sha256,
            local_path=current_path,
            source_url=source_url,
        )

        index_document(current_path, f"{name} ({ver_date})", "fedlex", f".{fmt}")

        logger.info(f"Saved: {filename}")

    async def _fallback_download(
        self, pw: PlaywrightDownloader, page, name: str, url: str
    ) -> None:
        """Fallback: try to download the current version in all formats via direct URLs."""
        logger.info(f"Fallback download for {name} using {url}")
        await self._process_version(page, pw, name, "current", 0)
