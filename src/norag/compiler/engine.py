"""Compiler Engine — orchestrates the full noRAG compile pipeline.

Pipeline per document:
    Parse  →  Compile (LLM)  →  Build CKU  →  Save  →  Index
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

from norag.config import Config
from norag.models.cku import (
    CKU,
    CKUMeta,
    CKUSummary,
    CKUEntity,
    CKUFact,
    CKUVisual,
    SectionSummary,
    Relation,
    SourceRef,
)
from norag.compiler.parsers import get_parser
from norag.compiler.providers import get_provider
from norag.store import CKUStore, KnowledgeMap

logger = logging.getLogger(__name__)
console = Console()

# File types the compiler supports
_SUPPORTED_SUFFIXES = frozenset({".pdf", ".md", ".markdown"})


class CompileResult:
    """Result of a compilation run."""

    def __init__(self) -> None:
        self.compiled: list[str] = []                    # successfully compiled
        self.skipped: list[str] = []                     # up-to-date, skipped
        self.failed: list[tuple[str, str]] = []          # (path, error_message)

    @property
    def total(self) -> int:
        return len(self.compiled) + len(self.skipped) + len(self.failed)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"CompileResult(compiled={len(self.compiled)}, "
            f"skipped={len(self.skipped)}, "
            f"failed={len(self.failed)})"
        )


class CompilerEngine:
    """Orchestrates the noRAG compile pipeline: Parse → Compile → Store → Index."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.store = CKUStore(config.ckus_dir)
        self.knowledge_map = KnowledgeMap(config.db_path)
        provider_kwargs: dict = {"api_key": config.api_key, "model": config.model}
        if config.provider == "ollama":
            provider_kwargs["host"] = config.ollama_host
        self.provider = get_provider(config.provider, **provider_kwargs)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compile(self, source: Path, force: bool = False) -> CompileResult:
        """Compile a file or directory of documents.

        Args:
            source: Path to a single file or a directory of documents.
            force:  If True, recompile even if the CKU is already up-to-date.

        Returns:
            A :class:`CompileResult` describing what was compiled, skipped, or
            failed.

        Raises:
            FileNotFoundError: If *source* does not exist.
        """
        result = CompileResult()

        if source.is_file():
            files = [source]
        elif source.is_dir():
            files = self._collect_files(source)
        else:
            raise FileNotFoundError(f"Source not found: {source}")

        if not files:
            console.print("[yellow]No supported documents found.[/yellow]")
            return result

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
            transient=False,
        ) as progress:
            task_id = progress.add_task("Compiling documents…", total=len(files))

            for file_path in files:
                short_name = file_path.name
                progress.update(task_id, description=f"[bold blue]{short_name}")

                try:
                    compiled = self._compile_single(file_path, force=force)
                    if compiled:
                        result.compiled.append(str(file_path))
                        logger.info("Compiled: %s", file_path)
                    else:
                        result.skipped.append(str(file_path))
                        logger.debug("Skipped (up-to-date): %s", file_path)
                except Exception as exc:
                    error_msg = str(exc)
                    result.failed.append((str(file_path), error_msg))
                    logger.warning("Failed: %s — %s", file_path, error_msg, exc_info=True)
                    console.print(
                        f"[red]  ✗ Failed:[/red] {short_name} — {error_msg}"
                    )
                finally:
                    progress.advance(task_id)

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compile_single(self, path: Path, force: bool = False) -> bool:
        """Compile one document.

        Returns:
            True  — document was (re-)compiled and stored.
            False — document was up-to-date and skipped.
        """
        # 1. Hash source file
        current_hash = CKUStore.compute_hash(path)

        # 2. Skip if up-to-date (unless forced)
        if not force and not self.store.needs_recompile(str(path), current_hash):
            return False

        # 3. Parse document
        parser = get_parser(path)
        parsed = parser.parse(path)

        # 4. Compile via LLM provider
        cku_data = self.provider.compile_document(parsed)

        # 5. Build CKU with meta — handle missing / malformed LLM output
        has_visuals = any(v for p in parsed.pages for v in p.visuals)
        doc_type = (
            f"{parsed.doc_type}/multimodal" if has_visuals else parsed.doc_type
        )

        meta = CKUMeta(
            source=str(path),
            compiled=datetime.now(timezone.utc),
            hash=current_hash,
            type=doc_type,
            language=cku_data.get("language", "en"),
        )

        cku = CKU(
            meta=meta,
            summaries=self._coerce_summaries(cku_data.get("summaries")),
            entities=self._coerce_entities(cku_data.get("entities", [])),
            facts=self._coerce_facts(cku_data.get("facts", [])),
            visuals=self._coerce_visuals(cku_data.get("visuals", [])),
            dependencies=self._coerce_list_of_strings(
                cku_data.get("dependencies", [])
            ),
        )

        # 6. Persist CKU
        self.store.save(cku)

        # 7. Index into knowledge map
        self.knowledge_map.index_cku(cku)

        return True

    # ------------------------------------------------------------------
    # Coercion helpers — make the LLM output tolerant
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce_summaries(raw: object) -> CKUSummary:
        """Build a CKUSummary from LLM output, falling back to empty defaults."""
        if isinstance(raw, dict):
            sections_raw = raw.get("sections", [])
            sections: list[SectionSummary] = []
            if isinstance(sections_raw, list):
                for s in sections_raw:
                    if isinstance(s, dict):
                        try:
                            sections.append(SectionSummary(**s))
                        except Exception:
                            pass
            return CKUSummary(
                document=str(raw.get("document", "")),
                sections=sections,
            )
        return CKUSummary(document="", sections=[])

    @staticmethod
    def _coerce_entities(raw: object) -> list[CKUEntity]:
        """Coerce raw entity list from LLM output."""
        if not isinstance(raw, list):
            return []
        entities: list[CKUEntity] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                relations_raw = item.get("relations", [])
                relations: list[Relation] = []
                if isinstance(relations_raw, list):
                    for r in relations_raw:
                        if isinstance(r, dict):
                            try:
                                relations.append(Relation(**r))
                            except Exception:
                                pass
                entities.append(
                    CKUEntity(
                        id=str(item.get("id", "")),
                        name=str(item.get("name", "")),
                        type=str(item.get("type", "concept")),
                        relations=relations,
                    )
                )
            except Exception:
                pass
        return entities

    @staticmethod
    def _coerce_facts(raw: object) -> list[CKUFact]:
        """Coerce raw facts list from LLM output."""
        if not isinstance(raw, list):
            return []
        facts: list[CKUFact] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                source_raw = item.get("source", {})
                if isinstance(source_raw, dict):
                    source = SourceRef(
                        page=source_raw.get("page"),
                        section=source_raw.get("section"),
                    )
                else:
                    source = SourceRef()

                entities_raw = item.get("entities", [])
                entities = (
                    [str(e) for e in entities_raw]
                    if isinstance(entities_raw, list)
                    else []
                )

                confidence_raw = item.get("confidence", 1.0)
                try:
                    confidence = float(confidence_raw)
                except (TypeError, ValueError):
                    confidence = 1.0

                facts.append(
                    CKUFact(
                        id=str(item.get("id", "")),
                        claim=str(item.get("claim", "")),
                        source=source,
                        confidence=confidence,
                        entities=entities,
                    )
                )
            except Exception:
                pass
        return facts

    @staticmethod
    def _coerce_visuals(raw: object) -> list[CKUVisual]:
        """Coerce raw visuals list from LLM output."""
        if not isinstance(raw, list):
            return []
        visuals: list[CKUVisual] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                source_raw = item.get("source", {})
                if isinstance(source_raw, dict):
                    source = SourceRef(
                        page=source_raw.get("page"),
                        section=source_raw.get("section"),
                    )
                else:
                    source = SourceRef()

                structured = item.get("structured_data")
                if structured is not None and not isinstance(structured, dict):
                    structured = None

                visuals.append(
                    CKUVisual(
                        id=str(item.get("id", "")),
                        type=str(item.get("type", "image")),
                        source=source,
                        description=str(item.get("description", "")),
                        structured_data=structured,
                        context=item.get("context"),
                    )
                )
            except Exception:
                pass
        return visuals

    @staticmethod
    def _coerce_list_of_strings(raw: object) -> list[str]:
        """Safely convert a raw value to a flat list of strings."""
        if not isinstance(raw, list):
            return []
        return [str(item) for item in raw if item is not None]

    # ------------------------------------------------------------------
    # File collection
    # ------------------------------------------------------------------

    @staticmethod
    def _collect_files(directory: Path) -> list[Path]:
        """Recursively collect supported document files, skipping hidden paths.

        Hidden directories (names starting with '.') and hidden files are
        excluded at every level of the tree.
        """
        files: list[Path] = []
        for path in sorted(directory.rglob("*")):
            # Skip hidden files/directories, but only check parts relative to the
            # input directory — not the absolute path (which may itself contain
            # hidden segments like /Users/reykz/.documents/).
            relative_parts = path.relative_to(directory).parts
            if any(part.startswith(".") for part in relative_parts):
                continue
            if path.is_file() and path.suffix.lower() in _SUPPORTED_SUFFIXES:
                files.append(path)
        return files
