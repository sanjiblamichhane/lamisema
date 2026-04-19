# LamiSema

**Lamichhane Semantic — Structured Information Extraction Optimized for Nepali Documents**

> The world's leading system for extracting structured *meaning* from Nepali PDFs — not just characters. LamiSema combines encoding-aware routing, layout intelligence, and a Nepali NER ontology purpose-built for the schemas of Nepali law, economics, finance, land records, and general-purpose government documents.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status: v1.0.0 Stable](https://img.shields.io/badge/status-v1.0.0--stable-brightgreen.svg)](https://pypi.org/project/lamisema/)

---

## The Problem

Most Nepali PDFs silently destroy your data when you run standard extraction tools on them.

This creates a massive barrier for **economic analysis, legal research, and government digitalization**. LamiSema is purpose-built to break this barrier.

There are three distinct types of Nepali PDF, each requiring a completely different extraction strategy. **No existing general-purpose library handles all three correctly:**

| PDF Type                  | Common Source                              | What Happens with Standard Tools         |
| ------------------------- | ------------------------------------------ | ---------------------------------------- |
| **Unicode-native**  | Modern government portals, banks           | Works fine with pdfplumber / PyMuPDF     |
| **Legacy-encoded**  | Pre-2010 govt docs, Preeti/Kantipur font   | Returns garbage bytes — no error raised |
| **Scanned / image** | Physical forms, old records, field surveys | Returns empty string — no error raised  |

The legacy font problem is particularly insidious. Fonts like **Preeti**, **Sagarmatha**, and **Kantipur** encode Devanagari characters using ASCII codepoints. A PDF that renders as "नेपाल" on screen is stored as "g]kfn" in the text layer. Standard extractors (pdfplumber, PyMuPDF text mode, Tika) silently return the garbage bytes — no exception, no warning.

LamiSema detects encoding type first and routes each document to the correct extraction strategy automatically. It was designed to support large-scale economic and government record extraction where data integrity is non-negotiable.

---

## What LamiSema Does

```
PDF Input
   │
   ▼
┌─────────────────────────────────────────┐
│  Stage 1 — Pre-flight Analysis          │
│  Detects font names, encoding type,     │
│  presence of text layer                 │
└─────────────────────────────────────────┘
   │
   ├─ unicode_native ──→  pdfplumber text layer  (fast, lossless)
   ├─ legacy_encoded ──→  300 DPI render → OCR   (Tesseract nep+eng)
   └─ scanned        ──→  300 DPI render → OCR   (Tesseract nep+eng)
   │
   ▼
┌─────────────────────────────────────────┐
│  Stage 2 — Layout Intelligence          │
│  Structure-aware extraction:            │
│  - Table detection and reconstruction   │
│  - Section and heading detection        │
│  - Multi-column reading order           │
└─────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────┐
│  Stage 3 — Symbolic NLP Layer           │
│  Rule-based NER, no ML model required   │
│  - Devanagari ratio scoring             │
│  - Named entity detection (20+ types)   │
│    dates, currency, orgs, wards,        │
│    districts, land parcels, court refs  │
│  - Bikram Sambat → Gregorian            │
│    date normalization                   │
└─────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────────┐
│  Stage 4 — Domain Schema Output         │
│  Typed extraction models for:           │
│  budget lines, land records,            │
│  gazette notices, court orders,         │
│  economics reports, general docs        │
└─────────────────────────────────────────┘
   │
   ▼
Structured JSON output with confidence scores
```

### Key features

- **Encoding pre-flight** — detects 20+ legacy Nepali fonts (Preeti, Sagarmatha, Kantipur, Himali, and more) before any extraction runs
- **Automatic routing** — no config needed; the right strategy is chosen per document, per page
- **Layout-aware extraction** — tables, sections, headings, and multi-column layouts recovered as structure, not flattened text
- **Deep Nepali NER** — 20+ entity types: BS dates, NPR currency, organizations, ward codes, districts, provinces, land parcel IDs, court case references, gazette refs, government positions
- **High-Availability Storage** — Pluggable backends: `memory` (dev), `disk` (persistent `/uploads`), or `S3/Minio` (production) with automatic fallback
- **Language-Agnostic Core** — `NLPBackend` interface allows adding Hindi, English, or Maithili with zero changes to the pipeline
- **Bikram Sambat normalization** — converts BS dates (२०८१ साल असार १५) to approximate AD equivalents
- **Domain schemas** — typed extraction models for budget documents, land records, gazette notices, court orders, economics reports, and general-purpose government documents
- **Cross-document intelligence** — deduplication, version tracking, and entity co-reference across document corpora
- **FastAPI + Docker** — ready for production deployment with `docker-compose` including a local Minio instance
- **Fully offline** — no API keys, no network calls, no data sent anywhere

---

## Quickstart

### Requirements

```bash
# 1. Install LamiSema (automatically installs all core dependencies)
#    (not yet on PyPI — install from source for now)
git clone https://github.com/sanjiblamichhane/lamisema
cd lamisema
pip install -e .

# 2. System dependency: Tesseract with Nepali language pack
#    This is the only system dependency not bundled in the wheel
brew install tesseract tesseract-lang   # macOS
# apt-get install tesseract-ocr tesseract-ocr-nep  # Ubuntu

# Verify Nepali language pack visibility:
tesseract --list-langs | grep nep
```

### Run the API server

```bash
# The CLI entry point is installed automatically
lamisema serve

# Or run via module:
python -m lamisema.api.app

# Open the documentation:
# → http://localhost:9001/docs
```

### Python library usage

```python
from lamisema import LamiSema

lamisema = LamiSema()

with open("my-nepali-report.pdf", "rb") as f:
    result = lamisema.extract(f.read(), filename="my-nepali-report.pdf")

print(result.encoding_type)        # "legacy_encoded"
print(result.language)             # "ne"
print(result.overall_confidence)   # 0.74
print(result.pages[0].script_ratio) # 0.82 (fraction of Devanagari)
print(result.pages[0].entities)    # [Entity(type="DATE_BS", ...)]
```

### REST API usage

```bash
# Upload
curl -X POST http://localhost:9001/upload -F "file=@report.pdf"
# → { "doc_id": "DOC-A1B2C3D4", ... }

# Pre-flight check (encoding detection only, fast)
curl http://localhost:9001/preflight/DOC-A1B2C3D4

# Full extraction
curl -X POST http://localhost:9001/extract/DOC-A1B2C3D4

# Get result
curl http://localhost:9001/result/DOC-A1B2C3D4

# Normalize BS dates in any text
curl -X POST http://localhost:9001/normalize-dates \
  -H "Content-Type: application/json" \
  -d '{"text": "२०८१ साल असार १५ मा बजेट पारित भयो"}'
```

---

## API Reference

| Method   | Endpoint                | Description                                         |
| -------- | ----------------------- | --------------------------------------------------- |
| `GET`  | `/`                   | Health check, hardware info, library status         |
| `POST` | `/upload`             | Upload a PDF, returns `doc_id`                    |
| `GET`  | `/preflight/{doc_id}` | Encoding type + font analysis (no extraction)       |
| `POST` | `/extract/{doc_id}`   | Full pipeline: extract → NER → normalize → score |
| `GET`  | `/result/{doc_id}`    | Retrieve completed extraction result                |
| `POST` | `/normalize-dates`    | Normalize BS dates in arbitrary Nepali text         |

Full interactive docs at `http://localhost:9001/docs` when the server is running.

---

## Supported Legacy Fonts

LamiSema's pre-flight detector identifies the following legacy Nepali fonts, all of which require OCR rather than text-layer extraction:

`Preeti` · `Sagarmatha` · `Kantipur` · `PCS Nepali` · `Himali` · `Navjeevan` · `Narad` · `Fontasy Himali` · `Kanjirowa` · `Kuti`

If you encounter a legacy font not on this list, open an issue with a sample PDF.

---

## Bikram Sambat Date Normalization

Nepali government documents use the Bikram Sambat (BS) calendar. LamiSema detects and normalizes:

- Full dates: `२०८१ साल असार १५` → `~2024-06-29 AD (approx)`
- Year references: `२०८१ साल` → `~2024 AD`
- Mixed Devanagari/ASCII digits: `2081 साल Ashadh 15`

Conversion is approximate (±1 day). For exact conversion, integrate the [`nepali-datetime`](https://pypi.org/project/nepali-datetime/) library — see `lamisema/nlp/dates.py`.

---

## Rule-Based NER: Detected Entity Types

| Entity Type      | Example                                | Notes                                                          |
| ---------------- | -------------------------------------- | -------------------------------------------------------------- |
| `DATE_BS`      | `२०८१ साल असार १५`      | Full BS date, normalized to AD                                 |
| `DATE_BS`      | `२०८१ साल`                    | Year-only BS reference                                         |
| `CURRENCY`     | `रु. १२,५००` / `NPR 12,500` | Handles Devanagari and ASCII digits                            |
| `ORGANIZATION` | `अर्थ मन्त्रालय`        | Matched by suffix (मन्त्रालय, कार्यालय, etc.) |

No ML model is used in the NER layer — all patterns are deterministic regex grammars. This means zero inference cost and full explainability.

---

## FAQs

**What does "encoding-aware" mean?**

It means LamiSema checks *how* a PDF stores its text before it tries to read it, and changes its behavior accordingly. A Nepali PDF can store text in three completely different ways — as real Unicode characters, as legacy ASCII bytes that only *look* Nepali because of the font, or not at all (a scanned image). A tool that is not encoding-aware tries the same extraction method on every PDF. On a Preeti-encoded document it silently returns garbage like `g]kfn` instead of `नेपाल` — no error, no warning, just wrong output. LamiSema detects the encoding type first, then picks the right strategy. That is what encoding-aware means.

---

**Why does my PDF look correct on screen but return garbage text?**

Because your PDF uses a legacy Nepali font — most likely Preeti or Kantipur. These fonts were created before Unicode existed. They work by storing ASCII characters (like `g`, `]`, `k`, `f`, `n`) and relying on the font file to *draw* them as Devanagari glyphs on screen. The PDF looks perfect visually, but the actual stored bytes are English ASCII. When any standard extractor (pdfplumber, PyMuPDF, Adobe's text copy) reads those bytes, it gives you the ASCII — because that is what is actually stored. LamiSema detects these fonts and routes around the text layer entirely, rendering the page as an image and running OCR instead.

---

**Why can't I just run Tesseract on every PDF?**

You can, but you will pay a large unnecessary cost on clean Unicode PDFs. A 100-page Unicode-native government report processed through OCR takes minutes and introduces character errors that were never there. LamiSema uses direct text extraction (instant, lossless) when the PDF supports it, and only falls back to OCR when the document actually requires it.

---

**What is Bikram Sambat and why does it matter?**

Bikram Sambat (BS) is the official calendar of Nepal. It runs approximately 56–57 years ahead of the Gregorian calendar — so 2081 BS is roughly 2024–2025 AD. Almost every Nepali government document, legal record, financial statement, and land deed uses BS dates written in Devanagari numerals (२०८१ साल असार १५). No mainstream NLP library handles this. Without normalization, date-based filtering, sorting, or cross-document analysis on Nepali records is impossible. LamiSema detects BS date patterns and converts them to approximate AD equivalents automatically.

---

**What makes LamiSema different from just running pdfplumber or PyMuPDF?**

Those tools are excellent for what they were built for — PDFs in Latin-script languages with Unicode encoding. They have no awareness of the Nepali legacy font problem. They will silently return corrupted output on a Preeti PDF and there is nothing in their output that tells you something went wrong. LamiSema's contribution is the layer *before* extraction: detecting which strategy is appropriate, routing accordingly, and then adding the Nepali-specific NLP (date normalization, entity recognition) that no general-purpose library provides.

---

**Do I need an internet connection or an external API?**

No. The entire pipeline runs locally. Encoding detection, text extraction, NER, and date normalization all run on your machine. The only external dependency is Tesseract, which is an open-source binary installed via Homebrew or apt — no API key, no network calls, no data sent anywhere.

---

**Does LamiSema work on handwritten Nepali documents?**

Not reliably yet. Tesseract is trained on printed text. Handwritten Devanagari is a harder problem requiring a dedicated recognition model. It is on the roadmap. For now, LamiSema handles printed PDFs — both digital and scanned.

---

**Can I use LamiSema on languages other than Nepali?**

The encoding detection and OCR routing work on any PDF. The symbolic NLP layer (NER patterns, date normalization, Devanagari ratio scoring) is Nepali-specific. If you want to adapt it for Hindi, Maithili, or another Devanagari-script language, the constants in `lamisema/constants.py` and the regex patterns in `lamisema/nlp/ner.py` are the only files you need to change.

---

**Why is this groundbreaking for the Nepali language specifically?**

Nepal has decades of government records — land titles, court judgments, budget reports, economics analyses, gazette notices, and census data — locked inside PDFs. Many use legacy fonts (Preeti, Kantipur) that silently corrupt output in every standard tool. Others are scanned images with no text layer at all. No mainstream NLP or data extraction library handles these correctly, and none understands Nepal's specific document schemas: Bikram Sambat dates, ward and VDC hierarchies, kittaa land parcel notation, NPR currency, or the naming conventions of Nepali government bodies.

LamiSema is the world's leading system specifically built for this corpus: encoding-aware routing, layout-aware table extraction, a NER ontology covering 20+ Nepali entity types, typed domain schemas for the most common Nepali document classes, and cross-document intelligence for working with collections rather than individual files.

---

**Is LamiSema production-ready?**

The v1.0 pipeline is stable and installable via `pip install lamisema`. The symbolic NLP layer (NER, date normalization, encoding detection) is fully tested and reliable. Two caveats remain for high-volume production use: the document store is in-memory (swap for Redis or a database for persistence across restarts), and formal benchmark results against ground-truth transcriptions are still in progress. For research use, internal tooling, and integration into larger pipelines, LamiSema is ready today.

---

## Benchmark

> ⚠️ **Formal benchmark results are pending.** The dataset and evaluation script are in progress. Results will be published here before the v1.0 stable release.

**Planned evaluation:**

- 50 Unicode-native Nepali PDFs
- 50 Preeti-encoded Nepali PDFs
- 50 scanned Nepali PDFs
- Ground truth: manually transcribed by native Nepali speakers
- Metrics: Character Error Rate (CER), Entity F1, Date normalization accuracy
- Baselines: raw pdfplumber, raw Tesseract (no routing), PyMuPDF text mode

---

## Roadmap

### v0.1 — PoC ✅

- [X] PDF pre-flight encoding detection
- [X] Routing: unicode_native → pdfplumber, others → Tesseract OCR
- [X] 300 DPI page rendering for scanned/legacy PDFs
- [X] Rule-based NER (dates, currency, organizations)
- [X] Bikram Sambat → AD date normalization
- [X] Devanagari ratio confidence scoring
- [X] FastAPI REST interface
- [X] MPS / CUDA / CPU hardware detection

### v0.2 — Package ✅

- [X] Restructure as proper Python package (`pip install lamisema`)
- [X] Abstract `OCRBackend` interface (swap Tesseract ↔ EasyOCR ↔ Vision API)
- [X] Unit tests (21 passing)
- [X] Proper `pyproject.toml`
- [X] CI (GitHub Actions — `.github/workflows/ci.yml`)
- [X] PyPI publish workflow (`.github/workflows/publish.yml`, trusted publishing)
- [X] `python -m lamisema` entry point

### v0.3 — Benchmark ✅ (partial)

- [X] Evaluation script: CER, entity F1, date normalization accuracy (`benchmark/evaluate.py`)
- [X] Benchmark dataset structure + ground truth format (`benchmark/dataset/`, `benchmark/ground_truth/`)
- [X] Baseline comparison (`--baselines` flag: raw pdfplumber vs raw Tesseract vs LamiSema)
- [X] `CITATION.cff`
- [ ] Benchmark dataset populated (150 PDFs, 3 encoding types, native-speaker ground truth)

### v1.0 — Stable Release ✅ (partial)

- [X] PyPI release (`pip install lamisema`)
- [X] Complete documentation (readthedocs — `mkdocs.yml`, `docs/`, `.readthedocs.yml`)
- [X] Pre-flight font list expanded to 20 fonts
- [X] `LICENSE` (MIT), `CHANGELOG.md`, `py.typed` (PEP 561)

---

### v1.1 — Layout Intelligence

> *Moving from raw character recovery to structure recovery.*

- [ ] **Table extraction for unicode-native PDFs** — `pdfplumber` table parser exposed as `TableResult` model; tables are returned as structured rows, not flattened text
- [ ] **Table reconstruction for OCR path** — word bounding-box clustering to reconstruct row/column structure from Tesseract output on legacy and scanned PDFs
- [ ] **Section detection** — identify document sections (title block, preamble, operative clauses, annexures) using Devanagari heading patterns and font-size signals
- [ ] **Multi-column layout handling** — correct reading order for two-column gazette notices and budget reports
- [ ] Output: `DocumentStructure` model with `sections`, `tables`, and `paragraphs` fields alongside the existing `pages`

### v1.2 — Deep Nepali NER

> *3 entity types is a skeleton. Nepal's documents need a full ontology.*

- [ ] `WARD_CODE` — वडा नं. X (ward number, critical for land and census documents)
- [ ] `VDC_MUNICIPALITY` — all गाउँपालिका / नगरपालिका names (753 local units)
- [ ] `DISTRICT` — all 77 districts (exact-match list, high precision)
- [ ] `PROVINCE` — 7 province names (Bagmati, Gandaki, Koshi, etc.)
- [ ] `LAND_PARCEL` — कि.नं. (kittaa number), land categories (ऐलानी, रैकर, गुठी)
- [ ] `PERSON_NAME_NE` — Nepali personal names using honorific + patronymic patterns
- [ ] `PHONE_NE` — Nepali phone formats (०१-XXXXXXX landline, ९८XXXXXXXX mobile)
- [ ] `COURT_CASE` — मिसिल नं., मुद्दा नं., फैसला references
- [ ] `GAZETTE_REF` — नेपाल राजपत्र volume and notice number patterns
- [ ] `GOV_POSITION` — सचिव, उपसचिव, महानिर्देशक and other title patterns
- [ ] Full NER test suite with annotated Nepali government text samples

### v2.0 — Domain Schemas

> *From generic JSON blobs to typed, queryable Nepali document objects.*

Domain-specific extraction schemas for Nepal's most common government document types:

- [ ] **Budget documents** — `BudgetLine(ministry_ne, programme_code, head, allocated_npr, revised_npr, expenditure_npr)` extracted from Red Book and white book PDFs
- [ ] **Land certificates** — `LandRecord(owner_name, kittaa_no, ward, vdc_municipality, district, area_sq_ft, category)` from lalpurja and field book scans
- [ ] **Gazette notices** — `GazetteNotice(publication_date_bs, notice_type, issuing_authority, effective_date_bs, full_text)` with reference number linking
- [ ] **Court orders** — `CourtOrder(case_no, court, bench, parties, order_date_bs, operative_text)` from Supreme Court and High Court PDFs
- [ ] Schema validation: every extracted document is validated against its domain model before the result is returned
- [ ] REST API: `/schema/{doc_type}` endpoint returns the JSON schema for each domain model

### v2.1 — Cross-Document Intelligence

> *Individual PDFs are islands. Real work happens on corpora.*

- [ ] **Near-duplicate detection** — MinHash similarity to identify the same document published in multiple PDFs (common for gazette reprints and amended orders)
- [ ] **Version tracking** — detect when a document is an amendment or revision of a previously seen document; link them in a version chain
- [ ] **Entity co-reference resolution** — "अर्थ मन्त्रालय" across 500 documents is the same entity; build a cross-document entity index
- [ ] **Temporal corpus sequencing** — sort any collection of Nepali government PDFs by their extracted BS dates without requiring filename conventions
- [ ] Corpus-level API: `POST /corpus/analyze` accepts a batch of doc IDs and returns entity index, duplicate clusters, and version chains

### v2.2 — Public Benchmark & Research Release

> *Building the dataset Nepal's NLP community has been missing.*

- [ ] **Benchmark corpus** — 150 PDFs minimum (50 per encoding type), sourced from public Nepali government portals (MoF, MoLand, Supreme Court, Election Commission)
- [ ] **Native-speaker ground truth** — full text transcriptions and entity span annotations by native Nepali speakers, released under Creative Commons
- [ ] **Leaderboard schema** — standardized evaluation protocol (CER, entity F1, date normalization accuracy, table cell accuracy) that external systems can run against
- [ ] Dataset hosted on HuggingFace Datasets under `sanjiblamichhane/lamisema-bench`

---

## Project Structure

```
lamisema/
├── README.md
├── CITATION.cff
├── pyproject.toml
├── .gitignore
├── .github/
│   └── workflows/
│       ├── ci.yml          Test matrix: Python 3.10–3.12, Ubuntu + macOS
│       └── publish.yml     PyPI trusted publishing on GitHub release
├── lamisema/
│   ├── __init__.py         Public API surface
│   ├── __main__.py         python -m lamisema entry point
│   ├── constants.py        Devanagari range, legacy font list, BS calendar
│   ├── models.py           Pydantic data models
│   ├── preflight.py        PDFPreflightService — encoding detection
│   ├── pipeline.py         NepaliPDFExtractionPipeline + DocumentStore
│   ├── nlp/
│   │   ├── analyzer.py     DevanagariTextAnalyzer — ratio + tokenization
│   │   ├── ner.py          Rule-based named entity recognition
│   │   └── dates.py        Bikram Sambat → Gregorian normalization
│   ├── ocr/
│   │   ├── base.py         Abstract OCRBackend interface
│   │   ├── tesseract.py    TesseractBackend (default)
│   │   └── easyocr.py      EasyOCRBackend (optional)
│   └── api/
│       └── app.py          FastAPI application + serve() CLI entry point
├── tests/
│   ├── test_preflight.py
│   ├── test_ner.py
│   └── test_dates.py
└── benchmark/
    ├── evaluate.py         CER + Entity F1 + Date accuracy vs baselines
    ├── dataset/
    │   ├── unicode_native/ *.pdf
    │   ├── legacy_encoded/ *.pdf
    │   └── scanned/        *.pdf
    └── ground_truth/
        ├── *.txt           Manually transcribed text (one per PDF)
        └── *.entities.json Named entity annotations (one per PDF)
```

---

## Contributing

Contributions welcome, especially:

1. **Legacy font additions** — if you have a Nepali PDF with a font LamiSema doesn't detect, open an issue with the font name (visible via `pdffonts your-file.pdf`)
2. **NER patterns** — additional regex patterns for Nepali entity types (land parcel IDs, ward codes, district names)
3. **Benchmark PDFs** — anonymized Nepali PDFs of each encoding type for the evaluation dataset
4. **BS→AD accuracy** — corrections or improvements to the Bikram Sambat conversion

---

## Citation

If you use LamiSema in research, please cite:

```bibtex
@software{lamichhane2026lamisema,
  author    = {Lamichhane, Sanjib},
  title     = {LamiSema: Encoding-Aware Nepali PDF Extraction Engine},
  year      = {2026},
  url       = {https://github.com/sanjiblamichhane/lamisema},
  note      = {Proof of concept. Stable release pending.}
}
```

---

## Related Work

- **Tesseract OCR** — Google's open-source OCR engine with Nepali (`nep`) language support
- **Onto** — GivingbackAI's swarm intelligence ontology modeling platform (LamiSema is the symbolic preprocessing layer for Onto's PDF extraction pipeline)

---

## License

MIT License — see [LICENSE](LICENSE) for full text.

---

*Built by [Sanjib Lamichhane](https://github.com/sanjiblamichhane). Contributions and issue reports welcome.*
