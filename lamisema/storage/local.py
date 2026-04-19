"""
Local disk storage implementation for LamiSema.

Saves PDFs and extraction results to a local directory.
Useful for persistent storage without S3/Minio overhead.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

from lamisema.models import ExtractionResult
from lamisema.storage.base import StorageBackend

logger = logging.getLogger(__name__)


class LocalStorage(StorageBackend):
    """
    Persistent storage using the local filesystem.
    Files are stored in a directory (default: ./uploads).
    """

    def __init__(self, base_dir: str = "uploads"):
        self.base_dir = Path(base_dir).resolve()
        self.pdf_dir = self.base_dir / "pdfs"
        self.result_dir = self.base_dir / "results"

        # Create hierarchy
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        self.result_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized LocalStorage at {self.base_dir}")

    def store_pdf(self, doc_id: str, filename: str, pdf_bytes: bytes) -> None:
        path = self.pdf_dir / f"{doc_id}.pdf"
        meta_path = self.pdf_dir / f"{doc_id}.meta"
        
        with open(path, "wb") as f:
            f.write(pdf_bytes)
        
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(filename)
            
        logger.debug(f"Stored PDF to disk: {path}")

    def get_pdf(self, doc_id: str) -> Optional[bytes]:
        path = self.pdf_dir / f"{doc_id}.pdf"
        if not path.exists():
            return None
        return path.read_bytes()

    def get_filename(self, doc_id: str) -> Optional[str]:
        meta_path = self.pdf_dir / f"{doc_id}.meta"
        if not meta_path.exists():
            return None
        return meta_path.read_text(encoding="utf-8")

    def store_result(self, doc_id: str, result: ExtractionResult) -> None:
        path = self.result_dir / f"{doc_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json())
        logger.debug(f"Stored result to disk: {path}")

    def get_result(self, doc_id: str) -> Optional[ExtractionResult]:
        path = self.result_dir / f"{doc_id}.json"
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ExtractionResult.model_validate(data)
        except Exception:
            return None
