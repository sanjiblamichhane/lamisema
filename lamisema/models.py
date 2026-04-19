"""Pydantic data models for the LamiSema extraction pipeline."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class EncodingType(str, Enum):
    """
    The three categories of PDF encoding that require different extraction strategies.

    Routing to the wrong extractor causes silent data corruption:
    - UNICODE_NATIVE  → safe for text layer extraction
    - LEGACY_ENCODED  → must use OCR; text layer contains legacy-font garbage
    - SCANNED         → no text layer; render at 300 DPI then OCR
    - UNKNOWN         → pre-flight could not determine type
    """
    UNICODE_NATIVE = "unicode_native"
    LEGACY_ENCODED = "legacy_encoded"
    SCANNED = "scanned"
    UNKNOWN = "unknown"


class FontInfo(BaseModel):
    """Represents a single font found in the PDF."""
    name: str = Field(description="Font name as stored in the PDF")
    encoding: Optional[str] = Field(None, description="Font encoding (e.g. WinAnsiEncoding)")
    is_legacy_nepali: bool = Field(description="True if this font silently corrupts text extraction")


class PreflightResult(BaseModel):
    """
    Output of Stage 1 (PDF Pre-flight Analysis).

    Read encoding_type first — it is the routing decision field.
    """
    doc_id: str
    filename: str
    page_count: int
    encoding_type: EncodingType
    fonts: List[FontInfo]
    has_text_layer: bool = Field(description="False means the PDF is a scanned image")
    recommended_strategy: str = Field(description="Human-readable extraction recommendation")


class Entity(BaseModel):
    """A named entity detected by the NLP backend."""
    text: str = Field(description="Exact surface form from the document")
    entity_type: str = Field(description="Entity class (e.g. DATE_BS, CURRENCY, ORGANIZATION, DISTRICT)")
    normalized: Optional[str] = Field(None, description="Normalized form (e.g. AD date string, canonical name)")
    confidence: float = Field(ge=0.0, le=1.0)


# Backward-compatible alias — kept so existing code does not break
NepaliEntity = Entity


class PageResult(BaseModel):
    """Extraction result for a single PDF page."""
    page_number: int
    raw_text: str = Field(description="Extracted text (may be empty for fully scanned pages)")
    script_ratio: float = Field(ge=0.0, le=1.0, description="Fraction of chars in the primary script of the active language")
    entities: List[Entity]
    extraction_method: str = Field(description="text_layer | tesseract | easyocr")
    confidence: float = Field(ge=0.0, le=1.0)

    # Backward-compatible alias
    @property
    def devanagari_ratio(self) -> float:
        return self.script_ratio


class ExtractionResult(BaseModel):
    """Complete extraction result for an uploaded document."""
    doc_id: str
    filename: str
    language: str = Field(default="ne", description="ISO 639-1 language code of the active NLP backend (e.g. 'ne', 'hi', 'en')")
    encoding_type: EncodingType
    total_pages: int
    pages: List[PageResult]
    overall_confidence: float = Field(ge=0.0, le=1.0)
    ocr_backend: str = Field(description="OCR backend used: tesseract | easyocr | none")
    warnings: List[str] = Field(default_factory=list)


class DateNormalizationRequest(BaseModel):
    """Request body for the /normalize-dates endpoint."""
    text: str = Field(description="Raw Nepali text possibly containing BS dates")


class DateNormalizationResponse(BaseModel):
    """All BS date occurrences found and normalized from the input text."""
    original_text: str
    normalized_dates: List[NepaliEntity]
    processed_text: str = Field(description="Input text with BS dates replaced by AD equivalents")
