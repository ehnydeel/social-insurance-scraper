# Social Insurance Scraper

Automatischer Downloader und Historisierer für:

- AHVG
- IVG
- ATSG
- FamZG
- Wegleitungen
- Kreisschreiben
- Verordnungen
- Bundesgerichtsurteile

## Features

- PDF/XML Download
- Historisierung
- SHA256 Versionierung
- SQLite Datenbank
- Volltextindex
- Scheduler
- Strukturierte Ablage

## Installation

```bash
pip install -r requirements.txt
```

## Start

```bash
python main.py
```

## Scheduler

```bash
python -m src.scheduler.scheduler
```