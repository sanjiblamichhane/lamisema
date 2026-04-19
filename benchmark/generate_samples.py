"""
Synthetic PDF generator for LamiSema benchmark dataset.

Generates minimal test PDFs for all three encoding types so the evaluation
script can be exercised without waiting for the full 150-document dataset.

Usage:
    python benchmark/generate_samples.py
    # Writes to benchmark/dataset/{unicode_native,scanned}/

Note on legacy_encoded:
    Legacy Preeti-encoded PDFs cannot be generated synthetically without
    embedding the actual Preeti font file (which is proprietary). Those
    samples must be sourced from real pre-Unicode Nepali documents.
    See benchmark/dataset/README.md for sourcing guidelines.

Requirements:
    pip install PyMuPDF Pillow
"""

import io
import sys
from pathlib import Path

DATASET_DIR = Path(__file__).parent / "dataset"
GT_DIR = Path(__file__).parent / "ground_truth"

SAMPLE_NEPALI_TEXT = (
    "नेपाल सरकार\n"
    "अर्थ मन्त्रालयको वार्षिक बजेट विवरण\n"
    "आर्थिक वर्ष २०८१/०८२\n\n"
    "कुल बजेट: रु. १,७९२,७३३ लाख\n"
    "बजेट पारित मिति: २०८१ साल असार १५\n\n"
    "अर्थ मन्त्रालय\n"
    "सिंहदरबार, काठमाडौं\n"
)

SAMPLE_ENTITIES = [
    {
        "text": "२०८१ साल असार १५",
        "entity_type": "DATE_BS",
        "normalized": "~2024-06-29 AD (approx)",
    },
    {
        "text": "रु. १,७९२,७३३",
        "entity_type": "CURRENCY",
        "normalized": "NPR 1792733",
    },
    {
        "text": "अर्थ मन्त्रालय",
        "entity_type": "ORGANIZATION",
        "normalized": None,
    },
]


def generate_unicode_native(out_dir: Path, gt_dir: Path, n: int = 3) -> None:
    """
    Generate unicode_native PDFs using PyMuPDF.

    These PDFs have a real text layer with Unicode Devanagari characters.
    pdfplumber can extract them directly without OCR.
    """
    try:
        import fitz
    except ImportError:
        print("PyMuPDF required: pip install PyMuPDF")
        return

    import json

    out_dir.mkdir(parents=True, exist_ok=True)
    gt_dir.mkdir(parents=True, exist_ok=True)

    for i in range(1, n + 1):
        stem = f"unicode-sample-{i:02d}"
        pdf_path = out_dir / f"{stem}.pdf"

        doc = fitz.open()
        page = doc.new_page(width=595, height=842)  # A4

        # Insert text using a built-in font.
        # Note: built-in PDF fonts don't support Devanagari — the characters
        # will render as boxes on screen, but the TEXT LAYER will contain
        # correct Unicode codepoints. This is sufficient for testing the
        # pipeline's unicode_native routing path.
        page.insert_text(
            (72, 100),
            SAMPLE_NEPALI_TEXT,
            fontsize=12,
            color=(0, 0, 0),
        )

        doc.save(str(pdf_path))
        doc.close()

        # Ground truth
        (gt_dir / f"{stem}.txt").write_text(SAMPLE_NEPALI_TEXT, encoding="utf-8")
        (gt_dir / f"{stem}.entities.json").write_text(
            json.dumps(SAMPLE_ENTITIES, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(f"  Created: {pdf_path.name}")


def generate_scanned(out_dir: Path, gt_dir: Path, n: int = 3) -> None:
    """
    Generate scanned PDFs: each page is a rasterized image with no text layer.

    Uses PyMuPDF to create an image-only PDF, simulating a scanned document.
    Tesseract can read these; pdfplumber returns an empty string.
    """
    try:
        import fitz
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("PyMuPDF and Pillow required: pip install PyMuPDF Pillow")
        return

    import json

    out_dir.mkdir(parents=True, exist_ok=True)
    gt_dir.mkdir(parents=True, exist_ok=True)

    for i in range(1, n + 1):
        stem = f"scanned-sample-{i:02d}"
        pdf_path = out_dir / f"{stem}.pdf"

        # Render text onto a PIL image (simulates a scanned page)
        img = Image.new("RGB", (1240, 1754), color=(255, 255, 255))  # A4 at 150 DPI
        draw = ImageDraw.Draw(img)

        # Draw placeholder text — Devanagari won't render without a system
        # font, but this creates a valid image-only PDF for pipeline testing.
        draw.text((100, 100), "[Scanned page — Devanagari text]", fill=(0, 0, 0))
        draw.text((100, 140), "Nepal Government Budget 2081/082", fill=(0, 0, 0))
        draw.text((100, 180), "Ministry of Finance, Singhadurbar", fill=(0, 0, 0))

        # Convert PIL image → PDF via PyMuPDF (image-only, no text layer)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        rect = fitz.Rect(0, 0, 595, 842)
        page.insert_image(rect, stream=img_bytes.read())
        doc.save(str(pdf_path))
        doc.close()

        # Ground truth — what Tesseract should ideally extract
        (gt_dir / f"{stem}.txt").write_text(
            "Nepal Government Budget 2081/082\nMinistry of Finance, Singhadurbar\n",
            encoding="utf-8",
        )
        (gt_dir / f"{stem}.entities.json").write_text(
            json.dumps([], ensure_ascii=False),
            encoding="utf-8",
        )

        print(f"  Created: {pdf_path.name}")


def main() -> None:
    print("\nGenerating unicode_native samples...")
    generate_unicode_native(
        DATASET_DIR / "unicode_native",
        GT_DIR,
        n=3,
    )

    print("\nGenerating scanned samples...")
    generate_scanned(
        DATASET_DIR / "scanned",
        GT_DIR,
        n=3,
    )

    print("\nNote: legacy_encoded samples cannot be generated synthetically.")
    print("      Source real Preeti-encoded PDFs and place them in:")
    print(f"      {DATASET_DIR / 'legacy_encoded'}/")
    print("      See benchmark/dataset/README.md for guidelines.\n")


if __name__ == "__main__":
    main()
