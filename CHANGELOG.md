# Changelog

All notable changes to LamiSema are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [1.1.0] — 2026-04-19

### Added

- `LamiSema.extract_iter()` — generator that yields SSE event dicts per page for streaming extraction
- `GET /extract/{doc_id}/stream` — Server-Sent Events endpoint; streams `preflight`, `page`, `done`, and `error` events as each page is processed
- Catch-all FastAPI exception handler so all unhandled 500s return JSON `{detail: ...}` instead of plain text

### Fixed

- Legacy font detection false positive: `NotoSansDevanagari` was incorrectly flagged as legacy because `"Devanagari"` is a substring of the font name. Switched from substring to exact match.
- All ruff lint errors (I001, F401, W293) across `__init__.py`, `api/app.py`, `ocr/`, `pipeline.py`, `storage/`

---

## [1.0.0] — 2026-04-18

### Added

- Complete readthedocs documentation site (`docs/`)
- `py.typed` PEP 561 marker for type checker support
- Expanded legacy font list: added Shangrila, GuptaLipi, Fontasy Himalb, Sabdatara, Sambhav, Everest, Devanagari, Nepal, Ratna, Himali TT
- `benchmark/generate_samples.py` — synthetic PDF generator for all three encoding types
- `CHANGELOG.md`

### Changed

- Version bumped to 1.0.0 — stable release
- README updated: v1.0 roadmap items marked complete
- FAQ: updated production-ready answer to reflect stable status

---

## [0.3.0] — 2026-04-18

### Added

- `benchmark/evaluate.py` — full evaluation script: CER, Entity F1, date normalization accuracy, baseline comparison
- `benchmark/dataset/` — directory structure with sourcing guidelines for 150-PDF target
- `benchmark/ground_truth/` — ground truth format spec (`.txt` + `.entities.json`)
- `CITATION.cff` — CFF citation metadata for academic use
- `--baselines` flag: compares raw pdfplumber and raw Tesseract against LamiSema

---

## [0.2.0] — 2026-04-18

### Added

- Full Python package structure — `pip install -e .` works
- Abstract `OCRBackend` interface (`lamisema/ocr/base.py`)
- `TesseractBackend` and `EasyOCRBackend` as pluggable implementations
- `pyproject.toml` with hatchling build, optional dependency groups
- `lamisema/__main__.py` — `python -m lamisema` entry point
- `lamisema serve` CLI entry point via `pyproject.toml` scripts
- 21 unit tests across preflight, NER, and date normalization
- GitHub Actions CI: Python 3.10–3.12 on Ubuntu + macOS
- GitHub Actions publish workflow: PyPI trusted publishing (OIDC, no API token)
- `.gitignore`

---

## [0.1.0] — 2026-04-18

### Added

- Initial proof-of-concept (`semantic-lab.py` monolith)
- `PDFPreflightService` — encoding type detection via PyMuPDF font introspection
- `DevanagariTextAnalyzer` — Devanagari ratio scoring, tokenization, NER, confidence
- Rule-based NER: Bikram Sambat dates, NPR currency, Nepali organizational entities
- BS→AD date normalization (approximate, ±1 day)
- `NepaliPDFExtractionPipeline` — orchestrates pre-flight → extract → NLP → score
- `DocumentStore` — in-memory PDF vault
- FastAPI REST interface on port 9001
- Hardware detection: Apple Silicon MPS, CUDA, CPU fallback
- 10 legacy Nepali fonts in pre-flight detector
- FastAPI endpoints: `/upload`, `/preflight`, `/extract`, `/result`, `/normalize-dates`
