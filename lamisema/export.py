"""
PDF export — converts an ExtractionResult into a clean, Unicode-native,
editable PDF.

The source document may have been unreadable (Preeti-encoded, scanned image)
but the exported PDF contains proper Devanagari Unicode text that is fully
selectable, searchable, copyable, and editable in any PDF viewer.

Requires: fpdf2 (pip install fpdf2)
Font:     Noto Sans Devanagari TTF — path resolved via LAMI_FONT_PATH env var
          or the DEFAULT_FONT_PATHS probe list.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from lamisema.models import ExtractionResult

logger = logging.getLogger(__name__)

DEFAULT_FONT_PATHS = [
    os.getenv("LAMI_FONT_PATH", ""),
    "/app/fonts/NotoSansDevanagari.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansDevanagari-Regular.otf",
    "/System/Library/Fonts/Supplemental/DevanagariMT.ttc",  # macOS
]

ENCODING_LABELS = {
    "unicode_native": "Unicode Native",
    "legacy_encoded": "Legacy Encoded (Preeti/Kantipur — OCR applied)",
    "scanned": "Scanned Image (OCR applied)",
    "unknown": "Unknown",
}


def _find_font() -> Optional[str]:
    for path in DEFAULT_FONT_PATHS:
        if path and Path(path).exists():
            return path
    return None


def export_pdf(result: ExtractionResult) -> bytes:
    """
    Generate an editable Unicode PDF from an ExtractionResult.

    Returns raw PDF bytes suitable for streaming as application/pdf.
    Raises RuntimeError if fpdf2 is not installed or no Devanagari font found.
    """
    try:
        from fpdf import FPDF
    except ImportError as exc:
        raise RuntimeError(
            "fpdf2 is required for PDF export. Run: pip install fpdf2"
        ) from exc

    font_path = _find_font()
    if not font_path:
        raise RuntimeError(
            "No Devanagari font found. Set LAMI_FONT_PATH to a NotoSansDevanagari TTF path."
        )

    logger.info(f"[{result.doc_id}] Exporting PDF using font: {font_path}")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_font("Noto", "", font_path)
    pdf.add_font("Noto", "B", font_path)  # bold uses same file; fpdf2 fakes bold

    _cover_page(pdf, result)

    for page in result.pages:
        if not page.raw_text.strip():
            continue
        _content_page(pdf, page, result.doc_id)

    return bytes(pdf.output())


def _cover_page(pdf, result: ExtractionResult) -> None:
    pdf.add_page()

    # ── Title bar ────────────────────────────────────────────────────────────
    pdf.set_fill_color(30, 27, 75)       # deep indigo
    pdf.rect(0, 0, 210, 42, style="F")

    pdf.set_font("Noto", size=22)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(15, 8)
    pdf.cell(0, 10, "LamiSema", ln=True)

    pdf.set_font("Noto", size=10)
    pdf.set_text_color(180, 180, 220)
    pdf.set_xy(15, 22)
    pdf.cell(0, 7, "Structured Information Extraction for Nepali Documents", ln=True)

    # ── Document info ─────────────────────────────────────────────────────────
    pdf.set_text_color(30, 30, 30)
    pdf.set_xy(15, 52)
    pdf.set_font("Noto", size=15)
    # Truncate long filenames
    name = result.filename if len(result.filename) < 60 else result.filename[:57] + "..."
    pdf.cell(0, 10, name, ln=True)

    pdf.set_font("Noto", size=10)
    pdf.set_text_color(90, 90, 90)
    pdf.set_xy(15, 67)
    pdf.cell(0, 7, f"Document ID: {result.doc_id}", ln=True)
    pdf.cell(0, 7, f"Exported:    {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", ln=True)

    # ── Metadata table ────────────────────────────────────────────────────────
    pdf.set_xy(15, 92)
    _meta_row(pdf, "Encoding type",
              ENCODING_LABELS.get(result.encoding_type, result.encoding_type))
    _meta_row(pdf, "Total pages",    str(result.total_pages))
    _meta_row(pdf, "OCR backend",    result.ocr_backend)
    _meta_row(pdf, "Confidence",
              f"{result.overall_confidence * 100:.1f}%")

    # ── Warnings ──────────────────────────────────────────────────────────────
    if result.warnings:
        y = pdf.get_y() + 6
        pdf.set_fill_color(255, 247, 220)
        pdf.set_draw_color(200, 160, 60)
        pdf.rect(15, y, 180, 8 * len(result.warnings) + 6, style="FD")
        pdf.set_xy(20, y + 3)
        pdf.set_text_color(120, 80, 0)
        pdf.set_font("Noto", size=9)
        for w in result.warnings:
            pdf.cell(0, 8, f"• {w[:100]}", ln=True)
        pdf.set_text_color(30, 30, 30)

    # ── Entity summary ────────────────────────────────────────────────────────
    all_entities = [e for page in result.pages for e in page.entities]
    if all_entities:
        from collections import Counter
        counts = Counter(e.entity_type for e in all_entities)

        y = pdf.get_y() + 12
        pdf.set_xy(15, y)
        pdf.set_font("Noto", size=11)
        pdf.set_text_color(30, 27, 75)
        pdf.cell(0, 8, f"Extracted Entities  ({len(all_entities)} total)", ln=True)

        pdf.set_font("Noto", size=9)
        pdf.set_text_color(50, 50, 50)
        col_w = 58
        for i, (etype, count) in enumerate(counts.most_common()):
            if i % 3 == 0:
                pdf.set_x(15)
            pdf.cell(col_w, 7, f"{etype}: {count}")
            if i % 3 == 2:
                pdf.ln()
        pdf.ln(4)

    # ── Note ─────────────────────────────────────────────────────────────────
    pdf.set_y(-40)
    pdf.set_font("Noto", size=8)
    pdf.set_text_color(150, 150, 150)
    pdf.set_x(15)
    pdf.multi_cell(
        0, 5,
        "This document was generated by LamiSema. Text is Unicode-native and fully "
        "editable regardless of the original PDF encoding. "
        "https://github.com/sanjiblamichhane/lamisema",
        align="C",
    )


def _meta_row(pdf, label: str, value: str) -> None:
    pdf.set_font("Noto", size=9)
    pdf.set_text_color(100, 100, 100)
    pdf.set_x(15)
    pdf.cell(42, 8, label)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(0, 8, value, ln=True)


def _content_page(pdf, page, doc_id: str) -> None:
    pdf.add_page()

    # ── Page header ───────────────────────────────────────────────────────────
    pdf.set_fill_color(245, 245, 250)
    pdf.rect(0, 0, 210, 14, style="F")
    pdf.set_font("Noto", size=8)
    pdf.set_text_color(80, 80, 120)
    pdf.set_xy(10, 3)
    conf_pct = f"{page.confidence * 100:.0f}%"
    pdf.cell(0, 7,
             f"Page {page.page_number}  |  {page.extraction_method}  |  "
             f"Confidence: {conf_pct}  |  {doc_id}")

    # ── Body text ─────────────────────────────────────────────────────────────
    pdf.set_xy(15, 20)
    pdf.set_font("Noto", size=11)
    pdf.set_text_color(20, 20, 20)
    pdf.multi_cell(180, 7, page.raw_text)

    # ── Entities footer (if any) ──────────────────────────────────────────────
    if page.entities:
        y = max(pdf.get_y() + 6, pdf.h - 50)
        pdf.set_xy(15, y)
        pdf.set_draw_color(200, 200, 220)
        pdf.line(15, y, 195, y)

        pdf.set_xy(15, y + 3)
        pdf.set_font("Noto", size=8)
        pdf.set_text_color(80, 80, 130)
        pdf.cell(0, 6, f"Entities on this page ({len(page.entities)}):", ln=True)

        pdf.set_text_color(50, 50, 80)
        for ent in page.entities:
            line = f"[{ent.entity_type}]  {ent.text}"
            if ent.normalized:
                line += f"  →  {ent.normalized}"
            pdf.set_x(15)
            pdf.cell(0, 5, line[:100], ln=True)
