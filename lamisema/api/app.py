"""
LamiSema API application.

Exposes the Nepali PDF extraction pipeline as a REST API.

Run with:
    lamisema serve          # via installed CLI entry point
    python -m lamisema      # from source
    uvicorn lamisema.api.app:app --port 9001

Interactive docs: http://localhost:9001/docs
"""

import asyncio
import concurrent.futures
import json
import logging
import os
import uuid

import uvicorn
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from lamisema.models import (
    DateNormalizationRequest,
    DateNormalizationResponse,
    ExtractionResult,
    PreflightResult,
)
from lamisema.nlp.nepali import NepaliNLPBackend
from lamisema.pipeline import LamiSema
from lamisema.preflight import PDFPreflightService
from lamisema.storage.base import StorageBackend

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")


def _get_storage_backend() -> StorageBackend:
    """Initialize storage based on LAMI_STORAGE_TYPE env var with fallback."""
    storage_type = os.getenv("LAMI_STORAGE_TYPE", "memory").lower()

    if storage_type == "s3":
        try:
            from lamisema.storage.s3 import S3Storage
            return S3Storage()
        except Exception as exc:
            logger.warning(f"S3 initialization failed: {exc}. Falling back to disk storage.")
            storage_type = "disk"

    if storage_type == "disk":
        from lamisema.storage.local import LocalStorage
        return LocalStorage()

    from lamisema.storage.memory import InMemoryStorage
    return InMemoryStorage()


# Singletons — initialized once at module import
_preflight_svc = PDFPreflightService()
_nlp_backend = NepaliNLPBackend()
_store = _get_storage_backend()
_pipeline = LamiSema(preflight=_preflight_svc, nlp_backend=_nlp_backend, storage=_store)
_thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)

app = FastAPI(
    title="LamiSema — Structured Information Extraction for Nepali Documents",
    description=(
        "The world's leading PDF extraction system optimized for Nepali and multilingual documents. "
        "Encoding-aware routing detects Preeti/Kantipur legacy fonts before extraction to prevent "
        "silent data corruption. Pluggable NLPBackend supports Nepali (default), English, and any "
        "language via a simple interface. Rule-based NER for 20+ entity types. No ML model required."
    ),
    version="1.0.0",
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(f"Unhandled error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(status_code=500, content={"detail": str(exc) or "Internal server error"})


@app.get("/", tags=["System"])
async def health():
    """System health check — hardware info, library availability, store stats."""
    try:
        import fitz  # noqa: F401
        pymupdf_ok = True
    except ImportError:
        pymupdf_ok = False

    try:
        import pdfplumber  # noqa: F401
        pdfplumber_ok = True
    except ImportError:
        pdfplumber_ok = False

    try:
        import pytesseract  # noqa: F401
        tesseract_ok = True
    except ImportError:
        tesseract_ok = False

    try:
        import easyocr  # noqa: F401
        easyocr_ok = True
    except ImportError:
        easyocr_ok = False

    return {
        "status": "online",
        "version": "1.0.0",
        "language": _pipeline.nlp_backend.language_code,
        "libraries": {
            "PyMuPDF": pymupdf_ok,
            "pdfplumber": pdfplumber_ok,
            "pytesseract": tesseract_ok,
            "easyocr": easyocr_ok,
        },
        "ocr_backend": _pipeline.ocr_backend.name if _pipeline.ocr_backend else "none",
        "storage_backend": _store.__class__.__name__,
        "store": {
            "uploaded_docs": len(_store.vault) if hasattr(_store, "vault") else "persisted",
            "completed_extractions": len(_store.results) if hasattr(_store, "results") else "persisted",
        },
    }


@app.post("/upload", tags=["Ingestion"])
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a Nepali PDF for analysis.

    Returns a doc_id to use with /preflight and /extract.
    Only .pdf files are accepted. Max practical size: ~50 MB (in-memory store).
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf files are accepted.")

    pdf_bytes = await file.read()
    if len(pdf_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    doc_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"
    _store.store_pdf(doc_id, file.filename, pdf_bytes)
    logger.info(f"Uploaded: {file.filename} → {doc_id} ({len(pdf_bytes):,} bytes)")

    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "size_bytes": len(pdf_bytes),
        "next_steps": {
            "preflight": f"/preflight/{doc_id}",
            "extract": f"POST /extract/{doc_id}",
        },
    }


@app.get("/preflight/{doc_id}", tags=["Analysis"], response_model=PreflightResult)
async def preflight(doc_id: str):
    """
    Stage 1: encoding type detection + font analysis. Read-only, no extraction.

    Encoding types:
    - unicode_native  → safe for direct text extraction (fastest path)
    - legacy_encoded  → Preeti/Kantipur font detected; OCR is mandatory
    - scanned         → no text layer; render at 300 DPI and OCR
    """
    pdf_bytes = _store.get_pdf(doc_id)
    if pdf_bytes is None:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found. Upload first via POST /upload.")

    filename = _store.get_filename(doc_id) or "unknown.pdf"
    try:
        return _preflight_svc.analyze(pdf_bytes, filename, doc_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/extract/{doc_id}", tags=["Analysis"], response_model=ExtractionResult)
async def extract(doc_id: str):
    """
    Run the full extraction pipeline (pre-flight → text/OCR → NER → scoring).

    Result is stored in memory and retrievable via GET /result/{doc_id}.
    Re-running overwrites any previous result.

    Note: Large PDFs (>20 pages) with OCR may take 30–120 seconds.
    """
    pdf_bytes = _store.get_pdf(doc_id)
    if pdf_bytes is None:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found.")

    filename = _store.get_filename(doc_id) or "unknown.pdf"
    try:
        result = _pipeline.extract(pdf_bytes, filename, doc_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    _store.store_result(doc_id, result)
    logger.info(f"[{doc_id}] Extraction complete — confidence={result.overall_confidence}, pages={result.total_pages}")
    return result


@app.get("/extract/{doc_id}/stream", tags=["Analysis"])
async def extract_stream(doc_id: str):
    """
    Streaming extraction via Server-Sent Events (SSE).

    Yields one event per page as it completes so the client can show live progress.
    Connect with EventSource('/extract/{doc_id}/stream').

    Event shapes:
      {"type": "preflight", "encoding_type": "...", "total_pages": N, "has_text_layer": bool}
      {"type": "page",      "data": <PageResult>}
      {"type": "done",      "result": <ExtractionResult>}
      {"type": "error",     "detail": "..."}
    """
    pdf_bytes = _store.get_pdf(doc_id)
    if pdf_bytes is None:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found.")

    filename = _store.get_filename(doc_id) or "unknown.pdf"
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def run() -> None:
        try:
            for event in _pipeline.extract_iter(pdf_bytes, filename, doc_id):
                loop.call_soon_threadsafe(queue.put_nowait, event)
        except Exception as exc:
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "detail": str(exc)})
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    _thread_pool.submit(run)

    async def generate():
        from lamisema.models import ExtractionResult as ER
        while True:
            event = await queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("type") == "done":
                try:
                    _store.store_result(doc_id, ER.model_validate(event["result"]))
                    logger.info(f"[{doc_id}] Stream extraction complete")
                except Exception as exc:
                    logger.warning(f"[{doc_id}] Could not store streamed result: {exc}")

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/result/{doc_id}", tags=["Results"], response_model=ExtractionResult)
async def get_result(doc_id: str):
    """
    Retrieve a completed extraction result.

    Returns 404 if extraction has not been run yet (call POST /extract/{doc_id} first).
    """
    result = _store.get_result(doc_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No result for {doc_id}. Run POST /extract/{doc_id} first.",
        )
    return result


@app.post("/normalize-dates", tags=["Results"], response_model=DateNormalizationResponse)
async def normalize_dates(request: DateNormalizationRequest):
    """
    Normalize Bikram Sambat dates in arbitrary Nepali text.

    Example input:  "२०८१ साल असार १५ मा बजेट पारित भयो"
    Example output entity:
        { "text": "२०८१ साल असार १५", "normalized": "~2024-06-29 AD (approx)" }
    """
    entities = _nlp_backend.extract_entities(request.text)
    date_entities = [e for e in entities if e.entity_type == "DATE_BS"]

    processed = request.text
    for entity in date_entities:
        if entity.normalized:
            processed = processed.replace(entity.text, entity.normalized, 1)

    return DateNormalizationResponse(
        original_text=request.text,
        normalized_dates=date_entities,
        processed_text=processed,
    )


def serve():
    """CLI entry point: `lamisema serve`"""
    uvicorn.run("lamisema.api.app:app", host="0.0.0.0", port=9001, reload=False)


if __name__ == "__main__":
    serve()
