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
| **AK40** (Ausgleichskasse Basel) | PDF-Download | ✅ Working |
| **Kantonale Quellen** | PDF-Download | ⚙️ Konfigurierbar |

## Architektur

```
main.py → run_all()
    ├── BSVCrawler        → Playwright → HtmlParser → FileStorage + VersionManager
    ├── FedlexCrawler      → Playwright → SPA Nav   → FileStorage + VersionManager
    ├── AHVIVCrawler       → Playwright → HtmlParser → FileStorage + VersionManager
    ├── BundesgerichtCrawler → Playwright → entscheidsuche.ch Index API → FileStorage + VersionManager
    ├── KantonCrawler      → Playwright → HTML Parser → FileStorage + VersionManager
    └── AK40Crawler        → Playwright → HTML Parser → FileStorage + VersionManager
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
├── AK40/
│   ├── FZ/
│   │   ├── 20260519-ak40-fz-anmeldeformular_nichterwerbst.pdf
│   │   └── ... (alle AK40 Dokumente für Familienzulagen)
│   ├── AHV/
│   │   ├── 20260519-ak40-ahv-ahv_rentenanmeldung.pdf
│   │   └── ... (alle AK40 Dokumente für AHV)
│   ├── IV/
│   │   ├── 20260519-ak40-iv-invalidenversicherung_anmeldung.pdf
│   │   └── ... (alle AK40 Dokumente für IV)
│   ├── EO/
│   │   ├── 20260519-ak40-eo-erwerbsersatz_antrag.pdf
│   │   └── ... (alle AK40 Dokumente für EO)
│   ├── MSE/
│   │   ├── 20260519-ak40-mse-mutterschaftsentgelt_anmeldung.pdf
│   │   └── ... (alle AK40 Dokumente für MSE)
│   ├── VSE/
│   │   ├── 20260519-ak40-vse-vaterschaftsentgelt_anmeldung.pdf
│   │   └── ... (alle AK40 Dokumente für VSE)
│   └── EL/
│       ├── 20260519-ak40-el-ergaenzungsleistungen_antrag.pdf
│       └── ... (alle AK40 Dokumente für EL)
├── Kanton/
│   ├── BL/
│   │   ├── 20260519-bl-gsov.pdf          # Beispiel: Kantonalgesetz über die soziale Vorsorge
│   │   └── 20260519-bl-famu.pdf          # Beispiel: Familienzulagengesetz
│   ├── ZH/
│   │   └── ... (weiteres Kanton BL)
│   └── ... (alle anderen Kantone)
├── Erläuterungen/
│   ├── ahv_iv/
│   │   ├── 20260519-ahv_iv-EL Weisungen.pdf
│   │   ├── 20260519-ahv_iv-EO Weisungen.pdf
│   │   └── ... (alle Erläuterungen)
│   └── bundesgericht/
│       ├── 20260519-bundesgericht-entscheid.json
│       ├── 20260519-bundesgericht-entscheid.html
│       └── 20260519-bundesgericht-entscheid.pdf
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
# Einmaliger Crawler-Durchlauf (alle Quellen)
python main.py

# Bestimmte Quellen ausführen
python main.py -s bsv,fedlex          # Nur BSV und Fedlex
python main.py --sources ahv_iv,ak40  # Nur AHV/IV und AK40

# Kontinuierlich mit Scheduler ausführen
python main.py --serve

# Hilfe anzeigen
python main.py --help
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