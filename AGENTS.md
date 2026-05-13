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
├── main.py                  # Application entry point (run_all: 4 crawlers)
├── src/
│   ├── __init__.py
│   ├── config.py            # YAML config loader
│   ├── database.py          # SQLAlchemy SQLite engine + DocumentVersion model
│   ├── logger.py            # Loguru setup -> logs/app.log
│   ├── models.py            # Document dataclass
│   ├── utils.py             # sha256_content()
│   ├── crawler/
│   │   ├── base_crawler.py         # ABC with abstract run()
│   │   ├── bsv_crawler.py          # BSV page -> PDF download (working)
│   │   ├── fedlex_crawler.py       # Fedlex SR -> XML/DOC/PDF/HTML (working)
│   │   ├── ahv_iv_crawler.py       # Wegleitungen/Kreisschreiben (working)
│   │   └── bundesgericht_crawler.py  # STUB — not implemented
│   ├── parser/
│   │   ├── html_parser.py    # BeautifulSoup link extraction (pdf/xml/html/zip)
│   │   └── xml_parser.py     # lxml wrapper
│   ├── downloader/
│   │   ├── playwright_downloader.py  # Playwright async context manager
│   │   └── file_downloader.py        # requests-based fallback (unused)
│   ├── storage/
│   │   ├── file_storage.py       # data/current/ + data/archive/ paths
│   │   └── version_manager.py    # SHA-256 dedup via SQLAlchemy
│   ├── indexing/
│   │   └── fulltext_index.py     # Whoosh schema — SKELETON (not integrated)
│   └── scheduler/
│       └── scheduler.py          # APScheduler, daily 3am via config
├── data/                   # Scraped output: cats/current/ + archive/YYYY-MM-DD/
├── logs/                   # Log output
├── config.yaml             # Sources, storage, DB, scheduler config
└── requirements.txt        # pip dependencies (11 packages)
```

## Current Project State — Summary for Next AI Session

### Implemented
| Module | Status | Notes |
|--------|--------|-------|
| `main.py` | ✓ Calls 4 crawlers synchronously | `run_all()` iterates `BSVCrawler`, `FedlexCrawler`, `AHVIVCrawler`, `BundesgerichtCrawler` |
| `BSVCrawler` | ✓ Working | Playwright page fetch + HtmlParser + SHA-256 dedup + FileStorage. Sources: AHVG, IVG, FamZG |
| `AHVIVCrawler` | ✓ Working | Same pattern. 5 wegleitungen + 2 kreisschreiben |
| `FedlexCrawler` | ✓ Working | Navigates SPA, dismisses cookie banner, finds version dates, downloads XML/DOC/PDF/HTML per consolidation version. Sources: 10 SR laws |
| `BundesgerichtCrawler` | ✓ Working | Uses entscheidsuche.ch index API (`docs/Index/CH_BGer/last`), SHA-256 dedup + FileStorage. Downloads JSON/HTML/PDF |
| `PlaywrightDownloader` | ✓ Complete | `fetch_page_html`, `download_file`, `fetch_binary`, `click_and_download`, `extract_download_links` |
| `FileStorage` | ✓ Complete | `data/<cat>/<sub>/current/<file>` + `archive/<date>/<file>` |
| `VersionManager` | ✓ Complete | `exists(sha256)` / `add(...)` via SQLAlchemy |
| `fulltext_index.py` | ✓ Working | Whoosh indexing of PDF/HTML/JSON/XML via pymupdf+BeautifulSoup, integrated into all 4 crawlers |
| `scheduler.py` | ✓ Complete | APScheduler, cron from config, calls `run_all()` |

### Config (`config.yaml`)
- 4 source blocks: `bsv`, `ahv_iv`, `fedlex`, `bundesgericht` (each with `enabled: bool`)
- DB path: `./data/metadata/documents.db`
- Scheduler cron: `0 3 * * *` (daily 3am)

### Database
- SQLite via SQLAlchemy, table `document_versions` (id, title, category, format, sha256, local_path, source_url, downloaded_at)
- Auto-created at startup via `init_db()`

### Architecture Pattern
- Each crawler has synchronous `run()` that calls `asyncio.run(self._run_async())`
- `PlaywrightDownloader` is async context manager; each crawler opens one session per run
- No shared state between crawlers — they run sequentially in `main.py`

### Changes Made in Last Session

| Task | Status | Details |
|------|--------|---------|
| `playwright` added to `requirements.txt` | ✅ | Line added after `pyyaml` |
| `BundesgerichtCrawler` implemented | ✅ | Uses entscheidsuche.ch index API (`docs/Index/CH_BGer/last`), downloads JSON/HTML/PDF per case via SHA-256 dedup + FileStorage |
| `fulltext_index.py` rewritten as proper module | ✅ | `_extract_text()` for PDF (fitz), HTML (BeautifulSoup), JSON (metadata fields), XML; `index_document()` called from all 4 crawlers after each file save; `search()` function available |
| Tests written | ✅ | 13 tests: utils (3), html_parser (3), file_storage (3), fulltext_index (4) — all pass |
| CI/CD set up | ✅ | `.pre-commit-config.yaml` (ruff lint+format, pyright), `.github/workflows/ci.yml` (lint+typecheck+test on push/PR to main) |

### Notable Gaps / Next-Session Starting Points
1. **Full-text search integration in `main.py`** — `search()` is implemented but not exposed via CLI/API
2. **Refine `BundesgerichtCrawler`** — currently fetches **all** new docs from the index; could add date/court filters
3. **No coverage reporting** — add `pytest-cov` and enforce a threshold
4. **No Docker setup** — containerised execution for scheduler deployment
5. **Scraper health monitoring** — `entcheidsuche.ch/status` could be polled periodically

## Coding Standards

- **Use async where I/O-bound** (networking, file ops); synchronous elsewhere
- **Prefer pathlib over os.path** for all file operations
- **Use context managers** (`with` statements) for resource management: files, DB sessions, HTTP clients
- **No bare `except`** — catch specific exceptions and log them
- **Use `src.logger` (loguru)** for all logging; `from src.logger import logger`
- **All crawler implementations extend `BaseCrawler`** and implement `run()` (synchronous, calls `asyncio.run()` internally)
- **Crawlers use `PlaywrightDownloader` via `async with PlaywrightDownloader() as pw:`**

## Dependencies

```
# Core requirements
beautifulsoup4>=4.12.0
lxml>=5.0.0
sqlalchemy>=2.0.0
apscheduler>=3.10.0
pyyaml>=6.0.0
loguru>=0.7.0
requests>=2.31.0
httpx>=0.27.0
whoosh>=2.7.4
pymupdf>=1.23.0
xmldiff>=2.6.0
playwright>=1.40.0         # <-- must be added separately (not in current requirements.txt)
```

## CI/CD

- **Pre-commit**: enforce `ruff check .` and `black .`
- **Testing**: pytest for all crawler and parser modules
- **GitHub Actions**: run lint/typecheck/tests on every PR
- **Not yet configured** — no `.github/` or `.pre-commit-config.yaml` exists

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
