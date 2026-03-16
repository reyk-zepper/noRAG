"""Unit tests for the noRAG query layer: Router and Assembler."""

from pathlib import Path
from datetime import datetime, timezone

import pytest

from norag.query.router import Router
from norag.query.assembler import Assembler, AssembledContext
from norag.store.cku_store import CKUStore
from norag.store.knowledge_map import KnowledgeMap
from norag.models.cku import (
    CKU,
    CKUMeta,
    CKUSummary,
    CKUEntity,
    CKUFact,
    CKUVisual,
    SourceRef,
    Relation,
    SectionSummary,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_cku(
    source="test/doc.pdf",
    hash="abc123",
    doc_summary="Test summary",
    entity_name="Onboarding",
    fact_claim="Buddy in 3 days",
    **kwargs,
) -> CKU:
    return CKU(
        meta=CKUMeta(
            source=source,
            compiled=datetime(2026, 3, 16, tzinfo=timezone.utc),
            hash=hash,
            type="pdf",
            language="de",
        ),
        summaries=CKUSummary(
            document=doc_summary,
            sections=[SectionSummary(id="s1", title="Intro", summary="Intro")],
        ),
        entities=[
            CKUEntity(
                id="e1",
                name=entity_name,
                type="process",
                relations=[Relation(target="e2", type="involves")],
            )
        ],
        facts=[
            CKUFact(
                id="f1",
                claim=fact_claim,
                source=SourceRef(page=4),
                confidence=0.95,
                entities=["e1"],
            )
        ],
        visuals=[
            CKUVisual(
                id="v1",
                type="flowchart",
                source=SourceRef(page=6),
                description="Process flow",
            )
        ],
        dependencies=[],
    )


def setup_store_and_map(tmp_path, ckus):
    """Helper: saves CKUs to store and indexes them in knowledge map."""
    store = CKUStore(tmp_path / "ckus")
    km = KnowledgeMap(tmp_path / "knowledge.db")
    for cku in ckus:
        store.save(cku)
        km.index_cku(cku)
    return store, km


# ---------------------------------------------------------------------------
# Router Tests
# ---------------------------------------------------------------------------


class TestExtractKeywords:
    def test_english_stopwords_removed(self):
        router = Router(KnowledgeMap.__new__(KnowledgeMap))
        # Bypass __init__ — we only test the pure helper method
        router.km = None  # not needed for keyword extraction
        keywords = router._extract_keywords("How does the onboarding process work?")
        assert "onboarding" in keywords
        assert "process" in keywords
        assert "work" in keywords
        # stopwords must be absent
        assert "how" not in keywords
        assert "does" not in keywords
        assert "the" not in keywords

    def test_german_stopwords_removed(self):
        router = Router.__new__(Router)
        keywords = router._extract_keywords("Wie funktioniert das Onboarding?")
        assert "funktioniert" in keywords
        assert "onboarding" in keywords
        # German stopwords
        assert "wie" not in keywords
        assert "das" not in keywords

    def test_short_words_filtered(self):
        router = Router.__new__(Router)
        # "is", "a", "to" are either stopwords or too short (len <= 2)
        keywords = router._extract_keywords("Is a go to action possible?")
        for kw in keywords:
            assert len(kw) > 2, f"Short word leaked through: {kw!r}"


class TestRouterRoute:
    def test_route_finds_entity_match(self, tmp_path):
        cku = make_cku(source="docs/onboarding.pdf", entity_name="Onboarding")
        store, km = setup_store_and_map(tmp_path, [cku])
        router = Router(km)

        results = router.route("Tell me about onboarding")
        expected_id = CKUStore._source_to_id("docs/onboarding.pdf")
        assert expected_id in results

    def test_route_finds_topic_match(self, tmp_path):
        # entity type "process" becomes a topic; keyword "process" should match
        cku = make_cku(source="docs/process.pdf", entity_name="Deployment", fact_claim="Deploy daily")
        store, km = setup_store_and_map(tmp_path, [cku])
        router = Router(km)

        results = router.route("Explain the process")
        expected_id = CKUStore._source_to_id("docs/process.pdf")
        assert expected_id in results

    def test_route_finds_fact_match(self, tmp_path):
        cku = make_cku(source="docs/buddy.pdf", fact_claim="Buddy assignment happens in 3 days")
        store, km = setup_store_and_map(tmp_path, [cku])
        router = Router(km)

        results = router.route("buddy")
        expected_id = CKUStore._source_to_id("docs/buddy.pdf")
        assert expected_id in results

    def test_route_returns_empty_for_no_match(self, tmp_path):
        cku = make_cku(source="docs/hr.pdf", entity_name="Vacation", fact_claim="30 days vacation")
        store, km = setup_store_and_map(tmp_path, [cku])
        router = Router(km)

        results = router.route("quantum entanglement laser photon")
        assert results == []

    def test_route_respects_top_k(self, tmp_path):
        # Create 10 distinct CKUs all matching keyword "process"
        ckus = [
            make_cku(
                source=f"docs/doc{i}.pdf",
                hash=f"hash{i}",
                entity_name="Process",
                fact_claim=f"Process step {i}",
            )
            for i in range(10)
        ]
        store, km = setup_store_and_map(tmp_path, ckus)
        router = Router(km)

        results = router.route("process steps", top_k=3)
        assert len(results) <= 3

    def test_route_ranking_entity_beats_fact_only(self, tmp_path):
        # cku_high matches on entity name ("buddy") → weight 3
        # cku_low matches only in fact text → weight 1
        cku_high = make_cku(
            source="docs/high.pdf",
            entity_name="Buddy",
            fact_claim="Onboarding overview",
        )
        cku_low = make_cku(
            source="docs/low.pdf",
            entity_name="Manager",
            fact_claim="Buddy is assigned after hiring",
        )
        store, km = setup_store_and_map(tmp_path, [cku_high, cku_low])
        router = Router(km)

        results = router.route("buddy", top_k=5)
        id_high = CKUStore._source_to_id("docs/high.pdf")
        id_low = CKUStore._source_to_id("docs/low.pdf")

        assert id_high in results
        assert id_low in results
        # high-scoring entry must appear before low-scoring one
        assert results.index(id_high) < results.index(id_low)


# ---------------------------------------------------------------------------
# Assembler Tests
# ---------------------------------------------------------------------------


class TestAssembler:
    def test_assemble_single_cku(self, tmp_path):
        cku = make_cku(
            source="docs/onboarding.pdf",
            doc_summary="Full onboarding guide",
            fact_claim="Buddy in 3 days",
        )
        store, _ = setup_store_and_map(tmp_path, [cku])
        assembler = Assembler(store)
        cku_id = CKUStore._source_to_id("docs/onboarding.pdf")

        ctx = assembler.assemble([cku_id], question="How does onboarding work?")

        assert len(ctx.summaries) == 1
        assert ctx.summaries[0]["summary"] == "Full onboarding guide"
        assert len(ctx.facts) == 1
        assert ctx.facts[0]["claim"] == "Buddy in 3 days"
        assert len(ctx.visuals) == 1
        assert "docs/onboarding.pdf" in ctx.sources

    def test_assemble_multiple_ckus(self, tmp_path):
        cku1 = make_cku(source="docs/a.pdf", doc_summary="Summary A", fact_claim="Fact A")
        cku2 = make_cku(source="docs/b.pdf", doc_summary="Summary B", fact_claim="Fact B", hash="xyz999")
        store, _ = setup_store_and_map(tmp_path, [cku1, cku2])
        assembler = Assembler(store)

        id1 = CKUStore._source_to_id("docs/a.pdf")
        id2 = CKUStore._source_to_id("docs/b.pdf")
        ctx = assembler.assemble([id1, id2], question="Everything")

        assert len(ctx.summaries) == 2
        summaries_text = [s["summary"] for s in ctx.summaries]
        assert "Summary A" in summaries_text
        assert "Summary B" in summaries_text

        claims = [f["claim"] for f in ctx.facts]
        assert "Fact A" in claims
        assert "Fact B" in claims

    def test_assemble_missing_cku_skipped(self, tmp_path):
        cku = make_cku(source="docs/real.pdf")
        store, _ = setup_store_and_map(tmp_path, [cku])
        assembler = Assembler(store)

        real_id = CKUStore._source_to_id("docs/real.pdf")
        ghost_id = "nonexistent-cku-id-0000"

        # Should not raise; ghost_id is silently skipped
        ctx = assembler.assemble([real_id, ghost_id], question="Something")

        assert len(ctx.summaries) == 1
        assert len(ctx.facts) == 1

    def test_assemble_empty_list(self, tmp_path):
        store = CKUStore(tmp_path / "ckus")
        assembler = Assembler(store)

        ctx = assembler.assemble([], question="Anything")

        assert ctx.summaries == []
        assert ctx.facts == []
        assert ctx.visuals == []
        assert ctx.sources == []

    def test_to_prompt_context_format(self, tmp_path):
        cku = make_cku(
            source="docs/guide.pdf",
            doc_summary="Onboarding guide",
            fact_claim="Day 1 starts with orientation",
        )
        store, _ = setup_store_and_map(tmp_path, [cku])
        assembler = Assembler(store)
        cku_id = CKUStore._source_to_id("docs/guide.pdf")

        ctx = assembler.assemble([cku_id], question="What happens on day 1?")
        prompt = ctx.to_prompt_context()

        assert "## Relevant Summaries" in prompt
        assert "## Relevant Facts" in prompt
        assert "docs/guide.pdf" in prompt  # source citation present

    def test_token_estimate_positive(self, tmp_path):
        cku = make_cku(source="docs/doc.pdf", doc_summary="A detailed knowledge document")
        store, _ = setup_store_and_map(tmp_path, [cku])
        assembler = Assembler(store)
        cku_id = CKUStore._source_to_id("docs/doc.pdf")

        ctx = assembler.assemble([cku_id], question="Tell me about this document")

        assert isinstance(ctx.token_estimate, int)
        assert ctx.token_estimate > 0

    def test_sources_deduplicated(self, tmp_path):
        # Two CKUs with the same source path — sources list must deduplicate
        cku1 = make_cku(source="docs/shared.pdf", hash="hash1", fact_claim="First fact")
        # Re-save with updated hash to simulate a re-compiled version;
        # same source → same CKU ID → store overwrites, one entry
        cku2 = make_cku(source="docs/shared.pdf", hash="hash2", fact_claim="Second fact")

        store = CKUStore(tmp_path / "ckus")
        # Only the last save persists (same ID), so sources can only appear once
        store.save(cku1)
        store.save(cku2)

        assembler = Assembler(store)
        cku_id = CKUStore._source_to_id("docs/shared.pdf")

        ctx = assembler.assemble([cku_id, cku_id], question="Anything")

        # Even when the same ID appears twice in input, source is listed only once
        assert ctx.sources.count("docs/shared.pdf") == 1

    def test_sources_deduplicated_across_ckus(self, tmp_path):
        # Two separate CKUs from different sources → both appear in sources
        cku_a = make_cku(source="docs/alpha.pdf", hash="h1", fact_claim="Alpha fact")
        cku_b = make_cku(source="docs/beta.pdf", hash="h2", fact_claim="Beta fact")
        store, _ = setup_store_and_map(tmp_path, [cku_a, cku_b])
        assembler = Assembler(store)

        id_a = CKUStore._source_to_id("docs/alpha.pdf")
        id_b = CKUStore._source_to_id("docs/beta.pdf")

        ctx = assembler.assemble([id_a, id_b], question="All facts")

        assert "docs/alpha.pdf" in ctx.sources
        assert "docs/beta.pdf" in ctx.sources
        # No duplicates
        assert len(ctx.sources) == len(set(ctx.sources))


# ---------------------------------------------------------------------------
# Integration: Router + Assembler end-to-end
# ---------------------------------------------------------------------------


class TestRouterAssemblerIntegration:
    def test_route_then_assemble(self, tmp_path):
        cku = make_cku(
            source="docs/integration.pdf",
            doc_summary="Integration test document",
            entity_name="Onboarding",
            fact_claim="Onboarding takes three days",
        )
        store, km = setup_store_and_map(tmp_path, [cku])
        router = Router(km)
        assembler = Assembler(store)

        # Step 1: route
        cku_ids = router.route("How long does onboarding take?", top_k=5)
        assert len(cku_ids) > 0, "Router should return at least one result"

        expected_id = CKUStore._source_to_id("docs/integration.pdf")
        assert expected_id in cku_ids

        # Step 2: assemble
        ctx = assembler.assemble(cku_ids, question="How long does onboarding take?")

        assert len(ctx.summaries) > 0
        assert any("onboarding" in f["claim"].lower() for f in ctx.facts)
        assert "docs/integration.pdf" in ctx.sources

        # Step 3: prompt context is usable
        prompt = ctx.to_prompt_context()
        assert len(prompt) > 0
        assert ctx.token_estimate > 0
