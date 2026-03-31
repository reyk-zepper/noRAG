"""Document Splitter — splits large documents into compilable sections.

Markdown documents are split at H1/H2 headings.
PDF documents are split into page-groups.
Documents below the line threshold are returned as-is.
"""

from __future__ import annotations

import re
from typing import List

from norag.compiler.parsers.base import ParsedDocument, ParsedPage


_HEADING_RE = re.compile(r"^(#{1,2})\s+", re.MULTILINE)


def needs_splitting(document: ParsedDocument, max_lines: int) -> bool:
    """Return True if the document exceeds the line threshold."""
    total_lines = sum(
        page.text_markdown.count("\n") + 1 for page in document.pages
    )
    return total_lines > max_lines


def split_document(
    document: ParsedDocument, max_lines: int
) -> List[ParsedDocument]:
    """Split a parsed document into smaller chunks.

    - If the document is below *max_lines*, returns ``[document]`` unchanged.
    - Markdown (single-page) documents are split at H1/H2 headings.
    - Multi-page documents (PDF) are split into page-groups whose combined
      line count stays below *max_lines*.

    Each returned ``ParsedDocument`` is a self-contained fragment that can
    be compiled independently.
    """
    if not needs_splitting(document, max_lines):
        return [document]

    # Markdown: single logical page → split by headings
    if len(document.pages) == 1:
        return _split_markdown(document, max_lines)

    # PDF / multi-page: split by page groups
    return _split_by_pages(document, max_lines)


# ------------------------------------------------------------------
# Markdown splitting (heading-aware)
# ------------------------------------------------------------------


def _split_markdown(
    document: ParsedDocument, max_lines: int
) -> List[ParsedDocument]:
    """Split a single-page markdown document at H1/H2 boundaries."""
    page = document.pages[0]
    text = page.text_markdown
    sections = _split_text_by_headings(text)

    if len(sections) <= 1:
        # No headings found — fall back to line-based chunking
        return _split_by_line_count(document, max_lines)

    # Group small consecutive sections to stay close to max_lines
    chunks = _group_sections(sections, max_lines)

    docs: List[ParsedDocument] = []
    for i, chunk_text in enumerate(chunks):
        # Carry over visuals whose markdown references appear in this chunk
        chunk_visuals = [
            v for v in page.visuals
            if v.data and v.data in chunk_text
        ]
        chunk_page = ParsedPage(
            number=i,
            text_markdown=chunk_text,
            visuals=chunk_visuals,
        )
        docs.append(
            ParsedDocument(
                source_path=document.source_path,
                pages=[chunk_page],
                page_count=1,
                doc_type=document.doc_type,
            )
        )
    return docs


def _split_text_by_headings(text: str) -> List[str]:
    """Split markdown text into sections at H1/H2 boundaries.

    Each section starts with its heading line (if any).  The first block
    before any heading is included as section 0.
    """
    positions = [m.start() for m in _HEADING_RE.finditer(text)]

    if not positions:
        return [text]

    sections: List[str] = []

    # Text before the first heading (preamble)
    if positions[0] > 0:
        preamble = text[: positions[0]].strip()
        if preamble:
            sections.append(preamble)

    for idx, start in enumerate(positions):
        end = positions[idx + 1] if idx + 1 < len(positions) else len(text)
        section = text[start:end].strip()
        if section:
            sections.append(section)

    return sections


def _group_sections(sections: List[str], max_lines: int) -> List[str]:
    """Merge consecutive small sections until they approach *max_lines*."""
    groups: List[str] = []
    current_parts: List[str] = []
    current_lines = 0

    for section in sections:
        section_lines = section.count("\n") + 1
        if current_parts and current_lines + section_lines > max_lines:
            groups.append("\n\n".join(current_parts))
            current_parts = []
            current_lines = 0
        current_parts.append(section)
        current_lines += section_lines

    if current_parts:
        groups.append("\n\n".join(current_parts))

    return groups


# ------------------------------------------------------------------
# Line-based fallback (no headings)
# ------------------------------------------------------------------


def _split_by_line_count(
    document: ParsedDocument, max_lines: int
) -> List[ParsedDocument]:
    """Split a single-page document by raw line count."""
    page = document.pages[0]
    lines = page.text_markdown.split("\n")

    docs: List[ParsedDocument] = []
    for i in range(0, len(lines), max_lines):
        chunk_lines = lines[i : i + max_lines]
        chunk_text = "\n".join(chunk_lines)
        chunk_page = ParsedPage(
            number=i // max_lines,
            text_markdown=chunk_text,
            visuals=[],
        )
        docs.append(
            ParsedDocument(
                source_path=document.source_path,
                pages=[chunk_page],
                page_count=1,
                doc_type=document.doc_type,
            )
        )
    return docs


# ------------------------------------------------------------------
# PDF / multi-page splitting
# ------------------------------------------------------------------


def _split_by_pages(
    document: ParsedDocument, max_lines: int
) -> List[ParsedDocument]:
    """Group pages into chunks whose combined line count stays ≤ *max_lines*."""
    docs: List[ParsedDocument] = []
    current_pages: List[ParsedPage] = []
    current_lines = 0

    for page in document.pages:
        page_lines = page.text_markdown.count("\n") + 1
        if current_pages and current_lines + page_lines > max_lines:
            docs.append(
                ParsedDocument(
                    source_path=document.source_path,
                    pages=current_pages,
                    page_count=len(current_pages),
                    doc_type=document.doc_type,
                )
            )
            current_pages = []
            current_lines = 0
        current_pages.append(page)
        current_lines += page_lines

    if current_pages:
        docs.append(
            ParsedDocument(
                source_path=document.source_path,
                pages=current_pages,
                page_count=len(current_pages),
                doc_type=document.doc_type,
            )
        )

    return docs
