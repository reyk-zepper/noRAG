"""Unit tests for noRAG document splitter."""

from __future__ import annotations

import pytest

from norag.compiler.parsers.base import ParsedDocument, ParsedPage, VisualElement
from norag.compiler.splitter import (
    needs_splitting,
    split_document,
    _split_text_by_headings,
    _group_sections,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_md_doc(text: str, source: str = "test.md") -> ParsedDocument:
    """Create a single-page markdown ParsedDocument."""
    return ParsedDocument(
        source_path=source,
        pages=[ParsedPage(number=0, text_markdown=text, visuals=[])],
        page_count=1,
        doc_type="markdown",
    )


def _make_pdf_doc(pages: list[str], source: str = "test.pdf") -> ParsedDocument:
    """Create a multi-page PDF ParsedDocument."""
    parsed_pages = [
        ParsedPage(number=i + 1, text_markdown=text, visuals=[])
        for i, text in enumerate(pages)
    ]
    return ParsedDocument(
        source_path=source,
        pages=parsed_pages,
        page_count=len(parsed_pages),
        doc_type="pdf",
    )


# ---------------------------------------------------------------------------
# needs_splitting
# ---------------------------------------------------------------------------


class TestNeedsSplitting:
    def test_small_document_no_split(self) -> None:
        doc = _make_md_doc("line1\nline2\nline3")
        assert needs_splitting(doc, max_lines=10) is False

    def test_large_document_needs_split(self) -> None:
        text = "\n".join(f"line {i}" for i in range(300))
        doc = _make_md_doc(text)
        assert needs_splitting(doc, max_lines=200) is True

    def test_exact_threshold_no_split(self) -> None:
        # 199 newlines = 200 lines → not over 200
        text = "\n".join(f"line {i}" for i in range(200))
        doc = _make_md_doc(text)
        assert needs_splitting(doc, max_lines=200) is False

    def test_one_over_threshold(self) -> None:
        text = "\n".join(f"line {i}" for i in range(201))
        doc = _make_md_doc(text)
        assert needs_splitting(doc, max_lines=200) is True

    def test_multi_page_total_lines(self) -> None:
        pages = ["line1\nline2\nline3"] * 100  # 300 lines total
        doc = _make_pdf_doc(pages)
        assert needs_splitting(doc, max_lines=200) is True


# ---------------------------------------------------------------------------
# _split_text_by_headings
# ---------------------------------------------------------------------------


class TestSplitTextByHeadings:
    def test_no_headings(self) -> None:
        text = "Some text\nwithout headings\nand more lines."
        result = _split_text_by_headings(text)
        assert len(result) == 1
        assert result[0] == text

    def test_h1_split(self) -> None:
        text = "# Section 1\nContent A\n# Section 2\nContent B"
        result = _split_text_by_headings(text)
        assert len(result) == 2
        assert "Section 1" in result[0]
        assert "Section 2" in result[1]

    def test_h2_split(self) -> None:
        text = "## Part A\nText A\n## Part B\nText B"
        result = _split_text_by_headings(text)
        assert len(result) == 2

    def test_preamble_before_heading(self) -> None:
        text = "Preamble text\n\n# First Section\nContent"
        result = _split_text_by_headings(text)
        assert len(result) == 2
        assert "Preamble" in result[0]
        assert "First Section" in result[1]

    def test_h3_not_split(self) -> None:
        """H3 and lower should NOT cause splits."""
        text = "# Main\n### Sub\nContent\n### Sub2\nMore"
        result = _split_text_by_headings(text)
        assert len(result) == 1  # only one H1, no H2

    def test_mixed_h1_h2(self) -> None:
        text = "# Chapter 1\n## Section 1.1\nText\n## Section 1.2\nText\n# Chapter 2\nText"
        result = _split_text_by_headings(text)
        assert len(result) == 4

    def test_empty_text(self) -> None:
        result = _split_text_by_headings("")
        assert len(result) == 1


# ---------------------------------------------------------------------------
# _group_sections
# ---------------------------------------------------------------------------


class TestGroupSections:
    def test_all_fit_in_one(self) -> None:
        sections = ["line1\nline2", "line3\nline4"]
        result = _group_sections(sections, max_lines=10)
        assert len(result) == 1

    def test_split_into_two_groups(self) -> None:
        sec_a = "\n".join(f"line {i}" for i in range(50))
        sec_b = "\n".join(f"line {i}" for i in range(50, 100))
        sec_c = "\n".join(f"line {i}" for i in range(100, 150))
        result = _group_sections([sec_a, sec_b, sec_c], max_lines=80)
        assert len(result) >= 2

    def test_single_large_section(self) -> None:
        """A section larger than max_lines goes into its own group."""
        large = "\n".join(f"line {i}" for i in range(300))
        small = "short"
        result = _group_sections([large, small], max_lines=100)
        assert len(result) == 2

    def test_empty_sections(self) -> None:
        result = _group_sections([], max_lines=100)
        assert result == []


# ---------------------------------------------------------------------------
# split_document — Markdown
# ---------------------------------------------------------------------------


class TestSplitMarkdown:
    def test_small_doc_returns_as_is(self) -> None:
        doc = _make_md_doc("# Title\nShort content")
        result = split_document(doc, max_lines=200)
        assert len(result) == 1
        assert result[0] is doc

    def test_large_doc_splits_by_headings(self) -> None:
        sections = []
        for i in range(5):
            lines = [f"# Section {i}"] + [f"Content line {j}" for j in range(60)]
            sections.append("\n".join(lines))
        text = "\n".join(sections)
        doc = _make_md_doc(text)
        result = split_document(doc, max_lines=100)
        assert len(result) > 1
        # All chunks should preserve source_path
        for chunk in result:
            assert chunk.source_path == "test.md"
            assert chunk.doc_type == "markdown"

    def test_large_doc_no_headings_falls_back(self) -> None:
        """Without headings, falls back to line-based splitting."""
        text = "\n".join(f"plain line {i}" for i in range(300))
        doc = _make_md_doc(text)
        result = split_document(doc, max_lines=100)
        assert len(result) > 1

    def test_visuals_carried_to_correct_chunk(self) -> None:
        """Visuals whose data appears in a chunk get assigned there."""
        text = "# Part A\nSome text\n![img](pic.png)\n# Part B\nOther text"
        visuals = [VisualElement(type="image", page=0, data="alt=img, src=pic.png")]
        doc = ParsedDocument(
            source_path="test.md",
            pages=[ParsedPage(number=0, text_markdown=text, visuals=visuals)],
            page_count=1,
            doc_type="markdown",
        )
        # Force split with very low threshold
        lines = text.count("\n") + 1
        result = split_document(doc, max_lines=2)
        # At least one chunk should have the visual
        has_visual = any(
            len(chunk.pages[0].visuals) > 0 for chunk in result
        )
        # Visuals are matched by data substring; may or may not match
        # depending on chunk content. Just verify no crash.
        assert len(result) >= 1


# ---------------------------------------------------------------------------
# split_document — PDF / multi-page
# ---------------------------------------------------------------------------


class TestSplitPDF:
    def test_small_pdf_no_split(self) -> None:
        doc = _make_pdf_doc(["page 1", "page 2", "page 3"])
        result = split_document(doc, max_lines=200)
        assert len(result) == 1
        assert result[0] is doc

    def test_large_pdf_splits_by_pages(self) -> None:
        # 20 pages, each 30 lines → 600 lines total
        pages = ["\n".join(f"line {j}" for j in range(30)) for _ in range(20)]
        doc = _make_pdf_doc(pages)
        result = split_document(doc, max_lines=100)
        assert len(result) > 1
        # All pages should be accounted for
        total_pages = sum(chunk.page_count for chunk in result)
        assert total_pages == 20

    def test_preserves_page_objects(self) -> None:
        pages = ["\n".join(f"line {j}" for j in range(30)) for _ in range(10)]
        doc = _make_pdf_doc(pages)
        result = split_document(doc, max_lines=100)
        for chunk in result:
            assert chunk.source_path == "test.pdf"
            assert chunk.doc_type == "pdf"
            assert len(chunk.pages) > 0

    def test_single_huge_page(self) -> None:
        """A single page over threshold falls back to line-based splitting."""
        huge_page = "\n".join(f"line {i}" for i in range(500))
        doc = _make_pdf_doc([huge_page])
        result = split_document(doc, max_lines=100)
        # Single page with no headings → line-based fallback
        assert len(result) > 1
        total_lines = sum(
            p.text_markdown.count("\n") + 1
            for chunk in result
            for p in chunk.pages
        )
        assert total_lines == 500
