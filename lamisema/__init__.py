"""
LamiSema — Language-agnostic PDF extraction pipeline.

Quick start (Nepali, default):
    from lamisema import LamiSema

    lamisema = LamiSema()
    with open("report.pdf", "rb") as f:
        result = lamisema.extract(f.read(), filename="report.pdf")

    print(result.language)           # "ne"
    print(result.encoding_type)      # "legacy_encoded"
    print(result.overall_confidence) # 0.74
    print(result.pages[0].entities)  # [Entity(entity_type="DATE_BS", ...)]

Extend to another language:
    from lamisema import LamiSema
    from lamisema.nlp.hindi import HindiNLPBackend  # when implemented

    lamisema = LamiSema(nlp_backend=HindiNLPBackend())
"""

from lamisema.models import (
    EncodingType,
    Entity,
    ExtractionResult,
    FontInfo,
    NepaliEntity,   # backward-compat alias for Entity
    PageResult,
    PreflightResult,
)
from lamisema.nlp.base import NLPBackend
from lamisema.nlp.nepali import NepaliNLPBackend
from lamisema.pipeline import LamiSema, NepaliPDFExtractionPipeline
from lamisema.preflight import PDFPreflightService
from lamisema.storage.base import StorageBackend
from lamisema.storage.memory import InMemoryStorage as DocumentStore

__version__ = "1.0.0"

__all__ = [
    # Primary pipeline class
    "LamiSema",
    # Backward-compatible alias
    "NepaliPDFExtractionPipeline",
    # NLP backend interface + default implementation
    "NLPBackend",
    "NepaliNLPBackend",
    # Supporting classes
    "PDFPreflightService",
    "DocumentStore",
    "StorageBackend",
    # Data models
    "EncodingType",
    "Entity",
    "NepaliEntity",   # backward-compat alias for Entity
    "ExtractionResult",
    "FontInfo",
    "PageResult",
    "PreflightResult",
]
