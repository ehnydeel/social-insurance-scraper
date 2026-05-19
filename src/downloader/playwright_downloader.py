from pathlib import Path
from typing import Optional, Union
from urllib.parse import urljoin

from playwright.async_api import async_playwright

from src.logger import logger

PLAYWRIGHT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "de-CH,de;q=0.9,en;q=0.8",
}


class PlaywrightDownloader:
    """Downloads documents from JavaScript-rendered (SPA) websites using Playwright."""

    def __init__(self):
        self._browser = None
        self._context = None

    @property
    def context(self):
        return self._context

    async def __aenter__(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        self._context = await self._browser.new_context(
            user_agent=PLAYWRIGHT_HEADERS["User-Agent"],
            locale="de-CH",
            accept_downloads=True,
        )
        return self

    async def __aexit__(self, *args):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def fetch_page_html(self, url: str, timeout: int = 30000) -> Optional[str]:
        """Navigate to a URL, wait for SPA render, return full HTML."""
        page = await self._context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=timeout)
            html = await page.content()
            return html
        except Exception as ex:
            logger.error(f"Playwright fetch failed for {url}: {ex}")
            return None
        finally:
            await page.close()

    async def extract_download_links(self, url: str, timeout: int = 30000) -> list[dict]:
        """Navigate to a URL and extract download links/buttons for documents.

        Returns list of dicts with keys: url, format (html/pdf/xml/doc), title, consolidation_date
        """
        page = await self._context.new_page()
        downloads = []

        try:
            await page.goto(url, wait_until="networkidle", timeout=timeout)

            # Find all buttons/links with download-related attributes
            buttons = await page.query_selector_all("button, a, [role=button]")

            for btn in buttons:
                text = (await btn.inner_text()).strip()
                href = await btn.get_attribute("href") or ""

                if not text and not href:
                    continue

                fmt = self._detect_format(text, href)
                if not fmt:
                    continue

                download_url = href
                if download_url and not download_url.startswith("http"):
                    download_url = urljoin(url, download_url)

                if download_url:
                    downloads.append({
                        "url": download_url,
                        "format": fmt,
                        "title": text,
                    })

            # Also check aria-labels
            for selector in ["[aria-label]", "[title]"]:
                els = await page.query_selector_all(selector)
                for el in els:
                    label = await el.get_attribute("aria-label") or await el.get_attribute("title") or ""
                    fmt = self._detect_format(label, "")
                    if fmt and not any(d["format"] == fmt and d["url"] == "" for d in downloads):
                        href = await el.get_attribute("href") or ""
                        if href:
                            if not href.startswith("http"):
                                href = urljoin(url, href)
                            downloads.append({"url": href, "format": fmt, "title": label})

            return downloads

        except Exception as ex:
            logger.error(f"Playwright extract links failed for {url}: {ex}")
            return downloads
        finally:
            await page.close()

    async def download_file(self, url: str, target_dir: Union[str, Path], timeout: int = 60000) -> Optional[Path]:
        """Download a file via the browser context (handles cookies/auth).

        Returns the path to the saved file, or None on failure.
        The filename is taken from the server's Content-Disposition header.
        """
        page = await self._context.new_page()
        try:
            async with page.expect_download(timeout=timeout) as download_info:
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                except Exception:
                    pass  # Navigation may be interrupted by download
            download = await download_info.value
            suggested = download.suggested_filename
            target_dir = Path(target_dir)
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / suggested
            await download.save_as(str(target_path))
            return target_path.resolve()
        except Exception as ex:
            logger.error(f"Playwright download failed for {url}: {ex}")
            return None
        finally:
            await page.close()

    async def fetch_binary(self, url: str, timeout: int = 30000) -> Optional[bytes]:
        """Fetch binary content (PDF, DOC, etc.) via browser."""
        page = await self._context.new_page()
        try:
            response = await page.goto(url, wait_until="networkidle", timeout=timeout)
            if response and response.ok:
                body = await response.body()
                return body
            return None
        except Exception as ex:
            logger.error(f"Playwright fetch binary failed for {url}: {ex}")
            return None
        finally:
            await page.close()

    async def click_and_download(
        self,
        page,
        element,
        target_path: Union[str, Path],
        timeout: int = 60000,
    ) -> bool:
        """Click an element on a live page and capture the triggered download.

        Args:
            page: A Playwright Page instance (must remain open).
            element: A CSS selector string or a Playwright Locator.
            target_path: Where to save the downloaded file.
            timeout: Max time to wait for the download to start.
        """
        try:
            async with page.expect_download(timeout=timeout) as download_info:
                if isinstance(element, str):
                    await page.click(element, timeout=timeout)
                else:
                    await element.click(timeout=timeout)
            download = await download_info.value
            target = Path(target_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            await download.save_as(str(target))
            logger.info(f"Downloaded via click -> {target}")
            return True
        except Exception as ex:
            logger.error(f"Click download failed: {ex}")
            return False

    @staticmethod
    def _detect_format(text: str, href: str) -> Optional[str]:
        combined = (text + " " + href).lower()
        if ".xml" in combined or combined.startswith("xml") or text.strip().upper() == "XML":
            return "xml"
        if ".doc" in combined or combined.startswith("doc") or text.strip().upper() in ("DOC", "DOCX"):
            return "doc"
        if ".pdf" in combined or combined.startswith("pdf") or text.strip().upper() == "PDF":
            return "pdf"
        if ".html" in href.lower() or text.strip().upper() == "HTML":
            return "html"
        return None
