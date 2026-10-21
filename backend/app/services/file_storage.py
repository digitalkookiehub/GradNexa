"""File storage abstraction. Local disk now; Azure Blob can implement the same interface."""
import logging
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


class FileStorage(ABC):
    """Opaque-key blob storage. Keys are generated here, never derived from client input."""

    @abstractmethod
    def save(self, college_id: int, data: bytes) -> str:
        """Persist bytes and return the storage key."""

    @abstractmethod
    def read(self, key: str) -> bytes:
        """Return the stored bytes."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove the stored object (missing is not an error)."""


class LocalFileStorage(FileStorage):
    """Stores files at <root>/<college_id>/<random uuid hex>."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root not in path.parents:
            raise ValueError("Invalid storage key")
        return path

    def save(self, college_id: int, data: bytes) -> str:
        key = f"{int(college_id)}/{uuid.uuid4().hex}"
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        try:
            self._path(key).unlink(missing_ok=True)
        except OSError:
            logger.exception("Failed to delete stored file")


def get_storage() -> FileStorage:
    """Storage backend for the current settings."""
    return LocalFileStorage(settings.UPLOAD_DIR)
