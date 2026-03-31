from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table

console = Console()


def compile_cmd(
    source: Path = typer.Argument(..., help="File or directory to compile"),
    store: Path = typer.Option(None, "--store", "-s", help="noRAG store directory (default: .norag)"),
    provider: str = typer.Option(None, "--provider", "-p", help="LLM provider: claude | ollama"),
    model: str = typer.Option(None, "--model", "-m", help="Model name"),
    force: bool = typer.Option(False, "--force", "-f", help="Recompile even if CKU is up-to-date"),
    roles: str = typer.Option("", "--roles", "-r", help="Access roles (comma-separated, e.g. 'hr,management')"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
) -> None:
    """Compile documents into Compiled Knowledge Units (CKUs)."""
    from norag.config import load_config
    from norag.compiler.engine import CompilerEngine

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

    # Validate source exists
    if not source.exists():
        console.print(f"[red]Error:[/red] Source not found: {source}")
        raise typer.Exit(1)

    console.print(f"[bold]noRAG Compiler[/bold] — {config.provider}/{config.model}")
    console.print(f"Source: {source}")
    console.print()

    # Parse roles
    role_list = [r.strip() for r in roles.split(",") if r.strip()] if roles else []

    # Run compilation
    engine = CompilerEngine(config)
    result = engine.compile(source, force=force, roles=role_list)

    # Print results
    console.print()

    if result.compiled:
        console.print(f"[green]✓ Compiled:[/green] {len(result.compiled)} document(s)")
        if verbose:
            for path in result.compiled:
                console.print(f"  + {path}")

    if result.skipped:
        console.print(f"[yellow]○ Skipped:[/yellow] {len(result.skipped)} (up-to-date)")
        if verbose:
            for path in result.skipped:
                console.print(f"  ~ {path}")

    if result.failed:
        console.print(f"[red]✗ Failed:[/red] {len(result.failed)}")
        for path, err in result.failed:
            console.print(f"  ! {path}: {err}")

    # Summary
    console.print()
    console.print(
        f"[bold]Total:[/bold] {result.total} | "
        f"Compiled: {len(result.compiled)} | "
        f"Skipped: {len(result.skipped)} | "
        f"Failed: {len(result.failed)}"
    )
