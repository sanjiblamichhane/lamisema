# Installation

## Requirements

- Python 3.10, 3.11, or 3.12
- Tesseract OCR with Nepali language pack (for legacy/scanned PDFs)

---

## Install LamiSema

```bash
pip install lamisema
```

This installs the core pipeline with pdfplumber and PyMuPDF. Tesseract is not bundled — it is a system binary installed separately.

### Install with S3/Minio support

```bash
pip install "lamisema[s3]"
```

This adds `boto3` for persistence to S3-compatible object storage.

### Install all extras

```bash
pip install "lamisema[all]"
```

This includes Tesseract support, EasyOCR, and S3 persistence drivers.

### Install from source

```bash
git clone https://github.com/sanjiblamichhane/lamisema
cd lamisema
pip install -e .
```

---

## Install Tesseract

Tesseract is required for legacy-encoded and scanned PDFs. The Nepali language pack (`nep`) must be installed alongside the binary.

=== "macOS"

    ```bash
    brew install tesseract tesseract-lang
    tesseract --list-langs | grep nep   # verify
    ```

=== "Ubuntu / Debian"

    ```bash
    sudo apt-get install tesseract-ocr tesseract-ocr-nep
    tesseract --list-langs | grep nep   # verify
    ```

=== "Windows"

    Download the installer from the [Tesseract GitHub releases](https://github.com/tesseract-ocr/tesseract/releases).
    During installation, select **Nepali** from the additional language packs list.

---

## Verify installation

```python
from lamisema import LamiSema

lamisema = LamiSema()
print(lamisema.ocr_backend)   # TesseractBackend or EasyOCRBackend or None
print(lamisema.storage)       # InMemoryStorage (default)
```

Or start the API server and hit the health endpoint:

```bash
lamisema serve
# → http://localhost:9001/
```

The response shows which libraries and storage backends are active:

```json
{
  "status": "online",
  "libraries": {
    "PyMuPDF": true,
    "pdfplumber": true,
    "pytesseract": true,
    "easyocr": false
  },
  "ocr_backend": "tesseract",
  "storage_backend": "InMemoryStorage"
}
```

---

## Running the API server

```bash
# via installed CLI (Recommended)
lamisema serve

# via Python module
python -m lamisema.api.app

# via uvicorn directly (with persistent storage fallback test)
export LAMI_STORAGE_TYPE=s3
uvicorn lamisema.api.app:app --port 9001 --reload
```

Interactive docs: `http://localhost:9001/docs`
