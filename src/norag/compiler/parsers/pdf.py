from __future__ import annotations

from typing import List

from pathlib import Path

from norag.compiler.parsers.base import DocumentParser, ParsedDocument, ParsedPage, VisualElement


class PDFParser(DocumentParser):
    """Parser for PDF documents using PyMuPDF (fitz).

    PyMuPDF is imported lazily inside :meth:`parse` so that importing this
    module does not raise ``ModuleNotFoundError`` in environments where
    PyMuPDF is not installed.  The parser will still raise at parse time if
    the dependency is absent.
    """

    def can_parse(self, path: Path) -> bool:
        return path.suffix.lower() == ".pdf"

    def parse(self, path: Path) -> ParsedDocument:
        try:
            import fitz  # PyMuPDF  # noqa: F401 (imported for use below)
        except ImportError as exc:
            raise ImportError(
                "PyMuPDF is required for PDF parsing. "
                "Install it with: pip install pymupdf"
            ) from exc

        doc = fitz.open(str(path))
        pages = []

        try:
            for page in doc:
                text_dict = page.get_text("dict")
                text_md = self._blocks_to_markdown(text_dict)

                visuals: List[VisualElement] = []

                # Detect raster images
                try:
                    for img_info in page.get_image_info(xrefs=True):
                        bbox_raw = img_info.get("bbox")
                        bbox = (
                            (float(bbox_raw[0]), float(bbox_raw[1]),
                             float(bbox_raw[2]), float(bbox_raw[3]))
                            if bbox_raw
                            else None
                        )
                        visuals.append(VisualElement(
                            type="image",
                            bbox=bbox,
                            page=page.number,
                        ))
                except Exception:
                    pass  # image extraction is best-effort

                # Detect tables
                try:
                    table_finder = page.find_tables()
                    for table in table_finder.tables:
                        raw_bbox = table.bbox
                        bbox = (
                            (float(raw_bbox[0]), float(raw_bbox[1]),
                             float(raw_bbox[2]), float(raw_bbox[3]))
                            if raw_bbox
                            else None
                        )
                        try:
                            md = table.to_markdown()
                        except Exception:
                            md = None
                        visuals.append(VisualElement(
                            type="table",
                            bbox=bbox,
                            page=page.number,
                            data=md,
                        ))
                except Exception:
                    pass  # table detection is best-effort

                # Detect vector drawings (potential diagrams / flowcharts)
                try:
                    drawings = page.get_drawings()
                    if len(drawings) > 5:  # heuristic: many paths = likely a diagram
                        combined = fitz.Rect()
                        for d in drawings:
                            r = d.get("rect")
                            if r:
                                combined |= fitz.Rect(r)
                        if not combined.is_empty:
                            visuals.append(VisualElement(
                                type="diagram",
                                bbox=(
                                    float(combined.x0),
                                    float(combined.y0),
                                    float(combined.x1),
                                    float(combined.y1),
                                ),
                                page=page.number,
                            ))
                except Exception:
                    pass  # drawing detection is best-effort

                pages.append(ParsedPage(
                    number=page.number,
                    text_markdown=text_md,
                    visuals=visuals,
                ))
        finally:
            doc.close()

        return ParsedDocument(
            source_path=str(path),
            pages=pages,
            page_count=len(pages),
            doc_type="pdf",
        )

    def _blocks_to_markdown(self, text_dict: dict) -> str:
        """Convert a PyMuPDF text dict to a markdown string.

        Heuristics:
        - Font size > 16  →  H1
        - Font size > 13  →  H2
        - Otherwise       →  plain paragraph line

        Consecutive plain lines are joined into paragraphs separated by a
        blank line.  Heading lines are always separated by blank lines.
        """
        if not text_dict:
            return ""

        segments: List[str] = []
        current_paragraph_lines: List[str] = []

        def flush_paragraph() -> None:
            if current_paragraph_lines:
                segments.append(" ".join(current_paragraph_lines))
                current_paragraph_lines.clear()

        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:  # 0 = text block; skip image blocks
                continue

            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue

                text = "".join(s.get("text", "") for s in spans)
                if not text.strip():
                    continue

                try:
                    max_size = max(s.get("size", 0) for s in spans)
                except (ValueError, TypeError):
                    max_size = 0

                if max_size > 16:
                    flush_paragraph()
                    segments.append(f"# {text.strip()}")
                elif max_size > 13:
                    flush_paragraph()
                    segments.append(f"## {text.strip()}")
                else:
                    current_paragraph_lines.append(text.strip())

        flush_paragraph()

        return "\n\n".join(segments)
