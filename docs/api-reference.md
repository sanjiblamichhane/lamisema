# REST API Reference

Start the server:

```bash
lamisema serve
# → http://localhost:9001/docs  (interactive Swagger UI)
```

---

## Endpoints

### `GET /`

System health check.

**Response:**
```json
{
  "status": "online",
  "version": "1.0.0",
  "libraries": {
    "PyMuPDF": true,
    "pdfplumber": true,
    "pytesseract": true,
    "easyocr": false
  },
  "ocr_backend": "tesseract",
  "storage_backend": "InMemoryStorage",
  "store": {
    "uploaded_docs": 3,
    "completed_extractions": 2
  }
}
```

---

### `POST /upload`

Upload a Nepali PDF. Returns a `doc_id` for subsequent calls.

**Request:** `multipart/form-data` with field `file` (PDF only).

**Response:**
```json
{
  "doc_id": "DOC-A1B2C3D4",
  "filename": "budget-2081.pdf",
  "size_bytes": 204800,
  "next_steps": {
    "preflight": "/preflight/DOC-A1B2C3D4",
    "extract": "POST /extract/DOC-A1B2C3D4"
  }
}
```

**Errors:**
- `400` — file is not a PDF, or is empty
- `413` — file too large (in-memory limit ~50 MB)

---

### `GET /preflight/{doc_id}`

Stage 1 encoding detection only. Read-only, fast (~100ms).

**Response:**
```json
{
  "doc_id": "DOC-A1B2C3D4",
  "filename": "budget-2081.pdf",
  "page_count": 48,
  "encoding_type": "legacy_encoded",
  "fonts": [
    {
      "name": "Preeti",
      "encoding": "WinAnsiEncoding",
      "is_legacy_nepali": true
    }
  ],
  "has_text_layer": true,
  "recommended_strategy": "Text layer contains Preeti/legacy-encoded bytes. Render each page at 300 DPI and run Tesseract (nep+eng). Do NOT use pdfplumber on this document."
}
```

**Errors:**
- `404` — doc_id not found
- `503` — PyMuPDF not installed

---

### `POST /extract/{doc_id}`

Run the full pipeline. May take 30–120 seconds for large OCR documents.

**Response:** Full `ExtractionResult` object:
```json
{
  "doc_id": "DOC-A1B2C3D4",
  "filename": "budget-2081.pdf",
  "language": "ne",
  "encoding_type": "legacy_encoded",
  "total_pages": 48,
  "overall_confidence": 0.74,
  "ocr_backend": "tesseract",
  "warnings": [
    "Legacy Nepali font detected (Preeti/Kantipur). Text layer was bypassed."
  ],
  "pages": [
    {
      "page_number": 1,
      "raw_text": "नेपाल सरकार अर्थ मन्त्रालय...",
      "script_ratio": 0.68,
      "extraction_method": "tesseract",
      "confidence": 0.77,
      "entities": [
        {
          "text": "२०८१ साल असार १५",
          "entity_type": "DATE_BS",
          "normalized": "~2024-06-29 AD (approx)",
          "confidence": 0.9
        }
      ]
    }
  ]
}
```

**Errors:**
- `404` — doc_id not found
- `503` — extraction dependency missing

---

### `GET /result/{doc_id}`

Retrieve a previously completed extraction.

**Errors:**
- `404` — doc_id not found, or extraction not yet run

---

### `POST /normalize-dates`

Normalize BS dates in arbitrary Nepali text. No PDF needed.

**Request:**
```json
{ "text": "२०८१ साल असार १५ मा बजेट पारित भयो" }
```

**Response:**
```json
{
  "original_text": "२०८१ साल असार १५ मा बजेट पारित भयो",
  "normalized_dates": [
    {
      "text": "२०८१ साल असार १५",
      "entity_type": "DATE_BS",
      "normalized": "~2024-06-29 AD (approx)",
      "confidence": 0.9
    }
  ],
  "processed_text": "~2024-06-29 AD (approx) मा बजेट पारित भयो"
}
```

---

## cURL examples

```bash
# Upload
curl -X POST http://localhost:9001/upload -F "file=@report.pdf"

# Pre-flight (encoding detection only)
curl http://localhost:9001/preflight/DOC-A1B2C3D4

# Full extraction
curl -X POST http://localhost:9001/extract/DOC-A1B2C3D4

# Get result
curl http://localhost:9001/result/DOC-A1B2C3D4

# Normalize dates in raw text
curl -X POST http://localhost:9001/normalize-dates \
  -H "Content-Type: application/json" \
  -d '{"text": "२०८१ साल असार १५ मा बजेट पारित भयो"}'
```
