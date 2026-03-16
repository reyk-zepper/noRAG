"""Unit tests for CKU models, Config, and utils."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from norag.config import Config, load_config
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
from norag.utils import source_to_id


# ---------------------------------------------------------------------------
# Helper — sample CKU factory
# ---------------------------------------------------------------------------


def make_sample_cku(**overrides) -> CKU:
    defaults = dict(
        meta=CKUMeta(
            source="test/sample.pdf",
            compiled=datetime(2026, 3, 16, 10, 0, 0, tzinfo=timezone.utc),
            hash="abc123def456",
            type="pdf/multimodal",
            language="de",
        ),
        summaries=CKUSummary(
            document="A test document about onboarding processes.",
            sections=[
                SectionSummary(id="s1", title="Intro", summary="Introduction to onboarding"),
            ],
        ),
        entities=[
            CKUEntity(
                id="e1",
                name="Onboarding",
                type="process",
                relations=[Relation(target="e2", type="involves")],
            ),
            CKUEntity(id="e2", name="Buddy Program", type="program"),
        ],
        facts=[
            CKUFact(
                id="f1",
                claim="Every new employee gets a buddy in the first 3 days",
                source=SourceRef(page=4, section="s1"),
                confidence=0.95,
                entities=["e1", "e2"],
            ),
        ],
        visuals=[
            CKUVisual(
                id="v1",
                type="flowchart",
                source=SourceRef(page=6),
                description="5-step onboarding flow",
                structured_data={"steps": ["Prep", "Day 1", "Week 1"]},
                context="Illustrates the overall process",
            ),
        ],
        dependencies=["cku:it-security"],
    )
    defaults.update(overrides)
    return CKU(**defaults)


# ---------------------------------------------------------------------------
# CKU construction — all fields populated
# ---------------------------------------------------------------------------


class TestCKUConstruction:
    def test_full_cku_all_fields_accessible(self) -> None:
        """A fully-populated CKU has all fields readable with correct values."""
        cku = make_sample_cku()

        assert cku.meta.source == "test/sample.pdf"
        assert cku.meta.hash == "abc123def456"
        assert cku.meta.type == "pdf/multimodal"
        assert cku.meta.language == "de"
        assert cku.meta.compiled == datetime(2026, 3, 16, 10, 0, 0, tzinfo=timezone.utc)

        assert cku.summaries.document == "A test document about onboarding processes."
        assert len(cku.summaries.sections) == 1
        assert cku.summaries.sections[0].id == "s1"
        assert cku.summaries.sections[0].title == "Intro"

        assert len(cku.entities) == 2
        assert cku.entities[0].id == "e1"
        assert cku.entities[0].name == "Onboarding"
        assert cku.entities[0].type == "process"
        assert len(cku.entities[0].relations) == 1
        assert cku.entities[0].relations[0].target == "e2"
        assert cku.entities[0].relations[0].type == "involves"

        assert len(cku.facts) == 1
        assert cku.facts[0].id == "f1"
        assert cku.facts[0].confidence == 0.95
        assert cku.facts[0].source.page == 4
        assert cku.facts[0].source.section == "s1"
        assert cku.facts[0].entities == ["e1", "e2"]

        assert len(cku.visuals) == 1
        assert cku.visuals[0].id == "v1"
        assert cku.visuals[0].type == "flowchart"
        assert cku.visuals[0].source.page == 6
        assert cku.visuals[0].structured_data == {"steps": ["Prep", "Day 1", "Week 1"]}
        assert cku.visuals[0].context == "Illustrates the overall process"

        assert cku.dependencies == ["cku:it-security"]

    def test_cku_entity_second_has_no_relations(self) -> None:
        """Entity without explicit relations defaults to an empty list."""
        cku = make_sample_cku()
        assert cku.entities[1].relations == []

    def test_cku_visual_description(self) -> None:
        """Visual description field is correctly stored."""
        cku = make_sample_cku()
        assert cku.visuals[0].description == "5-step onboarding flow"


# ---------------------------------------------------------------------------
# CKU with defaults — minimal required fields
# ---------------------------------------------------------------------------


class TestCKUDefaults:
    def test_minimal_cku_empty_lists(self) -> None:
        """CKU built with only required fields gets empty list defaults."""
        cku = CKU(
            meta=CKUMeta(
                source="minimal.md",
                compiled=datetime(2026, 1, 1, tzinfo=timezone.utc),
                hash="deadbeef",
                type="markdown",
            ),
            summaries=CKUSummary(document="Minimal document."),
        )

        assert cku.entities == []
        assert cku.facts == []
        assert cku.visuals == []
        assert cku.dependencies == []

    def test_cku_meta_language_default_en(self) -> None:
        """CKUMeta defaults language to 'en' when not specified."""
        meta = CKUMeta(
            source="doc.md",
            compiled=datetime(2026, 1, 1, tzinfo=timezone.utc),
            hash="aabbcc",
            type="markdown",
        )
        assert meta.language == "en"

    def test_cku_summary_sections_default_empty(self) -> None:
        """CKUSummary defaults sections to an empty list."""
        summary = CKUSummary(document="Just a summary.")
        assert summary.sections == []

    def test_cku_entity_relations_default_empty(self) -> None:
        """CKUEntity defaults relations to an empty list."""
        entity = CKUEntity(id="e1", name="Test", type="concept")
        assert entity.relations == []

    def test_cku_fact_entities_default_empty(self) -> None:
        """CKUFact defaults entities to an empty list."""
        fact = CKUFact(
            id="f1",
            claim="Something is true",
            source=SourceRef(page=1),
        )
        assert fact.entities == []

    def test_cku_fact_confidence_default_one(self) -> None:
        """CKUFact defaults confidence to 1.0."""
        fact = CKUFact(
            id="f1",
            claim="Something is true",
            source=SourceRef(page=1),
        )
        assert fact.confidence == 1.0

    def test_cku_visual_optional_fields_default_none(self) -> None:
        """CKUVisual optional fields structured_data and context default to None."""
        visual = CKUVisual(
            id="v1",
            type="image",
            source=SourceRef(page=3),
            description="A picture",
        )
        assert visual.structured_data is None
        assert visual.context is None

    def test_source_ref_all_optional(self) -> None:
        """SourceRef can be created with no fields — both default to None."""
        ref = SourceRef()
        assert ref.page is None
        assert ref.section is None


# ---------------------------------------------------------------------------
# CKU.to_yaml() — serialization
# ---------------------------------------------------------------------------


class TestCKUToYaml:
    def test_to_yaml_returns_string(self) -> None:
        """to_yaml() returns a str."""
        cku = make_sample_cku()
        result = cku.to_yaml()
        assert isinstance(result, str)

    def test_to_yaml_is_valid_yaml(self) -> None:
        """to_yaml() output can be parsed by yaml.safe_load without error."""
        cku = make_sample_cku()
        loaded = yaml.safe_load(cku.to_yaml())
        assert isinstance(loaded, dict)

    def test_to_yaml_contains_source(self) -> None:
        """Serialized YAML contains the meta.source value."""
        cku = make_sample_cku()
        assert "test/sample.pdf" in cku.to_yaml()

    def test_to_yaml_contains_document_summary(self) -> None:
        """Serialized YAML contains the document summary text."""
        cku = make_sample_cku()
        assert "onboarding processes" in cku.to_yaml()

    def test_to_yaml_contains_entity_name(self) -> None:
        """Serialized YAML contains entity names."""
        cku = make_sample_cku()
        yaml_str = cku.to_yaml()
        assert "Onboarding" in yaml_str
        assert "Buddy Program" in yaml_str

    def test_to_yaml_contains_fact_claim(self) -> None:
        """Serialized YAML contains the fact claim."""
        cku = make_sample_cku()
        assert "buddy" in cku.to_yaml()

    def test_to_yaml_contains_dependency(self) -> None:
        """Serialized YAML contains the dependency string."""
        cku = make_sample_cku()
        assert "cku:it-security" in cku.to_yaml()

    def test_to_yaml_top_level_keys(self) -> None:
        """Serialized YAML has expected top-level keys."""
        cku = make_sample_cku()
        data = yaml.safe_load(cku.to_yaml())
        assert set(data.keys()) >= {"meta", "summaries", "entities", "facts", "visuals"}


# ---------------------------------------------------------------------------
# CKU.from_yaml() — deserialization
# ---------------------------------------------------------------------------


class TestCKUFromYaml:
    def test_from_yaml_returns_cku_instance(self) -> None:
        """from_yaml() returns a CKU instance."""
        cku = make_sample_cku()
        restored = CKU.from_yaml(cku.to_yaml())
        assert isinstance(restored, CKU)

    def test_from_yaml_meta_source(self) -> None:
        """Deserialized CKU has correct meta.source."""
        cku = make_sample_cku()
        restored = CKU.from_yaml(cku.to_yaml())
        assert restored.meta.source == "test/sample.pdf"

    def test_from_yaml_meta_hash(self) -> None:
        """Deserialized CKU has correct meta.hash."""
        cku = make_sample_cku()
        restored = CKU.from_yaml(cku.to_yaml())
        assert restored.meta.hash == "abc123def456"

    def test_from_yaml_document_summary(self) -> None:
        """Deserialized CKU has correct document summary."""
        cku = make_sample_cku()
        restored = CKU.from_yaml(cku.to_yaml())
        assert restored.summaries.document == "A test document about onboarding processes."

    def test_from_yaml_entity_count(self) -> None:
        """Deserialized CKU has the same number of entities."""
        cku = make_sample_cku()
        restored = CKU.from_yaml(cku.to_yaml())
        assert len(restored.entities) == 2

    def test_from_yaml_fact_confidence(self) -> None:
        """Deserialized CKU preserves fact confidence."""
        cku = make_sample_cku()
        restored = CKU.from_yaml(cku.to_yaml())
        assert restored.facts[0].confidence == pytest.approx(0.95)


# ---------------------------------------------------------------------------
# YAML roundtrip — full field equality
# ---------------------------------------------------------------------------


class TestCKUYamlRoundtrip:
    def setup_method(self) -> None:
        self.original = make_sample_cku()
        self.restored = CKU.from_yaml(self.original.to_yaml())

    def test_roundtrip_meta_source(self) -> None:
        assert self.restored.meta.source == self.original.meta.source

    def test_roundtrip_meta_hash(self) -> None:
        assert self.restored.meta.hash == self.original.meta.hash

    def test_roundtrip_meta_type(self) -> None:
        assert self.restored.meta.type == self.original.meta.type

    def test_roundtrip_meta_language(self) -> None:
        assert self.restored.meta.language == self.original.meta.language

    def test_roundtrip_summary_document(self) -> None:
        assert self.restored.summaries.document == self.original.summaries.document

    def test_roundtrip_sections(self) -> None:
        assert len(self.restored.summaries.sections) == len(self.original.summaries.sections)
        assert self.restored.summaries.sections[0].id == "s1"
        assert self.restored.summaries.sections[0].title == "Intro"
        assert self.restored.summaries.sections[0].summary == "Introduction to onboarding"

    def test_roundtrip_entities(self) -> None:
        assert len(self.restored.entities) == len(self.original.entities)
        assert self.restored.entities[0].id == self.original.entities[0].id
        assert self.restored.entities[0].name == self.original.entities[0].name
        assert self.restored.entities[0].type == self.original.entities[0].type

    def test_roundtrip_entity_relations(self) -> None:
        rel_orig = self.original.entities[0].relations[0]
        rel_restored = self.restored.entities[0].relations[0]
        assert rel_restored.target == rel_orig.target
        assert rel_restored.type == rel_orig.type

    def test_roundtrip_facts(self) -> None:
        assert len(self.restored.facts) == len(self.original.facts)
        fact = self.restored.facts[0]
        assert fact.id == "f1"
        assert fact.claim == self.original.facts[0].claim
        assert fact.confidence == pytest.approx(0.95)
        assert fact.entities == ["e1", "e2"]

    def test_roundtrip_fact_source_ref(self) -> None:
        src = self.restored.facts[0].source
        assert src.page == 4
        assert src.section == "s1"

    def test_roundtrip_visuals(self) -> None:
        assert len(self.restored.visuals) == len(self.original.visuals)
        v = self.restored.visuals[0]
        assert v.id == "v1"
        assert v.type == "flowchart"
        assert v.description == "5-step onboarding flow"
        assert v.context == "Illustrates the overall process"

    def test_roundtrip_visual_structured_data(self) -> None:
        sd = self.restored.visuals[0].structured_data
        assert sd == {"steps": ["Prep", "Day 1", "Week 1"]}

    def test_roundtrip_visual_source_page(self) -> None:
        assert self.restored.visuals[0].source.page == 6

    def test_roundtrip_dependencies(self) -> None:
        assert self.restored.dependencies == self.original.dependencies


# ---------------------------------------------------------------------------
# CKUMeta datetime — YAML roundtrip
# ---------------------------------------------------------------------------


class TestCKUMetaDatetime:
    def test_datetime_preserved_after_roundtrip(self) -> None:
        """compiled datetime survives a to_yaml → from_yaml cycle."""
        original_dt = datetime(2026, 3, 16, 10, 0, 0, tzinfo=timezone.utc)
        cku = make_sample_cku()
        restored = CKU.from_yaml(cku.to_yaml())
        # Pydantic normalizes timezone-aware datetimes; compare as aware datetime
        assert restored.meta.compiled.year == original_dt.year
        assert restored.meta.compiled.month == original_dt.month
        assert restored.meta.compiled.day == original_dt.day
        assert restored.meta.compiled.hour == original_dt.hour
        assert restored.meta.compiled.minute == original_dt.minute

    def test_datetime_present_in_yaml_string(self) -> None:
        """The year of the compiled date appears in the YAML output."""
        cku = make_sample_cku()
        assert "2026" in cku.to_yaml()

    def test_datetime_naive_is_accepted(self) -> None:
        """CKUMeta also accepts a naive datetime (without tzinfo)."""
        meta = CKUMeta(
            source="naive.md",
            compiled=datetime(2025, 6, 1, 12, 0, 0),  # naive
            hash="ff00ff00",
            type="markdown",
        )
        assert meta.compiled.year == 2025
        assert meta.compiled.tzinfo is None


# ---------------------------------------------------------------------------
# CKUEntity with relations
# ---------------------------------------------------------------------------


class TestCKUEntityWithRelations:
    def test_entity_multiple_relations(self) -> None:
        """CKUEntity stores multiple Relation objects correctly."""
        entity = CKUEntity(
            id="e10",
            name="System X",
            type="system",
            relations=[
                Relation(target="e20", type="depends_on"),
                Relation(target="e30", type="owns"),
                Relation(target="e40", type="integrates"),
            ],
        )
        assert len(entity.relations) == 3
        assert entity.relations[0].target == "e20"
        assert entity.relations[1].type == "owns"
        assert entity.relations[2].target == "e40"

    def test_entity_relations_survive_yaml_roundtrip(self) -> None:
        """Multiple relations on an entity survive a full CKU YAML roundtrip."""
        cku = make_sample_cku(
            entities=[
                CKUEntity(
                    id="eA",
                    name="Alpha",
                    type="concept",
                    relations=[
                        Relation(target="eB", type="precedes"),
                        Relation(target="eC", type="conflicts"),
                    ],
                ),
                CKUEntity(id="eB", name="Beta", type="concept"),
                CKUEntity(id="eC", name="Gamma", type="concept"),
            ]
        )
        restored = CKU.from_yaml(cku.to_yaml())
        rels = restored.entities[0].relations
        assert len(rels) == 2
        assert rels[0].target == "eB"
        assert rels[0].type == "precedes"
        assert rels[1].target == "eC"
        assert rels[1].type == "conflicts"

    def test_entity_serializes_to_yaml_with_relations(self) -> None:
        """Entity relation targets appear in the serialized YAML string."""
        cku = make_sample_cku()
        yaml_str = cku.to_yaml()
        assert "e2" in yaml_str
        assert "involves" in yaml_str


# ---------------------------------------------------------------------------
# CKUFact with SourceRef
# ---------------------------------------------------------------------------


class TestCKUFactWithSourceRef:
    def test_fact_source_page_and_section(self) -> None:
        """CKUFact stores page and section in SourceRef."""
        fact = CKUFact(
            id="f99",
            claim="The sky is blue",
            source=SourceRef(page=12, section="s3"),
            confidence=0.8,
            entities=["eX"],
        )
        assert fact.source.page == 12
        assert fact.source.section == "s3"

    def test_fact_source_page_only(self) -> None:
        """SourceRef with only page has section as None."""
        fact = CKUFact(
            id="f100",
            claim="Claim with page ref only",
            source=SourceRef(page=7),
        )
        assert fact.source.page == 7
        assert fact.source.section is None

    def test_fact_source_section_only(self) -> None:
        """SourceRef with only section has page as None."""
        fact = CKUFact(
            id="f101",
            claim="Claim with section ref only",
            source=SourceRef(section="intro"),
        )
        assert fact.source.page is None
        assert fact.source.section == "intro"

    def test_fact_source_roundtrip(self) -> None:
        """SourceRef page and section survive a YAML roundtrip inside a CKU."""
        cku = make_sample_cku(
            facts=[
                CKUFact(
                    id="f1",
                    claim="Claim",
                    source=SourceRef(page=99, section="appendix"),
                    confidence=0.7,
                )
            ]
        )
        restored = CKU.from_yaml(cku.to_yaml())
        src = restored.facts[0].source
        assert src.page == 99
        assert src.section == "appendix"


# ---------------------------------------------------------------------------
# CKUVisual with structured_data
# ---------------------------------------------------------------------------


class TestCKUVisualWithStructuredData:
    def test_visual_structured_data_dict(self) -> None:
        """CKUVisual stores a dict as structured_data."""
        visual = CKUVisual(
            id="v99",
            type="table",
            source=SourceRef(page=5),
            description="Employee table",
            structured_data={"headers": ["Name", "Role"], "rows": [["Alice", "Dev"]]},
        )
        assert visual.structured_data["headers"] == ["Name", "Role"]
        assert visual.structured_data["rows"][0] == ["Alice", "Dev"]

    def test_visual_structured_data_nested(self) -> None:
        """CKUVisual stores nested dicts in structured_data."""
        visual = CKUVisual(
            id="v100",
            type="flowchart",
            source=SourceRef(page=10),
            description="Nested flow",
            structured_data={"nodes": {"start": "A", "end": "Z"}, "edges": 5},
        )
        assert visual.structured_data["nodes"]["start"] == "A"
        assert visual.structured_data["edges"] == 5

    def test_visual_structured_data_roundtrip(self) -> None:
        """structured_data dict survives a YAML roundtrip."""
        expected = {"steps": ["Prep", "Day 1", "Week 1"]}
        cku = make_sample_cku()
        restored = CKU.from_yaml(cku.to_yaml())
        assert restored.visuals[0].structured_data == expected

    def test_visual_no_structured_data(self) -> None:
        """CKUVisual without structured_data has None after roundtrip."""
        cku = make_sample_cku(
            visuals=[
                CKUVisual(
                    id="v1",
                    type="image",
                    source=SourceRef(page=2),
                    description="Just a photo",
                )
            ]
        )
        restored = CKU.from_yaml(cku.to_yaml())
        assert restored.visuals[0].structured_data is None


# ---------------------------------------------------------------------------
# Invalid data — ValidationError
# ---------------------------------------------------------------------------


class TestCKUValidation:
    def test_cku_missing_meta_raises(self) -> None:
        """CKU raises ValidationError when meta is missing."""
        with pytest.raises(ValidationError):
            CKU(summaries=CKUSummary(document="no meta"))  # type: ignore[call-arg]

    def test_cku_missing_summaries_raises(self) -> None:
        """CKU raises ValidationError when summaries is missing."""
        with pytest.raises(ValidationError):
            CKU(  # type: ignore[call-arg]
                meta=CKUMeta(
                    source="x.md",
                    compiled=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    hash="h",
                    type="markdown",
                )
            )

    def test_cku_meta_missing_source_raises(self) -> None:
        """CKUMeta raises ValidationError when source is missing."""
        with pytest.raises(ValidationError):
            CKUMeta(  # type: ignore[call-arg]
                compiled=datetime(2026, 1, 1, tzinfo=timezone.utc),
                hash="h",
                type="markdown",
            )

    def test_cku_meta_missing_compiled_raises(self) -> None:
        """CKUMeta raises ValidationError when compiled is missing."""
        with pytest.raises(ValidationError):
            CKUMeta(source="x.md", hash="h", type="markdown")  # type: ignore[call-arg]

    def test_cku_meta_missing_hash_raises(self) -> None:
        """CKUMeta raises ValidationError when hash is missing."""
        with pytest.raises(ValidationError):
            CKUMeta(  # type: ignore[call-arg]
                source="x.md",
                compiled=datetime(2026, 1, 1, tzinfo=timezone.utc),
                type="markdown",
            )

    def test_cku_entity_missing_id_raises(self) -> None:
        """CKUEntity raises ValidationError when id is missing."""
        with pytest.raises(ValidationError):
            CKUEntity(name="Test", type="concept")  # type: ignore[call-arg]

    def test_cku_fact_missing_claim_raises(self) -> None:
        """CKUFact raises ValidationError when claim is missing."""
        with pytest.raises(ValidationError):
            CKUFact(id="f1", source=SourceRef(page=1))  # type: ignore[call-arg]

    def test_cku_visual_missing_description_raises(self) -> None:
        """CKUVisual raises ValidationError when description is missing."""
        with pytest.raises(ValidationError):
            CKUVisual(id="v1", type="image", source=SourceRef(page=1))  # type: ignore[call-arg]

    def test_relation_missing_target_raises(self) -> None:
        """Relation raises ValidationError when target is missing."""
        with pytest.raises(ValidationError):
            Relation(type="involves")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Config — defaults
# ---------------------------------------------------------------------------


class TestConfigDefaults:
    def test_default_provider_is_claude(self) -> None:
        """Default Config has provider='claude'."""
        cfg = Config()
        assert cfg.provider == "claude"

    def test_default_model(self) -> None:
        """Default Config has a non-empty model string."""
        cfg = Config()
        assert cfg.model != ""
        assert "claude" in cfg.model.lower()

    def test_default_store_dir_is_norag_subdir(self) -> None:
        """Default store_dir ends with '.norag'."""
        cfg = Config()
        assert cfg.store_dir.name == ".norag"

    def test_default_api_key_is_none(self) -> None:
        """Default Config has api_key=None."""
        cfg = Config()
        assert cfg.api_key is None

    def test_default_ollama_host(self) -> None:
        """Default ollama_host points to localhost."""
        cfg = Config()
        assert "localhost" in cfg.ollama_host


# ---------------------------------------------------------------------------
# Config — derived paths
# ---------------------------------------------------------------------------


class TestConfigDerivedPaths:
    def test_ckus_dir_derived_from_store_dir(self, tmp_path: Path) -> None:
        """ckus_dir is store_dir / 'ckus'."""
        cfg = Config(store_dir=tmp_path / "mystore")
        assert cfg.ckus_dir == tmp_path / "mystore" / "ckus"

    def test_db_path_derived_from_store_dir(self, tmp_path: Path) -> None:
        """db_path is store_dir / 'knowledge.db'."""
        cfg = Config(store_dir=tmp_path / "mystore")
        assert cfg.db_path == tmp_path / "mystore" / "knowledge.db"

    def test_ckus_dir_is_path_instance(self, tmp_path: Path) -> None:
        """ckus_dir is a Path, not a string."""
        cfg = Config(store_dir=tmp_path)
        assert isinstance(cfg.ckus_dir, Path)

    def test_db_path_is_path_instance(self, tmp_path: Path) -> None:
        """db_path is a Path, not a string."""
        cfg = Config(store_dir=tmp_path)
        assert isinstance(cfg.db_path, Path)

    def test_store_dir_is_path_instance(self) -> None:
        """store_dir is coerced to a Path even if a string is passed."""
        cfg = Config(store_dir="/tmp/norag_test")
        assert isinstance(cfg.store_dir, Path)

    def test_ckus_dir_parent_is_store_dir(self, tmp_path: Path) -> None:
        """ckus_dir.parent equals store_dir."""
        store = tmp_path / "store"
        cfg = Config(store_dir=store)
        assert cfg.ckus_dir.parent == cfg.store_dir

    def test_db_path_parent_is_store_dir(self, tmp_path: Path) -> None:
        """db_path.parent equals store_dir."""
        store = tmp_path / "store"
        cfg = Config(store_dir=store)
        assert cfg.db_path.parent == cfg.store_dir


# ---------------------------------------------------------------------------
# load_config — env var overrides
# ---------------------------------------------------------------------------


class TestLoadConfigEnvVars:
    def test_norag_provider_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """NORAG_PROVIDER env var overrides the default provider."""
        monkeypatch.setenv("NORAG_PROVIDER", "ollama")
        cfg = load_config()
        assert cfg.provider == "ollama"

    def test_norag_model_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """NORAG_MODEL env var overrides the default model."""
        monkeypatch.setenv("NORAG_MODEL", "llama3:8b")
        cfg = load_config()
        assert cfg.model == "llama3:8b"

    def test_norag_api_key_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """NORAG_API_KEY env var sets api_key."""
        monkeypatch.setenv("NORAG_API_KEY", "sk-test-12345")
        cfg = load_config()
        assert cfg.api_key == "sk-test-12345"

    def test_anthropic_api_key_alias(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """ANTHROPIC_API_KEY env var sets api_key when NORAG_API_KEY is not set."""
        monkeypatch.delenv("NORAG_API_KEY", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic-abc")
        cfg = load_config()
        assert cfg.api_key == "sk-anthropic-abc"

    def test_norag_api_key_beats_anthropic_alias(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """NORAG_API_KEY takes precedence over ANTHROPIC_API_KEY."""
        monkeypatch.setenv("NORAG_API_KEY", "sk-norag-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic-key")
        cfg = load_config()
        assert cfg.api_key == "sk-norag-key"

    def test_norag_ollama_host_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """NORAG_OLLAMA_HOST env var sets ollama_host."""
        monkeypatch.setenv("NORAG_OLLAMA_HOST", "http://gpu-box:11434")
        cfg = load_config()
        assert cfg.ollama_host == "http://gpu-box:11434"

    def test_ollama_host_alias(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OLLAMA_HOST env var sets ollama_host when NORAG_OLLAMA_HOST is not set."""
        monkeypatch.delenv("NORAG_OLLAMA_HOST", raising=False)
        monkeypatch.setenv("OLLAMA_HOST", "http://remote:11434")
        cfg = load_config()
        assert cfg.ollama_host == "http://remote:11434"


# ---------------------------------------------------------------------------
# load_config — explicit store_dir argument
# ---------------------------------------------------------------------------


class TestLoadConfigStoreDir:
    def test_explicit_store_dir_overrides_default(self, tmp_path: Path) -> None:
        """Passing store_dir to load_config overrides the default."""
        custom = tmp_path / "custom_store"
        cfg = load_config(store_dir=custom)
        assert cfg.store_dir == custom

    def test_explicit_store_dir_overrides_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Explicit store_dir argument beats NORAG_STORE_DIR env var."""
        monkeypatch.setenv("NORAG_STORE_DIR", str(tmp_path / "env_store"))
        explicit = tmp_path / "explicit_store"
        cfg = load_config(store_dir=explicit)
        assert cfg.store_dir == explicit

    def test_explicit_store_dir_derives_ckus_dir(self, tmp_path: Path) -> None:
        """ckus_dir is derived from the explicit store_dir."""
        custom = tmp_path / "mystore"
        cfg = load_config(store_dir=custom)
        assert cfg.ckus_dir == custom / "ckus"

    def test_explicit_store_dir_derives_db_path(self, tmp_path: Path) -> None:
        """db_path is derived from the explicit store_dir."""
        custom = tmp_path / "mystore"
        cfg = load_config(store_dir=custom)
        assert cfg.db_path == custom / "knowledge.db"

    def test_load_config_reads_config_yaml(self, tmp_path: Path) -> None:
        """load_config reads provider from a config.yaml inside store_dir."""
        store = tmp_path / ".norag"
        store.mkdir(parents=True)
        (store / "config.yaml").write_text("provider: ollama\n", encoding="utf-8")
        cfg = load_config(store_dir=store)
        assert cfg.provider == "ollama"


# ---------------------------------------------------------------------------
# source_to_id — basic format
# ---------------------------------------------------------------------------


class TestSourceToIdBasic:
    def test_returns_string(self) -> None:
        """source_to_id returns a str."""
        result = source_to_id("docs/notes.md")
        assert isinstance(result, str)

    def test_format_lowercase_stem_dash_hash(self) -> None:
        """Result is '{stem}-{8-char-hex}' where stem is lowercase."""
        result = source_to_id("docs/Notes.md")
        # stem is 'notes', followed by '-' and 8 hex chars
        parts = result.rsplit("-", 1)
        assert len(parts) == 2
        stem_part, hash_part = parts
        assert stem_part.islower() or stem_part == stem_part.lower()
        assert len(hash_part) == 8
        assert all(c in "0123456789abcdef" for c in hash_part)

    def test_stem_is_lowercase(self) -> None:
        """The stem portion of the ID is always lowercase."""
        result = source_to_id("DOCS/REPORT.PDF")
        stem = result.rsplit("-", 1)[0]
        assert stem == stem.lower()

    def test_hash_is_8_chars(self) -> None:
        """The hash suffix is exactly 8 hex characters."""
        result = source_to_id("any/path/file.txt")
        hash_part = result.rsplit("-", 1)[1]
        assert len(hash_part) == 8

    def test_hash_matches_sha256_of_path(self) -> None:
        """The hash suffix equals the first 8 chars of sha256(source)."""
        path = "some/specific/document.md"
        expected_hash = hashlib.sha256(path.encode()).hexdigest()[:8]
        result = source_to_id(path)
        assert result.endswith(expected_hash)


# ---------------------------------------------------------------------------
# source_to_id — collision prevention
# ---------------------------------------------------------------------------


class TestSourceToIdCollisionPrevention:
    def test_same_filename_different_directories(self) -> None:
        """Files with the same name in different directories get different IDs."""
        id_a = source_to_id("docs/a/notes.md")
        id_b = source_to_id("docs/b/notes.md")
        assert id_a != id_b

    def test_same_stem_different_extension(self) -> None:
        """Files with same stem but different extension get different IDs."""
        id_md = source_to_id("docs/report.md")
        id_pdf = source_to_id("docs/report.pdf")
        assert id_md != id_pdf

    def test_different_files_deeply_nested(self) -> None:
        """Deeply nested files with same name collide only on hash, not stem."""
        id_x = source_to_id("a/b/c/d/e/readme.md")
        id_y = source_to_id("x/y/z/readme.md")
        assert id_x != id_y

    def test_same_path_same_id(self) -> None:
        """The same path always produces the same ID (deterministic)."""
        path = "docs/manual.pdf"
        assert source_to_id(path) == source_to_id(path)

    def test_single_char_filename(self) -> None:
        """source_to_id handles single-character filenames."""
        result = source_to_id("a/b.md")
        assert result.startswith("b-")


# ---------------------------------------------------------------------------
# source_to_id — special characters
# ---------------------------------------------------------------------------


class TestSourceToIdSpecialChars:
    def test_spaces_in_filename_replaced(self) -> None:
        """Spaces in the filename stem are replaced with hyphens."""
        result = source_to_id("docs/my document.pdf")
        stem = result.rsplit("-", 1)[0]
        assert " " not in stem

    def test_umlauts_in_filename(self) -> None:
        """Files with umlaut names produce a valid ID with safe characters.

        Python's str.isalnum() returns True for unicode letters (ü, ä, ö), so the
        implementation keeps them in the stem rather than replacing them with hyphens.
        The important guarantee is that the ID is deterministic and the hash suffix
        is correct regardless of what the stem looks like.
        """
        result = source_to_id("docs/schüler.pdf")
        # Must be deterministic
        assert result == source_to_id("docs/schüler.pdf")
        # Hash suffix must still be 8 hex chars
        hash_part = result.rsplit("-", 1)[1]
        assert len(hash_part) == 8
        assert all(c in "0123456789abcdef" for c in hash_part)
        # Stem portion must not contain a literal '.' (extension stripped)
        stem = result.rsplit("-", 1)[0]
        assert "." not in stem

    def test_special_chars_replaced_with_hyphens(self) -> None:
        """Special characters (!, @, #) become hyphens."""
        result = source_to_id("docs/my!special@file#.md")
        stem = result.rsplit("-", 1)[0]
        assert "!" not in stem
        assert "@" not in stem
        assert "#" not in stem

    def test_result_has_no_leading_trailing_hyphen_in_stem(self) -> None:
        """Leading/trailing hyphens are stripped from the stem."""
        result = source_to_id("docs/---file---.md")
        stem = result.rsplit("-", 1)[0]
        assert not stem.startswith("-")
        assert not stem.endswith("-")

    def test_unicode_path_produces_stable_hash(self) -> None:
        """A unicode path produces a consistent, 8-char hex hash."""
        path = "docs/données-financières.pdf"
        result1 = source_to_id(path)
        result2 = source_to_id(path)
        assert result1 == result2
        hash_part = result1.rsplit("-", 1)[1]
        assert len(hash_part) == 8

    def test_dot_in_stem_handled(self) -> None:
        """Dots in the stem (before extension) are replaced with hyphens."""
        result = source_to_id("docs/v1.2.3.release.md")
        stem = result.rsplit("-", 1)[0]
        assert "." not in stem

    def test_result_contains_only_safe_chars(self) -> None:
        """The full ID contains only alphanumeric characters and hyphens."""
        result = source_to_id("my path/file name (2024)!.pdf")
        assert all(c.isalnum() or c == "-" for c in result)
