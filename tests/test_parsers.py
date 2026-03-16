"""Unit tests for noRAG document parsers."""

from __future__ import annotations

from pathlib import Path

import pytest

from norag.compiler.parsers import get_parser
from norag.compiler.parsers.base import (
    DocumentParser,
    ParsedDocument,
    ParsedPage,
    VisualElement,
)
from norag.compiler.parsers.markdown import MarkdownParser
from norag.compiler.parsers.pdf import PDFParser


# ---------------------------------------------------------------------------
# MarkdownParser — can_parse
# ---------------------------------------------------------------------------


class TestMarkdownParserCanParse:
    def setup_method(self) -> None:
        self.parser = MarkdownParser()

    def test_can_parse_md(self) -> None:
        """Returns True for .md files."""
        assert self.parser.can_parse(Path("document.md")) is True

    def test_can_parse_markdown(self) -> None:
        """Returns True for .markdown files."""
        assert self.parser.can_parse(Path("document.markdown")) is True

    def test_cannot_parse_pdf(self) -> None:
        """Returns False for .pdf files."""
        assert self.parser.can_parse(Path("document.pdf")) is False

    def test_can_parse_md_uppercase(self) -> None:
        """Suffix matching is case-insensitive (.MD should work)."""
        assert self.parser.can_parse(Path("document.MD")) is True


# ---------------------------------------------------------------------------
# MarkdownParser — parse
# ---------------------------------------------------------------------------


class TestMarkdownParserParse:
    def setup_method(self) -> None:
        self.parser = MarkdownParser()

    def test_parse_simple_markdown(self, tmp_path: Path) -> None:
        """Parse a simple .md file and verify the ParsedDocument fields."""
        content = "# Hello\n\nThis is a test document."
        md_file = tmp_path / "simple.md"
        md_file.write_text(content, encoding="utf-8")

        result = self.parser.parse(md_file)

        assert isinstance(result, ParsedDocument)
        assert result.page_count == 1
        assert result.doc_type == "markdown"
        assert result.source_path == str(md_file)
        assert len(result.pages) == 1
        assert content in result.pages[0].text_markdown

    def test_parse_markdown_with_image(self, tmp_path: Path) -> None:
        """A single image reference produces one VisualElement of type 'image'."""
        content = "Some text.\n\n![A cute cat](image.png)\n\nMore text."
        md_file = tmp_path / "with_image.md"
        md_file.write_text(content, encoding="utf-8")

        result = self.parser.parse(md_file)
        visuals = result.pages[0].visuals

        assert len(visuals) == 1
        assert visuals[0].type == "image"
        # data must encode both alt text and src
        assert "A cute cat" in visuals[0].data
        assert "image.png" in visuals[0].data

    def test_parse_markdown_with_multiple_images(self, tmp_path: Path) -> None:
        """Three image references → three VisualElements."""
        content = (
            "![First](a.png)\n"
            "![Second](b.jpg)\n"
            "![Third](c.gif)\n"
        )
        md_file = tmp_path / "multi_image.md"
        md_file.write_text(content, encoding="utf-8")

        result = self.parser.parse(md_file)
        visuals = result.pages[0].visuals

        assert len(visuals) == 3
        assert all(v.type == "image" for v in visuals)

    def test_parse_empty_markdown(self, tmp_path: Path) -> None:
        """An empty .md file produces a valid ParsedDocument with empty text."""
        md_file = tmp_path / "empty.md"
        md_file.write_text("", encoding="utf-8")

        result = self.parser.parse(md_file)

        assert isinstance(result, ParsedDocument)
        assert result.page_count == 1
        assert result.doc_type == "markdown"
        assert result.pages[0].text_markdown == ""
        assert result.pages[0].visuals == []

    def test_parse_source_path_matches(self, tmp_path: Path) -> None:
        """source_path in the result matches the path that was parsed."""
        md_file = tmp_path / "path_check.md"
        md_file.write_text("Content.", encoding="utf-8")

        result = self.parser.parse(md_file)

        assert result.source_path == str(md_file)

    def test_parse_image_data_contains_alt_and_src(self, tmp_path: Path) -> None:
        """Visual data string contains both alt text and src for each image."""
        content = "![diagram overview](diagrams/arch.svg)"
        md_file = tmp_path / "data_check.md"
        md_file.write_text(content, encoding="utf-8")

        result = self.parser.parse(md_file)
        visual = result.pages[0].visuals[0]

        assert "diagram overview" in visual.data
        assert "diagrams/arch.svg" in visual.data

    def test_parse_no_images_produces_empty_visuals(self, tmp_path: Path) -> None:
        """Markdown without images has an empty visuals list."""
        content = "# Title\n\nParagraph without any images."
        md_file = tmp_path / "no_images.md"
        md_file.write_text(content, encoding="utf-8")

        result = self.parser.parse(md_file)

        assert result.pages[0].visuals == []


# ---------------------------------------------------------------------------
# PDFParser — can_parse only (no real PDF required)
# ---------------------------------------------------------------------------


class TestPDFParserCanParse:
    def setup_method(self) -> None:
        self.parser = PDFParser()

    def test_can_parse_pdf(self) -> None:
        """Returns True for .pdf files."""
        assert self.parser.can_parse(Path("report.pdf")) is True

    def test_cannot_parse_md(self) -> None:
        """Returns False for .md files."""
        assert self.parser.can_parse(Path("document.md")) is False

    def test_cannot_parse_txt(self) -> None:
        """Returns False for .txt files."""
        assert self.parser.can_parse(Path("notes.txt")) is False

    def test_can_parse_pdf_uppercase(self) -> None:
        """Suffix matching is case-insensitive (.PDF should work)."""
        assert self.parser.can_parse(Path("REPORT.PDF")) is True


# ---------------------------------------------------------------------------
# get_parser factory
# ---------------------------------------------------------------------------


class TestGetParser:
    def test_get_parser_markdown(self) -> None:
        """Returns a MarkdownParser for .md files."""
        parser = get_parser(Path("notes.md"))
        assert isinstance(parser, MarkdownParser)

    def test_get_parser_markdown_from_string(self) -> None:
        """Accepts a plain string path for .md files."""
        parser = get_parser("notes.md")
        assert isinstance(parser, MarkdownParser)

    def test_get_parser_pdf(self) -> None:
        """Returns a PDFParser for .pdf files."""
        parser = get_parser(Path("report.pdf"))
        assert isinstance(parser, PDFParser)

    def test_get_parser_unknown_raises(self) -> None:
        """Raises ValueError for unsupported extensions like .txt."""
        with pytest.raises(ValueError, match="No parser available"):
            get_parser(Path("notes.txt"))

    def test_get_parser_unknown_docx_raises(self) -> None:
        """Raises ValueError for .docx files (not yet supported)."""
        with pytest.raises(ValueError):
            get_parser(Path("document.docx"))

    def test_get_parser_error_message_contains_suffix(self) -> None:
        """ValueError message includes the unsupported suffix."""
        with pytest.raises(ValueError, match=r"\.csv"):
            get_parser(Path("data.csv"))


# ---------------------------------------------------------------------------
# ParsedDocument and related models
# ---------------------------------------------------------------------------


class TestParsedDocumentModel:
    def test_parsed_document_creation(self) -> None:
        """ParsedDocument can be constructed and fields are accessible."""
        page = ParsedPage(number=0, text_markdown="Hello world")
        doc = ParsedDocument(
            source_path="/tmp/test.md",
            pages=[page],
            page_count=1,
            doc_type="markdown",
        )

        assert doc.source_path == "/tmp/test.md"
        assert doc.page_count == 1
        assert doc.doc_type == "markdown"
        assert len(doc.pages) == 1
        assert doc.pages[0].text_markdown == "Hello world"

    def test_parsed_document_multiple_pages(self) -> None:
        """ParsedDocument holds multiple pages in order."""
        pages = [
            ParsedPage(number=i, text_markdown=f"Page {i}")
            for i in range(3)
        ]
        doc = ParsedDocument(
            source_path="/tmp/multi.pdf",
            pages=pages,
            page_count=3,
            doc_type="pdf",
        )

        assert doc.page_count == 3
        assert [p.number for p in doc.pages] == [0, 1, 2]

    def test_parsed_page_default_visuals(self) -> None:
        """ParsedPage has an empty visuals list by default."""
        page = ParsedPage(number=0, text_markdown="")
        assert page.visuals == []


class TestVisualElementModel:
    def test_visual_element_creation_all_fields(self) -> None:
        """VisualElement can be created with all fields populated."""
        ve = VisualElement(
            type="image",
            bbox=(0.0, 10.0, 100.0, 200.0),
            page=2,
            data="alt=logo, src=logo.png",
        )

        assert ve.type == "image"
        assert ve.bbox == (0.0, 10.0, 100.0, 200.0)
        assert ve.page == 2
        assert ve.data == "alt=logo, src=logo.png"

    def test_visual_element_optional_fields_default_none(self) -> None:
        """bbox and data are optional and default to None."""
        ve = VisualElement(type="diagram", page=0)

        assert ve.bbox is None
        assert ve.data is None

    def test_visual_element_table_type(self) -> None:
        """VisualElement accepts 'table' as type with markdown data."""
        ve = VisualElement(
            type="table",
            page=1,
            bbox=(5.0, 5.0, 300.0, 150.0),
            data="| A | B |\n|---|---|\n| 1 | 2 |",
        )

        assert ve.type == "table"
        assert "A" in ve.data

    def test_visual_element_page_field(self) -> None:
        """page field stores the page number correctly."""
        ve = VisualElement(type="chart", page=5)
        assert ve.page == 5


# ---------------------------------------------------------------------------
# DocumentParser abstract interface
# ---------------------------------------------------------------------------


class TestDocumentParserInterface:
    def test_markdown_parser_is_document_parser(self) -> None:
        """MarkdownParser is a subclass of DocumentParser."""
        assert issubclass(MarkdownParser, DocumentParser)

    def test_pdf_parser_is_document_parser(self) -> None:
        """PDFParser is a subclass of DocumentParser."""
        assert issubclass(PDFParser, DocumentParser)

    def test_document_parser_is_abstract(self) -> None:
        """DocumentParser cannot be instantiated directly."""
        with pytest.raises(TypeError):
            DocumentParser()  # type: ignore[abstract]
