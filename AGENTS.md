# AGENTS.md — Project Guidelines

## Python Development

- **Target Python Version**: 3.11+
- **Use type hints everywhere** with PEP 484 syntax; mark uncertain/evolving types with `typing.Any` sparingly
- **Use `uv`** for dependency management and virtual environment creation
- **Follow PEP 8** as baseline; line length: 88 chars (black-compatible)
- **No flake8**, use `ruff` for linting: `ruff check .`
- **Use `black`** for formatting: `black .`
- **Use `pyright`** for type checking: `pyright src/`

## Project Structure

```
social-insurance-scraper/
├── main.py              # Application entry point
├── src/                  # Application source code
│   ├── models.py         # Pydantic/SQLAlchemy data models
│   ├── config.py         # Configuration loader
│   ├── database.py       # Database connection/pool
│   ├── crawler/          # Web crawlers for various sources
│   ├── parser/           # XML/HTML/JSON parsers
│   ├── downloader/       # File download utilities
│   ├── indexer/          # Fulltext indexing
│   ├── storage/          # File/version management
│   └── scheduler/        # Cron/scheduled execution
├── data/                 # Scraped/processed data
├── logs/                 # Application logs
├── config.yaml           # Runtime configuration
└── requirements.txt      # Python dependencies
```

## Coding Standards

- **Use async where I/O-bound** (networking, file ops); synchronous elsewhere
- **Prefer pathlib over os.path** for all file operations
- **Use context managers** (`with` statements) for resource management: files, DB sessions, HTTP clients
- **No bare `except`** — catch specific exceptions and log them
- **Configurable log levels** via `src/logger.py`; prefer `logging.getLogger(__name__)` pattern
- **All crawler implementations extend `BaseCrawler`** (see `src/crawler/base_crawler.py`)

## Dependencies

```
# Core requirements
aiohttp>=3.9.0
beautifulsoup4>=4.12.0
lxml>=5.0.0
pydantic>=2.5.0
sqlalchemy>=2.0.0
python-dotenv>=1.0.0
pyyaml>=6.0.0
apscheduler>=3.10.0
```

## CI/CD

- **Pre-commit**: enforce `ruff check .` and `black .`
- **Testing**: pytest for all crawler and parser modules
- **GitHub Actions**: run lint/typecheck/tests on every PR

## Code Review Checklist

- [ ] Type hints on all function signatures
- [ ] No hardcoded credentials or secrets
- [ ] Proper error handling for external API calls
- [ ] Log levels are appropriate (not all `debug`)
- [ ] No unbounded loops or missing timeouts on network requests
- [ ] Configurable via `config.yaml`, not inline values

## Change Protocol

- **Always ask before making file changes.** Present findings and suggested fixes first.
- **Do not modify the codebase without explicit user approval.**
- **Present fixes grouped by severity** (blocker → runtime → style) with file/line references.
- **Let the user decide which fixes to apply.**
