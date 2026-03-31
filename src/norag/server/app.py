"""noRAG REST API — FastAPI application.

Endpoints:
    GET  /health     — Health check
    GET  /knowledge  — CKU overview and stats
    POST /compile    — Compile a document (file upload)
    POST /query      — Query compiled knowledge
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel, Field

from norag.config import Config, load_config
from norag.compiler.engine import CompilerEngine
from norag.query.engine import QueryEngine
from norag.store import CKUStore, KnowledgeMap


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    question: str
    top_k: int = Field(default=5, ge=1, le=50)


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]
    routed_ckus: list[str]
    token_estimate: int


class CompileResponse(BaseModel):
    status: str  # "compiled" | "skipped" | "failed"
    filename: str
    message: str


class KnowledgeCKU(BaseModel):
    id: str
    source: str
    doc_type: str
    language: str
    entity_count: int
    fact_count: int


class KnowledgeResponse(BaseModel):
    total_ckus: int
    stats: dict
    ckus: list[KnowledgeCKU]


class HealthResponse(BaseModel):
    status: str
    version: str
    provider: str
    model: str


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app(config: Config | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if config is None:
        config = load_config()

    app = FastAPI(
        title="noRAG API",
        description="Knowledge Compiler REST API. Compile documents into machine-optimized knowledge.",
        version="0.3.0",
    )

    # Shared state — engines are created once at startup
    state = {"config": config}

    def _get_compiler() -> CompilerEngine:
        if "compiler" not in state:
            state["compiler"] = CompilerEngine(config)
        return state["compiler"]

    def _get_query_engine() -> QueryEngine:
        if "query_engine" not in state:
            state["query_engine"] = QueryEngine(config)
        return state["query_engine"]

    def _get_store() -> CKUStore:
        return CKUStore(config.ckus_dir)

    def _get_knowledge_map() -> KnowledgeMap:
        return KnowledgeMap(config.db_path)

    # ------------------------------------------------------------------
    # Endpoints
    # ------------------------------------------------------------------

    @app.get("/health", response_model=HealthResponse)
    def health():
        """Health check."""
        return HealthResponse(
            status="ok",
            version="0.3.0",
            provider=config.provider,
            model=config.model,
        )

    @app.get("/knowledge", response_model=KnowledgeResponse)
    def knowledge():
        """List all compiled CKUs and knowledge stats."""
        store = _get_store()
        km = _get_knowledge_map()

        cku_ids = store.list_all()
        ckus: list[KnowledgeCKU] = []
        for cku_id in cku_ids:
            try:
                cku = store.load(cku_id)
                ckus.append(KnowledgeCKU(
                    id=cku_id,
                    source=cku.meta.source,
                    doc_type=cku.meta.type,
                    language=cku.meta.language,
                    entity_count=len(cku.entities),
                    fact_count=len(cku.facts),
                ))
            except Exception:
                continue

        stats = km.get_stats()

        return KnowledgeResponse(
            total_ckus=len(ckus),
            stats=stats,
            ckus=ckus,
        )

    @app.post("/compile", response_model=CompileResponse)
    async def compile_document(
        file: UploadFile = File(...),
        force: bool = False,
    ):
        """Compile an uploaded document into a CKU.

        Accepts .md, .markdown, and .pdf files.
        """
        filename = file.filename or "unknown"
        suffix = Path(filename).suffix.lower()

        if suffix not in {".md", ".markdown", ".pdf"}:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {suffix}. Supported: .md, .markdown, .pdf",
            )

        # Save upload to temp file
        tmp_dir = Path(tempfile.mkdtemp(prefix="norag_"))
        tmp_path = tmp_dir / filename
        try:
            with open(tmp_path, "wb") as f:
                content = await file.read()
                f.write(content)

            engine = _get_compiler()
            result = engine.compile(tmp_path, force=force)

            if result.compiled:
                return CompileResponse(
                    status="compiled",
                    filename=filename,
                    message=f"Successfully compiled {filename}",
                )
            elif result.skipped:
                return CompileResponse(
                    status="skipped",
                    filename=filename,
                    message=f"{filename} is up-to-date, skipped",
                )
            else:
                error_msg = result.failed[0][1] if result.failed else "Unknown error"
                return CompileResponse(
                    status="failed",
                    filename=filename,
                    message=error_msg,
                )
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    @app.post("/query", response_model=QueryResponse)
    def query(req: QueryRequest):
        """Query compiled knowledge."""
        engine = _get_query_engine()
        result = engine.query(req.question, top_k=req.top_k)

        return QueryResponse(
            answer=result.answer,
            sources=result.context.sources,
            routed_ckus=result.routed_ckus,
            token_estimate=result.context.token_estimate,
        )

    return app
