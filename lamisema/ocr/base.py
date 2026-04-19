"""
Abstract OCR backend interface for LamiSema.

Swap backends without changing pipeline logic:
    lamisema = LamiSema(ocr_backend=TesseractBackend())
    lamisema = LamiSema(ocr_backend=EasyOCRBackend())
"""

from abc import ABC, abstractmethod
from typing import List


class OCRBackend(ABC):
    """
    Interface that all OCR backends must implement.

    A backend receives a rendered page image (PNG bytes at 300 DPI) and
    returns the extracted text. All language/config concerns are internal.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier used in PageResult.extraction_method."""
        ...

    @abstractmethod
    def extract_text(self, image_bytes: bytes) -> str:
        """
        Extract text from a rendered PDF page image.

        Args:
            image_bytes: PNG bytes of a single PDF page rendered at 300 DPI.

        Returns:
            Extracted text string (may be empty if OCR finds nothing).
        """
        ...
