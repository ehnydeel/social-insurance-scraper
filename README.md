# Social Insurance Scraper

Automatischer Downloader und Historisierer für Schweizer Sozialversicherungsdokumente.

## Quellen

| Quelle | Typ | Status |
|--------|-----|--------|
| **BSV** (AHVG, IVG, FamZG) | PDF-Download | ✅ Working |
| **Fedlex** (10 SR Erlasse) | XML, DOC, PDF, HTML pro Konsolidierungsversion | ✅ Working |
| **AHV/IV Wegleitungen** (5 Seiten) | PDF-Download | ✅ Working |
| **AHV/IV Kreisschreiben** (2 Seiten) | PDF-Download | ✅ Working |
| **Bundesgericht** (entscheidsuche.ch) | JSON, HTML, PDF | ✅ Working |

## Architektur

```
main.py → run_all()
  ├── BSVCrawler        → Playwright → HtmlParser → FileStorage + VersionManager
  ├── FedlexCrawler      → Playwright → SPA Nav   → FileStorage + VersionManager
  ├── AHVIVCrawler       → Playwright → HtmlParser → FileStorage + VersionManager
  └── BundesgerichtCrawler → Playwright → entscheidsuche.ch Index API → FileStorage + VersionManager
```

- Jeder Crawler ist synchron (`run()`), intern via `asyncio.run()`
- `PlaywrightDownloader` als async context manager (ein Browser-Session pro Crawler-Durchlauf)
- SHA-256 Deduplizierung via `VersionManager` (SQLAlchemy / SQLite)
- `FileStorage` speichert in `data/<cat>/<sub>/current/` + archiviert nach `data/<cat>/<sub>/archive/YYYY-MM-DD/`

## Datenhaltung

```
data/
├── bsv/
│   ├── AHV/current/          # Aktuelle PDFs
│   ├── AHV/archive/YYYY-MM-DD/
│   ├── IV/current/
│   └── FamZG/current/
├── ahv_iv/
│   ├── weisungen/current/
│   ├── weisungen/archive/...
│   ├── kreisschreiben/current/
│   └── kreisschreiben/archive/...
├── fedlex/
│   ├── sr/current/           # ATSG_AHVG_IVG_..._{datum}.{xml,doc,pdf,html}
│   └── sr/archive/...
├── bundesgericht/
│   ├── entscheide/current/   # CH_BGer_*.{json,html,pdf}
│   └── entscheide/archive/...
├── metadata/
│   └── documents.db          # SQLite (document_versions Tabelle)
└── tmp/downloads/            # Temporäre Downloads (wird geleert)
```

## Konfiguration

`config.yaml` steuert:
- Aktivierte Quellen (`enabled: true/false`)
- URLs und Kategorien pro Gesetz/Erlass
- Scheduler-Cron (default: täglich 03:00)
- Datenbank-Pfad

Beispiel:
```yaml
sources:
  bsv:
    enabled: true
    gesetze:
      - name: "AHVG"
        category: "bsv"
        subcategory: "AHV"
        url: "https://www.bsv.admin.ch/..."
```

## Installation

```bash
# requirements installieren
pip install -r requirements.txt

# Playwright Browser installieren
playwright install chromium
```

**Hinweis:** `playwright` muss nach der Installation der requirements mittels `playwright install chromium` eingerichtet werden.

## Start

```bash
# Einmaliger Crawler-Durchlauf
python main.py

# Scheduler (täglicher Durchlauf via APScheduler)
python -m src.scheduler.scheduler
```

## Tests

```bash
pytest tests/ -v
```

## CI/CD

- **Pre-commit**: `.pre-commit-config.yaml` (ruff lint+format, pyright)
- **GitHub Actions**: `.github/workflows/ci.yml` (lint, typecheck, test auf push/PR zu main)

## Nächste Schritte (Ideas)

1. **Volltextsuche-CLI** — `search()` in `fulltext_index.py` ist implementiert, aber nicht via CLI/API erreichbar
2. **Filter für Bundesgericht** — aktuell werden **alle** neuen Dokumente vom Index geholt; Datums-/Gerichtsfilter wären nützlich
3. **Coverage Reporting** — `pytest-cov` für Threshold-basierte Coverage
4. **Docker Setup** — containerisierte Ausführung für Scheduler-Deployment
5. **Health Monitoring** — `entscheidsuche.ch/status` periodisch abfragen