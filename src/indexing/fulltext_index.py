import json
from pathlib import Path

from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID, STORED
from whoosh.qparser import QueryParser

from bs4 import BeautifulSoup
import fitz  # pymupdf

INDEX_DIR = Path("data") / "metadata" / "whoosh_index"

schema = Schema(
    title=TEXT(stored=True),
    content=TEXT(stored=True),
    path=ID(stored=True),
    category=ID(stored=True),
    file_format=ID(stored=True),
)


def _ensure_index():
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    if not (INDEX_DIR / "MAIN_WRITELOCK").exists() and not list(INDEX_DIR.glob("*.seg")):
        create_in(str(INDEX_DIR), schema)
    return open_dir(str(INDEX_DIR))


def _extract_text(file_path: str) -> str:
    path = Path(file_path)
    ext = path.suffix.lower()
    try:
        if ext == ".pdf":
            doc = fitz.open(file_path)
            return "".join(page.get_text() for page in doc)
        elif ext == ".html":
            soup = BeautifulSoup(path.read_text("utf-8", errors="replace"), "html.parser")
            return soup.get_text(separator=" ", strip=True)
        elif ext == ".json":
            data = json.loads(path.read_text("utf-8", errors="replace"))
            parts = []
            if isinstance(data, dict):
                for key in ("Kopfzeile", "Meta", "Abstract", "Sprache", "Signatur"):
                    val = data.get(key)
                    if val:
                        if isinstance(val, list):
                            for item in val:
                                if isinstance(item, dict):
                                    parts.append(item.get("Text", ""))
                                else:
                                    parts.append(str(item))
                        elif isinstance(val, str):
                            parts.append(val)
                        else:
                            parts.append(str(val))
            return " ".join(parts)
        elif ext == ".xml":
            soup = BeautifulSoup(path.read_text("utf-8", errors="replace"), "xml")
            return soup.get_text(separator=" ", strip=True)
    except Exception:
        pass
    return ""


def index_document(file_path: str, title: str, category: str, file_format: str) -> None:
    idx = _ensure_index()
    text = _extract_text(file_path)
    text = text[:50000]

    writer = idx.writer()
    writer.add_document(
        title=title,
        content=text,
        path=file_path,
        category=category,
        file_format=file_format,
    )
    writer.commit()


def search(query_str: str, limit: int = 20) -> list[dict]:
    idx = _ensure_index()
    parser = QueryParser("content", schema)
    query = parser.parse(query_str)

    with idx.searcher() as searcher:
        results = searcher.search(query, limit=limit)
        return [
            {
                "title": r["title"],
                "path": r["path"],
                "category": r["category"],
                "score": r.score,
                "snippet": r.highlights("content"),
            }
            for r in results
        ]
