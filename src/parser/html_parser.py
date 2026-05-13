import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

VALID_EXTENSIONS = [
    ".pdf",
    ".xml",
    ".xhtml",
    ".html",
    ".zip",
]

# Pattern for sozialversicherungen.admin.ch download URLs: /de/d/<id>/download
DOWNLOAD_PATH_PATTERN = re.compile(r"^/de/d/\d+/download(\?.*)?$", re.IGNORECASE)


class HtmlParser:
    def parse_documents(self, base_url, html):
        soup = BeautifulSoup(html, "html.parser")
        results = []
        seen_urls = set()

        for link in soup.find_all("a", href=True):
            href = link["href"]

            is_valid = any(
                href.lower().endswith(ext) for ext in VALID_EXTENSIONS
            ) or bool(DOWNLOAD_PATH_PATTERN.match(urlparse(href).path))

            if not is_valid:
                continue

            full_url = urljoin(base_url, href)
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            results.append({
                "url": full_url,
                "title": link.text.strip(),
            })

        return results