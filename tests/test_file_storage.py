import tempfile
from pathlib import Path
from datetime import datetime

from src.storage.file_storage import FileStorage


def test_build_path_returns_formatted_path():
    storage = FileStorage()
    document_type = "Gesetze"
    source = "bsv"
    filename = "dummy.pdf"

    path = storage.build_path(document_type, source, filename)
    assert path is not None
    # Normalize path separators for cross-platform compatibility
    normalized_path = path.replace("\\", "/")
    assert "data/Gesetze/bsv/" in normalized_path
    assert "2026" in path  # Contains current year
    assert "bsv-dummy.pdf" in path or "dummy.pdf" in path


def test_save_creates_file():
    storage = FileStorage()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "nested" / "file.pdf"
        content = b"pdf content here"
        storage.save(str(path), content)
        assert path.read_bytes() == content


def test_save_creates_parent_dirs():
    storage = FileStorage()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "a" / "b" / "c" / "doc.xml"
        storage.save(str(path), b"xml")
        assert path.exists()
