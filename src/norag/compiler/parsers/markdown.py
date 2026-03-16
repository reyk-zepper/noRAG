from __future__ import annotations

import re
from pathlib import Path

from norag.compiler.parsers.base import DocumentParser, ParsedDocument, ParsedPage, VisualElement

_IMAGE_RE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')


class MarkdownParser(DocumentParser):
    """Parser for Markdown documents (.md, .markdown)."""

    def can_parse(self, path: Path) -> bool:
        return path.suffix.lower() in (".md", ".markdown")

    def parse(self, path: Path) -> ParsedDocument:
        text = path.read_text(encoding="utf-8")

        visuals = self._detect_images(text)

        page = ParsedPage(
            number=0,
            text_markdown=text,
            visuals=visuals,
        )

        return ParsedDocument(
            source_path=str(path),
            pages=[page],
            page_count=1,
            doc_type="markdown",
        )

    def _detect_images(self, text: str) -> list[VisualElement]:
        """Find all markdown image references: ![alt](src)."""
        visuals: list[VisualElement] = []
        for match in _IMAGE_RE.finditer(text):
            alt = match.group(1)
            src = match.group(2)
            visuals.append(VisualElement(
                type="image",
                page=0,
                data=f"alt={alt}, src={src}",
            ))
        return visuals
