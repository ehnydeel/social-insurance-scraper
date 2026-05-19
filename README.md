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
- `FileStorage` speichert in `data/<document_type>/<source>/<YYYYMMDD>-<source>-<original_filename>.<ext>`

## Datenhaltung

```
data/
├── Gesetze/
│   ├── bsv/
│   │   ├── 20260519-bsv-AHVG.pdf
│   │   ├── 20260519-bsv-IVG.xml
│   │   └── 20260519-bsv-FamZG.pdf
│   └── fedlex/
│       ├── 20260519-fedlex-ATSG.{xml,doc,pdf}
│       ├── 20260519-fedlex-AHVG.{xml,doc,pdf,html}
│       └── ... (alle SR-Erlasse)
├── Wegleitungen/
│   └── ahv_iv/
│       ├── 20260519-ahv_iv-Weisungen Beiträge.pdf
│       ├── 20260519-ahv_iv-Weisungen Renten.pdf
│       └── ... (alle Weisungen)
├── Kreisschreiben/
│   └── ahv_iv/
│       ├── 20260519-ahv_iv-Kreisschreiben individuell.pdf
│       └── 20260519-ahv_iv-Kreisschreiben kollektiv.pdf
└── Erläuterungen/
    ├── ahv_iv/
    │   ├── 20260519-ahv_iv-EL Weisungen.pdf
    │   ├── 20260519-ahv_iv-EO Weisungen.pdf
    │   └── ... (alle Erläuterungen)
    └── bundesgericht/
        ├── 20260519-bundesgericht-entscheid.json
        ├── 20260519-bundesgericht-entscheid.html
        └── 20260519-bundesgericht-entscheid.pdf
├── metadata/
│   └── documents.db          # SQLite (document_versions Tabelle)
└── tmp/downloads/            # Temporäre Downloads (wird geleert)
```

## Konfiguration

`config.yaml` steuert:
- Aktivierte Quellen (`enabled: true/false`)
- URLs und Kategorien pro Gesetz/Erlass
- Dokumententyp-Mapping (Gesetze, Verordnungen, Erläuterungen, Kreisschreiben, Wegleitungen)
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
        document_type: "Gesetze"
        url: "https://www.bsv.admin.ch/..."
```

## Installation

```bash
# requirements installieren
pip install -r requirements.txt

# Playwright Browser installieren
playwright install
```

**Hinweis:** `playwright` muss nach der Installation der requirements mittels `playwright install` eingerichtet werden.

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