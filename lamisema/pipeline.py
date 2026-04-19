"""
LamiSema — Language-agnostic PDF extraction pipeline.

Usage (Nepali, default):
    from lamisema import LamiSema

    lamisema = LamiSema()
    with open("report.pdf", "rb") as f:
        result = lamisema.extract(f.read(), filename="report.pdf")

Usage (Hindi — once HindiNLPBackend is implemented):
    from lamisema import LamiSema
    from lamisema.nlp.hindi import HindiNLPBackend

    lamisema = LamiSema(nlp_backend=HindiNLPBackend())

Usage (English):
    from lamisema import LamiSema
    from lamisema.nlp.english import EnglishNLPBackend

    lamisema = LamiSema(nlp_backend=EnglishNLPBackend())
"""

import io
import logging
from typing import List, Optional

from lamisema.models import EncodingType, Entity, ExtractionResult, PageResult
from lamisema.nlp.base import NLPBackend
from lamisema.ocr.base import OCRBackend
from lamisema.preflight import PDFPreflightService
from lamisema.storage.base import StorageBackend

logger = logging.getLogger(__name__)


class LamiSema:
    """
    Language-agnostic PDF extraction pipeline.

    Orchestrates four stages:
      Stage 1: Pre-flight encoding detection (PDFPreflightService)
      Stage 2: Text extraction — text layer (unicode_native) or OCR (legacy/scanned)
      Stage 3: NLP analysis — script ratio, NER, normalization (NLPBackend)
      Stage 4: Confidence scoring per page and overall document

    The NLP layer and Storage layer are fully pluggable.
    To add a new language, implement NLPBackend and pass it here:

        lamisema = LamiSema(nlp_backend=HindiNLPBackend())

    To use persistent storage (e.g. Minio/S3) in the API:

        lamisema = LamiSema(storage=S3Storage())

    This class is stateless and safe to share across requests.
    """

    def __init__(
        self,
        preflight: Optional[PDFPreflightService] = None,
        nlp_backend: Optional[NLPBackend] = None,
        ocr_backend: Optional[OCRBackend] = None,
        storage: Optional[StorageBackend] = None,
    ):
        self.preflight = preflight or PDFPreflightService()
        self.nlp_backend = nlp_backend or self._default_nlp_backend()
        self.ocr_backend = ocr_backend or self._auto_select_ocr()
        self.storage = storage or self._default_storage()

    @staticmethod
    def _default_storage() -> StorageBackend:
        """Load the volatile in-memory storage (default)."""
        from lamisema.storage.memory import InMemoryStorage
        return InMemoryStorage()

    @staticmethod
    def _default_nlp_backend() -> NLPBackend:
        """Load the Nepali NLP backend (default language)."""
        from lamisema.nlp.nepali import NepaliNLPBackend
        return NepaliNLPBackend()

    @staticmethod
    def _auto_select_ocr() -> Optional[OCRBackend]:
        """Pick TesseractBackend if available, then EasyOCRBackend, then None."""
        try:
            import pytesseract  # noqa: F401

            from lamisema.ocr.tesseract import TesseractBackend
            return TesseractBackend()
        except ImportError:
            pass
        try:
            import easyocr  # noqa: F401

            from lamisema.ocr.easyocr import EasyOCRBackend
            return EasyOCRBackend()
        except ImportError:
            pass
        return None

    def extract(self, pdf_bytes: bytes, filename: str, doc_id: str = "DOC") -> ExtractionResult:
        """
        Run the full extraction pipeline on a PDF document.

        Args:
            pdf_bytes: Raw bytes of the PDF.
            filename:  Original file name (metadata only).
            doc_id:    Unique document identifier (used in log messages).

        Returns:
            ExtractionResult with per-page results, entities, and overall confidence.
        """
        flight = self.preflight.analyze(pdf_bytes, filename, doc_id)
        warnings: List[str] = []
        pages: List[PageResult] = []

        if flight.encoding_type == EncodingType.LEGACY_ENCODED:
            warnings.append(
                "Legacy font detected. "
                "Text layer was bypassed. Results from OCR — accuracy depends on scan quality."
            )

        if flight.encoding_type == EncodingType.UNICODE_NATIVE:
            pages = self._extract_text_layer(pdf_bytes, doc_id)
        elif self.ocr_backend is not None:
            pages = self._extract_via_ocr(pdf_bytes, doc_id, flight.page_count)
        else:
            warnings.append(
                "No OCR engine available. Install Tesseract "
                "(brew install tesseract && brew install tesseract-lang) "
                "or EasyOCR (pip install easyocr). Returning empty extraction."
            )
            pages = self._empty_pages(flight.page_count, doc_id)

        overall = sum(p.confidence for p in pages) / len(pages) if pages else 0.0

        return ExtractionResult(
            doc_id=doc_id,
            filename=filename,
            language=self.nlp_backend.language_code,
            encoding_type=flight.encoding_type,
            total_pages=flight.page_count,
            pages=pages,
            overall_confidence=round(overall, 4),
            ocr_backend=self.ocr_backend.name if self.ocr_backend else "none",
            warnings=warnings,
        )

    def _extract_text_layer(self, pdf_bytes: bytes, doc_id: str) -> List[PageResult]:
        """Direct text layer extraction via pdfplumber — only for UNICODE_NATIVE."""
        try:
            import pdfplumber
        except ImportError as exc:
            raise RuntimeError(
                "pdfplumber is required for Unicode-native PDF extraction. "
                "Run: pip install pdfplumber"
            ) from exc

        results = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for i, page in enumerate(pdf.pages):
                raw_text = page.extract_text() or ""
                entities: List[Entity] = self.nlp_backend.extract_entities(raw_text)
                script_ratio = self.nlp_backend.script_ratio(raw_text)
                confidence = self.nlp_backend.compute_confidence(raw_text, "text_layer")
                results.append(PageResult(
                    page_number=i + 1,
                    raw_text=raw_text,
                    script_ratio=script_ratio,
                    entities=entities,
                    extraction_method="text_layer",
                    confidence=confidence,
                ))
                logger.info(f"[{doc_id}] Page {i+1}: text_layer, {len(raw_text)} chars, conf={confidence}")
        return results

    def _extract_via_ocr(self, pdf_bytes: bytes, doc_id: str, page_count: int) -> List[PageResult]:
        """
        Render each page at 300 DPI via PyMuPDF, then pass PNG bytes to the OCR backend.

        300 DPI is the minimum for reliable Devanagari recognition — lower resolution
        causes character confusion on visually similar shapes (e.g. ग vs ग़, ध vs ब).
        """
        try:
            import fitz
        except ImportError:
            logger.warning(f"[{doc_id}] PyMuPDF unavailable — cannot render pages for OCR")
            return self._empty_pages(page_count, doc_id)

        results = []
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        dpi_matrix = fitz.Matrix(300 / 72, 300 / 72)

        for i in range(len(doc)):
            pix = doc[i].get_pixmap(matrix=dpi_matrix, colorspace=fitz.csRGB)
            image_bytes = pix.tobytes("png")

            raw_text = self.ocr_backend.extract_text(image_bytes)
            entities: List[Entity] = self.nlp_backend.extract_entities(raw_text)
            script_ratio = self.nlp_backend.script_ratio(raw_text)
            confidence = self.nlp_backend.compute_confidence(raw_text, self.ocr_backend.name)

            results.append(PageResult(
                page_number=i + 1,
                raw_text=raw_text,
                script_ratio=script_ratio,
                entities=entities,
                extraction_method=self.ocr_backend.name,
                confidence=confidence,
            ))
            logger.info(f"[{doc_id}] Page {i+1}: {self.ocr_backend.name}, {len(raw_text)} chars, conf={confidence}")

        doc.close()
        return results

    def _empty_pages(self, page_count: int, doc_id: str) -> List[PageResult]:
        logger.warning(f"[{doc_id}] Returning empty extraction — no OCR engine available")
        return [
            PageResult(
                page_number=i + 1,
                raw_text="",
                script_ratio=0.0,
                entities=[],
                extraction_method="none",
                confidence=0.0,
            )
            for i in range(page_count)
        ]


# Backward-compatible alias — kept so existing code does not break
NepaliPDFExtractionPipeline = LamiSema
