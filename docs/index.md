# LamiSema

**Lamichhane Semantic — Structured Information Extraction for Nepali Documents**

> The world's leading system for extracting structured *meaning* from Nepali PDFs — not just characters. LamiSema combines encoding-aware routing, layout intelligence, and a Nepali NER ontology purpose-built for the schemas of Nepali law, economics, finance, land records, and general-purpose government documents.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/sanjiblamichhane/lamisema/blob/master/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/lamisema)](https://pypi.org/project/lamisema/)
[![CI](https://github.com/sanjiblamichhane/lamisema/actions/workflows/ci.yml/badge.svg)](https://github.com/sanjiblamichhane/lamisema/actions/workflows/ci.yml)

---

## The Problem in One Paragraph

Nepal has decades of government records — land titles, court judgments, budget reports, economics analyses, gazette notices, and census data — stored as PDFs. Most of these documents use **legacy Nepali fonts** (Preeti, Kantipur, Sagarmatha) that store Devanagari characters as ASCII bytes. When any standard extraction tool reads the text layer, it returns garbage: `g]kfn` instead of `नेपाल`. No error is raised, no warning emitted — the output is silently wrong. Other documents are scanned images with no text layer at all. And even when characters are extracted correctly, mainstream tools have no understanding of Nepal’s document schemas: Bikram Sambat dates, ward and VDC hierarchies, kittaa land parcel notation, or NPR currency.

LamiSema solves this end-to-end: **detecting encoding type first**, routing to the correct extraction strategy, recovering document structure, and extracting structured meaning using Nepal’s own administrative and legal vocabulary.

---

## How It Works

```
PDF Input
   │
   ▼
┌──────────────────────────────────┐
│  Stage 1 — Pre-flight Analysis   │  Detects font names, encoding
│  PDFPreflightService             │  type, presence of text layer
└──────────────────────────────────┘
   │
   ├─ unicode_native ──→  pdfplumber (fast, lossless)
   ├─ legacy_encoded ──→  300 DPI render → Tesseract nep+eng
   └─ scanned        ──→  300 DPI render → Tesseract nep+eng
   │
   ▼
┌──────────────────────────────────┐
│  Stage 2 — Layout Intelligence   │  Tables, sections, headings,
│                                  │  multi-column reading order
└──────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────┐
│  Stage 3 — Symbolic NLP Layer    │  Rule-based NER (20+ types):
│  DevanagariTextAnalyzer          │  BS dates, currency, orgs,
└──────────────────────────────────┘  wards, districts, land parcels
   │
   ▼
┌──────────────────────────────────┐
│  Stage 4 — Domain Schema Output  │  Typed models: budget, land,
│                                  │  gazette, court, economics,
└──────────────────────────────────┘  general-purpose documents
   │
   ▼
Structured JSON output with confidence scores
```

---

## Quickstart

```bash
pip install lamisema
brew install tesseract tesseract-lang   # macOS
# apt-get install tesseract-ocr tesseract-ocr-nep  # Ubuntu
```

```python
from lamisema import LamiSema

lamisema = LamiSema()

with open("budget-2081.pdf", "rb") as f:
    result = lamisema.extract(f.read(), filename="budget-2081.pdf")

print(result.encoding_type)        # "legacy_encoded"
print(result.language)             # "ne"
print(result.overall_confidence)   # 0.74
print(result.pages[0].entities)    # [Entity(type="DATE_BS", ...)]
```

See [Installation](installation.md) for full setup instructions.

---

## Key Features

| Feature | Description |
|---|---|
| Encoding pre-flight | Detects 20+ legacy Nepali fonts before extraction |
| Automatic routing | No config — correct strategy chosen per document |
| Layout intelligence | Tables, sections, headings, multi-column layouts as structure |
| Deep Nepali NER | 20+ entity types: dates, currency, orgs, wards, districts, land parcels, court refs, gazette refs |
| High-Availability Storage | Pluggable backends: `memory`, `disk`, or `S3/Minio` with automatic fallback |
| Language-Agnostic Core | `NLPBackend` interface allows adding Hindi, English, etc. |
| Bikram Sambat normalization | Converts BS dates to approximate AD equivalents |
| Domain schemas | Typed output for budget, land, gazette, court, economics, and general-purpose documents |
| Cross-document intelligence | Deduplication, version tracking, entity co-reference across corpora |
| FastAPI + Docker | Ready for production deployment with `docker-compose` |
| Fully offline | No API keys, no network calls, no data sent anywhere |
