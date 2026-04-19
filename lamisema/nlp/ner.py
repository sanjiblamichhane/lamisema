"""
Rule-based named entity recognition for Nepali text.

All patterns are deterministic regex grammars — no ML model required.
This means zero inference cost and full explainability.

Detected entity types:
    DATE_BS      — Bikram Sambat full dates and year references
    CURRENCY     — NPR amounts (Devanagari or ASCII digits)
    ORGANIZATION — Nepali org names identified by suffix matching
"""

import re
from typing import List

from lamisema.constants import DEVANAGARI_DIGIT_MAP, NEPALI_ORG_SUFFIXES
from lamisema.models import Entity
from lamisema.nlp.dates import (
    RE_BS_DATE_FULL,
    RE_BS_YEAR_ONLY,
    bs_year_to_ad,
    normalize_bs_date,
)

_RE_CURRENCY_NPR = re.compile(
    r"(?:रु\.?|NPR|नेरु)\s*([०-९0-9,\.]+)"
)

_RE_ORG = re.compile(
    r"[\u0900-\u097F\s]+(?:" + "|".join(NEPALI_ORG_SUFFIXES) + r")"
)


def extract_entities(text: str) -> List[Entity]:
    """
    Run rule-based NER on extracted text.

    Args:
        text: Extracted text (Unicode).

    Returns:
        List of Entity objects.
    """
    entities: List[Entity] = []

    # Full BS dates: "२०८१ साल असार १५"
    for match in RE_BS_DATE_FULL.finditer(text):
        normalized = normalize_bs_date(match.group(1), match.group(2), match.group(3))
        entities.append(Entity(
            text=match.group(0).strip(),
            entity_type="DATE_BS",
            normalized=normalized,
            confidence=0.90,
        ))

    # Year-only BS references: "२०८१ साल"
    for match in RE_BS_YEAR_ONLY.finditer(text):
        ad_year = bs_year_to_ad(match.group(1))
        entities.append(Entity(
            text=match.group(0).strip(),
            entity_type="DATE_BS",
            normalized=f"~{ad_year} AD" if ad_year else None,
            confidence=0.80,
        ))

    # NPR currency: "रु. १२,५०० " or "NPR 12,500"
    for match in _RE_CURRENCY_NPR.finditer(text):
        amount_raw = match.group(1).translate(DEVANAGARI_DIGIT_MAP).replace(",", "")
        entities.append(Entity(
            text=match.group(0).strip(),
            entity_type="CURRENCY",
            normalized=f"NPR {amount_raw}",
            confidence=0.85,
        ))

    # Organizations by suffix
    for match in _RE_ORG.finditer(text):
        org_text = match.group(0).strip()
        if len(org_text) > 3:
            entities.append(Entity(
                text=org_text,
                entity_type="ORGANIZATION",
                normalized=None,
                confidence=0.70,
            ))

    return entities
