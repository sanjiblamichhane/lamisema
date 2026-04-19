"""
Tesseract OCR backend for LamiSema.

Requires:
    brew install tesseract tesseract-lang   # macOS
    # apt-get install tesseract-ocr tesseract-ocr-nep   # Ubuntu
    pip install pytesseract Pillow

Verify Nepali language pack is installed:
    tesseract --list-langs | grep nep
"""

import io
import logging

from lamisema.ocr.base import OCRBackend

logger = logging.getLogger(__name__)


class TesseractBackend(OCRBackend):
    """
    OCR backend using Tesseract with the Nepali language pack.

    Runs Tesseract with lang="nep+eng". Falls back to lang="eng" if the
    nep traineddata is not installed (with a warning logged).
    """

    @property
    def name(self) -> str:
        return "tesseract"

    def extract_text(self, image_bytes: bytes) -> str:
        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError(
                "Tesseract backend requires pytesseract and Pillow. "
                "Run: pip install pytesseract Pillow"
            ) from exc

        img = Image.open(io.BytesIO(image_bytes))
        try:
            return pytesseract.image_to_string(img, lang="nep+eng")
        except pytesseract.TesseractError:
            logger.warning("nep language pack not found — falling back to eng-only Tesseract")
            return pytesseract.image_to_string(img, lang="eng")
