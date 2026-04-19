"""
NepaliNLPBackend — the default NLP backend for LamiSema.

Implements NLPBackend for Nepali/Devanagari documents.
Handles Devanagari ratio scoring, rule-based NER, and BS date normalization.

To add a new language, implement NLPBackend in a new file (e.g. nlp/hindi.py)
following the same pattern as this class.
"""

import re
from typing import List

from lamisema.constants import DEVANAGARI_RANGE
from lamisema.models import Entity
from lamisema.nlp import ner
from lamisema.nlp.base import NLPBackend


class NepaliNLPBackend(NLPBackend):
    """
    Nepali language NLP backend (default).

    - language_code: 'ne'
    - ocr_language:  'nep+eng'
    - script_ratio:  Fraction of Devanagari Unicode block characters
    - extract_entities: Rule-based NER (DATE_BS, CURRENCY, ORGANIZATION, ...)
    - compute_confidence: 60% method reliability + 40% Devanagari ratio
    """

    @property
    def language_code(self) -> str:
        return "ne"

    @property
    def ocr_language(self) -> str:
        return "nep+eng"

    def script_ratio(self, text: str) -> float:
        """
        Fraction of characters in the Devanagari Unicode block (U+0900–U+097F).

        > 0.3  → meaningful Devanagari content
        < 0.05 → likely a failed OCR page or non-Nepali document
        = 0.0  → no Devanagari (empty, header-only, etc.)
        """
        if not text:
            return 0.0
        dev_chars = sum(
            1 for ch in text
            if DEVANAGARI_RANGE[0] <= ord(ch) <= DEVANAGARI_RANGE[1]
        )
        return dev_chars / len(text)

    def extract_entities(self, text: str) -> List[Entity]:
        """Delegate to the Nepali rule-based NER module."""
        return ner.extract_entities(text)

    def compute_confidence(self, text: str, extraction_method: str) -> float:
        """
        Per-page confidence score in [0.0, 1.0].

        Weighted: 60% method reliability baseline + 40% Devanagari ratio signal.
        Very short texts (<10 chars) return 0.05 regardless of method.
        """
        if not text or len(text) < 10:
            return 0.05

        ratio = self.script_ratio(text)
        method_base = {
            "text_layer": 0.90,
            "tesseract": 0.72,
            "easyocr": 0.75,
        }.get(extraction_method, 0.50)

        return round(min((method_base * 0.60) + (ratio * 0.40), 1.0), 4)

    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize Nepali text respecting Devanagari sentence markers.

        Uses ।  (U+0964, danda) and ॥ (U+0965, double danda) as sentence
        terminators, in addition to standard ASCII punctuation.
        """
        tokens = re.split(r"[\s।॥,;:!?\.\-\(\)\"\']+", text)
        return [t.strip() for t in tokens if t.strip()]


DevanagariTextAnalyzer = NepaliNLPBackend
