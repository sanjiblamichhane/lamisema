"""
DevanagariTextAnalyzer — orchestrates the symbolic NLP layer.

Combines Devanagari ratio scoring, tokenization, NER, and confidence
scoring into a single composable object used by the extraction pipeline.
"""

import re
from typing import List

from lamisema.constants import DEVANAGARI_RANGE
from lamisema.models import NepaliEntity
from lamisema.nlp import ner


class DevanagariTextAnalyzer:
    """
    Stage 2 of the extraction pipeline: symbolic NLP analysis.

    - devanagari_ratio: measures extraction quality (Devanagari character fraction)
    - tokenize:         splits text on Devanagari and ASCII punctuation
    - extract_entities: rule-based NER (dates, currency, organizations)
    - compute_confidence: per-page quality score combining method + ratio signal
    """

    def devanagari_ratio(self, text: str) -> float:
        """
        Fraction of characters in the Devanagari Unicode block (U+0900–U+097F).

        > 0.3  → meaningful Devanagari content
        < 0.05 → likely a failed OCR page or pure-English document
        = 0.0  → no Devanagari (empty, header-only, etc.)
        """
        if not text:
            return 0.0
        dev_chars = sum(1 for ch in text if DEVANAGARI_RANGE[0] <= ord(ch) <= DEVANAGARI_RANGE[1])
        return dev_chars / len(text)

    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize Nepali text respecting Devanagari sentence markers.

        Uses ।  (U+0964, danda) and ॥ (U+0965, double danda) as sentence
        terminators, in addition to standard ASCII punctuation.
        """
        tokens = re.split(r"[\s।॥,;:!?\.\-\(\)\"\']+", text)
        return [t.strip() for t in tokens if t.strip()]

    def extract_entities(self, text: str) -> List[NepaliEntity]:
        """Delegate to the rule-based NER module."""
        return ner.extract_entities(text)

    def compute_confidence(self, text: str, extraction_method: str) -> float:
        """
        Per-page extraction confidence score in [0.0, 1.0].

        Weighted: 60% method reliability baseline + 40% Devanagari ratio signal.
        Very short texts (<10 chars) return 0.05 regardless of method.
        """
        if not text or len(text) < 10:
            return 0.05

        dev_ratio = self.devanagari_ratio(text)
        method_base = {
            "text_layer": 0.90,
            "tesseract": 0.72,
            "easyocr": 0.75,
        }.get(extraction_method, 0.50)

        return round(min((method_base * 0.60) + (dev_ratio * 0.40), 1.0), 4)
