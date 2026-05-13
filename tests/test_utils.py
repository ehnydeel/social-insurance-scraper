from src.utils import sha256_content


def test_sha256_content_known_value():
    result = sha256_content(b"hello")
    assert result == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_sha256_content_empty():
    result = sha256_content(b"")
    assert result == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_sha256_content_unicode():
    result = sha256_content("föö".encode("utf-8"))
    assert isinstance(result, str)
    assert len(result) == 64
