"""Unit tests for noRAG REST API server."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from norag.config import Config
from norag.server.app import create_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config(tmp_path: Path) -> Config:
    """Create a Config pointing at a temporary store."""
    return Config(
        store_dir=tmp_path / ".norag",
        provider="ollama",
        model="test-model",
        ollama_host="http://localhost:11434",
    )


@pytest.fixture
def client(config: Config) -> TestClient:
    app = create_app(config)
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_returns_200(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_status_ok(self, client: TestClient) -> None:
        data = client.get("/health").json()
        assert data["status"] == "ok"

    def test_health_shows_provider(self, client: TestClient) -> None:
        data = client.get("/health").json()
        assert data["provider"] == "ollama"

    def test_health_shows_model(self, client: TestClient) -> None:
        data = client.get("/health").json()
        assert data["model"] == "test-model"

    def test_health_shows_version(self, client: TestClient) -> None:
        data = client.get("/health").json()
        assert data["version"] == "1.0.0"


# ---------------------------------------------------------------------------
# GET /knowledge — empty store
# ---------------------------------------------------------------------------


class TestKnowledgeEmpty:
    def test_returns_200(self, client: TestClient) -> None:
        resp = client.get("/knowledge")
        assert resp.status_code == 200

    def test_empty_ckus(self, client: TestClient) -> None:
        data = client.get("/knowledge").json()
        assert data["total_ckus"] == 0
        assert data["ckus"] == []

    def test_empty_stats(self, client: TestClient) -> None:
        data = client.get("/knowledge").json()
        assert data["stats"]["total_ckus"] == 0


# ---------------------------------------------------------------------------
# GET /knowledge — with data
# ---------------------------------------------------------------------------


class TestKnowledgeWithData:
    def test_lists_compiled_ckus(self, client: TestClient, config: Config) -> None:
        """Compile a small doc, then verify /knowledge lists it."""
        from norag.models.cku import CKU, CKUMeta, CKUSummary
        from norag.store import CKUStore, KnowledgeMap
        from datetime import datetime, timezone

        store = CKUStore(config.ckus_dir)
        km = KnowledgeMap(config.db_path)

        cku = CKU(
            meta=CKUMeta(
                source="test.md",
                compiled=datetime.now(timezone.utc),
                hash="abc123",
                type="markdown",
                language="en",
            ),
            summaries=CKUSummary(document="Test document summary"),
        )
        store.save(cku)
        km.index_cku(cku)

        data = client.get("/knowledge").json()
        assert data["total_ckus"] == 1
        assert data["ckus"][0]["source"] == "test.md"
        assert data["ckus"][0]["doc_type"] == "markdown"


# ---------------------------------------------------------------------------
# POST /compile
# ---------------------------------------------------------------------------


class TestCompile:
    def test_rejects_unsupported_type(self, client: TestClient) -> None:
        resp = client.post(
            "/compile",
            files={"file": ("test.txt", b"hello", "text/plain")},
        )
        assert resp.status_code == 400
        assert "Unsupported" in resp.json()["detail"]

    def test_rejects_python_file(self, client: TestClient) -> None:
        resp = client.post(
            "/compile",
            files={"file": ("script.py", b"print(1)", "text/x-python")},
        )
        assert resp.status_code == 400

    @patch("norag.compiler.engine.CompilerEngine.compile")
    def test_compile_markdown_success(self, mock_compile, client: TestClient) -> None:
        from norag.compiler.engine import CompileResult

        result = CompileResult()
        result.compiled.append("test.md")
        mock_compile.return_value = result

        resp = client.post(
            "/compile",
            files={"file": ("test.md", b"# Hello\nWorld", "text/markdown")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "compiled"
        assert data["filename"] == "test.md"

    @patch("norag.compiler.engine.CompilerEngine.compile")
    def test_compile_skipped(self, mock_compile, client: TestClient) -> None:
        from norag.compiler.engine import CompileResult

        result = CompileResult()
        result.skipped.append("test.md")
        mock_compile.return_value = result

        resp = client.post(
            "/compile",
            files={"file": ("test.md", b"# Hello", "text/markdown")},
        )
        data = resp.json()
        assert data["status"] == "skipped"

    @patch("norag.compiler.engine.CompilerEngine.compile")
    def test_compile_failed(self, mock_compile, client: TestClient) -> None:
        from norag.compiler.engine import CompileResult

        result = CompileResult()
        result.failed.append(("test.md", "LLM error"))
        mock_compile.return_value = result

        resp = client.post(
            "/compile",
            files={"file": ("test.md", b"# Hello", "text/markdown")},
        )
        data = resp.json()
        assert data["status"] == "failed"
        assert "LLM error" in data["message"]

    def test_compile_pdf_accepted(self, client: TestClient) -> None:
        """PDF files should be accepted (not rejected at validation)."""
        with patch("norag.compiler.engine.CompilerEngine.compile") as mock:
            from norag.compiler.engine import CompileResult

            result = CompileResult()
            result.compiled.append("doc.pdf")
            mock.return_value = result

            resp = client.post(
                "/compile",
                files={"file": ("doc.pdf", b"%PDF-1.4 fake", "application/pdf")},
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "compiled"


# ---------------------------------------------------------------------------
# POST /query
# ---------------------------------------------------------------------------


class TestQuery:
    def test_query_no_knowledge(self, client: TestClient) -> None:
        """Query with empty store returns helpful message."""
        with patch("norag.query.engine.QueryEngine.query") as mock:
            from norag.query.engine import QueryResult
            from norag.query.assembler import AssembledContext

            mock.return_value = QueryResult(
                answer="No relevant knowledge found.",
                context=AssembledContext(),
                routed_ckus=[],
            )

            resp = client.post("/query", json={"question": "What is noRAG?"})
            assert resp.status_code == 200
            data = resp.json()
            assert "No relevant knowledge" in data["answer"]
            assert data["sources"] == []

    def test_query_with_results(self, client: TestClient) -> None:
        with patch("norag.query.engine.QueryEngine.query") as mock:
            from norag.query.engine import QueryResult
            from norag.query.assembler import AssembledContext

            ctx = AssembledContext()
            ctx.sources = ["docs/test.md"]
            ctx.facts = [{"claim": "noRAG compiles knowledge", "source": {}, "cku_source": "test.md"}]

            mock.return_value = QueryResult(
                answer="noRAG is a knowledge compiler.",
                context=ctx,
                routed_ckus=["test-abc123"],
            )

            resp = client.post("/query", json={"question": "What is noRAG?"})
            assert resp.status_code == 200
            data = resp.json()
            assert "knowledge compiler" in data["answer"]
            assert "docs/test.md" in data["sources"]

    def test_query_custom_top_k(self, client: TestClient) -> None:
        with patch("norag.query.engine.QueryEngine.query") as mock:
            from norag.query.engine import QueryResult
            from norag.query.assembler import AssembledContext

            mock.return_value = QueryResult(
                answer="Answer", context=AssembledContext(), routed_ckus=[],
            )

            resp = client.post("/query", json={"question": "test", "top_k": 10})
            assert resp.status_code == 200
            mock.assert_called_once_with("test", top_k=10, user_role="")

    def test_query_missing_question(self, client: TestClient) -> None:
        resp = client.post("/query", json={})
        assert resp.status_code == 422  # validation error

    def test_query_top_k_too_high(self, client: TestClient) -> None:
        resp = client.post("/query", json={"question": "test", "top_k": 100})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# OpenAPI docs
# ---------------------------------------------------------------------------


class TestDocs:
    def test_openapi_available(self, client: TestClient) -> None:
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["info"]["title"] == "noRAG API"

    def test_docs_page(self, client: TestClient) -> None:
        resp = client.get("/docs")
        assert resp.status_code == 200
