from __future__ import annotations

from typing import List, Optional, Tuple

from pydantic import BaseModel, Field
from pathlib import Path
from abc import ABC, abstractmethod


class VisualElement(BaseModel):
    """A visual element detected in a document page."""

    type: str  # "image", "table", "diagram", "chart"
    bbox: Optional[Tuple[float, float, float, float]] = None  # x0, y0, x1, y1
    page: int
    data: Optional[str] = None  # e.g. table as markdown


class ParsedPage(BaseModel):
    """A single parsed page."""

    number: int
    text_markdown: str
    visuals: List[VisualElement] = Field(default_factory=list)


class ParsedDocument(BaseModel):
    """Result of parsing a document."""

    source_path: str
    pages: List[ParsedPage]
    page_count: int
    doc_type: str  # "pdf", "markdown"


class DocumentParser(ABC):
    """Abstract base for document parsers."""

    @abstractmethod
    def can_parse(self, path: Path) -> bool:
        """Check if this parser handles the given file."""
        ...

    @abstractmethod
    def parse(self, path: Path) -> ParsedDocument:
        """Parse a document into structured pages."""
        ...
