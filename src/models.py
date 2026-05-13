from dataclasses import dataclass

@dataclass
class Document:
    title: str
    category: str
    url: str
    format: str
    sha256: str
    local_path: str
    source: str
