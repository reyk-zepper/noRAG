from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


def query_cmd(
    question: str = typer.Argument(..., help="Natural language question"),
    store: Path = typer.Option(None, "--store", "-s", help="noRAG store directory"),
    provider: str = typer.Option(None, "--provider", "-p", help="LLM provider"),
    model: str = typer.Option(None, "--model", "-m", help="Model name"),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Max CKUs to include in context"),
    show_sources: bool = typer.Option(True, "--sources/--no-sources", help="Show source citations"),
    show_stats: bool = typer.Option(False, "--stats", help="Show query statistics"),
) -> None:
    """Query compiled knowledge. No vectors. No embeddings. Just understanding."""
    from norag.config import load_config
    from norag.query.engine import QueryEngine

    config = load_config()
    if store:
        config.store_dir = store
        config.ckus_dir = store / "ckus"
        config.db_path = store / "knowledge.db"
    if provider:
        config.provider = provider
    if model:
        config.model = model

    # Check if knowledge base exists
    if not config.db_path.exists():
        console.print("[red]Error:[/red] No compiled knowledge found. Run 'norag compile' first.")
        raise typer.Exit(1)

    # Run query
    engine = QueryEngine(config)
    result = engine.query(question, top_k=top_k)

    # Display answer
    console.print()
    console.print(Panel(Markdown(result.answer), title="Answer", border_style="green"))

    # Show sources
    if show_sources and result.context.sources:
        console.print()
        console.print("[bold]Sources:[/bold]")
        for source in result.context.sources:
            console.print(f"  📄 {source}")

    # Show stats
    if show_stats:
        console.print()
        console.print(
            f"[dim]CKUs consulted: {len(result.routed_ckus)} | "
            f"Context tokens: ~{result.context.token_estimate} | "
            f"Provider: {config.provider}/{config.model}[/dim]"
        )
