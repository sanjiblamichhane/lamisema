"""
In-memory storage implementation for LamiSema.

Default for development and library usage. Volatile across restarts.
"""

import logging
from typing import Dict, Optional

from lamisema.models import ExtractionResult
from lamisema.storage.base import StorageBackend

logger = logging.getLogger(__name__)


class InMemoryStorage(StorageBackend):
    """
    Simple in-memory store using dictionaries.
    Contents are lost when the process terminates.
    """

    def __init__(self):
        self.vault: Dict[str, bytes] = {}
        self.meta: Dict[str, Dict] = {}
        self.results: Dict[str, ExtractionResult] = {}
        logger.debug("Initialized volatile InMemoryStorage")

    def store_pdf(self, doc_id: str, filename: str, pdf_bytes: bytes) -> None:
        self.vault[doc_id] = pdf_bytes
        self.meta[doc_id] = {"filename": filename, "size_bytes": len(pdf_bytes)}

    def get_pdf(self, doc_id: str) -> Optional[bytes]:
        return self.vault.get(doc_id)

    def get_filename(self, doc_id: str) -> Optional[str]:
        return self.meta.get(doc_id, {}).get("filename")

    def store_result(self, doc_id: str, result: ExtractionResult) -> None:
        self.results[doc_id] = result

    def get_result(self, doc_id: str) -> Optional[ExtractionResult]:
        return self.results.get(doc_id)
