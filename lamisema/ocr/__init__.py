"""Pluggable OCR backends for LamiSema."""

from lamisema.ocr.base import OCRBackend
from lamisema.ocr.easyocr import EasyOCRBackend
from lamisema.ocr.tesseract import TesseractBackend

__all__ = ["OCRBackend", "TesseractBackend", "EasyOCRBackend"]
