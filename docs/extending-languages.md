# Extending LamiSema to Other Languages

LamiSema is built around a pluggable `NLPBackend` interface. Adding a new language requires implementing one class — the rest of the pipeline (encoding detection, OCR routing, confidence scoring, REST API) works unchanged.

---

## How It Works

The pipeline is split into two independent layers:

| Layer | Interface | What it does | Language-specific? |
|---|---|---|---|
| **PDF routing** | `PDFPreflightService` | Detects encoding type, routes to text layer or OCR | No — works for any PDF |
| **NLP analysis** | `NLPBackend` | Script ratio, entity extraction, confidence scoring | **Yes — one per language** |

When you call `LamiSema(nlp_backend=YourBackend())`, only the NLP layer changes. Everything else is identical.

---

## The `NLPBackend` Interface

```python
from abc import ABC, abstractmethod
from typing import List
from lamisema.models import Entity

class NLPBackend(ABC):

    @property
    @abstractmethod
    def language_code(self) -> str:
        """ISO 639-1 code, e.g. 'ne', 'hi', 'en', 'mai'"""
        ...

    @property
    @abstractmethod
    def ocr_language(self) -> str:
        """Tesseract language string, e.g. 'nep+eng', 'hin+eng', 'eng'"""
        ...

    @abstractmethod
    def script_ratio(self, text: str) -> float:
        """Fraction of characters in the primary script. Used as quality signal."""
        ...

    @abstractmethod
    def extract_entities(self, text: str) -> List[Entity]:
        """Run NER on extracted text. Return empty list if not implemented."""
        ...

    @abstractmethod
    def compute_confidence(self, text: str, extraction_method: str) -> float:
        """Per-page confidence score in [0.0, 1.0]."""
        ...
```

---

## Step-by-Step: Adding a New Language

### 1. Create the backend file

Create `lamisema/nlp/<language>.py`. Use `lamisema/nlp/nepali.py` as your reference implementation.

### 2. Implement `NLPBackend`

Minimum viable implementation — add NER patterns incrementally:

```python
# lamisema/nlp/english.py
import re
from typing import List
from lamisema.models import Entity
from lamisema.nlp.base import NLPBackend

# ASCII/Latin character range used as the primary script signal for English
_LATIN_RANGE = (0x0020, 0x007E)

class EnglishNLPBackend(NLPBackend):

    @property
    def language_code(self) -> str:
        return "en"

    @property
    def ocr_language(self) -> str:
        return "eng"  # Tesseract default

    def script_ratio(self, text: str) -> float:
        """Fraction of printable ASCII characters."""
        if not text:
            return 0.0
        latin = sum(1 for ch in text if _LATIN_RANGE[0] <= ord(ch) <= _LATIN_RANGE[1])
        return latin / len(text)

    def extract_entities(self, text: str) -> List[Entity]:
        """
        Add English-specific NER patterns here.
        Return an empty list until patterns are implemented.
        """
        entities = []
        # TODO: DATE patterns (YYYY-MM-DD, Month DD YYYY), USD/GBP currency,
        #       organization suffixes (Ltd, Inc, Corp, plc), etc.
        return entities

    def compute_confidence(self, text: str, extraction_method: str) -> float:
        if not text or len(text) < 10:
            return 0.05
        ratio = self.script_ratio(text)
        method_base = {
            "text_layer": 0.90,
            "tesseract": 0.72,
            "easyocr": 0.75,
        }.get(extraction_method, 0.50)
        return round(min((method_base * 0.60) + (ratio * 0.40), 1.0), 4)
```

### 3. Use it

```python
from lamisema import LamiSema
from lamisema.nlp.english import EnglishNLPBackend

lamisema = LamiSema(nlp_backend=EnglishNLPBackend())

with open("report.pdf", "rb") as f:
    result = lamisema.extract(f.read(), filename="report.pdf")

print(result.language)   # "en"
print(result.pages[0].entities)
```

### 4. Install the Tesseract language pack

```bash
# Ubuntu / Debian
sudo apt-get install tesseract-ocr-eng   # usually pre-installed

# macOS (all language packs included)
brew install tesseract tesseract-lang

# Verify
tesseract --list-langs | grep eng
```

---

## Language Support Matrix

| Language | Code | Tesseract pack | Backend | Status |
|---|---|---|---|---|
| Nepali (नेपाली) | `ne` | `nep` | `NepaliNLPBackend` | ✅ Default |
| Hindi (हिन्दी) | `hi` | `hin` | — | Planned |
| English | `en` | `eng` | — | Planned |
| Maithili (मैथिली) | `mai` | `mai` | — | Planned |
| Newari (नेवारी) | `new` | — | — | Research |

---

## What Each Language Backend Should Implement

| Feature | Required | Notes |
|---|---|---|
| `language_code` | ✅ | ISO 639-1 code |
| `ocr_language` | ✅ | Tesseract language string |
| `script_ratio` | ✅ | Quality signal for extraction |
| `compute_confidence` | ✅ | Per-page score |
| `extract_entities` | Optional | Can return `[]` — add NER incrementally |
| Date normalization | Optional | Language-specific calendar handling |
| Currency patterns | Optional | NPR, INR, USD, etc. |

---

## Notes

- **The OCR backend is separate from the NLP backend.** The same `TesseractBackend` works for all languages; it reads `nlp_backend.ocr_language` to choose the recognition model.
- **Devanagari script is shared** across Nepali, Hindi, Maithili, and Sanskrit. The `script_ratio` logic from `NepaliNLPBackend` can be reused as-is for any Devanagari-script language.
- **NER is purely additive.** You can ship a backend with an empty `extract_entities` and add patterns in later versions without breaking the interface.
