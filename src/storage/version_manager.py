from src.database import Session
from src.database import DocumentVersion

class VersionManager:

    def exists(self, sha256: str) -> bool:
        session = Session()
        try:
            result = (
                session.query(DocumentVersion)
                .filter_by(sha256=sha256)
                .first()
            )
            return result is not None
        finally:
            session.close()

    def add(
            self,
            title: str,
            category: str,
            file_format: str,
            sha256: str,
            local_path: str,
            source_url: str
    ) -> None:
        session = Session()
        try:
            version = DocumentVersion(
                title=title,
                category=category,
                file_format=file_format,
                sha256=sha256,
                local_path=local_path,
                source_url=source_url
            )
            session.add(version)
            session.commit()
        finally:
            session.close()