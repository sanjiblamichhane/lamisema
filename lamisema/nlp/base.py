"""
Abstract NLP backend interface for LamiSema.

Implement this interface to add support for a new language or script:

    class EnglishNLPBackend(NLPBackend):
        language_code = "en"
        ...

    from lamisema import LamiSema
    lamisema = LamiSema(nlp_backend=EnglishNLPBackend())

The Nepali implementation (NepaliNLPBackend) is the default backend and
lives in lamisema/nlp/nepali.py.
"""

from abc import ABC, abstractmethod
from typing import List

from lamisema.models import Entity


class NLPBackend(ABC):
    """
    Interface that all language-specific NLP backends must implement.

    A backend receives extracted text and returns named entities,
    a script quality ratio, and per-page confidence scores.

    To add a new language:
    1. Create a class that inherits from NLPBackend
    2. Implement all abstract methods
    3. Pass an instance to LamiSema(nlp_backend=YourBackend())
    """

    @property
    @abstractmethod
    def language_code(self) -> str:
        """
        ISO 639-1 language code (e.g. 'ne', 'hi', 'en').
        Used in ExtractionResult.language and for OCR language hints.
        """
        ...

    @property
    @abstractmethod
    def ocr_language(self) -> str:
        """
        Tesseract language string (e.g. 'nep+eng', 'hin+eng', 'eng').
        Passed to the OCR backend when rendering legacy/scanned pages.
        """
        ...

    @abstractmethod
    def script_ratio(self, text: str) -> float:
        """
        Fraction of characters in the primary script of this language.

        Used as an extraction quality signal — a high ratio means the
        extracted text contains real content in the expected script.

        Args:
            text: Extracted text string.

        Returns:
            Float in [0.0, 1.0].
        """
        ...

    @abstractmethod
    def extract_entities(self, text: str) -> List[Entity]:
        """
        Run rule-based named entity recognition on extracted text.

        Args:
            text: Extracted text in the target language.

        Returns:
            List of Entity objects with type, surface form, normalized value.
        """
        ...

    @abstractmethod
    def compute_confidence(self, text: str, extraction_method: str) -> float:
        """
        Per-page extraction confidence score in [0.0, 1.0].

        Args:
            text:              Extracted text for this page.
            extraction_method: 'text_layer', 'tesseract', 'easyocr', etc.

        Returns:
            Float confidence score.
        """
        ...
