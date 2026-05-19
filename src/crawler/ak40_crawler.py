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


class AK40Crawler(BaseCrawler):
    def __init__(self):
        self.storage = FileStorage()
        self.version_manager = VersionManager()
        self.config = CONFIG.get("sources", {}).get("ak40", {})
        self.base_url = self.config.get("base_url", "https://www.ak40.ch")
        self.versicherungsarten = self.config.get("versicherungsarten", [])

    def run(self):
        if not self.config.get("enabled", True):
            logger.info("AK40 Crawler disabled via config")
            return
        asyncio.run(self._run_async())

    async def _run_async(self):
        async with PlaywrightDownloader() as pw:
            # Process both formulares and merkblaetter pages
            pages_to_process = [
                ("/public/formulare.php?langId=1&folder=314&mainId=314", "Formulare"),
                ("/public/merkblaetter.php?langId=1&folder=315&mainId=315", "Merkblätter")
            ]
            
            for page_path, page_type in pages_to_process:
                url = urljoin(self.base_url, page_path)
                try:
                    await self._process_ak40_page(pw, url, page_type)
                except Exception as ex:
                    logger.exception(f"Failed to process {page_type} page {url}: {ex}")

    async def _process_ak40_page(self, pw: PlaywrightDownloader, url: str, page_type: str) -> None:
        logger.info(f"Processing AK40 {page_type} from {url}")
        html = await pw.fetch_page_html(url, timeout=60000)
        if not html:
            logger.warning(f"Empty page for {url}")
            return

        # For simplicity, we'll extract all PDF links and then try to categorize them
        # A more sophisticated approach would parse sections first
        from src.parser.html_parser import HtmlParser
        parser = HtmlParser()
        all_links = parser.parse_documents(url, html)
        
        # Filter for PDF documents (including wrapper links that serve PDFs)
        pdf_docs = []
        for doc in all_links:
            doc_url = doc.get("url", "").lower()
            # Direct PDF links
            if doc_url.endswith('.pdf'):
                pdf_docs.append(doc)
            # Wrapper links that serve PDFs (based on observed site structure)
            elif "mimefile.php" in doc_url and "tnk=docu" in doc_url:
                pdf_docs.append(doc)
                
        logger.info(f"Found {len(pdf_docs)} PDF document(s) in AK40 {page_type}")

        for doc in pdf_docs:
            try:
                await self._process_ak40_document(pw, doc)
            except Exception as ex:
                logger.warning(f"Failed to download {doc.get('url')}: {ex}")

    async def _process_ak40_document(
        self, pw: PlaywrightDownloader, doc: dict
    ) -> None:
        url = doc["url"]
        title = doc.get("title", "")

        # Make URL absolute if needed
        if not url.startswith(('http://', 'https://')):
            url = urljoin(self.base_url, url)

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
        # Try to determine insurance type from title or URL
        versicherungs_kurz = self._extract_versicherungs_kurz(title, url)
        
        # Use document_type = "AK40", source = versicherungs abbreviation
        current_path = self.storage.build_path("AK40", versicherungs_kurz, filename)

        self.storage.save(current_path, content)

        ext = downloaded_path.suffix

        self.version_manager.add(
            title=title or filename,
            category="ak40",
            file_format=ext,
            sha256=sha256,
            local_path=current_path,
            source_url=url,
        )

        # Index the document for full-text search
        index_document(current_path, title or filename, "ak40", ext)

        logger.info(f"Saved: {filename} (category: {versicherungs_kurz})")
        downloaded_path.unlink(missing_ok=True)

    def _extract_versicherungs_kurz(self, title: str, url: str) -> str:
        """
        Extract the insurance type abbreviation from title or URL.
        Falls back to 'SONSTIG' if not found.
        """
        # Combine title and URL for searching
        text_to_search = f"{title} {url}".upper()
        
        # Map of keywords to abbreviations based on AK40 site structure
        versicherungs_mapping = {
            "FAMILIENZULAGEN": "FZ",
            "KINDER- UND AUSBILDUNGSZULAGEN": "FZ",
            "AHV": "AHV",
            "ALTERS- UND HINTERLASSENENVERSICHERUNG": "AHV",
            "IV": "IV",
            "INVALIDENVERSICHERUNG": "IV",
            "EO": "EO",
            "ERWERBSERSATZ": "EO",
            "MILIT�R": "EO",
            "ZIVILDIENST": "EO",
            "MSE": "MSE",
            "MUTTERSCHAFTSENTSCH�DIGUNG": "MSE",
            "MUTTERSCHAFTSENTGELD": "MSE",
            "VSE": "VSE",
            "VATERSCHAFTSENTSCH�DIGUNG": "VSE",
            "VATERSCHAFTSENTGELD": "VSE",
            "EL": "EL",
            "ERG�NZUNGSLEISTUNGEN": "EL"
        }
        
        # Sort keywords by length (descending) to match longer phrases first
        sorted_keywords = sorted(versicherungs_mapping.keys(), key=len, reverse=True)
        
        # Check for matches in the text
        for keyword in sorted_keywords:
            if keyword in text_to_search:
                return versicherungs_mapping[keyword]
                
        # Default fallback
        return "SONSTIG"