from src.parser.html_parser import HtmlParser


def test_parse_documents_finds_pdf_links():
    parser = HtmlParser()
    html = """
    <html><body>
      <a href="/documents/test.pdf">Test PDF</a>
      <a href="https://example.com/doc.xml">Test XML</a>
      <a href="/page.html">Test HTML</a>
      <a href="https://other.ch/file.zip">ZIP</a>
    </body></html>
    """
    results = parser.parse_documents("https://www.bsv.admin.ch/base/", html)
    urls = [r["url"] for r in results]
    assert "https://www.bsv.admin.ch/documents/test.pdf" in urls
    assert "https://example.com/doc.xml" in urls
    assert "https://www.bsv.admin.ch/page.html" in urls
    assert "https://other.ch/file.zip" in urls


def test_parse_documents_ignores_non_document_links():
    parser = HtmlParser()
    html = """
    <html><body>
      <a href="/about">About</a>
      <a href="/contact.html">Contact</a>
    </body></html>
    """
    results = parser.parse_documents("https://example.com/", html)
    assert len(results) == 1
    assert results[0]["url"] == "https://example.com/contact.html"


def test_parse_documents_empty_page():
    parser = HtmlParser()
    results = parser.parse_documents("https://example.com/", "<html></html>")
    assert results == []
