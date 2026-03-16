"""Shared utility functions for noRAG."""

from __future__ import annotations

import hashlib
from pathlib import Path


def source_to_id(source: str) -> str:
    """Convert a source file path to a unique, safe CKU ID.

    Combines the filename stem with a short hash of the full path to prevent
    collisions between files that share the same name in different directories.

    Example:
        "/docs/a/notes.md" -> "notes-3f7a1b2c"
        "/docs/b/notes.md" -> "notes-9e4d8c1a"
    """
    name = Path(source).stem.lower()
    safe = "".join(c if c.isalnum() or c == "-" else "-" for c in name)
    safe = safe.strip("-")
    short_hash = hashlib.sha256(source.encode()).hexdigest()[:8]
    return f"{safe}-{short_hash}"
