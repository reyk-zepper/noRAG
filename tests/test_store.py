"""Comprehensive unit tests for the noRAG store layer (CKUStore + KnowledgeMap)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from norag.models.cku import (
    CKU,
    CKUEntity,
    CKUFact,
    CKUMeta,
    CKUSummary,
    CKUVisual,
    Relation,
    SectionSummary,
    SourceRef,
)
from norag.store.cku_store import CKUStore
from norag.store.knowledge_map import KnowledgeMap
from norag.utils import source_to_id


# ---------------------------------------------------------------------------
# Helper factory
# ---------------------------------------------------------------------------


def make_cku(source: str = "test/doc.pdf", hash: str = "abc123", **kwargs) -> CKU:
    """Create a minimal but fully populated CKU for testing."""
    defaults = dict(
        meta=CKUMeta(
            source=source,
            compiled=datetime(2026, 3, 16, tzinfo=timezone.utc),
            hash=hash,
            type="pdf",
            language="de",
        ),
        summaries=CKUSummary(
            document="Test doc summary",
            sections=[SectionSummary(id="s1", title="Intro", summary="Intro text")],
        ),
        entities=[
            CKUEntity(
                id="e1",
                name="Onboarding",
                type="process",
                relations=[Relation(target="e2", type="involves")],
            ),
            CKUEntity(id="e2", name="IT Security", type="system"),
        ],
        facts=[
            CKUFact(
                id="f1",
                claim="New employees get a buddy in 3 days",
                source=SourceRef(page=4),
                confidence=0.95,
                entities=["e1"],
            ),
            CKUFact(
                id="f2",
                claim="IT security training is mandatory",
                source=SourceRef(page=8),
                entities=["e2"],
            ),
        ],
        visuals=[
            CKUVisual(
                id="v1",
                type="flowchart",
                source=SourceRef(page=6),
                description="Onboarding flow",
            )
        ],
        dependencies=["cku:it-security"],
    )
    defaults.update(kwargs)
    return CKU(**defaults)


# ===========================================================================
# CKUStore Tests
# ===========================================================================


class TestCKUStoreSaveLoad:
    """Tests 1–2: basic persistence operations."""

    def test_save_and_load_roundtrip(self, tmp_path):
        """Save a CKU, load it by ID, verify all fields match."""
        store = CKUStore(tmp_path / "ckus")
        cku = make_cku()
        cku_id = source_to_id(cku.meta.source)

        store.save(cku)
        loaded = store.load(cku_id)

        assert loaded.meta.source == cku.meta.source
        assert loaded.meta.hash == cku.meta.hash
        assert loaded.meta.type == cku.meta.type
        assert loaded.meta.language == cku.meta.language
        assert loaded.summaries.document == cku.summaries.document
        assert len(loaded.summaries.sections) == 1
        assert loaded.summaries.sections[0].title == "Intro"
        assert len(loaded.entities) == 2
        assert loaded.entities[0].name == "Onboarding"
        assert loaded.entities[0].relations[0].target == "e2"
        assert len(loaded.facts) == 2
        assert loaded.facts[0].confidence == pytest.approx(0.95)
        assert len(loaded.visuals) == 1
        assert loaded.visuals[0].type == "flowchart"
        assert loaded.dependencies == ["cku:it-security"]

    def test_list_all_returns_both_ids(self, tmp_path):
        """Save 2 CKUs, list_all returns both IDs."""
        store = CKUStore(tmp_path / "ckus")
        cku_a = make_cku(source="docs/alpha.pdf", hash="aaa")
        cku_b = make_cku(source="docs/beta.pdf", hash="bbb")

        store.save(cku_a)
        store.save(cku_b)

        ids = store.list_all()
        expected_a = source_to_id("docs/alpha.pdf")
        expected_b = source_to_id("docs/beta.pdf")

        assert len(ids) == 2
        assert expected_a in ids
        assert expected_b in ids


class TestCKUStoreLoadBySource:
    """Tests 3–4: load_by_source."""

    def test_load_by_source_returns_cku(self, tmp_path):
        """Save CKU, load by source path, verify it works."""
        store = CKUStore(tmp_path / "ckus")
        cku = make_cku(source="reports/annual.pdf")
        store.save(cku)

        result = store.load_by_source("reports/annual.pdf")

        assert result is not None
        assert result.meta.source == "reports/annual.pdf"

    def test_load_by_source_not_found_returns_none(self, tmp_path):
        """Returns None for a source that was never compiled."""
        store = CKUStore(tmp_path / "ckus")

        result = store.load_by_source("nonexistent/file.pdf")

        assert result is None


class TestCKUStoreLoadNotFound:
    """Test 5: load raises on missing ID."""

    def test_load_raises_file_not_found_for_unknown_id(self, tmp_path):
        """Raises FileNotFoundError for a non-existent CKU ID."""
        store = CKUStore(tmp_path / "ckus")

        with pytest.raises(FileNotFoundError):
            store.load("totally-unknown-id")


class TestCKUStoreNeedsRecompile:
    """Tests 6–8: needs_recompile logic."""

    def test_needs_recompile_new_source_returns_true(self, tmp_path):
        """Returns True for a source that has never been compiled."""
        store = CKUStore(tmp_path / "ckus")

        assert store.needs_recompile("brand/new.pdf", "hash-xyz") is True

    def test_needs_recompile_same_hash_returns_false(self, tmp_path):
        """Returns False when the stored hash matches the current hash."""
        store = CKUStore(tmp_path / "ckus")
        cku = make_cku(source="stable/doc.pdf", hash="stable-hash")
        store.save(cku)

        assert store.needs_recompile("stable/doc.pdf", "stable-hash") is False

    def test_needs_recompile_different_hash_returns_true(self, tmp_path):
        """Returns True when the stored hash differs from the current hash."""
        store = CKUStore(tmp_path / "ckus")
        cku = make_cku(source="changed/doc.pdf", hash="old-hash")
        store.save(cku)

        assert store.needs_recompile("changed/doc.pdf", "new-hash") is True


class TestCKUStoreComputeHash:
    """Test 9: compute_hash."""

    def test_compute_hash_returns_16_char_hex(self, tmp_path):
        """compute_hash of a temp file returns a 16-character hex string."""
        test_file = tmp_path / "sample.pdf"
        test_file.write_bytes(b"dummy pdf content for hashing")

        result = CKUStore.compute_hash(test_file)

        assert isinstance(result, str)
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_compute_hash_is_deterministic(self, tmp_path):
        """Same file produces the same hash on repeated calls."""
        test_file = tmp_path / "deterministic.bin"
        test_file.write_bytes(b"\x00\x01\x02\x03" * 1024)

        h1 = CKUStore.compute_hash(test_file)
        h2 = CKUStore.compute_hash(test_file)

        assert h1 == h2

    def test_compute_hash_differs_for_different_content(self, tmp_path):
        """Different file content produces different hashes (collision sanity check)."""
        file_a = tmp_path / "a.bin"
        file_b = tmp_path / "b.bin"
        file_a.write_bytes(b"content-alpha")
        file_b.write_bytes(b"content-beta")

        assert CKUStore.compute_hash(file_a) != CKUStore.compute_hash(file_b)


class TestCKUStoreOverwrite:
    """Test 10: save overwrites existing entry for same source."""

    def test_overwrite_on_save_loads_latest(self, tmp_path):
        """Save CKU, save updated CKU with same source, verify latest is loaded."""
        store = CKUStore(tmp_path / "ckus")
        source = "docs/evolving.pdf"
        cku_v1 = make_cku(source=source, hash="hash-v1")
        cku_v2 = make_cku(
            source=source,
            hash="hash-v2",
            summaries=CKUSummary(
                document="Updated summary v2",
                sections=[],
            ),
        )

        store.save(cku_v1)
        store.save(cku_v2)

        ids = store.list_all()
        assert len(ids) == 1, "Overwrite must not create a second file"

        loaded = store.load_by_source(source)
        assert loaded is not None
        assert loaded.meta.hash == "hash-v2"
        assert loaded.summaries.document == "Updated summary v2"


# ===========================================================================
# KnowledgeMap Tests
# ===========================================================================


@pytest.fixture()
def km(tmp_path):
    """Provide a fresh KnowledgeMap backed by a temp SQLite DB."""
    kmap = KnowledgeMap(tmp_path / "knowledge.db")
    yield kmap
    kmap.close()


@pytest.fixture()
def indexed_km(km):
    """KnowledgeMap with one CKU already indexed."""
    cku = make_cku()
    km.index_cku(cku)
    return km, cku


class TestKnowledgeMapIndexAndFind:
    """Tests 11–14: indexing and entity/topic lookup."""

    def test_index_and_find_by_entity_exact(self, indexed_km):
        """Index a CKU, find by full entity name."""
        km, cku = indexed_km
        cku_id = source_to_id(cku.meta.source)

        results = km.find_by_entity("Onboarding")

        assert cku_id in results

    def test_find_by_entity_partial_match(self, indexed_km):
        """'Onboard' partial string should match 'Onboarding'."""
        km, cku = indexed_km
        cku_id = source_to_id(cku.meta.source)

        results = km.find_by_entity("Onboard")

        assert cku_id in results

    def test_find_by_entity_case_insensitive(self, indexed_km):
        """Lowercase 'onboarding' should match stored 'Onboarding'."""
        km, cku = indexed_km
        cku_id = source_to_id(cku.meta.source)

        results = km.find_by_entity("onboarding")

        assert cku_id in results

    def test_find_by_topic_entity_type(self, indexed_km):
        """Entity type 'process' should appear as a topic; find by it."""
        km, cku = indexed_km
        cku_id = source_to_id(cku.meta.source)

        # make_cku has entity types "process" and "system", and section title "Intro"
        results = km.find_by_topic("process")

        assert cku_id in results

    def test_find_by_topic_section_title(self, indexed_km):
        """Section title 'Intro' should also be stored as a topic."""
        km, cku = indexed_km
        cku_id = source_to_id(cku.meta.source)

        results = km.find_by_topic("intro")

        assert cku_id in results


class TestKnowledgeMapKeywordSearch:
    """Test 15: full-text keyword search on fact claims."""

    def test_find_by_keywords_matches_fact_claim(self, indexed_km):
        """FTS search with keyword from a fact claim returns the correct CKU."""
        km, cku = indexed_km
        cku_id = source_to_id(cku.meta.source)

        # fact f1: "New employees get a buddy in 3 days"
        results = km.find_by_keywords(["employees"])

        assert cku_id in results

    def test_find_by_keywords_multiple_words(self, indexed_km):
        """Multi-keyword FTS search returns matching CKU."""
        km, cku = indexed_km
        cku_id = source_to_id(cku.meta.source)

        # fact f2: "IT security training is mandatory"
        results = km.find_by_keywords(["security", "training"])

        assert cku_id in results

    def test_find_by_keywords_empty_list_returns_empty(self, indexed_km):
        """Empty keyword list returns an empty result set."""
        km, _ = indexed_km

        results = km.find_by_keywords([])

        assert results == []

    def test_find_by_keywords_no_match_returns_empty(self, indexed_km):
        """Keyword that appears in no fact returns an empty list."""
        km, _ = indexed_km

        results = km.find_by_keywords(["xyzzy_no_match_at_all"])

        assert results == []


class TestKnowledgeMapRelations:
    """Test 16: entity relation lookup."""

    def test_get_entity_relations_returns_correct_data(self, indexed_km):
        """get_entity_relations for 'Onboarding' returns the 'involves' relation."""
        km, cku = indexed_km
        cku_id = source_to_id(cku.meta.source)

        relations = km.get_entity_relations("Onboarding")

        assert len(relations) == 1
        rel = relations[0]
        assert rel["entity_name"] == "Onboarding"
        assert rel["entity_type"] == "process"
        assert rel["target"] == "e2"
        assert rel["relation_type"] == "involves"
        assert rel["cku_id"] == cku_id

    def test_get_entity_relations_no_relations_returns_empty(self, indexed_km):
        """Entity with no outgoing relations returns an empty list."""
        km, _ = indexed_km

        # "IT Security" entity has no relations in make_cku
        relations = km.get_entity_relations("IT Security")

        assert relations == []

    def test_get_entity_relations_unknown_entity_returns_empty(self, indexed_km):
        """Unknown entity name returns an empty list."""
        km, _ = indexed_km

        relations = km.get_entity_relations("does_not_exist")

        assert relations == []


class TestKnowledgeMapGetAllEntities:
    """Test 17: get_all_entities."""

    def test_get_all_entities_returns_indexed_entities(self, indexed_km):
        """All entities inserted during index_cku are returned."""
        km, cku = indexed_km
        cku_id = source_to_id(cku.meta.source)

        entities = km.get_all_entities()

        names = [e["name"] for e in entities]
        assert "Onboarding" in names
        assert "IT Security" in names
        for entity in entities:
            assert entity["cku_id"] == cku_id

    def test_get_all_entities_empty_map_returns_empty_list(self, km):
        """Fresh KnowledgeMap with nothing indexed returns an empty list."""
        entities = km.get_all_entities()

        assert entities == []


class TestKnowledgeMapStats:
    """Test 18: get_stats accuracy."""

    def test_get_stats_match_indexed_data(self, indexed_km):
        """Stats counters reflect the data from make_cku exactly."""
        km, _ = indexed_km

        stats = km.get_stats()

        assert stats["total_ckus"] == 1
        assert stats["total_entities"] == 2       # e1, e2
        assert stats["total_facts"] == 2           # f1, f2
        assert stats["total_relations"] == 1       # e1 -> e2 (involves)
        # topics: entity types "process", "system" + section title "intro" = 3 distinct
        assert stats["total_topics"] == 3

    def test_get_stats_empty_map(self, km):
        """Empty KnowledgeMap reports all-zero stats."""
        stats = km.get_stats()

        assert stats == {
            "total_ckus": 0,
            "total_entities": 0,
            "total_facts": 0,
            "total_relations": 0,
            "total_topics": 0,
        }


class TestKnowledgeMapReIndex:
    """Test 19: re-indexing replaces, no duplicates."""

    def test_reindex_same_cku_no_duplicates(self, km):
        """Index the same CKU twice; stats must not double-count."""
        cku = make_cku()
        km.index_cku(cku)
        km.index_cku(cku)

        stats = km.get_stats()

        assert stats["total_ckus"] == 1
        assert stats["total_entities"] == 2
        assert stats["total_facts"] == 2
        assert stats["total_relations"] == 1

    def test_reindex_updated_cku_reflects_new_data(self, km):
        """Re-indexing with modified data replaces old entry, not appends."""
        cku_v1 = make_cku(source="docs/versioned.pdf", hash="v1")
        km.index_cku(cku_v1)

        # v2 has a third entity added
        extra_entity = CKUEntity(id="e3", name="HR Department", type="team")
        cku_v2 = make_cku(
            source="docs/versioned.pdf",
            hash="v2",
            entities=cku_v1.entities + [extra_entity],
        )
        km.index_cku(cku_v2)

        stats = km.get_stats()
        assert stats["total_ckus"] == 1
        assert stats["total_entities"] == 3

        names = [e["name"] for e in km.get_all_entities()]
        assert "HR Department" in names


class TestKnowledgeMapMultipleCKUs:
    """Test 20: cross-CKU entity search."""

    def test_multiple_ckus_cross_cku_entity_search(self, km):
        """Index 2 CKUs; entity search returns IDs from both when entity names match."""
        cku_a = make_cku(source="docs/a.pdf", hash="aaa")
        cku_b = make_cku(source="docs/b.pdf", hash="bbb")

        km.index_cku(cku_a)
        km.index_cku(cku_b)

        id_a = source_to_id("docs/a.pdf")
        id_b = source_to_id("docs/b.pdf")

        # Both CKUs have "Onboarding" — both IDs should be returned.
        results = km.find_by_entity("Onboarding")

        assert id_a in results
        assert id_b in results

    def test_multiple_ckus_stats_aggregate_correctly(self, km):
        """Stats across 2 CKUs aggregate all rows."""
        km.index_cku(make_cku(source="docs/x.pdf", hash="x"))
        km.index_cku(make_cku(source="docs/y.pdf", hash="y"))

        stats = km.get_stats()

        assert stats["total_ckus"] == 2
        assert stats["total_entities"] == 4   # 2 per CKU
        assert stats["total_facts"] == 4       # 2 per CKU
        assert stats["total_relations"] == 2   # 1 per CKU

    def test_multiple_ckus_distinct_sources_no_collision(self, km):
        """source_to_id must produce distinct IDs for docs/x.pdf and docs/y.pdf."""
        km.index_cku(make_cku(source="docs/x.pdf", hash="x"))
        km.index_cku(make_cku(source="docs/y.pdf", hash="y"))

        id_x = source_to_id("docs/x.pdf")
        id_y = source_to_id("docs/y.pdf")

        assert id_x != id_y

        results_x = km.find_by_entity("Onboarding")
        assert id_x in results_x
        assert id_y in results_x  # both have "Onboarding"


class TestKnowledgeMapClose:
    """Test 21: close() does not raise."""

    def test_close_does_not_raise(self, tmp_path):
        """Calling close() on a KnowledgeMap must not raise any exception."""
        km = KnowledgeMap(tmp_path / "close_test.db")
        # Should complete without error.
        km.close()

    def test_close_idempotent_via_reconnect(self, tmp_path):
        """Opening, closing, and reopening the same DB file works cleanly."""
        db_path = tmp_path / "reopen.db"
        cku = make_cku()

        km1 = KnowledgeMap(db_path)
        km1.index_cku(cku)
        km1.close()

        km2 = KnowledgeMap(db_path)
        stats = km2.get_stats()
        km2.close()

        assert stats["total_ckus"] == 1
