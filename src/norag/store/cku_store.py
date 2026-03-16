"""Filesystem-based CKU store — manages CKU YAML files on disk."""

from __future__ import annotations

import hashlib
from pathlib import Path

from norag.models.cku import CKU
from norag.utils import source_to_id as _source_to_id_util


class CKUStore:
    """Manages CKU YAML files on the filesystem."""

    def __init__(self, ckus_dir: Path):
        self.ckus_dir = ckus_dir
        self.ckus_dir.mkdir(parents=True, exist_ok=True)

    def save(self, cku: CKU) -> Path:
        """Save a CKU to YAML file. Returns the file path."""
        cku_id = self._source_to_id(cku.meta.source)
        path = self.ckus_dir / f"{cku_id}.yaml"
        path.write_text(cku.to_yaml(), encoding="utf-8")
        return path

    def load(self, cku_id: str) -> CKU:
        """Load a CKU by ID."""
        path = self.ckus_dir / f"{cku_id}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"CKU not found: {cku_id}")
        return CKU.from_yaml(path.read_text(encoding="utf-8"))

    def load_by_source(self, source: str) -> CKU | None:
        """Load a CKU by source path, or None if not compiled yet."""
        cku_id = self._source_to_id(source)
        try:
            return self.load(cku_id)
        except FileNotFoundError:
            return None

    def list_all(self) -> list[str]:
        """List all CKU IDs."""
        return [p.stem for p in self.ckus_dir.glob("*.yaml")]

    def needs_recompile(self, source: str, current_hash: str) -> bool:
        """Check if a source document needs recompilation."""
        existing = self.load_by_source(source)
        if existing is None:
            return True
        return existing.meta.hash != current_hash

    @staticmethod
    def _source_to_id(source: str) -> str:
        """Convert source path to a unique, safe CKU ID."""
        return _source_to_id_util(source)

    @staticmethod
    def compute_hash(path: Path) -> str:
        """Compute SHA-256 hash of a file."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()[:16]  # short hash
