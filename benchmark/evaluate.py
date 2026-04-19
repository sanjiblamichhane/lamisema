"""
LamiSema Benchmark Evaluation Script
=====================================

Measures LamiSema's extraction quality against manually transcribed ground truth
across three PDF encoding types.

Metrics computed:
    CER   — Character Error Rate (Levenshtein edit distance / ground truth length)
    Entity F1 — Precision, Recall, F1 per entity type (DATE_BS, CURRENCY, ORGANIZATION)
    Date accuracy — Fraction of BS dates whose normalized AD value is correct

Usage:
    # From the repo root:
    python benchmark/evaluate.py

    # Against a single encoding type only:
    python benchmark/evaluate.py --type legacy_encoded

    # Compare baselines alongside LamiSema:
    python benchmark/evaluate.py --baselines

Dataset layout expected:
    benchmark/
      dataset/
        unicode_native/   *.pdf
        legacy_encoded/   *.pdf
        scanned/          *.pdf
      ground_truth/
        <pdf_stem>.txt    one file per PDF, manually transcribed

Ground truth files must be named exactly after the PDF they correspond to,
with .txt extension. Example: budget-2081.pdf → budget-2081.txt
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple

# Allow running from the repo root without installing
sys.path.insert(0, str(Path(__file__).parent.parent))

from lamisema import NepaliPDFExtractionPipeline
from lamisema.models import ExtractionResult


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class DocumentScore(NamedTuple):
    pdf_path: Path
    encoding_type: str
    cer: float
    entity_f1: Dict[str, float]
    date_accuracy: Optional[float]
    extraction_time_s: float
    warning_count: int


class BenchmarkResult(NamedTuple):
    encoding_type: str
    n_docs: int
    mean_cer: float
    mean_entity_f1: Dict[str, float]
    mean_date_accuracy: Optional[float]
    mean_extraction_time_s: float
    document_scores: List[DocumentScore]


# ---------------------------------------------------------------------------
# CER (Character Error Rate)
# ---------------------------------------------------------------------------

def levenshtein(a: str, b: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if not a:
        return len(b)
    if not b:
        return len(a)

    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            curr.append(min(
                prev[j] + 1,       # deletion
                curr[j - 1] + 1,   # insertion
                prev[j - 1] + (ca != cb),  # substitution
            ))
        prev = curr
    return prev[-1]


def character_error_rate(hypothesis: str, reference: str) -> float:
    """
    CER = edit_distance(hypothesis, reference) / len(reference)

    Returns 0.0 for empty reference (no ground truth = skip).
    Capped at 1.0 — a CER above 1.0 means more errors than characters.
    """
    if not reference:
        return 0.0
    distance = levenshtein(hypothesis.strip(), reference.strip())
    return min(distance / len(reference), 1.0)


# ---------------------------------------------------------------------------
# Entity F1
# ---------------------------------------------------------------------------

def entity_f1(
    predicted: List[Dict], reference: List[Dict], entity_type: str
) -> Dict[str, float]:
    """
    Compute Precision, Recall, F1 for a single entity type.

    Matching is exact surface-form match (lowercased, stripped).
    Both predicted and reference are lists of dicts with keys:
        text (str), entity_type (str)
    """
    pred_set = {
        e["text"].strip().lower()
        for e in predicted
        if e["entity_type"] == entity_type
    }
    ref_set = {
        e["text"].strip().lower()
        for e in reference
        if e["entity_type"] == entity_type
    }

    if not ref_set and not pred_set:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    if not ref_set:
        return {"precision": 0.0, "recall": 1.0, "f1": 0.0}
    if not pred_set:
        return {"precision": 1.0, "recall": 0.0, "f1": 0.0}

    tp = len(pred_set & ref_set)
    precision = tp / len(pred_set)
    recall = tp / len(ref_set)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}


# ---------------------------------------------------------------------------
# Date normalization accuracy
# ---------------------------------------------------------------------------

def date_normalization_accuracy(
    predicted: List[Dict], reference: List[Dict]
) -> Optional[float]:
    """
    Fraction of DATE_BS entities whose normalized AD value matches ground truth.

    Returns None if there are no BS dates in the reference (skip metric).
    Ground truth normalized field format: "~YYYY-MM-DD AD (approx)"
    """
    ref_dates = {
        e["text"].strip(): e.get("normalized")
        for e in reference
        if e["entity_type"] == "DATE_BS"
    }
    if not ref_dates:
        return None

    pred_dates = {
        e["text"].strip(): e.get("normalized")
        for e in predicted
        if e["entity_type"] == "DATE_BS"
    }

    correct = sum(
        1 for text, ref_norm in ref_dates.items()
        if pred_dates.get(text) == ref_norm
    )
    return round(correct / len(ref_dates), 4)


# ---------------------------------------------------------------------------
# Ground truth loader
# ---------------------------------------------------------------------------

def load_ground_truth_text(pdf_path: Path, gt_dir: Path) -> str:
    """Load manually transcribed text for a PDF. Returns '' if not found."""
    gt_file = gt_dir / (pdf_path.stem + ".txt")
    if not gt_file.exists():
        return ""
    return gt_file.read_text(encoding="utf-8")


def load_ground_truth_entities(pdf_path: Path, gt_dir: Path) -> List[Dict]:
    """
    Load ground truth entities from a JSON sidecar file.

    Expected format: list of {"text": ..., "entity_type": ..., "normalized": ...}
    File name: <pdf_stem>.entities.json
    Returns [] if not found.
    """
    gt_file = gt_dir / (pdf_path.stem + ".entities.json")
    if not gt_file.exists():
        return []
    return json.loads(gt_file.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Baseline extractors (for --baselines comparison)
# ---------------------------------------------------------------------------

def baseline_pdfplumber(pdf_bytes: bytes) -> str:
    """Raw pdfplumber text extraction — no routing, no OCR fallback."""
    try:
        import io
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)
    except Exception:
        return ""


def baseline_tesseract_all(pdf_bytes: bytes) -> str:
    """
    Raw Tesseract on every page — no pre-flight routing.
    Simulates naively running OCR on everything regardless of encoding type.
    """
    try:
        import io
        import fitz
        import pytesseract
        from PIL import Image

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        matrix = fitz.Matrix(300 / 72, 300 / 72)
        texts = []
        for page in doc:
            pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            texts.append(pytesseract.image_to_string(img, lang="nep+eng"))
        doc.close()
        return "\n".join(texts)
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Core evaluation loop
# ---------------------------------------------------------------------------

def evaluate_document(
    pdf_path: Path,
    gt_dir: Path,
    pipeline: NepaliPDFExtractionPipeline,
    run_baselines: bool,
) -> Tuple[DocumentScore, Optional[Dict]]:
    """
    Run the full pipeline on one PDF and score it against ground truth.

    Returns:
        DocumentScore for LamiSema
        Optional dict of baseline CER scores (if run_baselines=True)
    """
    pdf_bytes = pdf_path.read_bytes()
    gt_text = load_ground_truth_text(pdf_path, gt_dir)
    gt_entities = load_ground_truth_entities(pdf_path, gt_dir)

    t0 = time.perf_counter()
    result: ExtractionResult = pipeline.extract(pdf_bytes, pdf_path.name, pdf_path.stem)
    elapsed = time.perf_counter() - t0

    # Concatenate all page text
    hypothesis = "\n".join(p.raw_text for p in result.pages)

    # Flatten all predicted entities across pages
    predicted_entities = [
        {"text": e.text, "entity_type": e.entity_type, "normalized": e.normalized}
        for page in result.pages
        for e in page.entities
    ]

    cer = character_error_rate(hypothesis, gt_text)

    entity_types = ["DATE_BS", "CURRENCY", "ORGANIZATION"]
    ef1 = {et: entity_f1(predicted_entities, gt_entities, et) for et in entity_types}

    date_acc = date_normalization_accuracy(predicted_entities, gt_entities)

    score = DocumentScore(
        pdf_path=pdf_path,
        encoding_type=result.encoding_type.value,
        cer=cer,
        entity_f1=ef1,
        date_accuracy=date_acc,
        extraction_time_s=round(elapsed, 2),
        warning_count=len(result.warnings),
    )

    baselines = None
    if run_baselines and gt_text:
        baselines = {
            "pdfplumber_raw": character_error_rate(baseline_pdfplumber(pdf_bytes), gt_text),
            "tesseract_raw": character_error_rate(baseline_tesseract_all(pdf_bytes), gt_text),
            "lamisema": cer,
        }

    return score, baselines


def _mean(values: List[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def evaluate_encoding_type(
    encoding_type: str,
    dataset_dir: Path,
    gt_dir: Path,
    pipeline: NepaliPDFExtractionPipeline,
    run_baselines: bool,
) -> Tuple[BenchmarkResult, List[Dict]]:
    """Evaluate all PDFs of a given encoding type. Returns result + baseline rows."""
    pdf_dir = dataset_dir / encoding_type
    pdfs = sorted(pdf_dir.glob("*.pdf"))

    if not pdfs:
        print(f"  [skip] No PDFs found in {pdf_dir}")
        return BenchmarkResult(
            encoding_type=encoding_type,
            n_docs=0,
            mean_cer=0.0,
            mean_entity_f1={},
            mean_date_accuracy=None,
            mean_extraction_time_s=0.0,
            document_scores=[],
        ), []

    scores: List[DocumentScore] = []
    all_baselines: List[Dict] = []

    for pdf_path in pdfs:
        print(f"  Evaluating {pdf_path.name} ...", end=" ", flush=True)
        try:
            score, baseline = evaluate_document(pdf_path, gt_dir, pipeline, run_baselines)
            scores.append(score)
            if baseline:
                all_baselines.append({"pdf": pdf_path.name, **baseline})
            print(f"CER={score.cer:.3f}  time={score.extraction_time_s}s")
        except Exception as exc:
            print(f"ERROR: {exc}")

    entity_types = ["DATE_BS", "CURRENCY", "ORGANIZATION"]
    mean_ef1 = {
        et: {
            "precision": _mean([s.entity_f1.get(et, {}).get("precision", 0.0) for s in scores]),
            "recall":    _mean([s.entity_f1.get(et, {}).get("recall",    0.0) for s in scores]),
            "f1":        _mean([s.entity_f1.get(et, {}).get("f1",        0.0) for s in scores]),
        }
        for et in entity_types
    }

    date_accs = [s.date_accuracy for s in scores if s.date_accuracy is not None]

    return BenchmarkResult(
        encoding_type=encoding_type,
        n_docs=len(scores),
        mean_cer=_mean([s.cer for s in scores]),
        mean_entity_f1=mean_ef1,
        mean_date_accuracy=_mean(date_accs) if date_accs else None,
        mean_extraction_time_s=_mean([s.extraction_time_s for s in scores]),
        document_scores=scores,
    ), all_baselines


# ---------------------------------------------------------------------------
# Report printer
# ---------------------------------------------------------------------------

def print_report(results: List[BenchmarkResult], all_baselines: List[Dict]) -> None:
    """Print a human-readable benchmark report to stdout."""
    sep = "=" * 72

    print(f"\n{sep}")
    print("  LamiSema Benchmark Report")
    print(sep)

    for r in results:
        if r.n_docs == 0:
            continue
        print(f"\n  Encoding type : {r.encoding_type}")
        print(f"  Documents     : {r.n_docs}")
        print(f"  Mean CER      : {r.mean_cer:.4f}  (lower is better; 0.0 = perfect)")
        if r.mean_date_accuracy is not None:
            print(f"  Date accuracy : {r.mean_date_accuracy:.4f}  (BS→AD normalization)")
        print(f"  Avg time/doc  : {r.mean_extraction_time_s:.2f}s")
        print()
        print(f"  {'Entity Type':<16} {'Precision':>10} {'Recall':>10} {'F1':>10}")
        print(f"  {'-'*16} {'-'*10} {'-'*10} {'-'*10}")
        for et, scores in r.mean_entity_f1.items():
            print(
                f"  {et:<16} {scores['precision']:>10.4f} {scores['recall']:>10.4f} {scores['f1']:>10.4f}"
            )

    if all_baselines:
        print(f"\n{sep}")
        print("  Baseline Comparison (CER — lower is better)")
        print(sep)
        print(f"\n  {'PDF':<30} {'pdfplumber':>12} {'tesseract':>12} {'LamiSema':>12}")
        print(f"  {'-'*30} {'-'*12} {'-'*12} {'-'*12}")
        for row in all_baselines:
            print(
                f"  {row['pdf']:<30} "
                f"{row['pdfplumber_raw']:>12.4f} "
                f"{row['tesseract_raw']:>12.4f} "
                f"{row['lamisema']:>12.4f}"
            )

    print(f"\n{sep}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="LamiSema benchmark evaluation")
    parser.add_argument(
        "--type",
        choices=["unicode_native", "legacy_encoded", "scanned"],
        help="Evaluate only one encoding type (default: all three)",
    )
    parser.add_argument(
        "--baselines",
        action="store_true",
        help="Also run raw pdfplumber and raw Tesseract for comparison",
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path(__file__).parent / "dataset",
        help="Path to benchmark/dataset/ directory",
    )
    parser.add_argument(
        "--gt-dir",
        type=Path,
        default=Path(__file__).parent / "ground_truth",
        help="Path to benchmark/ground_truth/ directory",
    )
    args = parser.parse_args()

    pipeline = NepaliPDFExtractionPipeline()
    encoding_types = (
        [args.type] if args.type
        else ["unicode_native", "legacy_encoded", "scanned"]
    )

    all_results: List[BenchmarkResult] = []
    all_baselines: List[Dict] = []

    for et in encoding_types:
        print(f"\nEvaluating: {et}")
        result, baselines = evaluate_encoding_type(
            et, args.dataset_dir, args.gt_dir, pipeline, args.baselines
        )
        all_results.append(result)
        all_baselines.extend(baselines)

    print_report(all_results, all_baselines)


if __name__ == "__main__":
    main()
