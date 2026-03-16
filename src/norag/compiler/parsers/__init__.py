"""Document parsers — PDF, Markdown, and future connector formats."""

from __future__ import annotations

from typing import List, Union
from pathlib import Path

from norag.compiler.parsers.base import DocumentParser, ParsedDocument, ParsedPage, VisualElement
from norag.compiler.parsers.pdf import PDFParser
from norag.compiler.parsers.markdown import MarkdownParser

__all__ = [
    "DocumentParser",
    "ParsedDocument",
    "ParsedPage",
    "VisualElement",
    "PDFParser",
    "MarkdownParser",
    "get_parser",
]


def get_parser(path: Union[str, Path]) -> DocumentParser:
    """Return the appropriate parser for a given file path.

    Raises
    ------
    ValueError
        If no registered parser supports the file's suffix.
    """
    path = Path(path)
    parsers: List[DocumentParser] = [PDFParser(), MarkdownParser()]
    for parser in parsers:
        if parser.can_parse(path):
            return parser
    raise ValueError(f"No parser available for file type: '{path.suffix}' (path: {path})")
