"""Hash helpers for large connectome files."""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK_SIZE = 8 * 1024 * 1024


def sha256_file(path: Path, *, chunk_size: int = _CHUNK_SIZE) -> tuple[str, int]:
    """Return SHA-256 and byte count without loading a large file into memory."""

    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
            total += len(chunk)
    return digest.hexdigest(), total
