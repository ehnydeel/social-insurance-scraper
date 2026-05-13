import tempfile
from pathlib import Path

from src.indexing.fulltext_index import _extract_text


def test_extract_text_html():
    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False, encoding="utf-8") as f:
        f.write("<html><body><h1>Titel</h1><p>Dies ist ein Test.</p></body></html>")
        path = f.name
    try:
        text = _extract_text(path)
        assert "Titel" in text
        assert "Test" in text
    finally:
        Path(path).unlink(missing_ok=True)


def test_extract_text_json():
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False, encoding="utf-8") as f:
        f.write('{"Signatur": "CH_BGer_001", "Kopfzeile": [{"Text": "Bundesgericht Urteil"}], "Sprache": "de"}')
        path = f.name
    try:
        text = _extract_text(path)
        assert "Bundesgericht" in text
        assert "Urteil" in text
    finally:
        Path(path).unlink(missing_ok=True)


def test_extract_text_unsupported_format():
    with tempfile.NamedTemporaryFile(suffix=".xyz", mode="w", delete=False, encoding="utf-8") as f:
        f.write("some data")
        path = f.name
    try:
        text = _extract_text(path)
        assert text == ""
    finally:
        Path(path).unlink(missing_ok=True)


def test_extract_text_empty_html():
    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False, encoding="utf-8") as f:
        f.write("<html></html>")
        path = f.name
    try:
        text = _extract_text(path)
        assert text == ""
    finally:
        Path(path).unlink(missing_ok=True)
