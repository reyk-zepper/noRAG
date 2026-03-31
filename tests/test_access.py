"""Unit tests for noRAG access control."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from norag.models.cku import CKU, CKUAccess, CKUMeta, CKUSummary
from norag.store import CKUStore, KnowledgeMap
from norag.config import Config


# ---------------------------------------------------------------------------
# CKUAccess model
# ---------------------------------------------------------------------------


class TestCKUAccess:
    def test_default_empty_roles(self) -> None:
        access = CKUAccess()
        assert access.roles == []

    def test_roles_set(self) -> None:
        access = CKUAccess(roles=["hr", "management"])
        assert "hr" in access.roles
        assert "management" in access.roles

    def test_meta_default_access(self) -> None:
        meta = CKUMeta(
            source="test.md",
            compiled=datetime.now(timezone.utc),
            hash="abc",
            type="markdown",
        )
        assert meta.access.roles == []

    def test_meta_with_roles(self) -> None:
        meta = CKUMeta(
            source="secret.pdf",
            compiled=datetime.now(timezone.utc),
            hash="abc",
            type="pdf",
            access=CKUAccess(roles=["admin"]),
        )
        assert meta.access.roles == ["admin"]


# ---------------------------------------------------------------------------
# CKU YAML roundtrip with access
# ---------------------------------------------------------------------------


class TestCKUAccessYaml:
    def test_roundtrip_with_roles(self) -> None:
        cku = CKU(
            meta=CKUMeta(
                source="test.md",
                compiled=datetime.now(timezone.utc),
                hash="abc123",
                type="markdown",
                access=CKUAccess(roles=["hr", "management"]),
            ),
            summaries=CKUSummary(document="Test"),
        )
        yaml_str = cku.to_yaml()
        loaded = CKU.from_yaml(yaml_str)
        assert loaded.meta.access.roles == ["hr", "management"]

    def test_roundtrip_empty_roles(self) -> None:
        cku = CKU(
            meta=CKUMeta(
                source="public.md",
                compiled=datetime.now(timezone.utc),
                hash="abc",
                type="markdown",
            ),
            summaries=CKUSummary(document="Public doc"),
        )
        yaml_str = cku.to_yaml()
        loaded = CKU.from_yaml(yaml_str)
        assert loaded.meta.access.roles == []


# ---------------------------------------------------------------------------
# Access filtering in QueryEngine
# ---------------------------------------------------------------------------


class TestAccessFiltering:
    @pytest.fixture
    def store_with_ckus(self, tmp_path: Path):
        """Create a store with public and restricted CKUs."""
        store = CKUStore(tmp_path / "ckus")
        km = KnowledgeMap(tmp_path / "knowledge.db")

        # Public CKU
        public_cku = CKU(
            meta=CKUMeta(
                source="public.md",
                compiled=datetime.now(timezone.utc),
                hash="pub123",
                type="markdown",
                access=CKUAccess(roles=[]),
            ),
            summaries=CKUSummary(document="Public knowledge"),
        )
        store.save(public_cku)
        km.index_cku(public_cku)

        # HR-restricted CKU
        hr_cku = CKU(
            meta=CKUMeta(
                source="salaries.pdf",
                compiled=datetime.now(timezone.utc),
                hash="hr123",
                type="pdf",
                access=CKUAccess(roles=["hr", "management"]),
            ),
            summaries=CKUSummary(document="Salary data"),
        )
        store.save(hr_cku)
        km.index_cku(hr_cku)

        # Admin-only CKU
        admin_cku = CKU(
            meta=CKUMeta(
                source="secrets.md",
                compiled=datetime.now(timezone.utc),
                hash="adm123",
                type="markdown",
                access=CKUAccess(roles=["admin"]),
            ),
            summaries=CKUSummary(document="Secret info"),
        )
        store.save(admin_cku)
        km.index_cku(admin_cku)

        return store, km, tmp_path

    def test_anonymous_sees_only_public(self, store_with_ckus) -> None:
        """Anonymous user (empty role) only sees public CKUs."""
        store, km, tmp_path = store_with_ckus
        from norag.query.engine import QueryEngine

        # Get all CKU IDs
        all_ids = store.list_all()
        assert len(all_ids) == 3

        # Filter as anonymous
        config = Config(store_dir=tmp_path, provider="ollama")
        engine = QueryEngine(config)
        filtered = engine._filter_by_access(all_ids, user_role="")
        assert len(filtered) == 1
        # The public CKU should pass
        cku = store.load(filtered[0])
        assert cku.meta.source == "public.md"

    def test_hr_sees_public_and_hr(self, store_with_ckus) -> None:
        store, km, tmp_path = store_with_ckus
        from norag.query.engine import QueryEngine

        all_ids = store.list_all()
        config = Config(store_dir=tmp_path, provider="ollama")
        engine = QueryEngine(config)
        filtered = engine._filter_by_access(all_ids, user_role="hr")
        assert len(filtered) == 2
        sources = {store.load(cid).meta.source for cid in filtered}
        assert "public.md" in sources
        assert "salaries.pdf" in sources

    def test_admin_sees_public_and_admin(self, store_with_ckus) -> None:
        store, km, tmp_path = store_with_ckus
        from norag.query.engine import QueryEngine

        all_ids = store.list_all()
        config = Config(store_dir=tmp_path, provider="ollama")
        engine = QueryEngine(config)
        filtered = engine._filter_by_access(all_ids, user_role="admin")
        assert len(filtered) == 2
        sources = {store.load(cid).meta.source for cid in filtered}
        assert "public.md" in sources
        assert "secrets.md" in sources

    def test_management_sees_public_and_hr(self, store_with_ckus) -> None:
        store, km, tmp_path = store_with_ckus
        from norag.query.engine import QueryEngine

        all_ids = store.list_all()
        config = Config(store_dir=tmp_path, provider="ollama")
        engine = QueryEngine(config)
        filtered = engine._filter_by_access(all_ids, user_role="management")
        assert len(filtered) == 2
        sources = {store.load(cid).meta.source for cid in filtered}
        assert "public.md" in sources
        assert "salaries.pdf" in sources

    def test_unknown_role_sees_only_public(self, store_with_ckus) -> None:
        store, km, tmp_path = store_with_ckus
        from norag.query.engine import QueryEngine

        all_ids = store.list_all()
        config = Config(store_dir=tmp_path, provider="ollama")
        engine = QueryEngine(config)
        filtered = engine._filter_by_access(all_ids, user_role="intern")
        assert len(filtered) == 1
