from bs4 import BeautifulSoup
from urllib.parse import urljoin

VALID_EXTENSIONS = [
    ".pdf",
    ".xml",
    ".xhtml",
    ".html",
    ".zip"
]

class HtmlParser:
    def parse_documents(self, base_url, html):
        soup = BeautifulSoup(html, "html.parser")
        results = []

        for link in soup.find_all("a", href=True):
            href = link["href"]

            if any(
                href.lower().endswith(ext)
                for ext in VALID_EXTENSIONS
            ):
                results.append({
                    "url": urljoin(base_url, href),
                    "title": link.text.strip(),
                })
        return results