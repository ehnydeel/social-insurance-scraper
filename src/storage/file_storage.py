import os
from datetime import datetime
from pathlib import Path

class FileStorage:

    def build_path(
            self,
            document_type: str,
            source: str,
            filename: str
    ) -> str:
        base = Path("data") / document_type / source
        base.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime('%Y%m%d')
        # Insert date before the file extension, or at the end if no extension
        if '.' in filename:
            name_part, ext_part = filename.rsplit('.', 1)
            dated_filename = f"{date_str}-{source}-{name_part}.{ext_part}"
        else:
            dated_filename = f"{date_str}-{source}-{filename}"
        return str(base / dated_filename)

    def save(self, path: str, content: bytes) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)