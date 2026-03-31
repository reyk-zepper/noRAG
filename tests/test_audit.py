"""Unit tests for noRAG audit log."""

from __future__ import annotations

from pathlib import Path

import pytest

from norag.store.audit import AuditLog


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def audit(tmp_path: Path) -> AuditLog:
    return AuditLog(tmp_path / "audit.db")


# ---------------------------------------------------------------------------
# log_compile
# ---------------------------------------------------------------------------


class TestLogCompile:
    def test_returns_event_id(self, audit: AuditLog) -> None:
        eid = audit.log_compile("test.md", "compiled")
        assert isinstance(eid, int)
        assert eid > 0

    def test_stores_source(self, audit: AuditLog) -> None:
        audit.log_compile("doc.pdf", "compiled", user="alice")
        events = audit.list_events()
        assert events[0]["details"]["source"] == "doc.pdf"

    def test_stores_status(self, audit: AuditLog) -> None:
        audit.log_compile("test.md", "skipped")
        events = audit.list_events()
        assert events[0]["details"]["status"] == "skipped"

    def test_stores_roles(self, audit: AuditLog) -> None:
        audit.log_compile("secret.pdf", "compiled", roles=["hr", "management"])
        events = audit.list_events()
        assert events[0]["details"]["roles"] == ["hr", "management"]

    def test_stores_user(self, audit: AuditLog) -> None:
        audit.log_compile("test.md", "compiled", user="bob")
        events = audit.list_events()
        assert events[0]["user"] == "bob"

    def test_empty_user_default(self, audit: AuditLog) -> None:
        audit.log_compile("test.md", "compiled")
        events = audit.list_events()
        assert events[0]["user"] == ""


# ---------------------------------------------------------------------------
# log_query
# ---------------------------------------------------------------------------


class TestLogQuery:
    def test_returns_event_id(self, audit: AuditLog) -> None:
        eid = audit.log_query("What is X?", ["cku-1"], ["doc.md"])
        assert isinstance(eid, int)

    def test_stores_question(self, audit: AuditLog) -> None:
        audit.log_query("How does Y work?", [], [])
        events = audit.list_events()
        assert events[0]["details"]["question"] == "How does Y work?"

    def test_stores_cku_ids(self, audit: AuditLog) -> None:
        audit.log_query("Q?", ["cku-1", "cku-2"], ["a.md", "b.md"])
        events = audit.list_events()
        assert events[0]["details"]["cku_ids"] == ["cku-1", "cku-2"]

    def test_stores_user_role(self, audit: AuditLog) -> None:
        audit.log_query("Q?", [], [], user_role="admin")
        events = audit.list_events()
        assert events[0]["details"]["user_role"] == "admin"

    def test_event_type_is_query(self, audit: AuditLog) -> None:
        audit.log_query("Q?", [], [])
        events = audit.list_events()
        assert events[0]["event"] == "query"


# ---------------------------------------------------------------------------
# list_events
# ---------------------------------------------------------------------------


class TestListEvents:
    def test_empty_log(self, audit: AuditLog) -> None:
        assert audit.list_events() == []

    def test_newest_first(self, audit: AuditLog) -> None:
        audit.log_compile("a.md", "compiled")
        audit.log_compile("b.md", "compiled")
        events = audit.list_events()
        assert events[0]["details"]["source"] == "b.md"
        assert events[1]["details"]["source"] == "a.md"

    def test_filter_by_type(self, audit: AuditLog) -> None:
        audit.log_compile("a.md", "compiled")
        audit.log_query("Q?", [], [])
        audit.log_compile("b.md", "compiled")

        compile_events = audit.list_events(event_type="compile")
        assert len(compile_events) == 2
        query_events = audit.list_events(event_type="query")
        assert len(query_events) == 1

    def test_limit(self, audit: AuditLog) -> None:
        for i in range(10):
            audit.log_compile(f"doc{i}.md", "compiled")
        events = audit.list_events(limit=3)
        assert len(events) == 3

    def test_offset(self, audit: AuditLog) -> None:
        for i in range(5):
            audit.log_compile(f"doc{i}.md", "compiled")
        events = audit.list_events(limit=2, offset=2)
        assert len(events) == 2

    def test_has_timestamp(self, audit: AuditLog) -> None:
        audit.log_compile("test.md", "compiled")
        events = audit.list_events()
        assert "timestamp" in events[0]
        assert "T" in events[0]["timestamp"]  # ISO format


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------


class TestCount:
    def test_empty(self, audit: AuditLog) -> None:
        assert audit.count() == 0

    def test_total(self, audit: AuditLog) -> None:
        audit.log_compile("a.md", "compiled")
        audit.log_query("Q?", [], [])
        assert audit.count() == 2

    def test_by_type(self, audit: AuditLog) -> None:
        audit.log_compile("a.md", "compiled")
        audit.log_compile("b.md", "compiled")
        audit.log_query("Q?", [], [])
        assert audit.count("compile") == 2
        assert audit.count("query") == 1
