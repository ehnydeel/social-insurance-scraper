import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.crawler.ak40_crawler import AK40Crawler


def test_ak40_crawler_initialization():
    """Test that AK40Crawler initializes correctly"""
    crawler = AK40Crawler()
    assert crawler.storage is not None
    assert crawler.version_manager is not None
    assert crawler.config is not None


def test_extract_versicherungs_kurz_from_title():
    """Test extracting insurance type from document title"""
    crawler = AK40Crawler()
    
    # Test cases for different insurance types
    test_cases = [
        ("Antrag auf Kinder- und Ausbildungszulagen", "FZ"),
        ("AHV-Rentenanmeldung", "AHV"),
        ("Invalidenversicherung Anmeldung", "IV"),
        ("Erwerbsersatz bei Milit�rdienst", "EO"),
        ("Mutterschaftsentsch�digung Antrag", "MSE"),
        ("Vaterschaftsentsch�digung Formular", "VSE"),
        ("Erg�nzungsleistungen Gesuch", "EL"),
        ("Unbekanntes Dokument ohne Zuordnung", "SONSTIG")
    ]
    
    for title, expected in test_cases:
        result = crawler._extract_versicherungs_kurz(title, "")
        assert result == expected, f"Failed for title: {title}"


def test_extract_versicherungs_kurz_from_url():
    """Test extracting insurance type from URL"""
    crawler = AK40Crawler()
    
    # Test cases with URLs containing insurance type indicators
    test_cases = [
        ("https://www.ak40.ch/ahv/formular.pdf", "AHV"),
        ("https://www.ak40.ch/iv/antrag.doc", "IV"),
        ("https://www.ak40.ch/eo/militaer.pdf", "EO"),
        ("https://www.ak40.ch/unknown/file.pdf", "SONSTIG")
    ]
    
    for url, expected in test_cases:
        result = crawler._extract_versicherungs_kurz("", url)
        assert result == expected, f"Failed for URL: {url}"


def test_build_path_integration():
    """Test that the crawler works with FileStorage to build correct paths"""
    crawler = AK40Crawler()
    
    # Mock the storage to avoid actual file operations
    with patch.object(crawler.storage, 'build_path') as mock_build_path:
        mock_build_path.return_value = "/fake/path/20260519-ak40-fz-test.pdf"
        
        # Call build_path with AK40 parameters
        result = crawler.storage.build_path("AK40", "FZ", "test.pdf")
        
        # Verify it was called with correct parameters
        mock_build_path.assert_called_once_with("AK40", "FZ", "test.pdf")
        assert result == "/fake/path/20260519-ak40-fz-test.pdf"


if __name__ == "__main__":
    test_ak40_crawler_initialization()
    test_extract_versicherungs_kurz_from_title()
    test_extract_versicherungs_kurz_from_url()
    test_build_path_integration()
    print("All AK40 crawler tests passed!")