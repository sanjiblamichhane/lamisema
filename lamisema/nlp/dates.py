"""
Bikram Sambat (BS) → Gregorian (AD) date normalization.

Conversion is approximate (±1 day). For exact conversion, integrate the
`nepali-datetime` library: pip install nepali-datetime

Reference:
    https://en.wikipedia.org/wiki/Bikram_Samvat
"""

import re
from typing import Optional, Tuple

from lamisema.constants import (
    BS_MONTH_NAMES,
    BS_TO_AD_MONTH_OFFSET,
    BS_TO_AD_YEAR_OFFSET,
    DEVANAGARI_DIGIT_MAP,
)

# Full BS date: "२०८१ साल असार १५"
_RE_BS_DATE_FULL = re.compile(
    r"([०-९0-9]{4})\s*(?:साल|सन्)?\s*"
    r"(" + "|".join(BS_MONTH_NAMES.keys()) + r")\s*"
    r"([०-९0-9]{1,2})"
)

# Year-only BS reference: "२०८१ साल" or "2081 BS"
_RE_BS_YEAR_ONLY = re.compile(
    r"\b([२-२][०-९]{3})\s*(?:साल|सन्|B\.S\.|BS)\b"
)


def normalize_bs_date(bs_year_str: str, month_name: str, day_str: str) -> Optional[str]:
    """
    Convert a Bikram Sambat date triple to an approximate AD date string.

    Args:
        bs_year_str: BS year (may contain Devanagari digits).
        month_name:  Nepali month name (Devanagari).
        day_str:     Day of month (may contain Devanagari digits).

    Returns:
        Human-readable AD date string like "~2024-06-29 AD (approx)", or None.
    """
    try:
        bs_year = int(bs_year_str.translate(DEVANAGARI_DIGIT_MAP))
        bs_month = BS_MONTH_NAMES.get(month_name)
        bs_day = int(day_str.translate(DEVANAGARI_DIGIT_MAP))
        if bs_month is None:
            return None
        ad_year, ad_month = _bs_to_ad_approx(bs_year, bs_month)
        return f"~{ad_year}-{ad_month:02d}-{bs_day:02d} AD (approx)"
    except (ValueError, TypeError):
        return None


def bs_year_to_ad(bs_year_str: str) -> Optional[int]:
    """Convert a BS year string (Devanagari or ASCII digits) to an approximate AD year."""
    try:
        return int(bs_year_str.translate(DEVANAGARI_DIGIT_MAP)) - BS_TO_AD_YEAR_OFFSET
    except ValueError:
        return None


def _bs_to_ad_approx(bs_year: int, bs_month: int) -> Tuple[int, int]:
    """
    Approximate BS year+month → AD year+month.

    BS months 1–9 (Baishakh–Poush) fall in AD year = BS year - 57.
    BS months 10–12 (Magh–Chaitra) fall in AD year = BS year - 56.
    """
    ad_month = ((bs_month - 1 + BS_TO_AD_MONTH_OFFSET) % 12) + 1
    ad_year = bs_year - (BS_TO_AD_YEAR_OFFSET + 1) if bs_month <= 9 else bs_year - BS_TO_AD_YEAR_OFFSET
    return ad_year, ad_month


# Expose compiled regexes for use by the NER module
RE_BS_DATE_FULL = _RE_BS_DATE_FULL
RE_BS_YEAR_ONLY = _RE_BS_YEAR_ONLY
