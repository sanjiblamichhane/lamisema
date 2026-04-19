# Python API

## Quick reference

```python
from lamisema import LamiSema

lamisema = LamiSema()

with open("report.pdf", "rb") as f:
    result = lamisema.extract(f.read(), filename="report.pdf")

result.encoding_type        # "unicode_native" | "legacy_encoded" | "scanned"
result.language             # "ne" (or active language code)
result.overall_confidence   # 0.0 – 1.0
result.ocr_backend          # "tesseract" | "easyocr" | "none"
result.warnings             # list of str
result.pages[0].raw_text    # extracted text for page 1
result.pages[0].entities    # list of Entity
result.pages[0].script_ratio # fraction of chars in script (Devanagari/Latin/etc)
result.pages[0].confidence  # per-page confidence score
```

---

## LamiSema

The main entry point. `LamiSema` is the canonical alias — `NepaliPDFExtractionPipeline` is identical and also exported for verbose usage. Both are stateless and safe to share across threads and requests.

```python
from lamisema import LamiSema
from lamisema.ocr import TesseractBackend, EasyOCRBackend
from lamisema.storage.s3 import S3Storage

# Default: auto-selects OCR, Nepali NLP, and InMemoryStorage.
lamisema = LamiSema()

# Explicit S3 Storage + Tesseract
lamisema = LamiSema(
    ocr_backend=TesseractBackend(),
    storage=S3Storage()
)
```


### `.extract(pdf_bytes, filename, doc_id="DOC")`

Run the full four-stage pipeline.

| Parameter | Type | Description |
|---|---|---|
| `pdf_bytes` | `bytes` | Raw PDF content |
| `filename` | `str` | Original filename (metadata only) |
| `doc_id` | `str` | Identifier for log messages (optional) |

Returns: `ExtractionResult`

---

## PDFPreflightService

Run Stage 1 encoding detection without extraction.

```python
from lamisema import PDFPreflightService

svc = PDFPreflightService()

with open("report.pdf", "rb") as f:
    result = svc.analyze(f.read(), filename="report.pdf", doc_id="DOC-001")

result.encoding_type          # EncodingType enum
result.fonts                  # list of FontInfo
result.has_text_layer         # bool
result.recommended_strategy   # human-readable string
```

---

## Data Models

### `ExtractionResult`

| Field | Type | Description |
|---|---|---|
| `doc_id` | `str` | Document identifier |
| `filename` | `str` | Original filename |
| `encoding_type` | `EncodingType` | Detected encoding |
| `total_pages` | `int` | Page count |
| `pages` | `list[PageResult]` | Per-page results |
| `overall_confidence` | `float` | Mean confidence across pages |
| `ocr_backend` | `str` | Backend used: `tesseract`, `easyocr`, or `none` |
| `warnings` | `list[str]` | Non-fatal warnings |

### `PageResult`

| Field | Type | Description |
|---|---|---|
| `page_number` | `int` | 1-indexed page number |
| `raw_text` | `str` | Extracted text |
| `script_ratio` | `float` | Fraction of chars in target script (e.g. Devanagari) |
| `entities` | `list[Entity]` | Detected named entities |
| `extraction_method` | `str` | `text_layer`, `tesseract`, or `easyocr` |
| `confidence` | `float` | Per-page confidence score |

### `Entity`

| Field | Type | Description |
|---|---|---|
| `text` | `str` | Surface form from the document |
| `entity_type` | `str` | Entity class (see below) |
| `normalized` | `str | None` | Normalized form (e.g. AD date string, `NPR 12500`) |
| `confidence` | `float` | Rule match confidence |

**Entity types (v1.x and roadmap):**

| Type | Example | Status |
|---|---|---|
| `DATE_BS` | `२०८१ साल असार १५` | ✅ v1.0 |
| `CURRENCY` | `रु. १२,५००` | ✅ v1.0 |
| `ORGANIZATION` | `अर्थ मन्त्रालय` | ✅ v1.0 |
| `WARD_CODE` | `वडा नं. ४` | v1.2 |
| `VDC_MUNICIPALITY` | `काठमाडौं महानगरपालिका` | v1.2 |
| `DISTRICT` | `सिन्धुपाल्चोक` | v1.2 |
| `PROVINCE` | `बागमती प्रदेश` | v1.2 |
| `LAND_PARCEL` | `कि.नं. ४५२` | v1.2 |
| `PERSON_NAME_NE` | `श्री राम बहादुर थापा` | v1.2 |
| `PHONE_NE` | `९८४१२३४५६७` | v1.2 |
| `COURT_CASE` | `मिसिल नं. ०७८-CR-०४५` | v1.2 |
| `GAZETTE_REF` | `नेपाल राजपत्र भाग ३` | v1.2 |
| `GOV_POSITION` | `सचिव` | v1.2 |

### `EncodingType`

```python
from lamisema.models import EncodingType

EncodingType.UNICODE_NATIVE   # "unicode_native"
EncodingType.LEGACY_ENCODED   # "legacy_encoded"
EncodingType.SCANNED          # "scanned"
EncodingType.UNKNOWN          # "unknown"
```

---

## Custom OCR Backend

Implement `OCRBackend` to plug in any OCR engine:

```python
from lamisema.ocr import OCRBackend
from lamisema import LamiSema

class GeminiVisionBackend(OCRBackend):
    @property
    def name(self) -> str:
        return "gemini-vision"

    def extract_text(self, image_bytes: bytes) -> str:
        # Call Gemini Vision API with image_bytes
        ...

lamisema = LamiSema(
    ocr_backend=GeminiVisionBackend()
)
```

---

## Bikram Sambat normalization (standalone)

```python
from lamisema.nlp.dates import normalize_bs_date, bs_year_to_ad

normalize_bs_date("2081", "असार", "15")
# → "~2024-06-29 AD (approx)"

normalize_bs_date("२०८१", "असार", "१५")
# → "~2024-06-29 AD (approx)"

bs_year_to_ad("२०८१")
# → 2025
```

## Rule-based NER (standalone)

```python
from lamisema.nlp.ner import extract_entities

entities = extract_entities("अर्थ मन्त्रालयले २०८१ साल असार १५ मा रु. १२,५०० को बजेट पारित गर्यो।")

for e in entities:
    print(e.entity_type, e.text, e.normalized)
# DATE_BS    २०८१ साल असार १५    ~2024-06-29 AD (approx)
# CURRENCY   रु. १२,५००           NPR 12500
# ORGANIZATION  अर्थ मन्त्रालय     None
```
