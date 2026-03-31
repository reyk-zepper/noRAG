"""Watch command — monitors a directory and recompiles on changes."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

console = Console()

# File suffixes the watcher cares about
WATCHED_SUFFIXES = frozenset({".pdf", ".md", ".markdown"})


def _is_watched(path: Path) -> bool:
    """Return True if *path* is a supported document type."""
    return path.suffix.lower() in WATCHED_SUFFIXES


def watch_cmd(
    source: Path = typer.Argument(..., help="Directory to watch for document changes"),
    store: Path = typer.Option(None, "--store", "-s", help="noRAG store directory (default: .norag)"),
    provider: str = typer.Option(None, "--provider", "-p", help="LLM provider: claude | ollama"),
    model: str = typer.Option(None, "--model", "-m", help="Model name"),
    debounce: int = typer.Option(1000, "--debounce", "-d", help="Debounce delay in ms (default: 1000)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
) -> None:
    """Watch a directory and recompile documents on changes.

    Monitors *source* for .md, .markdown, and .pdf file changes.
    When a change is detected, the file is automatically recompiled.
    Press Ctrl+C to stop.
    """
    from watchfiles import watch, Change

    from norag.config import load_config
    from norag.compiler.engine import CompilerEngine

    if not source.is_dir():
        console.print(f"[red]Error:[/red] Source must be a directory: {source}")
        raise typer.Exit(1)

    # Load config with CLI overrides
    config = load_config()
    if store:
        config.store_dir = store
        config.ckus_dir = store / "ckus"
        config.db_path = store / "knowledge.db"
    if provider:
        config.provider = provider
    if model:
        config.model = model

    engine = CompilerEngine(config)

    console.print(f"[bold]noRAG Watch[/bold] — {config.provider}/{config.model}")
    console.print(f"Watching: {source.resolve()}")
    console.print(f"Debounce: {debounce}ms")
    console.print("[dim]Press Ctrl+C to stop.[/dim]")
    console.print()

    try:
        for changes in watch(
            source,
            debounce=debounce,
            watch_filter=lambda change, path: _is_watched(Path(path)),
        ):
            # Collect unique file paths from the change set
            changed_files: list[Path] = []
            seen: set[str] = set()
            for change_type, file_path in changes:
                if change_type == Change.deleted:
                    continue
                if file_path in seen:
                    continue
                p = Path(file_path)
                if _is_watched(p) and p.is_file():
                    changed_files.append(p)
                    seen.add(file_path)

            if not changed_files:
                continue

            console.print(
                f"[cyan]⟳ Change detected:[/cyan] "
                f"{len(changed_files)} file(s)"
            )

            for file_path in changed_files:
                console.print(f"  [dim]→[/dim] {file_path.relative_to(source)}")

            # Recompile changed files
            for file_path in changed_files:
                try:
                    result = engine.compile(file_path)
                    if result.compiled:
                        console.print(
                            f"  [green]✓ Compiled:[/green] {file_path.name}"
                        )
                    elif result.skipped:
                        console.print(
                            f"  [yellow]○ Skipped:[/yellow] {file_path.name} (unchanged)"
                        )
                    for path, err in result.failed:
                        console.print(f"  [red]✗ Failed:[/red] {path} — {err}")
                except Exception as exc:
                    console.print(
                        f"  [red]✗ Error:[/red] {file_path.name} — {exc}"
                    )

            console.print()

    except KeyboardInterrupt:
        console.print("\n[bold]Watch stopped.[/bold]")
