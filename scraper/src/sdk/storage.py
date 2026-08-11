"""Blob storage for scraped binaries (listing photos today).

Deliberately a tiny interface — `exists` / `save` / `location` — so the
local-disk backend used now can be swapped for S3 without touching any
stage. Stages address blobs by key, never by filesystem path; the key
("otodom/sell/apartment/197723-ID4CA1D/000-a1b2c3d4e5f6.jpg") becomes a
path under a root directory locally, and would become the object key in a
bucket. `exists()` is what makes re-runs cheap: an already-downloaded photo
is skipped rather than re-fetched.

To add S3 later: implement the same three methods over boto3 and switch on
an env var in get_storage(). No stage changes required.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class Storage(ABC):
    @abstractmethod
    def exists(self, key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def save(self, key: str, data: bytes) -> str:
        """Store data under key; returns a human-readable location."""
        raise NotImplementedError


class LocalStorage(Storage):
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        # Keys are slash-separated and built from sanitized components
        # (see stages), so they map straight onto directories.
        return self.root / key

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def save(self, key: str, data: bytes) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temp file then rename: a crash mid-write must not leave
        # a truncated file that exists() would later report as complete.
        tmp = path.with_suffix(path.suffix + ".part")
        tmp.write_bytes(data)
        tmp.replace(path)
        return str(path)


def get_storage() -> Storage:
    from config import PHOTO_STORAGE_DIR

    return LocalStorage(PHOTO_STORAGE_DIR)
