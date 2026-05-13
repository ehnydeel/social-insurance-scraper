from pathlib import Path

from loguru import logger

logs_dir = Path(__file__).resolve().parent.parent / "logs"
logs_dir.mkdir(parents=True, exist_ok=True)

logger.add(
    str(logs_dir / "app.log"),
    rotation="10 MB",
    retention="30 days",
    level="INFO"
)