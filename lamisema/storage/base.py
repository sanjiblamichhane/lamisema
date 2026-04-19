"""
Abstract storage backend interface for LamiSema.

Implement this interface to add support for a new storage system (e.g. S3, Disk, Redis).
"""

from abc import ABC, abstractmethod
from typing import Optional

from lamisema.models import ExtractionResult


class StorageBackend(ABC):
    """
    Interface for persisting uploaded PDFs and extraction results.
    """

    @abstractmethod
    def store_pdf(self, doc_id: str, filename: str, pdf_bytes: bytes) -> None:
        """Store the raw PDF bytes."""
        ...

    @abstractmethod
    def get_pdf(self, doc_id: str) -> Optional[bytes]:
        """Retrieve the raw PDF bytes or None if not found."""
        ...

    @abstractmethod
    def get_filename(self, doc_id: str) -> Optional[str]:
        """Retrieve the original filename for a doc_id."""
        ...

    @abstractmethod
    def store_result(self, doc_id: str, result: ExtractionResult) -> None:
        """Store the JSON extraction result."""
        ...

    @abstractmethod
    def get_result(self, doc_id: str) -> Optional[ExtractionResult]:
        """Retrieve the extraction result or None if not found."""
        ...
