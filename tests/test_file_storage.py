import tempfile
from pathlib import Path
from datetime import datetime

from src.storage.file_storage import FileStorage


def test_build_path_returns_current_and_archive():
    storage = FileStorage()
    base = Path(tempfile.mkdtemp())
    category = "test_cat"
    subcategory = "test_sub"
    filename = "dummy.pdf"

    current, archive = storage.build_path(category, subcategory, filename)
    assert current is not None
    assert archive is not None


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
