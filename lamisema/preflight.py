"""
PDF pre-flight analysis — Stage 1 of the LamiSema pipeline.

Determines the encoding type of a Nepali PDF before any extraction is attempted.
This prevents the silent data corruption that occurs when Preeti-encoded PDFs
are passed through a standard text extractor.

Requires: PyMuPDF (pip install PyMuPDF)
"""

import logging
from typing import Dict, List

from lamisema.constants import LEGACY_NEPALI_FONTS
from lamisema.models import EncodingType, FontInfo, PreflightResult

logger = logging.getLogger(__name__)


class PDFPreflightService:
    """
    Analyzes a PDF to determine its encoding type before extraction.

    This is the most critical step in the pipeline. Without it, a Preeti-encoded
    PDF silently produces garbage output — no error is raised, the text just
    looks like "g]kfn" instead of "नेपाल".
    """

    def analyze(self, pdf_bytes: bytes, filename: str, doc_id: str) -> PreflightResult:
        """
        Perform full pre-flight analysis on a PDF.

        Args:
            pdf_bytes: Raw PDF file content.
            filename:  Original filename (metadata only).
            doc_id:    Unique document identifier assigned at upload.

        Returns:
            PreflightResult with encoding_type, font list, and strategy recommendation.

        Raises:
            RuntimeError: If PyMuPDF is not installed.
        """
        try:
            import fitz
        except ImportError as exc:
            raise RuntimeError(
                "PyMuPDF (fitz) is required for pre-flight analysis. "
                "Run: pip install PyMuPDF"
            ) from exc

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_count = len(doc)
        fonts = self._collect_fonts(doc)
        has_text_layer = self._has_text_layer(doc)
        encoding_type = self._determine_encoding_type(fonts, has_text_layer)
        doc.close()

        logger.info(f"[{doc_id}] Pre-flight: {encoding_type}, {page_count} pages, {len(fonts)} fonts")
        return PreflightResult(
            doc_id=doc_id,
            filename=filename,
            page_count=page_count,
            encoding_type=encoding_type,
            fonts=fonts,
            has_text_layer=has_text_layer,
            recommended_strategy=self._recommend_strategy(encoding_type),
        )

    def _collect_fonts(self, doc) -> List[FontInfo]:
        """
        Extract font metadata from all pages.

        PyMuPDF get_fonts() returns tuples: (xref, ext, type, basefont, name, encoding, ref).
        We strip subset prefixes (e.g. "ABCDEF+Preeti" → "Preeti") before checking.
        """
        seen: Dict[str, FontInfo] = {}
        for page in doc:
            for font_tuple in page.get_fonts(full=True):
                base_name = font_tuple[3] or ""
                encoding = font_tuple[5] or None
                clean_name = base_name.split("+")[-1].strip()
                if clean_name and clean_name not in seen:
                    seen[clean_name] = FontInfo(
                        name=clean_name,
                        encoding=encoding,
                        is_legacy_nepali=clean_name.lower() in {f.lower() for f in LEGACY_NEPALI_FONTS},
                    )
        return list(seen.values())

    def _has_text_layer(self, doc) -> bool:
        """Returns True if at least one of the first three pages has extractable text."""
        for i in range(min(3, len(doc))):
            if doc[i].get_text().strip():
                return True
        return False

    def _determine_encoding_type(self, fonts: List[FontInfo], has_text_layer: bool) -> EncodingType:
        """
        Route to encoding category.

        Priority:
        1. Legacy font → LEGACY_ENCODED (text layer is garbage, must OCR)
        2. No text layer → SCANNED
        3. Text layer present → UNICODE_NATIVE
        """
        if any(f.is_legacy_nepali for f in fonts):
            return EncodingType.LEGACY_ENCODED
        if not has_text_layer:
            return EncodingType.SCANNED
        return EncodingType.UNICODE_NATIVE

    def _recommend_strategy(self, encoding_type: EncodingType) -> str:
        strategies = {
            EncodingType.UNICODE_NATIVE: (
                "Use pdfplumber to extract the text layer directly. "
                "Fast and lossless — no OCR needed."
            ),
            EncodingType.LEGACY_ENCODED: (
                "Text layer contains Preeti/legacy-encoded bytes. "
                "Render each page at 300 DPI and run Tesseract (nep+eng). "
                "Do NOT use pdfplumber on this document."
            ),
            EncodingType.SCANNED: (
                "No text layer detected — this is a scanned image PDF. "
                "Render each page at 300 DPI and run Tesseract (nep+eng)."
            ),
            EncodingType.UNKNOWN: "Could not determine encoding type. Manual inspection required.",
        }
        return strategies.get(encoding_type, "Unknown.")
