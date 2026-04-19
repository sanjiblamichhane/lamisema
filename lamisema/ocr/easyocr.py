"""
EasyOCR backend for LamiSema.

Use this when Tesseract is not available or for comparison.
EasyOCR supports Hindi/Devanagari via the 'hi' language code,
which covers Nepali text.

Requires:
    pip install easyocr
"""

import logging

from lamisema.ocr.base import OCRBackend

logger = logging.getLogger(__name__)


class EasyOCRBackend(OCRBackend):
    """
    OCR backend using EasyOCR with Hindi (Devanagari) + English.

    The EasyOCR reader is initialized lazily on first use and reused
    across calls — initialization downloads ~200MB of model weights.
    """

    def __init__(self, use_gpu: bool = False):
        self._use_gpu = use_gpu
        self._reader = None

    @property
    def name(self) -> str:
        return "easyocr"

    def _get_reader(self):
        if self._reader is None:
            try:
                import easyocr
            except ImportError as exc:
                raise RuntimeError(
                    "EasyOCR backend requires the easyocr package. "
                    "Run: pip install easyocr"
                ) from exc
            logger.info("Initializing EasyOCR reader (first-time download may take a moment)")
            self._reader = easyocr.Reader(["hi", "en"], gpu=self._use_gpu)
        return self._reader

    def extract_text(self, image_bytes: bytes) -> str:
        reader = self._get_reader()
        results = reader.readtext(image_bytes)
        return " ".join(text for (_, text, _) in results)
