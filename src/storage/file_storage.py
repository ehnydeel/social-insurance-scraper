import os
from datetime import datetime
from pathlib import Path

class FileStorage:

    def build_path(
            self,
            category: str,
            subcategory: str,
            filename: str
    ) -> tuple[str, str]:
        base = Path("data") / category / subcategory

        current_path = base / "current"

        archive_path = (
            base / "archive"
            / datetime.now().strftime('%Y-%m-%d')
        )

        current_path.mkdir(parents=True, exist_ok=True)
        archive_path.mkdir(parents=True, exist_ok=True)

        return (
            str(current_path / filename),
            str(archive_path / filename)
        )

    def save(self, path: str, content: bytes) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)