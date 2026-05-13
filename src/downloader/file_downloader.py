import time

import requests

from src.logger import logger

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "de-CH,de;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
}

MAX_RETRIES = 3
RETRY_DELAY = 1.0


class FileDownloader:
    def download(self, url):
        last_exception = None

        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(url, headers=HEADERS, timeout=120)

                if response.status_code == 200:
                    return response.content

                logger.error(f"HTTP Error: {response.status_code}: {url}")
                return None

            except requests.ConnectionError as ex:
                last_exception = ex
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_DELAY * (2 ** attempt)
                    logger.warning(
                        f"Connection error (attempt {attempt + 1}/{MAX_RETRIES}) "
                        f"for {url}, retrying in {wait:.0f}s"
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        f"Connection error after {MAX_RETRIES} attempts: {url}"
                    )

            except Exception as ex:
                logger.exception(ex)
                return None

        return None