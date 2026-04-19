"""Pluggable OCR backends for LamiSema."""

from lamisema.ocr.base import OCRBackend
from lamisema.ocr.tesseract import TesseractBackend
from lamisema.ocr.easyocr import EasyOCRBackend

__all__ = ["OCRBackend", "TesseractBackend", "EasyOCRBackend"]
