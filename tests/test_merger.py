"""Unit tests for noRAG CKU merger."""

from __future__ import annotations

from norag.compiler.merger import merge_cku_dicts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunk(
    doc_summary: str = "",
    sections: list | None = None,
    entities: list | None = None,
    facts: list | None = None,
    visuals: list | None = None,
    dependencies: list | None = None,
    language: str = "en",
) -> dict:
    return {
        "summaries": {
            "document": doc_summary,
            "sections": sections or [],
        },
        "entities": entities or [],
        "facts": facts or [],
        "visuals": visuals or [],
        "dependencies": dependencies or [],
        "language": language,
    }


# ---------------------------------------------------------------------------
# Empty / single
# ---------------------------------------------------------------------------


class TestMergeEdgeCases:
    def test_empty_list(self) -> None:
        result = merge_cku_dicts([])
        assert result["summaries"]["document"] == ""
        assert result["entities"] == []
        assert result["facts"] == []

    def test_single_chunk_passthrough(self) -> None:
        chunk = _make_chunk(doc_summary="Hello", entities=[{"id": "e1", "name": "A", "type": "concept"}])
        result = merge_cku_dicts([chunk])
        assert result is chunk


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------


class TestMergeSummaries:
    def test_combines_document_summaries(self) -> None:
        c1 = _make_chunk(doc_summary="Part one.")
        c2 = _make_chunk(doc_summary="Part two.")
        result = merge_cku_dicts([c1, c2])
        assert "Part one." in result["summaries"]["document"]
        assert "Part two." in result["summaries"]["document"]

    def test_deduplicates_sections_by_id(self) -> None:
        sec = {"id": "sec-1", "title": "Intro", "summary": "Text"}
        c1 = _make_chunk(sections=[sec])
        c2 = _make_chunk(sections=[sec])  # duplicate
        result = merge_cku_dicts([c1, c2])
        assert len(result["summaries"]["sections"]) == 1

    def test_keeps_unique_sections(self) -> None:
        s1 = {"id": "sec-1", "title": "A", "summary": "X"}
        s2 = {"id": "sec-2", "title": "B", "summary": "Y"}
        result = merge_cku_dicts([_make_chunk(sections=[s1]), _make_chunk(sections=[s2])])
        assert len(result["summaries"]["sections"]) == 2


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------


class TestMergeEntities:
    def test_deduplicates_by_id(self) -> None:
        e = {"id": "e1", "name": "Python", "type": "concept", "relations": []}
        result = merge_cku_dicts([_make_chunk(entities=[e]), _make_chunk(entities=[e])])
        assert len(result["entities"]) == 1

    def test_merges_relations(self) -> None:
        e1 = {"id": "e1", "name": "A", "type": "concept", "relations": [{"target": "e2", "type": "uses"}]}
        e2 = {"id": "e1", "name": "A", "type": "concept", "relations": [{"target": "e3", "type": "extends"}]}
        result = merge_cku_dicts([_make_chunk(entities=[e1]), _make_chunk(entities=[e2])])
        entity = result["entities"][0]
        assert len(entity["relations"]) == 2

    def test_no_duplicate_relations(self) -> None:
        rel = {"target": "e2", "type": "uses"}
        e1 = {"id": "e1", "name": "A", "type": "concept", "relations": [rel]}
        e2 = {"id": "e1", "name": "A", "type": "concept", "relations": [rel]}
        result = merge_cku_dicts([_make_chunk(entities=[e1]), _make_chunk(entities=[e2])])
        assert len(result["entities"][0]["relations"]) == 1

    def test_unique_entities_both_kept(self) -> None:
        e1 = {"id": "e1", "name": "A", "type": "concept", "relations": []}
        e2 = {"id": "e2", "name": "B", "type": "person", "relations": []}
        result = merge_cku_dicts([_make_chunk(entities=[e1]), _make_chunk(entities=[e2])])
        assert len(result["entities"]) == 2


# ---------------------------------------------------------------------------
# Facts
# ---------------------------------------------------------------------------


class TestMergeFacts:
    def test_deduplicates_by_id(self) -> None:
        f = {"id": "f1", "claim": "X is true", "source": {}, "confidence": 1.0, "entities": []}
        result = merge_cku_dicts([_make_chunk(facts=[f]), _make_chunk(facts=[f])])
        assert len(result["facts"]) == 1

    def test_unique_facts_kept(self) -> None:
        f1 = {"id": "f1", "claim": "A", "source": {}, "confidence": 1.0, "entities": []}
        f2 = {"id": "f2", "claim": "B", "source": {}, "confidence": 0.8, "entities": []}
        result = merge_cku_dicts([_make_chunk(facts=[f1]), _make_chunk(facts=[f2])])
        assert len(result["facts"]) == 2


# ---------------------------------------------------------------------------
# Visuals
# ---------------------------------------------------------------------------


class TestMergeVisuals:
    def test_deduplicates_by_id(self) -> None:
        v = {"id": "v1", "type": "table", "source": {}, "description": "A table"}
        result = merge_cku_dicts([_make_chunk(visuals=[v]), _make_chunk(visuals=[v])])
        assert len(result["visuals"]) == 1


# ---------------------------------------------------------------------------
# Dependencies & Language
# ---------------------------------------------------------------------------


class TestMergeDependencies:
    def test_deduplicates(self) -> None:
        result = merge_cku_dicts([
            _make_chunk(dependencies=["a.md", "b.md"]),
            _make_chunk(dependencies=["b.md", "c.md"]),
        ])
        assert result["dependencies"] == ["a.md", "b.md", "c.md"]


class TestMergeLanguage:
    def test_picks_most_common(self) -> None:
        result = merge_cku_dicts([
            _make_chunk(language="de"),
            _make_chunk(language="de"),
            _make_chunk(language="en"),
        ])
        assert result["language"] == "de"

    def test_defaults_to_en(self) -> None:
        result = merge_cku_dicts([{}, {}])
        assert result["language"] == "en"


# ---------------------------------------------------------------------------
# Robustness — malformed input
# ---------------------------------------------------------------------------


class TestMergeRobustness:
    def test_missing_keys(self) -> None:
        """Chunks with missing keys should not crash."""
        result = merge_cku_dicts([{"summaries": {"document": "ok"}}, {}])
        assert "entities" in result

    def test_non_list_entities(self) -> None:
        result = merge_cku_dicts([{"entities": "not a list"}, _make_chunk()])
        assert isinstance(result["entities"], list)

    def test_non_dict_entity(self) -> None:
        result = merge_cku_dicts([{"entities": [42, "string", None]}, _make_chunk()])
        assert isinstance(result["entities"], list)
